# CAMPS-Japan

Calibrated Agent-based Macroeconomic Pension System - Japan.
Agent-based overlapping-generations model of the Japanese economy and its
public pension system, calibrated on 1994-2003 and tested out of sample on
2009-2018.

## Layout

- `model/CAPMSJapan_v2.nlogo` - the model, including all BehaviorSpace experiments
- `analysis/` - the ten scripts that produce every figure and table in the paper
- `data/empirical/` - historical Japanese input and validation series, and
  `Japan_1994_2018_data_collection_EN.xlsx`, the full data-collection workbook
  (one sheet per series, sources documented in `00_README`)
- `data/validation/` - raw BehaviorSpace exports: the 22 one-at-a-time sensitivity
  tables and the baseline, out-of-sample, demographic, OLG and scaling runs
- `outputs/` - figures (fig01-fig23) and result tables (tab10-tab18) as produced by the scripts

## Reproducing the results

To regenerate every figure and table from the data in this repository:

    bash run_all_analysis.sh

`bash run_all_analysis.sh --check` verifies the inputs and Python dependencies
without writing anything; `--list` shows which script produces which figure.
Two analyses are skipped automatically because their BehaviorSpace exports are
too large to distribute (see Data availability); the script names the experiment
that regenerates each one. Per-analysis logs are written to `logs/`.


Requires NetLogo (BehaviorSpace) and Python with pandas, numpy, matplotlib and scipy.

| Paper item | Script |
| --- | --- |
| Fig. 2 validation | `validate_1994-2003_smoothed.py`, `validate_2009-2018_smoothed_.py` |
| Fig. 3 demographic counterfactual | `plot_olg_results_fixed.py` |
| Fig. 4 policy-feasible region, Table 3 | `policy_analysis.py` |
| Fig. 5 response surfaces | `surface_figures.py` |
| Fig. 6 solvency frontiers | `surface_figures.py` |
| Supplementary sensitivity analysis | `rsa_all_v2.py`, `interaction_matrix.py` |
| Supplementary scaling test | `scaling.py` |
| Supplementary demography and regularities | `demographic_validation.py`, `plot_theory_neutral_1000ticks_burn400.py` |


## Figure numbering

Files in `outputs/` are named by their number in the doctoral thesis (`fig01`-`fig23`).
The journal article renumbers a subset of them; the table above gives the mapping.
The article's six figures correspond to thesis figures 2, 7+9, 10, 19+20, 21 and 23
respectively, and the remaining thesis figures appear in the article's Supplementary
Information. Filenames here are deliberately left at the thesis numbering so that the
scripts and the thesis remain consistent.

All figures are generated at 600 dpi.

## Data availability

`data/validation/` holds the BehaviorSpace exports behind every figure and table,
with two exceptions that exceed GitHub's file-size limit or are simply too large
to distribute: the five two-dimensional response-surface scans
(`… surf …-table.csv`) and the full 5x3 policy scan (`complete scan 5x3-table.csv`,
152 MB). Both can be regenerated with `run_surfaces.sh` and `run_all_rsa.sh`, and
are available from the author on request.

## Policy-rate experiment

The one-at-a-time policy-rate experiment applies an additive shift to the historical
policy-rate path, `policy-rate-shift` in {-0.25, 0, +0.25, +0.5, +0.75} percentage
points, floored at zero. `data/validation/1994-2003 policy-rate-shift-table.csv` is
the raw export; `outputs/fig16_oat_count_shift.png` and
`outputs/tab15_oat_count_shift_{level,rmse}.csv` are produced from it.

## Licence

MIT. See `LICENSE`.
