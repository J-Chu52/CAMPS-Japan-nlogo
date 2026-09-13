#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CAMPS-Japan — 四组双参数响应面 + 年金收支平衡前沿
================================================================================
输入 : data/validation/1994-2003 surf <a> x <b>-table.csv   （四个扫描）
输出 : outputs/fig_<scan>.png            每个扫描一张，四个面板 = 四个目标
       outputs/fig_pension_frontier.png  替代率 × 缴费率平面上的收支平衡等值线
       outputs/surf_runs_collapsed.csv   每次运行一行的压缩表（缓存）

指标口径与 policy_analysis.py / interaction_matrix.py 完全一致：
Unemployment、GDP Growth 取运行内均值，Inflation 取运行内标准差，
Pension Growth 取 [step] > 3 之后的均值。

用法 :  python analysis/surface_figures.py
       python analysis/surface_figures.py --rebuild   # 忽略缓存重读原始 CSV
================================================================================
"""
import argparse, glob, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D            # noqa: F401
from matplotlib import cm
from matplotlib.colors import TwoSlopeNorm

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_DIR, "data", "validation")
OUT_DIR  = os.path.join(REPO_DIR, "outputs")
CACHE    = os.path.join(OUT_DIR, "surf_runs_collapsed.csv")
SKIP_HEADER_ROWS, PENSION_WARMUP_TICKS = 6, 3

FIGNAME = {"mpc x retire":        "fig21_surface_mpc_x_retire.png",
           "mpc x birth":         "fig22_surface_mpc_x_birth.png",
           "mpc x productivity":  "si_surface_mpc_x_productivity.png",
           "replace x retire":    "si_surface_replace_x_retire.png",
           "replace x paygo":     "si_surface_replace_x_paygo.png"}

METRICS = [("GDP Growth", "% per quarter"), ("Unemployment", "%"),
           ("Pension Growth", "% per year"), ("Inflation", "SD, %")]
LAB = {"mpc-income": "MPC out of income", "birth-count-shift": "Birth count shift",
       "productivity-growth-scale": "Productivity growth (scale)",
       "retirement-ages": "Retirement age", "pension-replace-scale": "Replacement rate",
       "paygo-rate-scale": "PAYGO rate (scale)"}
TITLE = {"mpc x birth": "Demand \u00d7 cohort inflow", "mpc x productivity": "Demand \u00d7 supply",
         "mpc x retire": "Demand \u00d7 retirement age", "replace x paygo": "Pension outflow \u00d7 inflow",
         "replace x retire": "Pension outflow \u00d7 retirement age"}

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                     "axes.labelsize": 9, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
                     "axes.titlesize": 10, "axes.titleweight": "bold",
                     "figure.facecolor": "white", "axes.facecolor": "white",
                     "savefig.facecolor": "white"})


def plain3d(ax):
    """去掉三维默认的灰色坐标面，换成白底 + 浅灰网格，与全文其他图一致"""
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.pane.set_facecolor("white")
        a.pane.set_edgecolor("0.80")
        a.pane.set_alpha(1.0)
        a._axinfo["grid"]["color"] = (0.85, 0.85, 0.85, 1.0)
        a._axinfo["grid"]["linewidth"] = 0.5
        a.line.set_color("0.35")


def load(rebuild=False):
    if os.path.exists(CACHE) and not rebuild:
        return pd.read_csv(CACHE)
    frames = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "1994-2003 surf *-table.csv"))):
        scan = os.path.basename(path).replace("1994-2003 surf ", "").replace("-table.csv", "")
        df = pd.read_csv(path, skiprows=SKIP_HEADER_ROWS, low_memory=False)
        cols = list(df.columns); i = cols.index("[step]")
        params = [c for c in cols[:i] if c not in ("[run number]", "run-mode", "simulation-period")]
        rows = []
        for run_id, g in df.groupby("[run number]", sort=True):
            rows.append({"scan": scan, "run": run_id, "px": params[0], "py": params[1],
                         "x": g[params[0]].iloc[0], "y": g[params[1]].iloc[0],
                         "Unemployment": g["total-unemployment"].mean(),
                         "GDP Growth": g["gdp-growth"].mean(),
                         "Inflation": g["Inflation"].std(ddof=1),
                         "Pension Growth": g.loc[g["[step]"] > PENSION_WARMUP_TICKS,
                                                 "annual-pension-growth"].mean()})
        frames.append(pd.DataFrame(rows)); print("loaded %-20s %5d runs" % (scan, len(rows)))
    allf = pd.concat(frames, ignore_index=True)
    os.makedirs(OUT_DIR, exist_ok=True); allf.to_csv(CACHE, index=False)
    return allf


def ticklab(param, vals):
    if param == "retirement-ages":
        return ["%d\n(%d)" % (v, 15 + v / 4) if i % 2 == 0 else "" for i, v in enumerate(vals)]
    if param == "birth-count-shift":
        return ["%+d" % v for v in vals]
    return ["%g" % v if i % 2 == 0 else "" for i, v in enumerate(vals)]


def surfaces(d, scan, fname):
    g = d[d.scan == scan]
    px, py = g.px.iloc[0], g.py.iloc[0]
    fig = plt.figure(figsize=(11.6, 8.8))
    notes = []
    for i, (m, unit) in enumerate(METRICS, 1):
        t = g.groupby(["x", "y"])[m].mean().unstack() * 100
        X = np.array(t.index, float); Y = np.array(t.columns, float)
        XX, YY = np.meshgrid(X, Y, indexing="ij"); Z = t.values
        ax = fig.add_subplot(2, 2, i, projection="3d")
        if m == "Pension Growth" and Z.min() < 0 < Z.max():
            floor = np.percentile(Z, 4)
            if Z.min() < floor - 1:
                notes.append("panel (%s) surface floored at %.1f for legibility; "
                             "true minimum %.1f" % ("abcd"[i - 1], floor, Z.min()))
                Z = np.clip(Z, floor, None)
            kw = dict(cmap=cm.RdBu_r,
                      norm=TwoSlopeNorm(vmin=min(Z.min(), -1e-6), vcenter=0, vmax=Z.max()))
        else:
            kw = dict(cmap=cm.viridis)
        ax.plot_surface(XX, YY, Z, rstride=1, cstride=1, linewidth=.15,
                        edgecolor="0.55", antialiased=True, shade=True, **kw)
        ax.set_xticks(X); ax.set_xticklabels(ticklab(px, X))
        ax.set_yticks(Y); ax.set_yticklabels(ticklab(py, Y))
        ax.set_xlabel(LAB[px], labelpad=12, fontsize=8.5)
        ax.set_ylabel(LAB[py], labelpad=12, fontsize=8.5)
        ax.set_zlabel(""); ax.view_init(elev=24, azim=-132)
        ax.set_title("(%s) %s (%s)" % ("abcd"[i - 1], m, unit), pad=2, fontsize=9.5)
        ax.tick_params(pad=0.5); ax.set_box_aspect((1, 1, .78)); plain3d(ax)
    fig.suptitle(TITLE[scan], y=.975, fontsize=12, fontweight="bold")
    cells = g.groupby(["x", "y"]).ngroups
    reps = int(g.groupby(["x", "y"]).size().iloc[0])
    foot = ("%s: %d x %d grid, %d replications per cell, Japan 1994-2003."
            % (TITLE[scan], t.shape[0], t.shape[1], reps))
    if notes:
        foot += "  " + "; ".join(notes) + "."
    fig.text(.5, .012, foot, ha="center", fontsize=8, style="italic")
    fig.subplots_adjust(left=.02, right=.98, top=.93, bottom=.07, wspace=.02, hspace=.18)
    out = os.path.join(OUT_DIR, fname)
    fig.savefig(out, dpi=600, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("wrote", out)


def _grid(g, metric):
    t = g.groupby(["x", "y"])[metric].mean().unstack() * 100
    return np.array(t.index, float), np.array(t.columns, float), t


def _crossings(P, U):
    """for each x, the y at which pension growth crosses zero, plus unemployment there"""
    xs, ys, us = [], [], []
    yv = np.array(P.columns, float)
    for xi in P.index:
        zv = P.loc[xi].values
        k = np.where(np.diff(np.sign(zv)) != 0)[0]
        if not len(k):
            continue
        k = k[0]; f = -zv[k] / (zv[k + 1] - zv[k]); c = yv[k] + f * (yv[k + 1] - yv[k])
        xs.append(xi); ys.append(c); us.append(np.interp(c, yv, U.loc[xi].values))
    return np.array(xs), np.array(ys), np.array(us)


def frontier(d):
    panels = [("replace x paygo", "PAYGO contribution rate (scale, 1.0 = historical)",
               "(a) Funded by contributions"),
              ("replace x retire", "Retirement age (model age)",
               "(b) Funded by later retirement")]
    fig = plt.figure(figsize=(15.5, 4.8))
    store = {}
    for k, (scan, ylab, ttl) in enumerate(panels):
        g = d[d.scan == scan]
        X, Y, P = _grid(g, "Pension Growth")
        _, _, U = _grid(g, "Unemployment")
        store[scan] = _crossings(P, U)
        XX, YY = np.meshgrid(X, Y, indexing="ij")
        ax = fig.add_subplot(1, 3, k + 1)
        lv = np.array([-30, -20, -15, -10, -6, -3, -1, 0, 1, 3, 6, 9, 12, 15])
        cf = ax.contourf(XX, YY, np.clip(P.values, -30, None), levels=lv, cmap="RdBu_r",
                         norm=TwoSlopeNorm(vmin=-30, vcenter=0, vmax=15), extend="min")
        ax.contour(XX, YY, P.values, levels=lv, colors="0.35", linewidths=.4)
        z = ax.contour(XX, YY, P.values, levels=[0], colors="k", linewidths=2.4)
        ax.clabel(z, fmt={0: " fund balanced "}, fontsize=8.5)
        fig.colorbar(cf, ax=ax, label="Pension fund growth (% per year)", pad=.02)
        ax.set_xlabel("Replacement rate"); ax.set_ylabel(ylab)
        ax.set_title(ttl, fontweight="bold", fontsize=10)
        ax.set_xticks(X); ax.set_yticks(Y); ax.tick_params(labelsize=7)
        if scan == "replace x retire":
            ax.set_yticklabels(["%d (%d)" % (v, 15 + v / 4) for v in Y])

    ax = fig.add_subplot(1, 3, 3)
    for scan, lab, c in [("replace x paygo", "via contribution rate", "#1f6f8b"),
                         ("replace x retire", "via retirement age", "#c1442e")]:
        xs, ys, us = store[scan]
        ax.plot(xs, us, marker="o", ms=4.5, lw=2, color=c, label=lab)
    ax.set_xlabel("Replacement rate")
    ax.set_ylabel("Unemployment rate on the solvency line (%)")
    ax.set_title("(c) What solvency costs in the labour market",
                 fontweight="bold", fontsize=10)
    ax.grid(alpha=.25, lw=.6); ax.legend(frameon=False, fontsize=9)
    fig.text(.5, -.02, "Each line in (c) traces the fund-balanced contour of the matching panel. "
                       "13 replacement rates x 11 levels of the second lever, 30 replications per cell, "
                       "Japan 1994-2003.", ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "fig23_pension_frontiers.png")
    fig.savefig(out, dpi=600, bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("wrote", out)
    for scan, _, ttl in panels:
        xs, ys, us = store[scan]
        print("\n%s" % ttl)
        for a, b, c in zip(xs, ys, us):
            print("   replace %.3f -> %8.3f   unemployment %.2f%%" % (a, b, c))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="忽略缓存，重读原始 CSV")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    d = load(rebuild=args.rebuild)
    for sc, fn in FIGNAME.items():
        surfaces(d, sc, fn)
    frontier(d)
