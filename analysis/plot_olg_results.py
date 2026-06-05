"""
OLG Necessity Experiment: Visualization Script (v2)
====================================================
Generates 3 paper-ready figures from BehaviorSpace CSV output.

Default paths (edit DATA_DIR / OUT_DIR in CONFIG section if needed):
    Input:  /Users/sonatachu/Downloads/4.17/olg check-table.csv
    Output: /Users/sonatachu/Downloads/4.17/outputs/

Usage:
    python plot_olg_results.py                        # use defaults
    python plot_olg_results.py path/to/your-csv.csv   # override input

Outputs:
    fig_combined_demo.png   - Population pyramids + dep ratio evolution (3 panels)
    fig1_pension_core.png   - Core OLG necessity evidence (1995-2002, 4 subplots)
    fig3_macro.png          - Macroeconomic outcomes (3 subplots, no loan index)
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

COLORS = {
    'baseline': '#1F4E79',
    'uniform': '#C00000',
    'baseline_retired': '#7BA7CC',
    'uniform_retired': '#E89090',
}
LABELS = {
    '1994-2003': 'Baseline (1994 actual structure)',
    '1994-2003 uniform': 'Uniform (counterfactual)',
}

RETIREMENT_AGE_REAL = 60
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
    for scenario in ['1994-2003', '1994-2003 uniform']:
        s = summary[summary['scenario'] == scenario]
        col = COLORS['baseline' if 'uniform' not in scenario else 'uniform']
        ax.plot(s['year'], s['mean'] * factor, color=col, label=LABELS[scenario], lw=2)
        ax.fill_between(s['year'], s['ci_lo'] * factor, s['ci_hi'] * factor,
                        color=col, alpha=0.18)
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
# POPULATION PYRAMID DATA (from NetLogo setup)
# ============================================================
BASELINE_DATA = [
    (0, 20, 42), (20, 40, 48), (40, 60, 41),
    (60, 80, 38), (80, 100, 38), (100, 120, 45),
    (120, 140, 48), (140, 160, 43), (160, 180, 38),
    (180, 200, 35), (200, 220, 30), (220, 240, 21),
    (240, 260, 15), (260, 280, 11), (280, 300, 5),
    (300, 320, 1), (320, 340, 1), (340, 360, 0),
]
UNIFORM_DATA = [
    (0, 20, 28), (20, 40, 28), (40, 60, 28),
    (60, 80, 28), (80, 100, 28), (100, 120, 28),
    (120, 140, 28), (140, 160, 28), (160, 180, 28),
    (180, 200, 28), (200, 220, 28), (220, 240, 28),
    (240, 260, 28), (260, 280, 28), (280, 300, 27),
    (300, 320, 27), (320, 340, 27), (340, 360, 27),
]


def to_real_age_bins(data):
    """Model age tick → real age year (model age 0 = real age 15, 4 ticks = 1 yr)."""
    return [(15 + lo / 4, 15 + hi / 4, c) for lo, hi, c in data]


def to_labels_counts(bins):
    labels, counts = [], []
    for lo, hi, c in bins:
        labels.append(f'{int(lo)}–{int(hi)}')
        counts.append(c)
    return labels, counts


def bar_colors(bins, base_color, retired_color):
    return [retired_color if lo >= RETIREMENT_AGE_REAL else base_color for lo, hi, c in bins]


# ============================================================
# FIGURE 1: Combined demographics (3 panels)
# ============================================================
def plot_combined_demo(df):
    """Panel A: baseline pyramid | Panel B: uniform pyramid | Panel C: dep ratio over time."""
    baseline_bins = to_real_age_bins(BASELINE_DATA)
    uniform_bins = to_real_age_bins(UNIFORM_DATA)
    labels, baseline_counts = to_labels_counts(baseline_bins)
    _, uniform_counts = to_labels_counts(uniform_bins)
    baseline_colors_list = bar_colors(baseline_bins, COLORS['baseline'], COLORS['baseline_retired'])
    uniform_colors_list = bar_colors(uniform_bins, COLORS['uniform'], COLORS['uniform_retired'])

    working_b = sum(c for (lo, hi, c) in baseline_bins if lo < RETIREMENT_AGE_REAL)
    retired_b = sum(c for (lo, hi, c) in baseline_bins if lo >= RETIREMENT_AGE_REAL)
    working_u = sum(c for (lo, hi, c) in uniform_bins if lo < RETIREMENT_AGE_REAL)
    retired_u = sum(c for (lo, hi, c) in uniform_bins if lo >= RETIREMENT_AGE_REAL)
    dep_b = retired_b / working_b
    dep_u = retired_u / working_u

    fig = plt.figure(figsize=(16, 8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.4], wspace=0.35)
    ax_left = fig.add_subplot(gs[0, 0])
    ax_mid = fig.add_subplot(gs[0, 1], sharey=ax_left)
    ax_right = fig.add_subplot(gs[0, 2])

    y_pos = np.arange(len(labels))
    bar_height = 0.78
    retire_y_idx = next(i for i, l in enumerate(labels) if l.startswith('60'))
    xmax = max(max(baseline_counts), max(uniform_counts)) * 1.18

    # Panel A: Baseline pyramid
    ax_left.barh(y_pos, baseline_counts, height=bar_height,
                 color=baseline_colors_list, edgecolor='white', linewidth=0.5)
    for i, c in enumerate(baseline_counts):
        if c > 0.5:
            ax_left.text(c + 1, i, f'{int(c)}', va='center', ha='left',
                         fontsize=8.5, color='#333333')
    ax_left.set_yticks(y_pos)
    ax_left.set_yticklabels(labels, fontsize=9)
    ax_left.set_ylabel('Age group')
    ax_left.set_xlabel('Population count')
    ax_left.set_title(f'A. Baseline (1994 actual)\nDep. ratio = {dep_b:.2f}',
                      color=COLORS['baseline'], fontsize=12, fontweight='bold')
    ax_left.axhline(retire_y_idx - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax_left.set_xlim(0, xmax)
    ax_left.grid(True, axis='x', alpha=0.3)
    ax_left.set_axisbelow(True)

    # Panel B: Uniform pyramid
    ax_mid.barh(y_pos, uniform_counts, height=bar_height,
                color=uniform_colors_list, edgecolor='white', linewidth=0.5)
    for i, c in enumerate(uniform_counts):
        if c > 0.5:
            ax_mid.text(c + 1, i, f'{int(c)}', va='center', ha='left',
                        fontsize=8.5, color='#333333')
    ax_mid.set_xlabel('Population count')
    ax_mid.set_title(f'B. Uniform (counterfactual)\nDep. ratio = {dep_u:.2f}',
                     color=COLORS['uniform'], fontsize=12, fontweight='bold')
    ax_mid.axhline(retire_y_idx - 0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax_mid.text(xmax * 0.55, retire_y_idx - 0.5 + 0.15,
                'Retirement age', fontsize=8.5, color='gray', style='italic')
    ax_mid.set_xlim(0, xmax)
    ax_mid.grid(True, axis='x', alpha=0.3)
    ax_mid.set_axisbelow(True)
    plt.setp(ax_mid.get_yticklabels(), visible=False)

    # Panel C: Dep ratio over time
    plot_var(ax_right, df, 'dep_ratio', 'Old-age dependency ratio',
             'C. Dependency ratio evolution (1994–2003)')
    ax_right.legend(loc='best', fontsize=9, frameon=True, framealpha=0.9)

    legend_elements = [
        Patch(facecolor='#888888', label='Working age (15–59)'),
        Patch(facecolor='#CCCCCC', label='Retired (60+)'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=2,
               bbox_to_anchor=(0.33, -0.02), frameon=False, fontsize=9)

    plt.suptitle('Demographic structure: initial pyramids and dependency ratio over time',
                 fontsize=14, y=1.00)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/fig_combined_demo.png', bbox_inches='tight')
    plt.close()
    print('  Saved fig_combined_demo.png')


# ============================================================
# FIGURE 2: Pension core (1995-2002, log-diff growth)
# ============================================================
def plot_pension_core(df):
    """Restrict to 1995-2002. Use log-difference for pension growth.
    Uniform line ends naturally when balance crosses zero."""
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
    # All 8 years plotted; symlog y-axis to handle uniform's extreme negative values.
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

    for scenario in ['1994-2003', '1994-2003 uniform']:
        s = summary_g[summary_g['scenario'] == scenario].dropna(subset=['mean'])
        col = COLORS['baseline' if 'uniform' not in scenario else 'uniform']
        ax.plot(s['year_int'], s['mean'] * 100, color=col, label=LABELS[scenario],
                lw=2, marker='s', ms=6)
        ax.fill_between(s['year_int'], s['ci_lo'] * 100, s['ci_hi'] * 100,
                        color=col, alpha=0.18)

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
    ax.legend(loc='lower left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(target_years)

    # Symlog y-axis: linear within ±10%, log beyond.
    # Lets baseline / Japan stay readable while showing uniform's catastrophic drop.
    ax.set_yscale('symlog', linthresh=10)

    # C. Pension contributions
    ax = axes[1, 0]
    plot_var(ax, df_window, 'pension_contrib', 'Pension contributions (units)',
             'C. Pension contributions (per quarter)')

    # D. Pension benefits
    ax = axes[1, 1]
    plot_var(ax, df_window, 'pension_benefits', 'Pension benefits (units)',
             'D. Pension benefits (per quarter)')

    handles, labels_legend = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels_legend, loc='lower center', ncol=2,
               bbox_to_anchor=(0.5, -0.02), frameon=False)
    plt.suptitle('OLG necessity: pension dynamics under counterfactual age distribution (1995–2002)',
                 fontsize=14, y=1.00)
    plt.tight_layout()
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

    handles, labels_legend = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_legend, loc='lower center', ncol=2,
               bbox_to_anchor=(0.5, -0.05), frameon=False)
    plt.suptitle('Macroeconomic outcomes', fontsize=14, y=1.02)
    plt.tight_layout()
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

    print('\n--- t=1 (initial) ---')
    init = df[df['tick'] == 1].groupby('scenario')[
        ['avg_age', 'dep_ratio', 'pension_balance',
         'pension_contrib', 'pension_benefits', 'unemployment']
    ].mean().round(3)
    print(init)

    print('\n--- t=40 (final) ---')
    final = df[df['tick'] == 40].groupby('scenario')[
        ['avg_age', 'dep_ratio', 'pension_balance',
         'pension_contrib', 'pension_benefits', 'unemployment']
    ].mean().round(3)
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
    plot_combined_demo(df)
    plot_pension_core(df)
    plot_macro(df)

    print_summary(df)
    print(f'\nAll figures saved to ./{OUTPUT_DIR}/')
