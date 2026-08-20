import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import TwoSlopeNorm
from scipy import stats
from scipy.optimize import curve_fit
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置
# ============================================================
REPO_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(REPO_DIR, 'data', 'validation')
EMP_DIR   = os.path.join(REPO_DIR, 'data', 'empirical')
OAT_DIR   = os.path.join(REPO_DIR, 'data', 'sensitivity_oat')
OUT_DIR   = os.path.join(REPO_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

SIM_PATH  = os.path.join(DATA_DIR, '1994-2003-table.csv')
REAL_PATH = os.path.join(EMP_DIR, 'real-data1.csv')
EXP_NAME  = '1994-2003'
START_YEAR = 1994

QUARTERLY_BURNIN = 2    # 跳过tick 1-2 (初始化噪声)
QUARTERLY_LAG    = 0
PENSION_LAG      = 0    # no lag
N_RUNS = 100

# 平滑设置：对季度高频变量(GDP, Inflation)做4Q MA
SMOOTH_WINDOW = 4

# ============================================================
# 1. 读取 baseline
# ============================================================
df = pd.read_csv(SIM_PATH, skiprows=6)
real = pd.read_csv(REAL_PATH)

COL = {
    'run':       '[run number]',
    'step':      '[step]',
    'unemp':     'total-unemployment',
    'delta':     'delta-unemployment',
    'young':     'young-unemployment',
    'old':       'old-unemployment',
    'infl':      'Inflation',
    'vacancy':   'vacancy-rate',
    'gdp':       'gdp-growth',
    'loan':      'loan-index',
    'bankrupt':  'bankruptcies-this-tick',
    'pension_g': 'annual-pension-growth',
    'leverage':  'median [leverage] of firms',
}

# ===== 新增：区分"完整数据"(给图1三联图用，可以覆盖到tick 200) 和 "历史窗口数据"(~40 tick，
# 其余所有图表/拟合统计沿用原来的行为，不受影响) =====
THEORY_TICK_MIN = 2     # 图1三联图起点(不含)
THEORY_TICK_MAX = 200   # 图1三联图终点(含)
df_theory = df[(df[COL['step']] > THEORY_TICK_MIN) & (df[COL['step']] <= THEORY_TICK_MAX)].copy()
df = df[df[COL['step']] <= 40].copy()

sim = df.groupby(COL['step']).agg(
    unemp_m=(COL['unemp'],'mean'), unemp_s=(COL['unemp'],'std'),
    young_m=(COL['young'],'mean'), young_s=(COL['young'],'std'),
    old_m  =(COL['old'],'mean'),   old_s  =(COL['old'],'std'),
    infl_m =(COL['infl'],'mean'),  infl_s =(COL['infl'],'std'),
    gdp_m  =(COL['gdp'],'mean'),   gdp_s  =(COL['gdp'],'std'),
    loan_m =(COL['loan'],'mean'),  loan_s =(COL['loan'],'std'),
    bank_m =(COL['bankrupt'],'mean'), bank_s=(COL['bankrupt'],'std'),
    lev_m  =(COL['leverage'],'mean'), lev_s =(COL['leverage'],'std'),
    pen_m  =(COL['pension_g'],'mean'), pen_s=(COL['pension_g'],'std'),
).reset_index()

steps = sim[COL['step']].values

# ============================================================
# 1.5 平滑函数
# ============================================================
def smooth_per_run(df_long, col_name, window=4):
    """
    对每个run分别做rolling mean，再聚合(mean/std across runs)。
    这样SD带反映的是"平滑后路径之间"的离散度，
    而不是用平滑只搞均值线、SD不变那种伪造的"窄SD带"。
    """
    pivot = df_long.pivot(index=COL['step'], columns=COL['run'], values=col_name)
    smoothed = pivot.rolling(window=window, min_periods=1).mean()
    return smoothed.mean(axis=1).values, smoothed.std(axis=1).values

def smooth_series(arr, window=4):
    return pd.Series(arr).rolling(window=window, min_periods=1).mean().values

# ============================================================
# 2. 数据对齐
# ============================================================
bi  = QUARTERLY_BURNIN
lag = QUARTERLY_LAG

s_start = bi; s_end = 40
r_start = s_start + lag; r_end = s_end + lag
if r_start < 0: s_start += (-r_start); r_start = 0
if r_end > 40:  s_end -= (r_end - 40); r_end = 40

nq = s_end - s_start
q_sim_sl  = slice(s_start, s_start + nq)
q_real_sl = slice(r_start, r_start + nq)

q_labels = []
for i in range(r_start, r_start + nq):
    y = START_YEAR + i // 4
    q = i % 4 + 1
    q_labels.append(f'{y}Q{q}')

# --- 原始(raw)序列 ---
q_sim_unemp   = sim['unemp_m'].values[q_sim_sl]
q_sim_unemp_s = sim['unemp_s'].values[q_sim_sl]
q_real_unemp  = real['real unemployment'].values[q_real_sl]

q_sim_infl_raw   = sim['infl_m'].values[q_sim_sl]
q_sim_infl_raw_s = sim['infl_s'].values[q_sim_sl]
q_real_infl_raw  = real['real inflation'].values[q_real_sl]

q_sim_gdp_raw    = sim['gdp_m'].values[q_sim_sl]
q_sim_gdp_raw_s  = sim['gdp_s'].values[q_sim_sl]
q_real_gdp_raw   = real['real rgdp growth'].values[q_real_sl]

# --- 4Q MA 平滑序列 (per-run smoothing) ---
gdp_sm_m, gdp_sm_s   = smooth_per_run(df, COL['gdp'],  window=SMOOTH_WINDOW)
infl_sm_m, infl_sm_s = smooth_per_run(df, COL['infl'], window=SMOOTH_WINDOW)
unemp_sm_m, unemp_sm_s = smooth_per_run(df, COL['unemp'], window=SMOOTH_WINDOW)

q_sim_gdp_sm    = gdp_sm_m[q_sim_sl]
q_sim_gdp_sm_s  = gdp_sm_s[q_sim_sl]
q_sim_infl_sm   = infl_sm_m[q_sim_sl]
q_sim_infl_sm_s = infl_sm_s[q_sim_sl]
q_sim_unemp_sm   = unemp_sm_m[q_sim_sl]
q_sim_unemp_sm_s = unemp_sm_s[q_sim_sl]

q_real_gdp_sm  = smooth_series(real['real rgdp growth'].values, SMOOTH_WINDOW)[q_real_sl]
q_real_infl_sm = smooth_series(real['real inflation'].values, SMOOTH_WINDOW)[q_real_sl]
q_real_unemp_sm = smooth_series(real['real unemployment'].values, SMOOTH_WINDOW)[q_real_sl]

# Pension 对齐: no lag, 1995-2002 (drop 1994 and 2003)
pension_steps_idx = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39]
sim_pen_all_m = sim['pen_m'].values[pension_steps_idx]
sim_pen_all_s = sim['pen_s'].values[pension_steps_idx]
real_pen_all  = real['real pension growth'].dropna().values

