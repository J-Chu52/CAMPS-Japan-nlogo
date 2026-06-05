import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置
# ============================================================
REPO_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(REPO_DIR, 'data', 'sensitivity_oat')   # OAT 表都在这
EMP_DIR    = os.path.join(REPO_DIR, 'data', 'empirical')
OUT_DIR    = os.path.join(REPO_DIR, 'outputs')
REAL_PATH  = os.path.join(EMP_DIR, 'real-data1.csv')
os.makedirs(OUT_DIR, exist_ok=True)

EXP_NAME   = '1994-2003'
START_YEAR = 1994
QUARTERLY_BURNIN = 2
N_RUNS = 100

# ============================================================
# RSA 参数配置 — 重新分组
# ============================================================
# Count-Shift 组 (9 个参数: 离散位移/计数型/利率位移)
COUNT_SHIFT_PARAMS = {
    'birth-rate-shift':       ('birth-rate-shift',     'Birth Rate Shift'),
    'lend-rate-shift':        ('lend-rate-shift',      'Lend Rate Shift'),
    'deposit-rate-shift':     ('deposit-rate-shift',   'Deposit Rate Shift'),
    'consumer-choices':       ('consumer-choices',     'Consumer Choices'),
    'job-applications':       ('job-applications',     'Job Applications'),
    'credit-thre':            ('credit-thre',          'Credit Threshold'),
    'default-tole':           ('default-tole',         'Default Tolerance'),
    'debt-repayment-rate':    ('debt-repayment-rate',  'Debt Repayment Rate'),
    'retirement-ages':        ('retirement-ages',      'Retirement Ages'),
}

# Rate-Scale 组 (13 个参数: 比例/连续型)
RATE_SCALE_PARAMS = {
    'death-prob-shift':           ('death-prob-shift',          'Death Prob. Shift'),
    'productivity-growth-scale':  ('productivity-growth-scale', 'Productivity Growth'),
    'wage-growth-scale':          ('wage-growth-scale',         'Wage Growth'),
    'pension-replace-scale':      ('pension-replace-scale',     'Pension Replace'),
    'paygo-rate-scale':           ('paygo-rate-scale',          'PAYGO Rate'),
    'mpc-income':                 ('mpc-income',                'MPC Income'),
    'mpc-wealth':                 ('mpc-wealth',                'MPC Wealth'),
    'reorganization-prob':        ('reorganization-prob',       'Reorganisation Prob.'),
    'profit-tax-rate':            ('profit-tax-rate',           'Profit Tax Rate'),
    'credit-memory-window':       ('credit-memory-window',      'Credit Memory Window'),
    'contract-length':            ('contract-length',           'Contract Length'),
    'price-adjustment':           ('price-adjustment',          'Price Adjustment'),
    'production-adjustment':      ('production-adjustment',     'Prod. Adjustment'),
}

def build_paths(param_dict):
    """构建文件路径字典"""
    paths = {}
    for key in param_dict:
        fname = f'1994-2003 {key}-table.csv'
        paths[key] = os.path.join(DATA_DIR, fname)
    return paths

# ============================================================
# 读取真实数据
# ============================================================
real = pd.read_csv(REAL_PATH)
real_unemp_ref = real['real unemployment'].values
real_infl_ref  = real['real inflation'].values
real_gdp_ref   = real['real rgdp growth'].values
real_pen_all   = real['real pension growth'].dropna().values

# ============================================================
# 工具函数
# ============================================================
OUTPUT_METRICS = ['Mean Unemployment', 'Mean GDP Growth', 'Mean Inflation', 'Mean Pension Growth']
METRIC_COLS = {
    'Mean Unemployment':   'total-unemployment',
    'Mean GDP Growth':     'gdp-growth',
    'Mean Inflation':      'Inflation',
    'Mean Pension Growth': 'annual-pension-growth',
}

RMSE_METRICS_Q = {
    'Unemployment': ('total-unemployment', real_unemp_ref),
    'Inflation':    ('Inflation',          real_infl_ref),
    'GDP Growth':   ('gdp-growth',         real_gdp_ref),
}
RMSE_METRIC_NAMES = ['Unemployment', 'Inflation', 'GDP Growth', 'Pension Growth']

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

