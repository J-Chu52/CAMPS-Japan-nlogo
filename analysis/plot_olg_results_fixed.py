"""
OLG Necessity Experiment: Visualization Script (v4)
====================================================
Generates 3 paper-ready figures from BehaviorSpace CSV output, covering all 5
demographic scenarios (Japan baseline, Uniform, India, China, Finland).

Default paths (edit DATA_DIR / OUT_DIR in CONFIG section if needed):
    Input:  /Users/sonatachu/Downloads/4.17/olg check-table.csv
    Output: /Users/sonatachu/Downloads/4.17/outputs/

Usage:
    python plot_olg_results.py                        # use defaults
    python plot_olg_results.py path/to/your-csv.csv   # override input

Outputs:
    fig_demographic_setup.png - Panels A-E: population pyramids for all 5 scenarios.
                                 Panel F: dependency ratio evolution, 1994-2003.
    fig1_pension_core.png     - Core OLG necessity evidence (1995-2002, 4 subplots)
    fig3_macro.png            - Macroeconomic outcomes (3 subplots, no loan index)
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Patch


# ============================================================
# CONFIG
# ============================================================
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_DIR, 'data', 'validation')
OUT_DIR  = os.path.join(REPO_DIR, 'outputs')

# Default CSV: 4.17/olg_check-table.csv. Override by passing path as argv[1].
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA_DIR, 'olg check-table.csv')
OUTPUT_DIR = OUT_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

mpl.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'legend.fontsize': 10,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 120,
    'savefig.dpi': 200,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Canonical scenario order, colors, and display labels. All plotting functions
# loop over whichever of these scenarios are actually present in the loaded data,
# so the script degrades gracefully if a run only has a subset of scenarios.
SCENARIOS = ['1994-2003', '1994-2003 uniform', '1994-2003 India', '1994-2003 China', '1994-2003 Finland']
COLORS = {
    '1994-2003': '#1F4E79',
    '1994-2003 uniform': '#C00000',
    '1994-2003 India': '#2E8B57',
    '1994-2003 China': '#E08214',
    '1994-2003 Finland': '#7B3F9E',
}
LABELS = {
    '1994-2003': 'Japan (1994 actual)',
    '1994-2003 uniform': 'Uniform (counterfactual)',
    '1994-2003 India': 'India',
    '1994-2003 China': 'China',
    '1994-2003 Finland': 'Finland',
}

RETIREMENT_AGE_REAL = 60   # actual model retirement-age parameter (labor-force exit), 1994-2003 window
DEPENDENCY_AGE_THRESHOLD = 65   # old-age dependency ratio convention (65+ / 15-64), matches validation §5.2.1
START_YEAR = 1994


# ============================================================
# DATA LOADING
# ============================================================
def load_data(path):
    df = pd.read_csv(path, skiprows=6)
    df = df.rename(columns={
        'mean [age] of households / 4': 'avg_age',
        'count households with [age >= 200] / count households with [age < 200]': 'dep_ratio',
        'total-unemployment': 'unemployment',
        'young-unemployment': 'young_unemployment',
        'old-unemployment': 'old_unemployment',
        'Inflation': 'inflation',
        'gdp-growth': 'gdp_growth',
        'sum [pension-balance] of governments': 'pension_balance',
        'annual-pension-growth': 'pension_growth_annual',
        'pension-contributions': 'pension_contrib',
        'pension-benefits': 'pension_benefits',
        '[step]': 'tick',
        'simulation-period': 'scenario',
    })
    df['year'] = START_YEAR + (df['tick'] - 1) / 4
    return df


def present_scenarios(df):
    """Return the subset of SCENARIOS actually present in df, in canonical order."""
    have = set(df['scenario'].unique())
    return [s for s in SCENARIOS if s in have]


def summarize(df, var):
    g = df.groupby(['scenario', 'tick'])[var].agg(['mean', 'std', 'count']).reset_index()
    g['se'] = g['std'] / np.sqrt(g['count'])
    g['ci_lo'] = g['mean'] - 1.96 * g['se']
    g['ci_hi'] = g['mean'] + 1.96 * g['se']
    g['year'] = START_YEAR + (g['tick'] - 1) / 4
    return g


def plot_var(ax, df, var, ylabel, title, percent=False):
    summary = summarize(df, var)
    factor = 100 if percent else 1
    for scenario in present_scenarios(df):
        s = summary[summary['scenario'] == scenario]
        col = COLORS[scenario]
        ax.plot(s['year'], s['mean'] * factor, color=col, label=LABELS[scenario], lw=2)
        ax.fill_between(s['year'], s['ci_lo'] * factor, s['ci_hi'] * factor,
                         color=col, alpha=0.15)
    ax.set_xlabel('Year')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)


# ============================================================
# REAL JAPAN DATA
# ============================================================
REAL_PENSION_GROWTH = [0.0696, 0.0594, 0.0616, 0.0405, 0.0302, 0.0154, -0.0167, -0.0188, 0.0291]
REAL_PENSION_YEARS = list(range(1995, 1995 + len(REAL_PENSION_GROWTH)))


# ============================================================
# POPULATION PYRAMID DATA (from NetLogo age-distributions setup)
# ============================================================
PYRAMID_DATA = {
    '1994-2003': [
        (0, 20, 42), (20, 40, 48), (40, 60, 41),
        (60, 80, 38), (80, 100, 38), (100, 120, 45),
        (120, 140, 48), (140, 160, 43), (160, 180, 38),
        (180, 200, 35), (200, 220, 30), (220, 240, 21),
        (240, 260, 15), (260, 280, 11), (280, 300, 5),
        (300, 320, 1), (320, 340, 1), (340, 360, 0),
    ],
    '1994-2003 uniform': [
        (0, 20, 28), (20, 40, 28), (40, 60, 28),
        (60, 80, 28), (80, 100, 28), (100, 120, 28),
        (120, 140, 28), (140, 160, 28), (160, 180, 28),
        (180, 200, 28), (200, 220, 28), (220, 240, 28),
        (240, 260, 28), (260, 280, 28), (280, 300, 27),
        (300, 320, 27), (320, 340, 27), (340, 360, 27),
    ],
    '1994-2003 India': [
        (0, 20, 81), (20, 40, 72), (40, 60, 64),
        (60, 80, 57), (80, 100, 50), (100, 120, 42),
        (120, 140, 32), (140, 160, 26), (160, 180, 23),
        (180, 200, 19), (200, 220, 14), (220, 240, 10),
        (240, 260, 6), (260, 280, 3), (280, 300, 1),
        (300, 320, 0), (320, 340, 0), (340, 360, 0),
    ],
    '1994-2003 China': [
        (0, 20, 57), (20, 40, 73), (40, 60, 72),
        (60, 80, 54), (80, 100, 51), (100, 120, 48),
        (120, 140, 33), (140, 160, 26), (160, 180, 25),
        (180, 200, 21), (200, 220, 16), (220, 240, 12),
        (240, 260, 7), (260, 280, 4), (280, 300, 1),
        (300, 320, 0), (320, 340, 0), (340, 360, 0),
    ],
    '1994-2003 Finland': [
        (0, 20, 40), (20, 40, 37), (40, 60, 44),
        (60, 80, 46), (80, 100, 48), (100, 120, 50),
        (120, 140, 51), (140, 160, 35), (160, 180, 32),
        (180, 200, 30), (200, 220, 28), (220, 240, 23),
        (240, 260, 16), (260, 280, 12), (280, 300, 6),
        (300, 320, 2), (320, 340, 0), (340, 360, 0),
    ],
}


def to_real_age_bins(data):
    """Model age tick -> real age year (model age 0 = real age 15, 4 ticks = 1 yr)."""
    return [(15 + lo / 4, 15 + hi / 4, c) for lo, hi, c in data]


def dep_ratio_from_bins(bins):
    """Old-age dependency ratio = retired (65+) / working-age (15-64)."""
    working = sum(c for lo, hi, c in bins if lo < DEPENDENCY_AGE_THRESHOLD)
    retired = sum(c for lo, hi, c in bins if lo >= DEPENDENCY_AGE_THRESHOLD)
    return retired / working if working else float('nan')


# ============================================================
# FIGURE 1: Demographic setup (2x3 grid: 5 pyramids + dep ratio evolution)
# ============================================================
def plot_demographic_setup(df):
    """Panels A-E: population pyramid for each scenario present in the data.
    Panel F: dependency ratio evolution over 1994-2003, all scenarios overlaid."""
    scenarios = present_scenarios(df)

    bins_by = {s: to_real_age_bins(PYRAMID_DATA[s]) for s in scenarios if s in PYRAMID_DATA}
    scenarios = [s for s in scenarios if s in bins_by]  # keep only scenarios with pyramid data

    labels = [f'{int(lo)}–{int(hi)}' for lo, hi, c in next(iter(bins_by.values()))]
    xmax = max(max(c for lo, hi, c in bins) for bins in bins_by.values()) * 1.2
    y_pos = np.arange(len(labels))
    retire_idx = next(i for i, l in enumerate(labels) if l.startswith('65'))

    n = len(scenarios)
    ncols = 3 if n > 3 else n
    nrows = 2 if n > 3 else 1

    fig = plt.figure(figsize=(13.5, 9.2 if nrows == 2 else 5.5))
    gs = fig.add_gridspec(nrows, ncols, hspace=0.5, wspace=0.28)

    # Grid positions for pyramid panels, leaving the last cell of the grid for Panel F
    all_positions = [(r, c) for r in range(nrows) for c in range(ncols)]
    pyramid_positions = all_positions[:n]
    dep_ratio_pos = all_positions[n] if len(all_positions) > n else None

    first_ax = None
    for i, s in enumerate(scenarios):
        r, c = pyramid_positions[i]
        ax = fig.add_subplot(gs[r, c], sharey=first_ax)
        if first_ax is None:
            first_ax = ax
        bins = bins_by[s]
        counts = [cc for lo, hi, cc in bins]
        col = COLORS[s]
        alphas = [0.95 if lo < DEPENDENCY_AGE_THRESHOLD else 0.42 for lo, hi, cc in bins]
        bars = ax.barh(y_pos, counts, height=0.78, color=col, edgecolor='white', linewidth=0.4)
        for bar, a in zip(bars, alphas):
            bar.set_alpha(a)
        dep = dep_ratio_from_bins(bins)
        ax.set_title(f'{chr(65 + i)}. {LABELS[s]}\nDep. ratio = {dep:.2f}',
                     color=col, fontsize=11, fontweight='bold')
        ax.axhline(retire_idx - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.6)
        ax.set_xlim(0, xmax)
        ax.grid(True, axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_xlabel('Population count', fontsize=9)
        if c == 0:
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=7.5)
            ax.set_ylabel('Age group', fontsize=9)
        else:
            plt.setp(ax.get_yticklabels(), visible=False)

    # Panel F (or last panel): dependency ratio evolution, all scenarios
    if dep_ratio_pos is not None:
        r, c = dep_ratio_pos
        ax = fig.add_subplot(gs[r, c])
        summary = summarize(df, 'dep_ratio')
        for s in scenarios:
            sub = summary[summary.scenario == s]
            ax.plot(sub.year, sub['mean'], color=COLORS[s], lw=1.8, label=LABELS[s])
            ax.fill_between(sub.year, sub.ci_lo, sub.ci_hi, color=COLORS[s], alpha=0.15)
        ax.set_title(f'{chr(65 + n)}. Dependency ratio\nevolution ({START_YEAR}–{START_YEAR + 9})',
                     fontsize=11, fontweight='bold')
        ax.set_xlabel('Year', fontsize=9)
        ax.set_ylabel('Old-age dependency ratio', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=6.5, frameon=True, framealpha=0.9)

    legend_elements = [
        Patch(facecolor='#888888', alpha=0.95, label='Working age (15–64)'),
        Patch(facecolor='#888888', alpha=0.42, label='Retired (65+)'),
    ]
    fig.tight_layout(rect=[0, 0.04, 1, 0.98])
    fig.legend(handles=legend_elements, loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0),
               frameon=False, fontsize=9)

    plt.savefig(f'{OUTPUT_DIR}/fig_demographic_setup.png', bbox_inches='tight')
    plt.close()
    print('  Saved fig_demographic_setup.png')


# ============================================================
# FIGURE 2: Pension core (1995-2002, log-diff growth)
# ============================================================
def plot_pension_core(df):
    """Restrict to 1995-2002. Use annual pension growth (symlog scale).
    Falls back to young/old unemployment for Panels C/D if pension_contrib /
    pension_benefits are missing or entirely NaN in the loaded CSV."""
    scenarios = present_scenarios(df)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # Filter to 1995-2002 (tick 5 = 1995 Q1, tick 36 = 2002 Q4)
    df_window = df[(df['tick'] >= 5) & (df['tick'] <= 36)].copy()

    # A. Pension balance
    ax = axes[0, 0]
    plot_var(ax, df_window, 'pension_balance', 'Pension balance (units)',
             'A. Pension balance trajectory')
    ax.axhline(0, color='gray', linestyle=':', lw=0.8)

    # B. Annual pension growth — match reference validation code's alignment.
    # NetLogo updates annual-pension-growth at tick%4==3 (steps 3, 7, 11, ...),
    # but the reference validation code reads at steps 4, 8, 12, ..., 36 (i.e.
    # one tick after update), and aligns them to integer years 1994, 1995, ..., 2002.
    # We follow the same convention: step 8 → 1995, step 12 → 1996, ..., step 36 → 2002.
    ax = axes[0, 1]

    target_steps = list(range(8, 37, 4))  # [8, 12, 16, 20, 24, 28, 32, 36]
    target_years = list(range(1995, 2003))  # 1995-2002

    year_end_df = df[df['tick'].isin(target_steps)].copy()
    step_to_year = dict(zip(target_steps, target_years))
    year_end_df['year_int'] = year_end_df['tick'].map(step_to_year)

    summary_g = (year_end_df.groupby(['scenario', 'year_int'])['pension_growth_annual']
                 .agg(['mean', 'std', 'count']).reset_index())
    summary_g['se'] = summary_g['std'] / np.sqrt(summary_g['count'])
    summary_g['ci_lo'] = summary_g['mean'] - 1.96 * summary_g['se']
    summary_g['ci_hi'] = summary_g['mean'] + 1.96 * summary_g['se']

    for scenario in scenarios:
        s = summary_g[summary_g['scenario'] == scenario].dropna(subset=['mean'])
        col = COLORS[scenario]
        ax.plot(s['year_int'], s['mean'] * 100, color=col, label=LABELS[scenario],
                lw=2, marker='s', ms=5)
        ax.fill_between(s['year_int'], s['ci_lo'] * 100, s['ci_hi'] * 100,
                         color=col, alpha=0.15)

    # Japan real data
    real_in_window = [(y, v) for y, v in zip(REAL_PENSION_YEARS, REAL_PENSION_GROWTH)
                       if 1995 <= y <= 2002]
    if real_in_window:
        real_years_w = [y for y, _ in real_in_window]
        real_vals_w = [v * 100 for _, v in real_in_window]
        ax.plot(real_years_w, real_vals_w, color='black', linestyle='--', lw=1.5,
                marker='o', ms=5, label='Japan actual data')

    ax.axhline(0, color='gray', linestyle=':', lw=0.8)
    ax.set_xlabel('Year')
    ax.set_ylabel('Annual pension growth (%)')
    ax.set_title('B. Annual pension growth (1995–2002)')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(target_years)
    ax.set_yscale('symlog', linthresh=10)

    # C / D. Pension contributions & benefits, with fallback to unemployment
    # breakdown if these columns are missing / entirely NaN in the CSV.
    have_contrib = 'pension_contrib' in df.columns and df['pension_contrib'].notna().any()
    have_benefits = 'pension_benefits' in df.columns and df['pension_benefits'].notna().any()

    ax = axes[1, 0]
    if have_contrib:
        plot_var(ax, df_window, 'pension_contrib', 'Pension contributions (units)',
                 'C. Pension contributions (per quarter)')
    else:
        plot_var(ax, df_window, 'young_unemployment', 'Young-age unemployment (%)',
                 'C. Young-age unemployment (fallback)', percent=True)

    ax = axes[1, 1]
    if have_benefits:
        plot_var(ax, df_window, 'pension_benefits', 'Pension benefits (units)',
                 'D. Pension benefits (per quarter)')
    else:
        plot_var(ax, df_window, 'old_unemployment', 'Old-age unemployment (%)',
                 'D. Old-age unemployment (fallback)', percent=True)

    plt.suptitle('OLG necessity: pension dynamics under the five demographic scenarios (1995–2002)',
                 fontsize=14, y=0.995)
    fig.tight_layout(rect=[0, 0.08, 1, 0.96])
    handles, labels_legend = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels_legend, loc='lower center', ncol=3,
               bbox_to_anchor=(0.5, 0.0), frameon=False)
    plt.savefig(f'{OUTPUT_DIR}/fig1_pension_core.png', bbox_inches='tight')
    plt.close()
    print('  Saved fig1_pension_core.png')


# ============================================================
# FIGURE 3: Macro (3 subplots, no loan index)
# ============================================================
def plot_macro(df):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    plot_var(axes[0], df, 'unemployment', 'Unemployment (%)',
             'A. Unemployment rate', percent=True)

    plot_var(axes[1], df, 'inflation', 'Inflation (%)',
             'B. Inflation', percent=True)
    axes[1].axhline(0, color='gray', linestyle=':', lw=0.8)

    df_gdp = df[df['tick'] >= 2].copy()
    plot_var(axes[2], df_gdp, 'gdp_growth', 'GDP growth (%)',
             'C. Real GDP growth (quarterly)', percent=True)
    axes[2].axhline(0, color='gray', linestyle=':', lw=0.8)

    plt.suptitle('Macroeconomic outcomes under the five OLG scenarios', fontsize=14, y=1.02)
    fig.tight_layout(rect=[0, 0.14, 1, 0.90])
    handles, labels_legend = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_legend, loc='lower center', ncol=3,
               bbox_to_anchor=(0.5, 0.0), frameon=False)
    plt.savefig(f'{OUTPUT_DIR}/fig3_macro.png', bbox_inches='tight')
    plt.close()
    print('  Saved fig3_macro.png')


# ============================================================
# Summary
# ============================================================
def print_summary(df):
    print('\n' + '=' * 60)
    print('Summary statistics')
    print('=' * 60)

    candidate_cols = ['avg_age', 'dep_ratio', 'pension_balance',
                       'pension_contrib', 'pension_benefits', 'unemployment']
    cols = [c for c in candidate_cols if c in df.columns]

    print('\n--- t=1 (initial) ---')
    init = df[df['tick'] == 1].groupby('scenario')[cols].mean().round(3)
    print(init)

    print('\n--- t=40 (final) ---')
    final = df[df['tick'] == 40].groupby('scenario')[cols].mean().round(3)
    print(final)


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print(f'Loading data from {CSV_PATH}...')
    df = load_data(CSV_PATH)
    print(f'  {len(df)} rows, {df.scenario.nunique()} scenarios, '
          f'{df.groupby("scenario")["[run number]"].nunique().to_dict()}\n')

    print('Generating figures:')
    plot_demographic_setup(df)
    plot_pension_core(df)
    plot_macro(df)

    print_summary(df)
    print(f'\nAll figures saved to ./{OUTPUT_DIR}/')
