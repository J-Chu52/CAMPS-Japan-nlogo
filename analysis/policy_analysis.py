#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
ABM-OLG 政策模拟分析脚本
================================================================================
作用：读取 NetLogo BehaviorSpace 导出的五参数扫描 CSV，
      找出能同时满足以下四个目标的参数组合（"可行政策"）：
        主目标：失业率 低于现实基准（要改善）
        约束1：实际 GDP 增长 ≥ 0（不衰退）
        约束2：养老金增长 ≥ 0（养老金不萎缩）
        约束3：通胀波动 ≤ 阈值（不剧烈波动）

用法：
      1. 修改下面【配置区】的 DATA_DIR / OUT_DIR / CSV_NAME
      2. 运行：  python policy_analysis.py
      3. 跑完会：①把图和清单存到 OUT_DIR  ②在屏幕上弹窗显示两张图

依赖：  pip install pandas numpy matplotlib
================================================================================
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt          # 注意：不再强制 Agg，这样才能弹窗显示
from matplotlib.gridspec import GridSpec

# ============================================================================
# 【配置区】—— 你主要改这里
# ============================================================================
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_DIR, 'data', 'validation')   
OUT_DIR  = os.path.join(REPO_DIR, 'outputs')
CSV_NAME = "complete scan 5x3-table.csv"

SHOW_PLOTS = True   # True=跑完弹窗显示图；False=只存文件不弹窗

# 五个被扫描的参数（NetLogo 变量名，必须和 CSV 列名完全一致）
PARAMS = ["retirement-ages", "pension-replace-scale", "mpc-income",
          "consumer-choices", "job-applications"]

# 现实世界基准点（你的真实日本参数值）—— 用来当对照基线
BASELINE = {"retirement-ages": 181, "pension-replace-scale": 0.6,
            "mpc-income": 0.85, "consumer-choices": 4, "job-applications": 4}

# 养老金是"年度"指标，前几个 tick（季度）还没攒满一年、恒为0，算均值时要剔除
PENSION_WARMUP_TICKS = 3

# 通胀"不剧烈波动"阈值 = 基准通胀波动 × 这个倍数。1.5=允许比现实大50%；改小则更严
INFLATION_SD_MULTIPLIER = 1.5

# NetLogo BehaviorSpace 的 CSV 前 6 行是元数据，第 7 行才是列名
SKIP_HEADER_ROWS = 6

# 自动拼出完整路径
CSV_PATH = os.path.join(DATA_DIR, CSV_NAME)


# ============================================================================
# 第 1 步：读数据，把每一次运行(run)压缩成"四个指标的一组数值"
# ============================================================================
def load_and_collapse(csv_path):
    print(f"读取 {csv_path} ...")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"找不到文件：{csv_path}\n"
            f"请检查 DATA_DIR 和 CSV_NAME 是否正确（特别注意文件名里是空格还是下划线）。")
    df = pd.read_csv(csv_path, skiprows=SKIP_HEADER_ROWS)
    print(f"  原始数据 {len(df)} 行")

    records = []
    for run_id, g in df.groupby("[run number]"):       # 按运行编号分组
        rec = {"run": run_id}
        for p in PARAMS:                               # 记下这次用的参数值
            rec[p] = g[p].iloc[0]
        rec["Unemployment"]   = g["total-unemployment"].mean()
        rec["GDP_growth"]     = g["gdp-growth"].mean()
        rec["Inflation_mean"] = g["Inflation"].mean()
        rec["Inflation_sd"]   = g["Inflation"].std(ddof=1)     # 波动=标准差
        pension = g.loc[g["[step]"] > PENSION_WARMUP_TICKS, "annual-pension-growth"]
        rec["Pension_growth"] = pension.mean()                 # 剔除暖机后取均值
        records.append(rec)

    runs = pd.DataFrame(records)
    print(f"  压缩成 {len(runs)} 次运行")
    return runs


# ============================================================================
# 第 2 步：把"同一组参数的多次重复"平均成一个代表值
# ============================================================================
def average_replications(runs):
    cell = runs.groupby(PARAMS).mean(numeric_only=True).reset_index()
    print(f"  按参数组合平均后 {len(cell)} 个组合")
    return cell