def compute_per_run_rmse(rdf, param_col, param_val, real_data, sim_col, burn_in=2):
    sub = rdf[rdf[param_col]==param_val]
    rmses = []
    for run_id, run_df in sub.groupby('[run number]'):
        run_df = run_df.sort_values('[step]')
        sim_vals = run_df[sim_col].values[burn_in:]
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
        s = pen_vals[1:9]  # no lag, 1995-2002
        r = real_pen_vals[:8]
        n = min(len(s), len(r))
        if n < 2:
            rmses.append(np.nan); continue
        rmse = np.sqrt(np.mean((s[:n] - r[:n])**2))
        rmses.append(rmse)
    return np.array(rmses)

def compute_effect_sizes(param_dict, group_name):
    """对一组参数计算 Cohen's d (Level + RMSE)"""
    paths = build_paths(param_dict)
    level_d = {}
    rmse_d  = {}
    names_ordered   = []
    display_ordered = []
    skipped = []

    print(f'\n=== {group_name} 组 ===')
    for key, (param_col, display_name) in param_dict.items():
        fpath = paths[key]
        if not os.path.exists(fpath):
            skipped.append(key)
            print(f'  ⚠ 跳过 (文件不存在): {os.path.basename(fpath)}')
            continue

        rdf = pd.read_csv(fpath, skiprows=6)
        actual_param_col = rdf.columns[1]
        vals = sorted(rdf[actual_param_col].unique())
        lowest, highest = vals[0], vals[-1]

        names_ordered.append(key)
        display_ordered.append(display_name)

        # Level Effect
        run_low  = rdf[rdf[actual_param_col]==lowest].groupby('[run number]')
        run_high = rdf[rdf[actual_param_col]==highest].groupby('[run number]')

        level_d[key] = {}
        for metric_name, col_name in METRIC_COLS.items():
            low_means  = run_low[col_name].mean().values
            high_means = run_high[col_name].mean().values
            level_d[key][metric_name] = cohens_d(low_means, high_means)

        # RMSE Effect
        rmse_d[key] = {}
        for metric_name, (col_name, real_ref) in RMSE_METRICS_Q.items():
            low_rmses  = compute_per_run_rmse(rdf, actual_param_col, lowest,  real_ref, col_name, burn_in=QUARTERLY_BURNIN)
            high_rmses = compute_per_run_rmse(rdf, actual_param_col, highest, real_ref, col_name, burn_in=QUARTERLY_BURNIN)
            rmse_d[key][metric_name] = cohens_d(low_rmses, high_rmses)

        # Pension RMSE
        low_pen  = compute_per_run_pension_rmse(rdf, actual_param_col, lowest,  real_pen_all)
        high_pen = compute_per_run_pension_rmse(rdf, actual_param_col, highest, real_pen_all)
        low_pen  = low_pen[~np.isnan(low_pen)]
        high_pen = high_pen[~np.isnan(high_pen)]
        rmse_d[key]['Pension Growth'] = cohens_d(low_pen, high_pen)

        print(f'  ✓ {display_name:25s} ({actual_param_col}: {lowest} → {highest})')

    if skipped:
        print(f'  共跳过 {len(skipped)} 个文件')

    return level_d, rmse_d, names_ordered, display_ordered

def plot_heatmap_pair(level_d, rmse_d, names_ordered, display_ordered, group_name, file_suffix):
    """画 side-by-side 热力图: Level + RMSE"""
    n_params  = len(names_ordered)
    n_metrics = len(OUTPUT_METRICS)

    if n_params == 0:
        print(f'  ⚠ {group_name} 没有可用数据,跳过画图')
        return None, None

    level_matrix = np.zeros((n_params, n_metrics))
    for i, pn in enumerate(names_ordered):
        for j, mn in enumerate(OUTPUT_METRICS):
            level_matrix[i, j] = level_d[pn][mn]

    rmse_matrix = np.zeros((n_params, len(RMSE_METRIC_NAMES)))
    for i, pn in enumerate(names_ordered):
        for j, mn in enumerate(RMSE_METRIC_NAMES):
            rmse_matrix[i, j] = rmse_d[pn][mn]

    fig_h = max(6, n_params * 0.55)
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(20, fig_h))
    fig.suptitle(
        f"Sensitivity Analysis: {group_name} Parameters — {EXP_NAME}\n"
        f"Cohen's d: lowest vs. highest parameter level",
        fontweight='bold', fontsize=12, y=1.02)

    clip_val = min(max(abs(level_matrix).max(), abs(rmse_matrix).max()), 50)
    if clip_val == 0:
        clip_val = 1.0  # 兜底

    for ax, matrix, title, metric_names, subtitle in [
        (ax_l, level_matrix, 'Level Effect Size',
         [m.replace('Mean ','') for m in OUTPUT_METRICS],
         'Positive d = increase raises mean'),
        (ax_r, rmse_matrix,  'RMSE Effect Size',
         RMSE_METRIC_NAMES,
         'Positive d = increase worsens fit'),
    ]:
        clipped = np.clip(matrix, -clip_val, clip_val)
        norm = TwoSlopeNorm(vmin=-clip_val, vcenter=0, vmax=clip_val)
        im = ax.imshow(clipped, cmap='RdBu_r', norm=norm, aspect='auto')

        ax.set_xticks(np.arange(len(metric_names)))
        ax.set_xticklabels(metric_names, fontsize=10)
        ax.set_yticks(np.arange(n_params))
        ax.set_yticklabels(display_ordered, fontsize=9)

        for i in range(n_params):
            for j in range(len(metric_names)):
                d_val = matrix[i, j]
                mag = magnitude_label(abs(d_val))
                text_color = 'white' if abs(clipped[i, j]) > clip_val * 0.5 else 'black'
                ax.text(j, i, f'{d_val:+.2f}\n({mag})', ha='center', va='center',
                        fontsize=8, fontweight='bold', color=text_color)

        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04).set_label("Cohen's d", fontsize=9)
        ax.set_title(f'{title}\n{subtitle}', fontweight='bold', fontsize=10)

    fig.tight_layout()
    out_path = f'{OUT_DIR}/{EXP_NAME}_rsa_{file_suffix}_effect.png'
    fig.savefig(out_path, dpi=180, bbox_inches='tight')
    print(f'  ✓ 保存: {os.path.basename(out_path)}')
    return level_matrix, rmse_matrix

