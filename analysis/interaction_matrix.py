#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CAMPS-Japan — 五参数全因子实验的两两交互强度矩阵 (Figure 18)
================================================================================
对应论文 §6.3.1：

  "each macro indicator was regressed on the five parameters as categorical
   factors together with all ten two-way interaction terms, and the share of
   total variance attributable to each interaction (partial eta-squared) was
   computed by analysis of variance."

输入 : data/validation/complete scan 5x3-table.csv   (243 组合 x 50 重复)
输出 : outputs/fig18_interaction_matrix.png
       outputs/tab18_interaction_matrix.csv          (数值备查)

指标口径与 policy_analysis.py 的 load_and_collapse() 完全一致，
这样 Figure 18 和 §6.3.2 的可行域分析建立在同一组数值上。

方法说明
--------
设计是平衡的 (每个参数组合重复次数相同)，因此 Type I / II / III 平方和
三者等价，可以直接用经典方差分解，不需要 statsmodels：

    SS_A  = n_A  * sum_i  (ybar_i  - ybar)^2
    SS_AB = n_AB * sum_ij (ybar_ij - ybar_i - ybar_j + ybar)^2

只拟合到二阶交互，因此残差里含三阶及以上交互 + 纯重复误差：

    SS_resid = SS_total - sum(SS_main) - sum(SS_2way)

两种效应量都会输出：

    eta^2          = SS_effect / SS_total          <- 论文 Figure 18 报告的就是这个
    partial eta^2  = SS_effect / (SS_effect + SS_resid)

注意：论文 §6.3.1 与 Figure 18 图注写的是 "partial eta-squared"，但同时又说
"percentage of total variance"，而实际报告的数值（如 2.27%）对应的是普通
eta^2。本脚本默认输出 eta^2 以复现论文数值；论文中的术语建议改为 eta^2。

用法 :  python analysis/interaction_matrix.py
       python analysis/interaction_matrix.py --effect peta2     # 换成 partial eta^2
       python analysis/interaction_matrix.py --inflation mean   # 通胀列换成均值