pen_sim   = sim_pen_all_m[1:9]
pen_sim_s = sim_pen_all_s[1:9]
pen_real  = real_pen_all[:8]
n_pen     = 8
pen_real_years = list(range(1995, 2003))
pen_labels     = [str(y) for y in pen_real_years]

print(f'Quarterly: burn-in={bi}, lag={lag}, N={nq} points')
print(f'  range: {q_labels[0]} - {q_labels[-1]}')
print(f'Pension: no lag, 1995-2002, N={n_pen} points')
print(f'Smoothing: 4Q MA applied to GDP & Inflation (per-run, then aggregated)')

# ============================================================
# 波动率对比（平滑前后 / sim vs real）
# ============================================================
print('\n--- Volatility comparison (σ) ---')
print(f'{"Variable":<12}{"Real raw":>12}{"Sim raw":>12}{"Real 4QMA":>12}{"Sim 4QMA":>12}{"Sim/Real raw":>14}{"Sim/Real MA":>14}')
for name, rraw, sraw, rsm, ssm in [
    ('GDP',       q_real_gdp_raw, q_sim_gdp_raw, q_real_gdp_sm, q_sim_gdp_sm),
    ('Inflation', q_real_infl_raw, q_sim_infl_raw, q_real_infl_sm, q_sim_infl_sm),
]:
    rraw_sd = np.std(rraw); sraw_sd = np.std(sraw)
    rsm_sd  = np.std(rsm);  ssm_sd  = np.std(ssm)
    print(f'{name:<12}{rraw_sd:>12.5f}{sraw_sd:>12.5f}{rsm_sd:>12.5f}{ssm_sd:>12.5f}'
          f'{sraw_sd/rraw_sd:>14.2f}{ssm_sd/rsm_sd:>14.2f}')

# ============================================================
# 3. 绘图样式
# ============================================================
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.linewidth': 0.7, 'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.direction': 'out', 'ytick.direction': 'out',
})

SIM_C  = '#2C7BB6'
REAL_C = '#D7191C'
LW     = 1.8
FALPHA = 0.15
DCMAP  = 'YlGnBu_r'
HG     = 45