def save_csv_tables(level_d, rmse_d, names_ordered, display_ordered, file_suffix):
    """保存 Level + RMSE 表格"""
    if not names_ordered:
        return

    level_rows = []
    for pn, dn in zip(names_ordered, display_ordered):
        row = {'Parameter': dn}
        for mn in OUTPUT_METRICS:
            d = level_d[pn][mn]
            mag = magnitude_label(abs(d))
            row[mn.replace('Mean ', '')] = f'{d:+.2f} ({mag})'
        level_rows.append(row)
    level_table = pd.DataFrame(level_rows)
    level_table.to_csv(f'{OUT_DIR}/{EXP_NAME}_rsa_{file_suffix}_level_table.csv',
                       index=False, encoding='utf-8-sig')

    rmse_rows = []
    for pn, dn in zip(names_ordered, display_ordered):
        row = {'Parameter': dn}
        for mn in RMSE_METRIC_NAMES:
            d = rmse_d[pn][mn]
            mag = magnitude_label(abs(d))
            row[mn] = f'{d:+.2f} ({mag})'
        rmse_rows.append(row)
    rmse_table = pd.DataFrame(rmse_rows)
    rmse_table.to_csv(f'{OUT_DIR}/{EXP_NAME}_rsa_{file_suffix}_rmse_table.csv',
                      index=False, encoding='utf-8-sig')

    print(f'\n  Level Effect Size Table ({file_suffix}):')
    print('  ' + level_table.to_string(index=False).replace('\n', '\n  '))
    print(f'\n  RMSE Effect Size Table ({file_suffix}):')
    print('  ' + rmse_table.to_string(index=False).replace('\n', '\n  '))

# ============================================================
# 主流程: 分别处理两个组
# ============================================================
print('=' * 70)
print(f'Running RSA for {EXP_NAME}')
print('=' * 70)

# Count-Shift 组
print('\n' + '─' * 70)
print('处理 COUNT-SHIFT 组 (9 个参数)')
print('─' * 70)
cs_level, cs_rmse, cs_names, cs_display = compute_effect_sizes(
    COUNT_SHIFT_PARAMS, 'Count-Shift')
plot_heatmap_pair(cs_level, cs_rmse, cs_names, cs_display,
                  'Count-Shift', 'count_shift')
save_csv_tables(cs_level, cs_rmse, cs_names, cs_display, 'count_shift')

# Rate-Scale 组
print('\n' + '─' * 70)
print('处理 RATE-SCALE 组 (13 个参数)')
print('─' * 70)
rs_level, rs_rmse, rs_names, rs_display = compute_effect_sizes(
    RATE_SCALE_PARAMS, 'Rate-Scale')
plot_heatmap_pair(rs_level, rs_rmse, rs_names, rs_display,
                  'Rate-Scale', 'rate_scale')
save_csv_tables(rs_level, rs_rmse, rs_names, rs_display, 'rate_scale')

print('\n' + '=' * 70)
print('全部完成!')
print('=' * 70)

plt.show()
