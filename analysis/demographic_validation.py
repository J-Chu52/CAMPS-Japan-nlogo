"""
Section 5.2: Internal Validity — Demographic Reproduction and Mortality Validation

Generates two figures:
  Figure 5.2.1: Demographic reproduction (age structure + dependency ratio)
  Figure 5.2.2: Mortality process validation (observed mortality vs life table)

Data inputs (in DATA_DIR):
  - population1994.csv                  (real Japan 1994/2003 age distribution + WDI dep ratio)
  - real_death_prob.csv                 (Japan 1990-1999 life table, 18 age bins)
  - demographic_validation-table.csv    (BehaviorSpace: 18 age counts + 18 death counts per tick)

Outputs (in OUT_DIR):
  - fig_521_demographic_reproduction.png
  - fig_522_mortality_validation.png

Model baseline: n* = 4 (~2028 agents), 100 runs × 40 ticks, 1994 Q1 → 2003 Q4.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================================================
# 0. Paths
# ============================================================

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMP_DIR  = os.path.join(REPO_DIR, 'data', 'empirical')
DATA_DIR = os.path.join(REPO_DIR, 'data', 'validation')
OUT_DIR  = os.path.join(REPO_DIR, 'outputs')

POP_FILE  = os.path.join(EMP_DIR, "population1994.csv")
LIFE_FILE = os.path.join(EMP_DIR, "real death prob.csv")
SIM_FILE  = os.path.join(DATA_DIR, "demographic validation-table.csv")

OUT_521 = os.path.join(OUT_DIR, "demographic_reproduction.png")
OUT_522 = os.path.join(OUT_DIR, "mortality_validation.png")

os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# Shared style settings
# ============================================================

ACTUAL_COLOR = '#888888'
MODEL_COLOR  = '#1f4e79'
BAND_COLOR   = '#1f4e79'
INPUT_COLOR  = '#888888'   # same as ACTUAL_COLOR but with semantic name for Fig 5.2.2

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Common age-group labels
AGE_GROUPS_16 = ['15-19', '20-24', '25-29', '30-34', '35-39', '40-44',
                 '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
                 '75-79', '80-84', '85-89', '90+']
AGE_GROUPS_18 = ['15-19', '20-24', '25-29', '30-34', '35-39', '40-44',
                 '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
                 '75-79', '80-84', '85-89', '90-94', '95-99', '100+']

def parse_pct(s):
    if pd.isna(s): return np.nan
    return float(str(s).strip().rstrip('%'))


# ============================================================
# 1. Load all data once (shared by both figures)
# ============================================================

print("=" * 60)
print("Loading data...")
print("=" * 60)

# --- 1a. Real Japan population data ---
raw = pd.read_csv(POP_FILE, header=1)
raw.columns = ['age_1994', 'total_1994', 'pct_1994',
               '_blank1',
               'age_2003', 'total_2003', 'pct_2003',
               '_blank2',
               'year_dep', 'dep_ratio']

def extract_pct_series(df, age_col, pct_col):
    out = []
    for ag in AGE_GROUPS_16:
        row = df[df[age_col].astype(str).str.strip() == ag]
        out.append(parse_pct(row.iloc[0][pct_col]) if not row.empty else np.nan)
    return np.array(out)

pct_1994_actual = extract_pct_series(raw, 'age_1994', 'pct_1994')
pct_2003_actual = extract_pct_series(raw, 'age_2003', 'pct_2003')
pct_1994_actual = pct_1994_actual / pct_1994_actual.sum() * 100
pct_2003_actual = pct_2003_actual / pct_2003_actual.sum() * 100

dep_real_df = raw[['year_dep', 'dep_ratio']].dropna()
dep_real_df['year_dep']  = dep_real_df['year_dep'].astype(int)
dep_real_df['dep_ratio'] = dep_real_df['dep_ratio'].astype(float)
years_real = dep_real_df['year_dep'].values
dep_real   = dep_real_df['dep_ratio'].values

# --- 1b. Life table (1990-1999, 18 bins) ---
lt_raw = pd.read_csv(LIFE_FILE, nrows=18).dropna(subset=['age'])
lt_raw['prob'] = lt_raw['prob'].astype(float)
lt_dict = {}
for _, row in lt_raw.iterrows():
    key = row['age']
    if key == '100-104':
        key = '100+'
    lt_dict[key] = row['prob']
life_table_annual = np.array([lt_dict[ag] for ag in AGE_GROUPS_18])

# --- 1c. Simulation output (merged) ---
df = pd.read_csv(SIM_FILE, skiprows=6)

age_cols_18 = [c for c in df.columns
               if c.startswith('count households with [age >= ') and '/' not in c]
assert len(age_cols_18) == 18, f"Expected 18 age cols, got {len(age_cols_18)}"

death_cols = ['deaths-15-19', 'deaths-20-24', 'deaths-25-29', 'deaths-30-34',
              'deaths-35-39', 'deaths-40-44', 'deaths-45-49', 'deaths-50-54',
              'deaths-55-59', 'deaths-60-64', 'deaths-65-69', 'deaths-70-74',
              'deaths-75-79', 'deaths-80-84', 'deaths-85-89',
              'deaths-90-94', 'deaths-95-99', 'deaths-100plus']

dep_col = 'count households with [age >= 200] / count households with [age < 200]'

print(f"  Simulation: {df.shape[0]} rows ({df['[run number]'].nunique()} runs × "
      f"{df['[step]'].nunique()} ticks)")
print(f"  Real Japan dep ratio: {years_real[0]}-{years_real[-1]}")


# ============================================================
# 2. FIGURE 5.2.1 — Demographic Reproduction
# ============================================================

print("\n" + "=" * 60)
print("Figure 5.2.1: Demographic Reproduction")
print("=" * 60)

def aggregate_to_16(values_18):
    """Collapse 90-94/95-99/100+ into a single 90+ bin."""
    out = np.zeros(16)
    out[:15] = values_18[:15]
    out[15]  = values_18[15] + values_18[16] + values_18[17]
    return out

# Panel A: model t=1 distribution (16 bins to match real data)
t1_counts_18 = df[df['[step]'] == 1][age_cols_18].mean(axis=0).values
t1_counts_16 = aggregate_to_16(t1_counts_18)
pct_1994_model = t1_counts_16 / t1_counts_16.sum() * 100

# Panel B: model t=40 distribution
t40_counts_18 = df[df['[step]'] == 40][age_cols_18].mean(axis=0).values
t40_counts_16 = aggregate_to_16(t40_counts_18)
pct_2003_model = t40_counts_16 / t40_counts_16.sum() * 100

# Panel C: dependency ratio time series
df['year'] = 1994 + (df['[step]'] - 1) // 4
per_run_annual = df.groupby(['[run number]', 'year'])[dep_col].mean().reset_index()
annual_stats   = per_run_annual.groupby('year')[dep_col].agg(['mean', 'std']).reset_index()
years_model    = annual_stats['year'].values
dep_model_mean = annual_stats['mean'].values
dep_model_std  = annual_stats['std'].values

# Fit statistics
rA    = np.corrcoef(pct_1994_model, pct_1994_actual)[0, 1]
rB    = np.corrcoef(pct_2003_model, pct_2003_actual)[0, 1]
rmseA = np.sqrt(np.mean((pct_1994_model - pct_1994_actual) ** 2))
rmseB = np.sqrt(np.mean((pct_2003_model - pct_2003_actual) ** 2))
rC    = np.corrcoef(dep_model_mean, dep_real)[0, 1]
rmseC = np.sqrt(np.mean((dep_model_mean - dep_real) ** 2))

print(f"  Panel A: r = {rA:.4f}, RMSE = {rmseA:.3f}pp")
print(f"  Panel B: r = {rB:.4f}, RMSE = {rmseB:.3f}pp")
print(f"  Panel C: r = {rC:.4f}, RMSE = {rmseC:.4f}")

# --- Plot ---
fig1, axes1 = plt.subplots(1, 3, figsize=(14, 5.4),
                           gridspec_kw={'width_ratios': [1, 1, 1.15]})
y_pos = np.arange(len(AGE_GROUPS_16))
bar_h = 0.4

# Panel A
axA = axes1[0]
axA.barh(y_pos + bar_h/2, pct_1994_actual, height=bar_h,
         color=ACTUAL_COLOR, edgecolor='white', linewidth=0.4)
axA.barh(y_pos - bar_h/2, pct_1994_model, height=bar_h,
         color=MODEL_COLOR, edgecolor='white', linewidth=0.4)
axA.set_yticks(y_pos); axA.set_yticklabels(AGE_GROUPS_16, fontsize=8.5)
axA.set_xlabel('Share of 15+ population (%)')
axA.set_title('A. Initial age structure (1994)\nStatic calibration', fontweight='bold')
axA.grid(axis='x', alpha=0.25, linewidth=0.5); axA.set_axisbelow(True)
axA.text(0.98, 0.04, f'$r$ = {rA:.3f}\nRMSE = {rmseA:.2f}pp',
         transform=axA.transAxes, ha='right', va='bottom', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.9))

# Panel B
axB = axes1[1]
axB.barh(y_pos + bar_h/2, pct_2003_actual, height=bar_h,
         color=ACTUAL_COLOR, edgecolor='white', linewidth=0.4)
axB.barh(y_pos - bar_h/2, pct_2003_model, height=bar_h,
         color=MODEL_COLOR, edgecolor='white', linewidth=0.4)
axB.set_yticks(y_pos); axB.set_yticklabels(AGE_GROUPS_16, fontsize=8.5)
axB.set_xlabel('Share of 15+ population (%)')
axB.set_title('B. End-of-window age structure (2003)\nDynamic validation', fontweight='bold')
axB.grid(axis='x', alpha=0.25, linewidth=0.5); axB.set_axisbelow(True)
axB.text(0.98, 0.04, f'$r$ = {rB:.3f}\nRMSE = {rmseB:.2f}pp',
         transform=axB.transAxes, ha='right', va='bottom', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.9))

xmax = max(axA.get_xlim()[1], axB.get_xlim()[1])
axA.set_xlim(0, xmax); axB.set_xlim(0, xmax)

# Panel C
axC = axes1[2]
axC.fill_between(years_model, dep_model_mean - dep_model_std, dep_model_mean + dep_model_std,
                 color=BAND_COLOR, alpha=0.18, label='Model 100-run ±1σ band')
axC.plot(years_model, dep_model_mean, color=MODEL_COLOR, linewidth=2.2,
         marker='o', markersize=4.5, label='Model mean')
axC.plot(years_real, dep_real, color=ACTUAL_COLOR, linewidth=2.2,
         linestyle='--', marker='s', markersize=4.5, label='Actual (Japan, WDI)')
axC.set_xlabel('Year'); axC.set_ylabel('Old-age dependency ratio (65+ / 15–64)')
axC.set_title('C. Old-age dependency ratio (1994–2003)\nDerived indicator', fontweight='bold')
axC.legend(loc='upper left', frameon=False, fontsize=8.5)
axC.grid(alpha=0.25, linewidth=0.5); axC.set_axisbelow(True)
axC.set_xticks(years_model[::2])
axC.text(0.98, 0.04, f'$r$ = {rC:.3f}\nRMSE = {rmseC:.4f}',
         transform=axC.transAxes, ha='right', va='bottom', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.9))

shared_handles_521 = [
    Patch(facecolor=ACTUAL_COLOR, label='Actual (Japan)'),
    Patch(facecolor=MODEL_COLOR,  label='Model (100-run mean)'),
]
fig1.legend(handles=shared_handles_521, loc='lower center', ncol=2,
            frameon=False, fontsize=10, bbox_to_anchor=(0.34, -0.02))

fig1.suptitle('Demographic reproduction: model vs actual Japan, 1994–2003',
              fontsize=12.5, y=1.00)
fig1.tight_layout(rect=[0, 0.02, 1, 1])
fig1.savefig(OUT_521, dpi=180, bbox_inches='tight', facecolor='white')
print(f"  Saved: {OUT_521}")


# ============================================================
# 3. FIGURE 5.2.2 — Mortality Process Validation
# ============================================================

print("\n" + "=" * 60)
print("Figure 5.2.2: Mortality Process Validation")
print("=" * 60)

# Compute model observed annual mortality, per run, 18 bins
run_level = []
for run_id in df['[run number]'].unique():
    sub = df[df['[run number]'] == run_id]
    deaths_run    = sub[death_cols].sum().values
    pop_mean_run  = sub[age_cols_18].mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        quarterly_rate = np.where(pop_mean_run > 0,
                                  deaths_run / (pop_mean_run * 40),
                                  np.nan)
    annual_rate = 1 - (1 - quarterly_rate) ** 4
    run_level.append(annual_rate)

run_level = np.array(run_level)
model_annual_mean = np.nanmean(run_level, axis=0)
model_annual_std  = np.nanstd(run_level, axis=0)

# Fit statistics
pearson_r    = np.corrcoef(life_table_annual, model_annual_mean)[0, 1]
rmse         = np.sqrt(np.mean((life_table_annual - model_annual_mean) ** 2))
rel_err      = np.abs(model_annual_mean - life_table_annual) / life_table_annual * 100
mean_rel_err = rel_err.mean()

print(f"  Pearson r          = {pearson_r:.4f}")
print(f"  RMSE               = {rmse:.4f}")
print(f"  Mean |rel. error|  = {mean_rel_err:.2f}%")

# --- Plot ---
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 5.4))
x = np.arange(len(AGE_GROUPS_18))
bar_w = 0.38

# Panel A: linear
axA = axes2[0]
axA.bar(x - bar_w/2, life_table_annual, width=bar_w,
        color=INPUT_COLOR, edgecolor='white', linewidth=0.4,
        label='Life table (Japan 1990–1999)')
axA.bar(x + bar_w/2, model_annual_mean, width=bar_w,
        yerr=model_annual_std, capsize=2.5,
        color=MODEL_COLOR, edgecolor='white', linewidth=0.4,
        error_kw={'elinewidth': 0.8, 'ecolor': '#333333'},
        label='Model (100-run mean ±1σ)')
axA.set_xticks(x); axA.set_xticklabels(AGE_GROUPS_18, rotation=45, ha='right', fontsize=8.5)
axA.set_xlabel('Age group'); axA.set_ylabel('Annual mortality probability')
axA.set_title('A. Linear scale', fontweight='bold')
axA.grid(axis='y', alpha=0.25, linewidth=0.5); axA.set_axisbelow(True)
axA.legend(loc='upper left', frameon=False, fontsize=9)
axA.text(0.97, 0.97,
         f'$r$ = {pearson_r:.4f}\nRMSE = {rmse:.4f}\nMean |rel. err| = {mean_rel_err:.1f}%',
         transform=axA.transAxes, ha='right', va='top', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                   edgecolor='#aaaaaa', alpha=0.9))

# Panel B: log
axB = axes2[1]
axB.bar(x - bar_w/2, life_table_annual, width=bar_w,
        color=INPUT_COLOR, edgecolor='white', linewidth=0.4,
        label='Life table (Japan 1990–1999)')
axB.bar(x + bar_w/2, np.maximum(model_annual_mean, 1e-5), width=bar_w,
        yerr=model_annual_std, capsize=2.5,
        color=MODEL_COLOR, edgecolor='white', linewidth=0.4,
        error_kw={'elinewidth': 0.8, 'ecolor': '#333333'},
        label='Model (100-run mean ±1σ)')
axB.set_xticks(x); axB.set_xticklabels(AGE_GROUPS_18, rotation=45, ha='right', fontsize=8.5)
axB.set_xlabel('Age group'); axB.set_ylabel('Annual mortality probability (log scale)')
axB.set_title('B. Log scale (reveals young-age detail)', fontweight='bold')
axB.set_yscale('log')
axB.grid(axis='y', alpha=0.25, linewidth=0.5, which='both'); axB.set_axisbelow(True)
axB.set_ylim(bottom=1e-4)

fig2.suptitle('Mortality process validation: model output vs life table input',
              fontsize=12.5, y=1.00)
fig2.tight_layout()
fig2.savefig(OUT_522, dpi=180, bbox_inches='tight', facecolor='white')
print(f"  Saved: {OUT_522}")

print("\nDone.")