def band(ax, x, m, s, c):
    ax.fill_between(x, m - s, m + s, color=c, alpha=FALPHA)

# ============================================================
# 图1: 理论验证三联图 (改为使用 tick 2-200 的长程数据，其余图表不变)
# ============================================================
print('\n--- 图1: 理论三联图 (tick %d-%d) ---' % (THEORY_TICK_MIN+1, THEORY_TICK_MAX))
fig1, axs1 = plt.subplots(1, 3, figsize=(15, 5))
fig1.suptitle(
    f'Macroeconomic Regularities — Japan {START_YEAR}–{START_YEAR+9}'
    f'\n(N = {N_RUNS} runs × {THEORY_TICK_MAX-THEORY_TICK_MIN} ticks, tick {THEORY_TICK_MIN+1}-{THEORY_TICK_MAX})',
    fontsize=11, fontweight='bold', y=1.02)

xo = df_theory[COL['delta']].values; yo = df_theory[COL['gdp']].values
xu = df_theory[COL['unemp']].values; xv = df_theory[COL['vacancy']].values
xi = df_theory[COL['infl']].values

# Okun
ax = axs1[0]
hb = ax.hexbin(xo, yo, gridsize=HG, cmap=DCMAP, mincnt=1, linewidths=0.2, alpha=0.85)
sl, ic, r, *_ = stats.linregress(xo, yo)
xf = np.linspace(xo.min(), xo.max(), 200)
ax.plot(xf, sl*xf+ic, color=REAL_C, lw=2, zorder=5,
        label=f'Fit: slope = {sl:.3f}\n$R^2$ = {r**2:.3f}')