# ============================================================================
# 第 3 步：找到现实基准格的指标值
# ============================================================================
def get_baseline_row(cell):
    mask = np.ones(len(cell), dtype=bool)
    for p, v in BASELINE.items():
        mask &= (cell[p] == v)
    if mask.sum() == 0:
        raise ValueError("在数据里找不到 BASELINE 指定的参数组合，请检查 BASELINE 的值是否在扫描档位中。")
    base = cell[mask].iloc[0]
    print("\n=== 现实基准 ===")
    print(f"  失业       = {base['Unemployment']*100:.2f}%")
    print(f"  GDP增长    = {base['GDP_growth']*100:+.3f}%")
    print(f"  养老金增长 = {base['Pension_growth']*100:+.2f}%")
    print(f"  通胀波动SD = {base['Inflation_sd']*100:.3f}%")
    return base


# ============================================================================
# 第 4 步：政策筛选 —— 四个条件全满足才算"可行"
# ============================================================================
def screen_policies(cell, base):
    unemp_cap = base["Unemployment"]
    infl_cap  = base["Inflation_sd"] * INFLATION_SD_MULTIPLIER
    feasible = cell[
        (cell["Unemployment"]   <  unemp_cap) &   # 主目标：失业改善
        (cell["GDP_growth"]     >= 0) &           # 约束1：GDP不衰退
        (cell["Pension_growth"] >= 0) &           # 约束2：养老金不萎缩
        (cell["Inflation_sd"]   <= infl_cap)      # 约束3：通胀不剧烈波动
    ].copy().sort_values("Unemployment").reset_index(drop=True)
    print(f"\n=== 可行解：{len(feasible)} / {len(cell)} 个组合满足全部目标 ===")
    print(f"    (通胀波动阈值 = 基准×{INFLATION_SD_MULTIPLIER} = {infl_cap*100:.3f}%)")
    return feasible


