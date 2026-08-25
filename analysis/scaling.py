"""
Section 5.7: Robustness — Scaling Experiment

Tests whether the model's emergent regularities are invariant to the population
multiplier n* ∈ {1, 2, 4, 8, 16, 32}. Three figures:

  Figure 5.7.1: Scale-invariance check
                Each indicator's end-of-run value vs n*. Bars should be flat
                if scale-invariant.

  Figure 5.7.2: CV scaling
                Coefficient of variation across runs vs n*, on log-log axes.
                Theoretical expectation: CV ~ 1/sqrt(n*) by central limit theorem.

  Figure 5.7.3: Time-series fan charts
                Dependency ratio and unemployment over 40 ticks, mean ± 1σ band
                for each n*. Visual check that trajectories overlap.

Data input (in DATA_DIR):
  - scaling-table-n32.csv   (BehaviorSpace: 6 n* x 100 runs x 40 ticks x 23 reporters)

Outputs (in OUT_DIR):
  - fig13_scaling_invariance.png
  - fig14_scaling_cv_totals.png
  - fig15_scaling_trajectories.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================================================
# 0. Paths
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)                     # CAMPS-Japan/
DATA_DIR = os.path.join(REPO_DIR, "data", "validation")
OUT_DIR = os.path.join(REPO_DIR, "outputs")                # 改这里
os.makedirs(OUT_DIR, exist_ok=True)

SIM_FILE = os.path.join(DATA_DIR, "scaling-table.csv")
OUT_571 = os.path.join(OUT_DIR, "fig13_scaling_invariance.png")
OUT_572 = os.path.join(OUT_DIR, "fig14_scaling_cv_totals.png")
OUT_573 = os.path.join(OUT_DIR, "fig15_scaling_trajectories.png")

# ============================================================
# 1. Load data
# ============================================================

df = pd.read_csv(SIM_FILE, skiprows=6)

# Friendly column rename
# NOTE: the actual BehaviorSpace run reports the built-in `total-unemployment`
# reporter (not the manually-written "employed? = false and age < retirement-age"
# expression) — they are mathematically identical (verified against model source),
# so we just map the column that's actually in the CSV.
# Likewise there is no `sum [pension] of households with [age >= retirement-age]`
# column in this run (it is mathematically identical to the `pension-benefits`
# flow, which wasn't included either); the closest "stock" quantity actually
# collected is `sum [pension-balance] of governments` — the pension system's
# reserve fund balance — which we use for the "pension stock" absolute-scaling
# check instead.
col_map = {
    'count households with [age >= 200] / count households with [age < 200]':
        'dep_ratio',
    'mean [age] of households / 4':
        'mean_age',
    'total-unemployment':
        'unemp_rate',
    'mean [price] of firms':
        'price',
    'mean [productivity] of firms':
        'productivity',
    'mean [wage-offer] of firms':
        'wage',
    'sum [savings] of households / count households':
        'savings_pc',
    'sum [production-capacity] of firms / count households':
        'prod_capacity_pc',
    'mean [income] of households with [employed?]':
        'income_employed',
    'count households':
        'n_households',
    'count firms':
        'n_firms',
    'sum [savings] of households':
        'total_savings',
    'sum [pension-balance] of governments':
        'pension_balance',
}
df = df.rename(columns=col_map)
df['n_star'] = df['n*'].astype(int)
df['run'] = df['[run number]']
df['step'] = df['[step]']

N_STARS = sorted(df['n_star'].unique().tolist())

print(f"Loaded: {df.shape}, n* values: {N_STARS}, "
      f"runs per n*: {df.groupby('n_star')['run'].nunique().iloc[0]}")

# ============================================================
# Indicator definitions
# ============================================================

# Scale-invariant indicators (ratios, rates, per-capita)
INVARIANT_INDICATORS = [
    ('dep_ratio',         'Old-age dependency ratio', 'ratio'),
    ('mean_age',          'Mean age (years)',         'years'),
    ('unemp_rate',        'Unemployment rate',        'rate'),
    ('price',             'Mean firm price',          'level'),
    ('productivity',      'Mean firm productivity',   'level'),
    ('wage',              'Mean wage offer',          'level'),
    ('savings_pc',        'Savings per capita',       'level'),
    ('prod_capacity_pc',  'Production capacity / household', 'level'),
    ('income_employed',   'Mean income (employed)',   'level'),
]

# Absolute levels (sanity check: should scale linearly with n*)
ABSOLUTE_INDICATORS = [
    ('n_households',    'Total households',       'count'),
    ('n_firms',         'Total firms',            'count'),
    ('total_savings',   'Total savings',          'level'),
    ('pension_balance', 'Pension fund balance',   'level'),
]

# ============================================================
# Style
# ============================================================

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 10.5,
    'axes.labelsize': 9.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Color per n* (sequential blue, generated for however many n* values are present)
_cmap = plt.cm.Blues(np.linspace(0.35, 0.95, len(N_STARS)))
NSTAR_COLORS = {n: _cmap[i] for i, n in enumerate(N_STARS)}
INVARIANT_COLOR = '#1f4e79'
ABSOLUTE_COLOR = '#aa3939'

# ============================================================
# 2. FIGURE 5.7.1 — Scale invariance check (last tick)
# ============================================================

# For invariance, use end-of-run values (tick 40), averaged over the last 4 ticks
# of each run to reduce noise (quarterly fluctuation)
df_end = df[df['step'] >= 37].groupby(['n_star', 'run']).mean(numeric_only=True).reset_index()

def panel_invariance(ax, indicator, title, ylabel_unit):
    means, stds = [], []
    for n in N_STARS:
        vals = df_end[df_end['n_star'] == n][indicator].values
        means.append(np.mean(vals))
        stds.append(np.std(vals))
    means = np.array(means)
    stds = np.array(stds)
    x = np.arange(len(N_STARS))

    ax.errorbar(x, means, yerr=stds, fmt='o-', color=INVARIANT_COLOR,
                ecolor='#666666', elinewidth=1, capsize=4,
                markersize=7, linewidth=1.5)
    ax.set_xticks(x); ax.set_xticklabels([f'n*={n}' for n in N_STARS], fontsize=8.5)
    ax.set_ylabel(ylabel_unit, fontsize=8.5)
    ax.set_title(title, fontweight='bold', fontsize=9.5)
    ax.grid(axis='y', alpha=0.25, linewidth=0.5); ax.set_axisbelow(True)

    # Reference line at baseline (middle n*) value
    mid_idx = len(N_STARS) // 2
    baseline_val = means[mid_idx]
    ax.axhline(baseline_val, color='#cccccc', linestyle=':', linewidth=0.8, zorder=0)

    # Compute CV across n* (relative spread of means) — measure of invariance
    rel_spread = np.std(means) / np.mean(means) * 100
    ax.text(0.97, 0.05, f'Rel. spread\nof means: {rel_spread:.1f}%',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='#aaaaaa', alpha=0.85))

fig1, axes1 = plt.subplots(3, 3, figsize=(13, 10))
for ax, (col, title, unit) in zip(axes1.flat, INVARIANT_INDICATORS):
    panel_invariance(ax, col, title, unit)

fig1.suptitle('Scale invariance of emergent indicators\n'
              '(end-of-run mean ± 1σ across 100 runs)',
              fontsize=12, y=1.00)
fig1.tight_layout()
fig1.savefig(OUT_571, dpi=180, bbox_inches='tight', facecolor='white')
print(f'Saved: {OUT_571}')

# ============================================================
# 3. FIGURE 5.7.2 — CV scaling (1/sqrt(n*) check) + absolute sanity
# ============================================================

fig2, axes2 = plt.subplots(1, 2, figsize=(13, 5.4))

# --- 5.7.2 Panel A: CV vs n* (normalised) ---
axA = axes2[0]
n_arr = np.array(N_STARS, dtype=float)

# Exclude near-zero CV indicators (wage, income) — they are driven by exogenous
# time series rather than emergent stochasticity, so their CV reflects only
# floating-point noise and doesn't belong on a 1/sqrt(n*) scaling test.
INVARIANT_FOR_CV = [(c, t, u) for c, t, u in INVARIANT_INDICATORS
                    if c not in ('wage', 'income_employed')]

# Distinct color per indicator
indicator_colors = plt.cm.tab10(np.linspace(0, 1, len(INVARIANT_FOR_CV)))

# Compute and plot CV normalised to CV(n*=min) so all start at 1
fitted_slopes = []
for (col, title, _), color in zip(INVARIANT_FOR_CV, indicator_colors):
    cvs = []
    for n in N_STARS:
        vals = df_end[df_end['n_star'] == n][col].values
        cv = np.std(vals) / abs(np.mean(vals)) * 100 if np.mean(vals) != 0 else 0
        cvs.append(cv)
    cvs = np.array(cvs)
    cvs_norm = cvs / cvs[0]   # normalise to smallest n*

    # Fit slope in log-log space
    slope = np.polyfit(np.log(n_arr), np.log(cvs), 1)[0]
    fitted_slopes.append(slope)

    axA.plot(n_arr, cvs_norm, 'o-', linewidth=1.4, markersize=5.5,
             color=color, alpha=0.85,
             label=f'{title} (slope = {slope:+.2f})')

# Prominent theoretical reference: 1/sqrt(n*), starting at 1
ref = 1.0 / np.sqrt(n_arr / n_arr[0])
axA.plot(n_arr, ref, 'k--', linewidth=2.5, alpha=0.7,
         label=r'Theory: $1/\sqrt{n^{*}}$ (slope = $-0.50$)', zorder=10)

axA.set_xscale('log', base=2)
axA.set_yscale('log')
axA.set_xticks(N_STARS)
axA.set_xticklabels([f'{n}' for n in N_STARS])
axA.set_xlabel('Population multiplier $n^{*}$')
axA.set_ylabel(r'CV($n^{*}$) / CV($n^{*}_{\min}$), log scale')
axA.set_title('A. CV decay — empirical slopes vs $-0.5$ theoretical reference',
              fontweight='bold')
axA.legend(loc='lower left', fontsize=7.8, frameon=False)
axA.grid(alpha=0.25, linewidth=0.5, which='both'); axA.set_axisbelow(True)

# Add annotation summarising slope statistics
mean_slope = np.mean(fitted_slopes)
axA.text(0.97, 0.97,
         f'Mean empirical slope: ${mean_slope:+.2f}$\n'
         f'Theoretical (CLT): $-0.50$',
         transform=axA.transAxes, ha='right', va='top', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.92))

# --- 5.7.2 Panel B: absolute levels — empirical / theoretical ratio ---
# Instead of plotting absolute values (which overlap perfectly on y=x and
# become invisible), we show the ratio of empirical scaling to the perfect
# linear-scaling expectation. Values close to 1.0 indicate exact linear
# scaling; deviations highlight any imperfection in the population-scaling
# logic of the model.
axB = axes2[1]

# Distinct markers per indicator so they remain visible if values coincide
abs_markers = ['o', 's', '^', 'D']
abs_colors = ['#2171b5', '#cc4c02', '#238b45', '#cb181d']

n_max = N_STARS[-1]
n_min = N_STARS[0]
for (col, title, _), marker, color in zip(ABSOLUTE_INDICATORS, abs_markers, abs_colors):
    means = np.array([df_end[df_end['n_star'] == n][col].mean() for n in N_STARS])
    # Empirical scaling ratio relative to smallest n*
    empirical_ratio = means / means[0]
    # Theoretical: should equal n* / n*_min
    deviation = empirical_ratio / (n_arr / n_arr[0])   # 1.0 means perfect linear scaling
    axB.plot(n_arr, deviation, marker=marker, linestyle='-',
             color=color, linewidth=1.5, markersize=8,
             markerfacecolor='white', markeredgewidth=1.8,
             label=f'{title} (n*={n_max}: {means[-1] / means[0]:.2f}x)')

# Reference line at 1.0 (perfect scaling)
axB.axhline(1.0, color='k', linestyle='--', linewidth=1.5, alpha=0.6,
            label='Perfect linear scaling', zorder=0)

# Tight y-axis so even tiny deviations show
axB.set_ylim(0.95, 1.05)
axB.set_xscale('log', base=2)
axB.set_xticks(N_STARS)
axB.set_xticklabels([f'{n}' for n in N_STARS])
axB.set_xlabel('Population multiplier $n^{*}$')
axB.set_ylabel(r'Empirical ratio ÷ $n^{*}$')
axB.set_title('B. Absolute levels — deviation from perfect linear scaling',
              fontweight='bold')
axB.legend(loc='lower left', fontsize=8.2, frameon=False)
axB.grid(alpha=0.25, linewidth=0.5); axB.set_axisbelow(True)

# Annotation summarising max deviation
all_deviations = []
for col, _, _ in ABSOLUTE_INDICATORS:
    means = np.array([df_end[df_end['n_star'] == n][col].mean() for n in N_STARS])
    all_deviations.extend(list((means / means[0]) / (n_arr / n_arr[0])))
max_dev = max(abs(d - 1) for d in all_deviations) * 100
axB.text(0.97, 0.97,
         f'Max deviation from\nperfect scaling: {max_dev:.2f}%',
         transform=axB.transAxes, ha='right', va='top', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.92))

fig2.suptitle('Statistical scaling of variance and linear scaling of totals',
              fontsize=12, y=1.00)
fig2.tight_layout()
fig2.savefig(OUT_572, dpi=180, bbox_inches='tight', facecolor='white')
print(f'Saved: {OUT_572}')

# ============================================================
# 4. FIGURE 5.7.3 — Time series fan charts for key indicators
# ============================================================

# 4 key indicators: dep ratio, unemployment, price, mean income
TS_INDICATORS = [
    ('dep_ratio', 'Old-age dependency ratio'),
    ('unemp_rate', 'Unemployment rate'),
    ('price', 'Mean firm price'),
    ('income_employed', 'Mean income (employed)'),
]

fig3, axes3 = plt.subplots(2, 2, figsize=(13, 8))

for ax, (col, title) in zip(axes3.flat, TS_INDICATORS):
    for n in N_STARS:
        sub = df[df['n_star'] == n].copy()
        # Smooth per run (4-quarter moving average)
        sub[f'{col}_smooth'] = sub.groupby('run')[col].transform(
            lambda x: x.rolling(4, min_periods=1).mean())
        # Aggregate across runs by step
        agg = sub.groupby('step')[f'{col}_smooth'].agg(['mean', 'std']).reset_index()
        steps = agg['step'].values
        # Convert ticks to years (tick 1 = 1994 Q1)
        years = 1994 + (steps - 1) / 4

        ax.fill_between(years, agg['mean'] - agg['std'], agg['mean'] + agg['std'],
                        color=NSTAR_COLORS[n], alpha=0.18)
        ax.plot(years, agg['mean'], color=NSTAR_COLORS[n], linewidth=1.8,
                label=f'n* = {n}')

    ax.set_xlabel('Year')
    ax.set_ylabel(title)
    ax.set_title(title, fontweight='bold')
    ax.grid(alpha=0.25, linewidth=0.5); ax.set_axisbelow(True)
    ax.legend(loc='best', frameon=False, fontsize=8.5)

fig3.suptitle('Trajectory overlap across n* (4-quarter smoothed; band = ±1σ)',
              fontsize=12, y=1.00)
fig3.tight_layout()
fig3.savefig(OUT_573, dpi=180, bbox_inches='tight', facecolor='white')
print(f'Saved: {OUT_573}')

# ============================================================
# Summary report
# ============================================================

print("\n" + "=" * 60)
print("Scaling test summary")
print("=" * 60)
header_cols = "".join(f"{'n=' + str(n):>10s}" for n in N_STARS)
print(f"{'Indicator':<35s} {header_cols} {'spread':>8s}")
for col, title, _ in INVARIANT_INDICATORS:
    means = [df_end[df_end['n_star'] == n][col].mean() for n in N_STARS]
    spread = np.std(means) / np.mean(means) * 100
    print(f"{title:<35s} " + " ".join(f"{m:>10.4f}" for m in means) + f"  {spread:>6.2f}%")

ratio_header = f"n={n_max}/n={n_min}"
print(f"\n{'Indicator':<35s} {header_cols}  {ratio_header:>10s}")
for col, title, _ in ABSOLUTE_INDICATORS:
    means = [df_end[df_end['n_star'] == n][col].mean() for n in N_STARS]
    ratio = means[-1] / means[0]
    print(f"{title:<35s} " + " ".join(f"{m:>10.2f}" for m in means) + f"  {ratio:>8.2f}x")
print(f"\n(Perfect linear scaling would give n={n_max}/n={n_min} = {n_max / n_min:.2f})")

print("\nDone.")