================================================================================
"""

import argparse
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy import stats as _sps
except ImportError:                                   # p 值可选，缺 scipy 也能出图
    _sps = None


# ============================================================================
# 配置
# ============================================================================
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_DIR, "data", "validation")
OUT_DIR = os.path.join(REPO_DIR, "outputs")
CSV_NAME = "complete scan 5x3-table.csv"
SKIP_HEADER_ROWS = 6
PENSION_WARMUP_TICKS = 3                              # 与 policy_analysis.py 一致

PARAMS = ["retirement-ages", "pension-replace-scale", "mpc-income",
          "consumer-choices", "job-applications"]

# 表格/图上显示的参数名（沿用论文 §6.3 的写法）
PARAM_LABEL = {
    "retirement-ages":       "Retirement age",
    "pension-replace-scale": "Replacement rate",
    "mpc-income":            "MPC income",
    "consumer-choices":      "Consumer search",
    "job-applications":      "Job applications",
}

# 图注量级标签：L >= 14%, M 6-14%, S 1-6%, . < 1%
MAG_L, MAG_M, MAG_S = 14.0, 6.0, 1.0

OUT_PNG = os.path.join(OUT_DIR, "fig18_interaction_matrix.png")
OUT_CSV = os.path.join(OUT_DIR, "tab18_interaction_matrix.csv")

# 论文 §6.3.1 里给出的锚点，用来校验口径是否复原正确
ANCHOR = (("retirement-ages", "pension-replace-scale"), "Pension Growth", 2.27)


def magnitude_label(pct):
    if pct >= MAG_L:
        return "L"
    if pct >= MAG_M:
        return "M"
    if pct >= MAG_S:
        return "S"
    return "·"


# ============================================================================
# 1. 读数据，压缩成每次运行一行（口径同 policy_analysis.py）
# ============================================================================
def load_runs(csv_path, inflation="sd"):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"找不到文件：{csv_path}\n"
            f"请确认 complete scan 的 CSV 就在 data/validation/ 下，文件名含空格。")
    print(f"读取 {csv_path} ...")
    df = pd.read_csv(csv_path, skiprows=SKIP_HEADER_ROWS, low_memory=False)
    print(f"  原始 {len(df):,} 行")

    missing = [c for c in PARAMS + ["[run number]", "[step]", "total-unemployment",
                                    "gdp-growth", "Inflation", "annual-pension-growth"]
               if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少列：{missing}")

    rows = []
    for run_id, g in df.groupby("[run number]", sort=True):
        rec = {"run": run_id}
        for p in PARAMS:
            rec[p] = g[p].iloc[0]
        rec["Unemployment"] = g["total-unemployment"].mean()
        rec["GDP Growth"] = g["gdp-growth"].mean()
        rec["Inflation"] = (g["Inflation"].std(ddof=1) if inflation == "sd"
                            else g["Inflation"].mean())
        pen = g.loc[g["[step]"] > PENSION_WARMUP_TICKS, "annual-pension-growth"]
        rec["Pension Growth"] = pen.mean()
        rows.append(rec)

    runs = pd.DataFrame(rows)
    print(f"  压缩成 {len(runs):,} 次运行")
    return runs


# ============================================================================
# 2. 平衡设计下的方差分解
# ============================================================================
def anova_effects(runs, metric):
    """返回 {effect_name: dict(ss, df, eta2, peta2, F, p)}；effect_name 为参数名或参数对。"""
    y = runs[metric].to_numpy(dtype=float)
    if np.isnan(y).any():
        raise ValueError(f"指标 {metric} 含 NaN，无法做 ANOVA")
    n = len(y)
    grand = y.mean()
    ss_total = ((y - grand) ** 2).sum()

    codes = {p: runs[p].to_numpy() for p in PARAMS}
    levels = {p: np.unique(codes[p]) for p in PARAMS}
    for p in PARAMS:
        if len(levels[p]) < 2:
            raise ValueError(f"参数 {p} 在数据里只有一个水平")

    # 平衡性检查：每个五元组合的重复数必须一致
    sizes = runs.groupby(PARAMS).size()
    if sizes.nunique() != 1:
        print(f"  ⚠ 设计不平衡（每格重复数 {sizes.min()}–{sizes.max()}），"
              f"经典方差分解不再等价于 Type III SS，结果仅供参考")
    else:
        print(f"  设计平衡：{len(sizes)} 个组合 × {sizes.iloc[0]} 次重复 = {n:,}")

    eff = {}

    # ---- 主效应 ----
    means1 = {}
    for p in PARAMS:
        m = {lv: y[codes[p] == lv].mean() for lv in levels[p]}
        cnt = {lv: (codes[p] == lv).sum() for lv in levels[p]}
        means1[p] = m
        ss = sum(cnt[lv] * (m[lv] - grand) ** 2 for lv in levels[p])
        eff[p] = {"ss": ss, "df": len(levels[p]) - 1}

    # ---- 两两交互 ----
    for a, b in itertools.combinations(PARAMS, 2):
        ss = 0.0
        for la in levels[a]:
            for lb in levels[b]:
                mask = (codes[a] == la) & (codes[b] == lb)
                k = mask.sum()
                if k == 0:
                    continue
                cell = y[mask].mean()
                ss += k * (cell - means1[a][la] - means1[b][lb] + grand) ** 2
        eff[(a, b)] = {"ss": ss, "df": (len(levels[a]) - 1) * (len(levels[b]) - 1)}

    # ---- 残差（含三阶及以上交互）----
    ss_model = sum(v["ss"] for v in eff.values())
    df_model = sum(v["df"] for v in eff.values())
    ss_resid = ss_total - ss_model
    df_resid = n - 1 - df_model
    ms_resid = ss_resid / df_resid

    for k, v in eff.items():
        v["eta2"] = 100.0 * v["ss"] / ss_total
        v["peta2"] = 100.0 * v["ss"] / (v["ss"] + ss_resid)
        v["F"] = (v["ss"] / v["df"]) / ms_resid
        v["p"] = (float(_sps.f.sf(v["F"], v["df"], df_resid))
                  if _sps is not None else float("nan"))

    eff["_resid"] = {"ss": ss_resid, "df": df_resid}
    eff["_total"] = {"ss": ss_total, "df": n - 1}
    return eff


# ============================================================================
# 3. 画图
# ============================================================================
def plot_matrix(mat, pair_labels, metrics, effect_name, out_png, n_runs, n_cells, n_reps):
    n_rows = len(pair_labels)
    fig, ax = plt.subplots(figsize=(11, max(4.5, n_rows * 0.52)))

    vmax = max(mat.max(), MAG_S * 2)
    im = ax.imshow(mat, cmap="Reds", vmin=0, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(pair_labels, fontsize=9)

    for i in range(n_rows):
        for j in range(len(metrics)):
            val = mat[i, j]
            colour = "white" if val > vmax * 0.55 else "black"
            ax.text(j, i, f"{val:.2f}%\n({magnitude_label(val)})",
                    ha="center", va="center", fontsize=8,
                    fontweight="bold", color=colour)

    label = ("Partial $\\eta^2$" if effect_name == "peta2" else "$\\eta^2$")
    fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02).set_label(
        f"{label} (% of variance)", fontsize=9)
    ax.set_title(
        "Two-Parameter Interaction Strength — Five-Parameter Factorial Experiment\n"
        f"{label}, Japan 1994–2003 "
        f"({n_cells} combinations × {n_reps} replications = {n_runs:,} runs)",
        fontweight="bold", fontsize=11, pad=12)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\n  ✓ 保存图：{os.path.basename(out_png)}")


# ============================================================================
# 主流程
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--effect", choices=["eta2", "peta2"], default="eta2",
                    help="图上用 eta^2（默认，与论文报告的数值一致）还是 partial eta^2")
    ap.add_argument("--inflation", choices=["sd", "mean"], default="sd",
                    help="通胀列用波动率（默认，与 §6.3.2 的筛选口径一致）还是均值")
    ap.add_argument("--input", default=os.path.join(DATA_DIR, CSV_NAME))
    ap.add_argument("--out-png", default=OUT_PNG)
    ap.add_argument("--out-csv", default=OUT_CSV)
    args = ap.parse_args()

    runs = load_runs(args.input, inflation=args.inflation)
    sizes = runs.groupby(PARAMS).size()
    n_cells, n_reps = len(sizes), int(sizes.iloc[0])

    metrics = ["Unemployment", "GDP Growth", "Inflation", "Pension Growth"]
    pairs = list(itertools.combinations(PARAMS, 2))

    results, records = {}, []
    for m in metrics:
        print(f"\n=== ANOVA: {m} ===")
        eff = anova_effects(runs, m)
        results[m] = eff
        r2 = 100.0 * (eff["_total"]["ss"] - eff["_resid"]["ss"]) / eff["_total"]["ss"]
        print(f"  模型解释 {r2:.1f}% 的总变异（主效应 + 十个二阶交互）")
        for key, v in eff.items():
            if key in ("_resid", "_total"):
                continue
            name = (f"{PARAM_LABEL[key[0]]} × {PARAM_LABEL[key[1]]}"
                    if isinstance(key, tuple) else PARAM_LABEL[key])
            records.append({
                "Effect": name,
                "Type": "interaction" if isinstance(key, tuple) else "main",
                "Metric": m, "SS": v["ss"], "df": v["df"],
                "eta2_pct": v["eta2"], "partial_eta2_pct": v["peta2"],
                "F": v["F"], "p": v["p"],
            })

    # ---------------- 矩阵：行=参数对，列=指标 ----------------
    key = args.effect
    mat = np.array([[results[m][p][key] for m in metrics] for p in pairs])
    order = np.argsort(-mat.max(axis=1))            # 按最大交互强度排序（图注要求）
    mat, pairs_sorted = mat[order], [pairs[i] for i in order]
    labels = [f"{PARAM_LABEL[a]} × {PARAM_LABEL[b]}" for a, b in pairs_sorted]

    print(f"\n=== 交互强度矩阵（{'partial eta^2' if key=='peta2' else 'eta^2'}, %）===")
    hdr = f"  {'Pair':<38}" + "".join(f"{m:>17}" for m in metrics)
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    for lab, row in zip(labels, mat):
        print(f"  {lab:<38}" + "".join(f"{v:>12.2f} ({magnitude_label(v)})" for v in row))

    # ---------------- 锚点校验 ----------------
    (pa, pb), am, aval = ANCHOR
    got = results[am][(pa, pb) if (pa, pb) in results[am] else (pb, pa)][key]
    ok = abs(got - aval) < 0.05
    print(f"\n=== 口径校验（论文 §6.3.1 报告 {PARAM_LABEL[pa]} × {PARAM_LABEL[pb]} "
          f"对 {am} 的值为 {aval}%）===")
    print(f"  本次算得 {got:.2f}%  →  {'✓ 一致，口径复原正确' if ok else '✗ 不一致，见下方提示'}")
    if not ok:
        alt = results[am][(pa, pb) if (pa, pb) in results[am] else (pb, pa)]
        print(f"  参考：eta^2 = {alt['eta2']:.2f}% / partial eta^2 = {alt['peta2']:.2f}%")
        print("  若两者都对不上，依次尝试： --effect eta2 / --inflation mean，"
              "或确认养老金暖机 tick 数、是否该先对重复取平均。")
    biggest = max(range(len(pairs_sorted)),
                  key=lambda i: mat[i][metrics.index(am)])
    print(f"  该指标上最强的交互项：{labels[biggest]} "
          f"({mat[biggest][metrics.index(am)]:.2f}%)")

    # ---------------- 输出 ----------------
    out = pd.DataFrame(records)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    out.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    print(f"\n  ✓ 保存表：{os.path.basename(args.out_csv)}")

    plot_matrix(mat, labels, metrics, key, args.out_png,
                len(runs), n_cells, n_reps)

    inter = out[out.Type == "interaction"]
    if _sps is not None and len(inter):
        print(f"\n  十个交互项的 p 值上界：{inter['p'].max():.2e} "
              f"({'全部 p < 0.001，与图注一致' if inter['p'].max() < 1e-3 else '注意：并非全部 p < 0.001，图注需要修改'})")
    print("\n全部完成!")


if __name__ == "__main__":
    main()