# ============================================================================
# 第 5 步：画图1 —— 可行解的参数分布（每个旋钮该往哪拧）
# ============================================================================
def plot_distribution(feasible, cell, outpath):
    labels = ["Retirement Age", "Replace Rate", "MPC-Income",
              "Consumer Search", "Job Applications"]
    levmap = {p: sorted(cell[p].unique()) for p in PARAMS}

    fig, axes = plt.subplots(1, 5, figsize=(20, 4.3))
    fig.suptitle(f"Feasible policies: {len(feasible)} of {len(cell)} meet all four goals "
                 f"· red dashed = baseline", fontsize=13, fontweight="bold")
    ymax = max((feasible[p] == l).sum() for p in PARAMS for l in levmap[p]) + 4
    for ax, p, lab in zip(axes, PARAMS, labels):
        levs = levmap[p]
        counts = [(feasible[p] == l).sum() for l in levs]
        bars = ax.bar(range(len(levs)), counts, color="#4C72B0",
                      edgecolor="black", linewidth=0.6)
        ax.set_xticks(range(len(levs)))
        ax.set_xticklabels([f"{l:g}" for l in levs], fontsize=11)
        ax.set_title(lab, fontsize=12, fontweight="bold")
        ax.set_ylim(0, ymax)
        for b, c in zip(bars, counts):
            ax.text(b.get_x()+b.get_width()/2, c+0.4, str(c),
                    ha="center", fontsize=9, fontweight="bold")
        if BASELINE[p] in levs:
            ax.axvline(levs.index(BASELINE[p]), color="red", ls="--",
                       alpha=0.7, linewidth=2)
        if p == PARAMS[0]:
            ax.set_ylabel("# feasible", fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(outpath, dpi=140, bbox_inches="tight")
    print(f"  已保存图：{outpath}")
    return fig


# ============================================================================
# 第 6 步：画图2 —— 每个可行解相对基准的"收益与代价"
# ============================================================================
def plot_vs_baseline(feasible, base, outpath):
    f = feasible.copy()
    f["d_unemp"]  = (f["Unemployment"]   - base["Unemployment"])   * 100
    f["d_pens"]   = (f["Pension_growth"] - base["Pension_growth"]) * 100
    f["d_gdp"]    = (f["GDP_growth"]     - base["GDP_growth"])     * 100
    f["d_inflsd"] = (f["Inflation_sd"]   - base["Inflation_sd"])   * 100
    f = f.sort_values("d_unemp").reset_index(drop=True)
    n = len(f); y = np.arange(n)

    fig = plt.figure(figsize=(16, max(6, n*0.4)))
    gs = GridSpec(1, 4, width_ratios=[1.5, 1, 1, 1], wspace=0.32)
    fig.suptitle("What each feasible policy buys, and at what cost (vs. baseline)",
                 fontsize=13, fontweight="bold", y=0.99)

    ax1 = fig.add_subplot(gs[0])
    reduction = -f["d_unemp"].values
    ax1.barh(y, reduction, color="#2a9d4a", edgecolor="black", linewidth=0.4)
    ax1.set_title("UNEMPLOYMENT REDUCTION", fontsize=11, fontweight="bold", color="#1a5")
    ax1.set_xlabel("pp below baseline", fontsize=9)
    ax1.invert_yaxis()
    row_labels = [f"R{int(r['retirement-ages'])}/p{r['pension-replace-scale']:.2f}"
                  f"/M{r['mpc-income']:.2f}/Z{int(r['consumer-choices'])}/J{int(r['job-applications'])}"
                  for _, r in f.iterrows()]
    ax1.set_yticks(y)
    ax1.set_yticklabels(row_labels, fontsize=7, fontfamily="monospace")

    def side_panel(gs_i, vals, title, good_dir):
        ax = fig.add_subplot(gs_i, sharey=ax1)
        colors = ["#2a9d4a" if v*good_dir > 0 else "#c0392b" for v in vals]
        ax.barh(y, vals, color=colors, edgecolor="black", linewidth=0.4)
        ax.axvline(0, color="black", lw=1)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("pp vs baseline", fontsize=9)
        plt.setp(ax.get_yticklabels(), visible=False)

    side_panel(gs[1], f["d_pens"].values,   "PENSION GROWTH\n(cost if red)", +1)
    side_panel(gs[2], f["d_gdp"].values,    "GDP GROWTH",                    +1)
    side_panel(gs[3], f["d_inflsd"].values, "INFL. VOLATILITY\n(cost if red)", -1)

    fig.text(0.5, 0.01, "Green = better than baseline · Red = worse (but still feasible)",
             ha="center", fontsize=9, style="italic")
    fig.savefig(outpath, dpi=140, bbox_inches="tight")
    print(f"  已保存图：{outpath}")
    return fig


# ============================================================================
# 主流程
# ============================================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)        # 输出文件夹不存在就自动创建

    runs = load_and_collapse(CSV_PATH)
    cell = average_replications(runs)
    base = get_baseline_row(cell)
    feasible = screen_policies(cell, base)

    # 保存可行解清单
    out = feasible.copy()
    for c in ["Unemployment", "GDP_growth", "Pension_growth",
              "Inflation_mean", "Inflation_sd"]:
        out[c] = (out[c] * 100).round(3)
    csv_out = os.path.join(OUT_DIR, "my_feasible_policies.csv")
    out.to_csv(csv_out, index=False)
    print(f"  已保存清单：{csv_out}")

    # 画两张图（同时存文件）
    fig1 = plot_distribution(feasible, cell,
                             os.path.join(OUT_DIR, "my_feasible_distribution.png"))
    fig2 = plot_vs_baseline(feasible, base,
                            os.path.join(OUT_DIR, "my_feasible_vs_baseline.png"))

    # 打印最优解
    if len(feasible) > 0:
        b = feasible.iloc[0]
        print("\n=== 失业最低的可行解 ===")
        print(f"  退休年龄={b['retirement-ages']:.0f}  替代率={b['pension-replace-scale']}  "
              f"MPC={b['mpc-income']}  消费={b['consumer-choices']:.0f}  求职={b['job-applications']:.0f}")
        print(f"  失业={b['Unemployment']*100:.2f}%  GDP={b['GDP_growth']*100:+.3f}%  "
              f"养老金={b['Pension_growth']*100:+.2f}%  通胀波动={b['Inflation_sd']*100:.3f}%")

    print("\n完成！")

    # 弹窗显示图（放在最后，关掉窗口脚本才结束）
    if SHOW_PLOTS:
        print("（正在弹出图窗，关闭窗口即可结束程序）")
        plt.show()


if __name__ == "__main__":
    main()