ax.set_xlabel('Δ Unemployment Rate'); ax.set_ylabel('GDP Growth')
ax.set_title("Okun's Law", fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
fig1.colorbar(hb, ax=ax, fraction=0.046, pad=0.02).set_label('Count', fontsize=8)

# Beveridge
ax = axs1[1]
hb = ax.hexbin(xu, xv, gridsize=HG, cmap=DCMAP, mincnt=1, linewidths=0.2, alpha=0.85)
def expf(x, a, b): return a * np.exp(b * x)
try:
    po, _ = curve_fit(expf, xu, xv, p0=[0.1, -1.5], maxfev=5000)
    xf2 = np.linspace(xu.min(), xu.max(), 200)
    ax.plot(xf2, expf(xf2, *po), color=REAL_C, lw=2, zorder=5,
            label=f'Exp fit: $y={po[0]:.3f}\\,e^{{{po[1]:.3f}x}}$')
except:
    sl2, ic2, *_ = stats.linregress(xu, xv)
    xf2 = np.linspace(xu.min(), xu.max(), 200)
    ax.plot(xf2, sl2*xf2+ic2, color=REAL_C, lw=2, zorder=5)
ax.set_xlabel('Unemployment Rate'); ax.set_ylabel('Vacancy Rate')
ax.set_title('Beveridge Curve', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
fig1.colorbar(hb, ax=ax, fraction=0.046, pad=0.02).set_label('Count', fontsize=8)

# Phillips
ax = axs1[2]
hb = ax.hexbin(xu, xi, gridsize=HG, cmap=DCMAP, mincnt=1, linewidths=0.2, alpha=0.85)
sl3, ic3, r3, *_ = stats.linregress(xu, xi)
xf3 = np.linspace(xu.min(), xu.max(), 200)
ax.plot(xf3, sl3*xf3+ic3, color=REAL_C, lw=2, zorder=5,
        label=f'Fit: slope = {sl3:.3f}\n$R^2$ = {r3**2:.3f}')
ax.set_xlabel('Unemployment Rate'); ax.set_ylabel('Inflation Rate')
ax.set_title('Phillips Curve', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
fig1.colorbar(hb, ax=ax, fraction=0.046, pad=0.02).set_label('Count', fontsize=8)

fig1.tight_layout()
fig1.savefig(f'{OUT_DIR}/{EXP_NAME}_fig1_theory.png', dpi=180, bbox_inches='tight')
print('✓ 图1')

# ============================================================
# 图2 (主图): 模拟vs真实 四联图 — GDP/Inflation 用 4Q MA
# ============================================================
print('\n--- 图2: 模拟 vs 真实 四联图 (GDP/Infl: 4Q MA) ---')
fig2, axs2 = plt.subplots(2, 2, figsize=(14, 10))
fig2.suptitle(
    f'Simulated vs. Real — Japan {START_YEAR}–{START_YEAR+9}'
    f'\n(burn-in = {bi} ticks; GDP, Inflation & Unemployment: 4-quarter moving average; pension: no lag, 1995–2002)',
    fontsize=11, fontweight='bold', y=1.02)

x_q = np.arange(nq)
tick_pos = np.arange(0, nq, 4)

# GDP Growth (4Q MA)
ax = axs2[0, 0]
band(ax, x_q, q_sim_gdp_sm, q_sim_gdp_sm_s, SIM_C)
# 浅色: 原始未平滑 real (作为参考)
ax.plot(x_q, q_real_gdp_raw, color=REAL_C, lw=0.9, ls='-', alpha=0.35,
        label='Real (raw)')
ax.plot(x_q, q_sim_gdp_sm, color=SIM_C, lw=LW, label='Simulated (4Q MA, mean ± SD)')
ax.plot(x_q, q_real_gdp_sm, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5,
        label='Real (4Q MA)')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)
# 对齐 raw 图的 y 轴范围,以便视觉上直接看出平滑效果
gdp_ylim = (
    min(np.min(q_sim_gdp_raw - q_sim_gdp_raw_s), np.min(q_real_gdp_raw)) * 1.1,
    max(np.max(q_sim_gdp_raw + q_sim_gdp_raw_s), np.max(q_real_gdp_raw)) * 1.1,
)
ax.set_ylim(gdp_ylim)
ax.set_ylabel('Growth Rate'); ax.set_title('GDP Growth (4Q MA)', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

# Inflation (4Q MA)
ax = axs2[0, 1]
band(ax, x_q, q_sim_infl_sm, q_sim_infl_sm_s, SIM_C)
# 浅色: 原始未平滑 real (作为参考)
ax.plot(x_q, q_real_infl_raw, color=REAL_C, lw=0.9, ls='-', alpha=0.35,
        label='Real (raw)')
ax.plot(x_q, q_sim_infl_sm, color=SIM_C, lw=LW, label='Simulated (4Q MA, mean ± SD)')
ax.plot(x_q, q_real_infl_sm, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5,
        label='Real (4Q MA)')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)

# 标注: 1997Q2 消费税从3%上调到5% (Hashimoto政府,1997年4月)
try:
    tax_idx = q_labels.index('1997Q2')
    ax.axvline(tax_idx, color='#555555', lw=0.8, ls='--', alpha=0.7, zorder=1)
    ax.text(tax_idx + 0.3, infl_ylim_top := max(np.max(q_sim_infl_raw + q_sim_infl_raw_s),
                                                  np.max(q_real_infl_raw)) * 1.1 * 0.78,
            'Tax hike\n3% → 5%',
            fontsize=7.5, color='#444444', ha='left', va='top',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                      edgecolor='#888888', linewidth=0.5, alpha=0.85))
except ValueError:
    pass  # 1997Q2不在显示范围内则跳过

infl_ylim = (
    min(np.min(q_sim_infl_raw - q_sim_infl_raw_s), np.min(q_real_infl_raw)) * 1.1,
    max(np.max(q_sim_infl_raw + q_sim_infl_raw_s), np.max(q_real_infl_raw)) * 1.1,
)
ax.set_ylim(infl_ylim)
ax.set_ylabel('Inflation Rate'); ax.set_title('Inflation (4Q MA)', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

# Pension (no lag, 1995-2002, 不平滑——已是年度数据)
ax = axs2[1, 0]
x_pen = np.arange(n_pen)
band(ax, x_pen, pen_sim, pen_sim_s, SIM_C)
ax.plot(x_pen, pen_sim, color=SIM_C, lw=LW, marker='s', ms=5,
        label='Simulated (no lag)')
ax.plot(x_pen, pen_real, color=REAL_C, lw=LW, ls='--', marker='o', ms=5, label='Real')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)
ax.set_ylabel('Annual Growth Rate'); ax.set_title('Pension Fund Growth', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(x_pen); ax.set_xticklabels(pen_labels, fontsize=9)

# Unemployment (4Q MA - 与GDP/Inflation方法论一致)
ax = axs2[1, 1]
band(ax, x_q, q_sim_unemp_sm, q_sim_unemp_sm_s, SIM_C)
# 浅蓝色: 原始未平滑 sim (展示平滑效果,因为锯齿主要在sim上)
ax.plot(x_q, q_sim_unemp, color=SIM_C, lw=0.9, ls='-', alpha=0.35,
        label='Simulated (raw)')
ax.plot(x_q, q_sim_unemp_sm, color=SIM_C, lw=LW, label='Simulated (4Q MA, mean ± SD)')
ax.plot(x_q, q_real_unemp, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5,
        label='Real')
# 对齐 raw 图的 y 轴范围
unemp_ylim = (
    min(np.min(q_sim_unemp - q_sim_unemp_s), np.min(q_real_unemp)) * 0.9,
    max(np.max(q_sim_unemp + q_sim_unemp_s), np.max(q_real_unemp)) * 1.05,
)
ax.set_ylim(unemp_ylim)
ax.set_ylabel('Rate'); ax.set_title('Total Unemployment Rate (4Q MA)', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

fig2.tight_layout()
fig2.savefig(f'{OUT_DIR}/{EXP_NAME}_fig2_comparison.png', dpi=180, bbox_inches='tight')
print('✓ 图2 (主图, 4Q MA)')

# ============================================================
# 图2附录: 原始未平滑版本 (备查)
# ============================================================
print('\n--- 图2附录: 原始未平滑版本 ---')
fig2r, axs2r = plt.subplots(2, 2, figsize=(14, 10))
fig2r.suptitle(
    f'Simulated vs. Real (Raw, Unsmoothed) — Japan {START_YEAR}–{START_YEAR+9}'
    f'\n(burn-in = {bi} ticks; pension: no lag, 1995–2002) — Appendix / Robustness',
    fontsize=11, fontweight='bold', y=1.02)

# GDP raw
ax = axs2r[0, 0]
band(ax, x_q, q_sim_gdp_raw, q_sim_gdp_raw_s, SIM_C)
ax.plot(x_q, q_sim_gdp_raw, color=SIM_C, lw=LW, label='Simulated (mean ± SD)')
ax.plot(x_q, q_real_gdp_raw, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5, label='Real')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)
ax.set_ylabel('Growth Rate'); ax.set_title('GDP Growth (raw)', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

# Inflation raw
ax = axs2r[0, 1]
band(ax, x_q, q_sim_infl_raw, q_sim_infl_raw_s, SIM_C)
ax.plot(x_q, q_sim_infl_raw, color=SIM_C, lw=LW, label='Simulated (mean ± SD)')
ax.plot(x_q, q_real_infl_raw, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5, label='Real')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)
ax.set_ylabel('Inflation Rate'); ax.set_title('Inflation (raw)', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

# Pension (同主图)
ax = axs2r[1, 0]
band(ax, x_pen, pen_sim, pen_sim_s, SIM_C)
ax.plot(x_pen, pen_sim, color=SIM_C, lw=LW, marker='s', ms=5, label='Simulated (no lag)')
ax.plot(x_pen, pen_real, color=REAL_C, lw=LW, ls='--', marker='o', ms=5, label='Real')
ax.axhline(0, color='gray', lw=0.6, ls=':', alpha=0.6)
ax.set_ylabel('Annual Growth Rate'); ax.set_title('Pension Fund Growth', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(x_pen); ax.set_xticklabels(pen_labels, fontsize=9)

# Unemployment (同主图)
ax = axs2r[1, 1]
band(ax, x_q, q_sim_unemp, q_sim_unemp_s, SIM_C)
ax.plot(x_q, q_sim_unemp, color=SIM_C, lw=LW, label='Simulated (mean ± SD)')
ax.plot(x_q, q_real_unemp, color=REAL_C, lw=LW, ls='--', marker='o', ms=2.5, label='Real')
ax.set_ylabel('Rate'); ax.set_title('Total Unemployment Rate', fontweight='bold')
ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
ax.grid(True, alpha=0.2, ls='--')
ax.set_xticks(tick_pos)
ax.set_xticklabels([q_labels[i] for i in tick_pos], rotation=45, ha='right', fontsize=8)

fig2r.tight_layout()
fig2r.savefig(f'{OUT_DIR}/{EXP_NAME}_fig2_comparison_raw.png', dpi=180, bbox_inches='tight')
print('✓ 图2附录 (raw, 备查)')

# ============================================================
# 图3: 金融指标三联图
# ============================================================
print('\n--- 图3: 金融三联图 ---')
fig3, axs3 = plt.subplots(1, 3, figsize=(15, 4.5))
fig3.suptitle(
    f'Financial Indicators: Mean of {N_RUNS} Simulations — Japan {START_YEAR}–{START_YEAR+9}',
    fontsize=11, fontweight='bold', y=1.02)

fin_cfg = [
    ('loan_m', 'loan_s', 'Loan Index (relative to initial)'),
    ('bank_m', 'bank_s', 'Bankruptcies per Tick'),
    ('lev_m',  'lev_s',  'Median Leverage (Debt / Assets)'),
]
for ax, (sm, ss, title) in zip(axs3, fin_cfg):
    band(ax, steps, sim[sm].values, sim[ss].values, SIM_C)
    ax.plot(steps, sim[sm].values, color=SIM_C, lw=LW, label='Mean ± SD')
    ax.set_xlabel('Tick (quarter)'); ax.set_ylabel(title.split('(')[0].strip())
    ax.set_title(title, fontweight='bold')
    ax.legend(fontsize=8, framealpha=0.9, edgecolor='#CCC')
    ax.grid(True, alpha=0.2, ls='--')

fig3.tight_layout()
fig3.savefig(f'{OUT_DIR}/{EXP_NAME}_fig3_financial.png', dpi=180, bbox_inches='tight')
print('✓ 图3')

# ============================================================
# 4. 拟合统计表 (raw + 4Q MA 对比)
# ============================================================
print('\n--- 拟合统计 ---')

def theil_u(sv, rv):
    sv = np.asarray(sv, dtype=float); rv = np.asarray(rv, dtype=float)
    num = np.sqrt(np.mean((sv - rv) ** 2))
    den = np.sqrt(np.mean(sv ** 2)) + np.sqrt(np.mean(rv ** 2))
    return num / den if den > 0 else np.nan

def fit_stats(sv, rv, label):
    """返回一行统计: RMSE, MAE, Pearson r (+p), Spearman ρ (+p), Theil U, σ_sim, σ_real, σ_ratio, n"""
    sv = np.asarray(sv, dtype=float); rv = np.asarray(rv, dtype=float)
    n = len(sv)
    rmse = np.sqrt(np.mean((sv - rv) ** 2))
    mae  = np.mean(np.abs(sv - rv))
    if np.std(sv) > 0 and np.std(rv) > 0:
        r, r_p = stats.pearsonr(sv, rv)
        rho, rho_p = stats.spearmanr(sv, rv)
    else:
        r = r_p = rho = rho_p = np.nan
    u = theil_u(sv, rv)
    s_sim, s_real = np.std(sv), np.std(rv)

    def stars(p):
        if np.isnan(p): return ''
        if p < 0.001: return '***'
        if p < 0.01:  return '**'
        if p < 0.05:  return '*'
        return ''

    return {
        'Variable': label,
        'n': n,
        'RMSE': f'{rmse:.5f}',
        'MAE':  f'{mae:.5f}',
        'Pearson r': f'{r:+.3f}{stars(r_p)}',
        'Pearson p': f'{r_p:.4f}',
        'Spearman ρ': f'{rho:+.3f}{stars(rho_p)}',
        'Spearman p': f'{rho_p:.4f}',
        'Theil U': f'{u:.3f}',
        'σ_sim':  f'{s_sim:.5f}',
        'σ_real': f'{s_real:.5f}',
        'σ_sim/σ_real': f'{s_sim/s_real:.2f}' if s_real > 0 else 'NA',
    }

fit_rows = []
# Raw
fit_rows.append(fit_stats(q_sim_gdp_raw,  q_real_gdp_raw,  'GDP (raw)'))
fit_rows.append(fit_stats(q_sim_infl_raw, q_real_infl_raw, 'Inflation (raw)'))
fit_rows.append(fit_stats(q_sim_unemp,    q_real_unemp,    'Unemployment (raw)'))
# Smoothed (4Q MA)
fit_rows.append(fit_stats(q_sim_gdp_sm,   q_real_gdp_sm,   'GDP (4Q MA)'))
fit_rows.append(fit_stats(q_sim_infl_sm,  q_real_infl_sm,  'Inflation (4Q MA)'))
fit_rows.append(fit_stats(q_sim_unemp_sm, q_real_unemp_sm, 'Unemployment (4Q MA)'))
# Annual
fit_rows.append(fit_stats(pen_sim,        pen_real,        'Pension (annual)'))

fit_table = pd.DataFrame(fit_rows)
fit_table.to_csv(f'{OUT_DIR}/{EXP_NAME}_fit_stats.csv', index=False, encoding='utf-8-sig')
print('\nFit statistics:')
print(fit_table.to_string(index=False))

# ============================================================
# 5. RSA: Count-Shift Effect Size (保持原样)
# ============================================================
RSA_FILES = {
    # 把这里替换成你实际的RSA文件路径
    # 'fert-rate':         f'{DATA_DIR}/RSA/fert-rate-table.csv',
    # ...
}

# 如果没有RSA文件，跳过这部分
if not RSA_FILES:
    print('\n(RSA section skipped — no RSA_FILES configured)')
    plt.show()
    print('\n全部完成!')
    raise SystemExit

PARAM_DISPLAY = {
    'fert-rate':          'Fertility Rate',
    'job-applications':   'Job Applications',
    'lend-rate-shift':    'Lend Rate Shift',
    'retirement-ages':    'Retirement Ages',
}

OUTPUT_METRICS = ['Mean Unemployment', 'Mean GDP Growth', 'Mean Inflation', 'Mean Pension Growth']
METRIC_COLS = {
    'Mean Unemployment':   'total-unemployment',
    'Mean GDP Growth':     'gdp-growth',
    'Mean Inflation':      'Inflation',
    'Mean Pension Growth': 'annual-pension-growth',
}

def cohens_d(group1, group2):
    n1, n2 = len(group1), len(group2)
    m1, m2 = group1.mean(), group2.mean()
    s1, s2 = group1.std(ddof=1), group2.std(ddof=1)
    sp = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    if sp == 0: return 0.0
    return (m2 - m1) / sp

def magnitude_label(d_abs):
    if d_abs >= 0.8: return 'L'
    elif d_abs >= 0.5: return 'M'
    elif d_abs >= 0.2: return 'S'
    else: return '·'

level_d_matrix = {}
param_names_ordered = list(RSA_FILES.keys())

for param_name, fpath in RSA_FILES.items():
    rdf = pd.read_csv(fpath, skiprows=6)
    param_col = rdf.columns[1]
    vals = sorted(rdf[param_col].unique())
    lowest, highest = vals[0], vals[-1]
    run_stats_low = rdf[rdf[param_col]==lowest].groupby('[run number]')
    run_stats_high = rdf[rdf[param_col]==highest].groupby('[run number]')
    level_d_matrix[param_name] = {}
    for metric_name, col_name in METRIC_COLS.items():
        low_means  = run_stats_low[col_name].mean().values
        high_means = run_stats_high[col_name].mean().values
        d = cohens_d(low_means, high_means)
        level_d_matrix[param_name][metric_name] = d

print('\nLevel Effect Size (Cohen\'s d):')
for pn in param_names_ordered:
    vals = [f'{level_d_matrix[pn][m]:+.2f}' for m in OUTPUT_METRICS]
    print(f'  {PARAM_DISPLAY[pn]:25s}: {", ".join(vals)}')

print('\n--- Effect Size Heatmap (Count-Shift) ---')

n_params = len(param_names_ordered)
n_metrics = len(OUTPUT_METRICS)
level_matrix = np.zeros((n_params, n_metrics))
for i, pn in enumerate(param_names_ordered):
    for j, mn in enumerate(OUTPUT_METRICS):
        level_matrix[i, j] = level_d_matrix[pn][mn]

def compute_per_run_rmse(rdf, param_col, param_val, real_data, real_col, burn_in=2):
    sub = rdf[rdf[param_col]==param_val]
    rmses = []
    for run_id, run_df in sub.groupby('[run number]'):
        run_df = run_df.sort_values('[step]')
        sim_vals = run_df[real_col].values[burn_in:]
        real_vals = real_data[:len(sim_vals)]
        rmse = np.sqrt(np.mean((sim_vals - real_vals)**2))
        rmses.append(rmse)
    return np.array(rmses)

def compute_per_run_pension_rmse(rdf, param_col, param_val, real_pen_vals):
    sub = rdf[rdf[param_col]==param_val]
    rmses = []
    pension_steps = [4, 8, 12, 16, 20, 24, 28, 32, 36, 40]
    for run_id, run_df in sub.groupby('[run number]'):
        run_df = run_df.sort_values('[step]')
        pen_vals = run_df[run_df['[step]'].isin(pension_steps)]['annual-pension-growth'].values
        s = pen_vals[1:9]
        r_ = real_pen_vals[:8]
        n = min(len(s), len(r_))
        if n < 2:
            rmses.append(np.nan); continue
        rmse = np.sqrt(np.mean((s[:n] - r_[:n])**2))
        rmses.append(rmse)
    return np.array(rmses)

real_unemp_ref = real['real unemployment'].values
real_infl_ref  = real['real inflation'].values
real_gdp_ref   = real['real rgdp growth'].values

RMSE_METRICS = {
    'Unemployment': ('total-unemployment', real_unemp_ref),
    'Inflation':    ('Inflation',          real_infl_ref),
    'GDP Growth':   ('gdp-growth',         real_gdp_ref),
}
RMSE_METRIC_NAMES = ['Unemployment', 'Inflation', 'GDP Growth', 'Pension Growth']

rmse_d_matrix = {}
for param_name, fpath in RSA_FILES.items():
    rdf = pd.read_csv(fpath, skiprows=6)
    param_col = rdf.columns[1]
    vals = sorted(rdf[param_col].unique())
    lowest, highest = vals[0], vals[-1]
    rmse_d_matrix[param_name] = {}
    for metric_name, (col_name, real_ref) in RMSE_METRICS.items():
        low_rmses  = compute_per_run_rmse(rdf, param_col, lowest,  real_ref, col_name, burn_in=QUARTERLY_BURNIN)
        high_rmses = compute_per_run_rmse(rdf, param_col, highest, real_ref, col_name, burn_in=QUARTERLY_BURNIN)
        rmse_d_matrix[param_name][metric_name] = cohens_d(low_rmses, high_rmses)
    low_pen  = compute_per_run_pension_rmse(rdf, param_col, lowest,  real_pen_all)
    high_pen = compute_per_run_pension_rmse(rdf, param_col, highest, real_pen_all)
    low_pen  = low_pen[~np.isnan(low_pen)]
    high_pen = high_pen[~np.isnan(high_pen)]
    rmse_d_matrix[param_name]['Pension Growth'] = cohens_d(low_pen, high_pen)

rmse_matrix = np.zeros((n_params, len(RMSE_METRIC_NAMES)))
for i, pn in enumerate(param_names_ordered):
    for j, mn in enumerate(RMSE_METRIC_NAMES):
        rmse_matrix[i, j] = rmse_d_matrix[pn][mn]

fig_es, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(18, 5))
fig_es.suptitle(
    f"Sensitivity Analysis: Count-Shift Parameters — {EXP_NAME}\n"
    f"Cohen's d: lowest vs. highest parameter level",
    fontweight='bold', fontsize=12, y=1.04)

clip_val = min(max(abs(level_matrix).max(), abs(rmse_matrix).max()), 50)

for ax, matrix, title, metric_names, subtitle in [
    (ax_l, level_matrix, 'Level Effect Size', [m.replace('Mean ','') for m in OUTPUT_METRICS],
     'Positive d = increase raises mean'),
    (ax_r, rmse_matrix,  'RMSE Effect Size',  RMSE_METRIC_NAMES,
     'Positive d = increase worsens fit'),
]:
    clipped = np.clip(matrix, -clip_val, clip_val)
    norm = TwoSlopeNorm(vmin=-clip_val, vcenter=0, vmax=clip_val)
    im = ax.imshow(clipped, cmap='RdBu_r', norm=norm, aspect='auto')
    ax.set_xticks(np.arange(len(metric_names)))
    ax.set_xticklabels(metric_names, fontsize=10)
    ax.set_yticks(np.arange(n_params))
    ax.set_yticklabels([PARAM_DISPLAY[p] for p in param_names_ordered], fontsize=10)
    for i in range(n_params):
        for j in range(len(metric_names)):
            d_val = matrix[i, j]
            mag = magnitude_label(abs(d_val))
            text_color = 'white' if abs(clipped[i, j]) > clip_val * 0.5 else 'black'
            ax.text(j, i, f'{d_val:+.2f}\n({mag})', ha='center', va='center',
                    fontsize=9, fontweight='bold', color=text_color)
    fig_es.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("Cohen's d", fontsize=9)
    ax.set_title(f'{title}\n{subtitle}', fontweight='bold', fontsize=10)

fig_es.tight_layout()
fig_es.savefig(f'{OUT_DIR}/{EXP_NAME}_rsa_count_shift_effect.png', dpi=180, bbox_inches='tight')
print('✓ Count-Shift Effect Size (side-by-side)')

print('\n--- 输出 Effect Size 表格 ---')
level_rows = []
for pn in param_names_ordered:
    row = {'Parameter': PARAM_DISPLAY[pn]}
    for mn in OUTPUT_METRICS:
        d = level_d_matrix[pn][mn]
        mag = magnitude_label(abs(d))
        row[mn.replace('Mean ','')] = f'{d:+.2f} ({mag})'
    level_rows.append(row)
level_table = pd.DataFrame(level_rows)
level_table.to_csv(f'{OUT_DIR}/{EXP_NAME}_level_effect_table.csv', index=False, encoding='utf-8-sig')

rmse_rows = []
for pn in param_names_ordered:
    row = {'Parameter': PARAM_DISPLAY[pn]}
    for mn in RMSE_METRIC_NAMES:
        d = rmse_d_matrix[pn][mn]
        mag = magnitude_label(abs(d))
        row[mn] = f'{d:+.2f} ({mag})'
    rmse_rows.append(row)
rmse_table = pd.DataFrame(rmse_rows)
rmse_table.to_csv(f'{OUT_DIR}/{EXP_NAME}_rmse_effect_table.csv', index=False, encoding='utf-8-sig')

print('\nLevel Effect Size Table:')
print(level_table.to_string(index=False))
print('\nRMSE Effect Size Table:')
print(rmse_table.to_string(index=False))

print('\n✓ 表格已保存')

plt.show()
print('\n全部完成!')
