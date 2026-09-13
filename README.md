# CAMPS-Japan

Calibrated Agent-based Macroeconomic Pension System - Japan.
Agent-based overlapping-generations model of the Japanese economy and its
public pension system, calibrated on 1994-2003 and tested out of sample on
2009-2018.

## Layout

- `model/CAPMSJapan_v2.nlogo` - the model, including all BehaviorSpace experiments
- `run_all.sh` - single entry point: regenerates every figure and table
- `analysis/` - the ten scripts it calls, one per group of figures
- `simulations/` - NetLogo drivers that regenerate the BehaviorSpace exports
- `data/empirical/` - historical Japanese input and validation series, and
  `Japan_1994_2018_data_collection_EN.xlsx`, the full data-collection workbook
  (one sheet per series, sources documented in `00_README`)
- `data/validation/` - every raw BehaviorSpace export, gzip-compressed: the 22
  one-at-a-time sensitivity tables, the two response-surface scan sets, the
  5 x 3 policy scan, and the baseline, out-of-sample, demographic, OLG and
  scaling runs. `run_all.sh` unpacks them on first use
- `outputs/` - figures (fig01-fig23) and result tables (tab10-tab18) as produced by the scripts

## Reproducing the results

To regenerate every figure and table from the data in this repository:

    bash run_all.sh

That is the only command needed, and it needs Python but not NetLogo: the
simulation output it works from is in `data/validation/`. It takes about a
minute and writes to `outputs/`.

The first run unpacks the compressed simulation output, which adds about a
minute; later runs skip that step.

`--check` verifies the inputs and Python dependencies without writing anything;
`--list` shows which analysis produces which figure; `--with-simulations`
re-runs the NetLogo experiments from the model itself (NetLogo 6.4, several
hours) before redoing the analysis. Per-analysis logs go to `logs/`.

Requires Python 3.9 or newer with pandas, numpy, matplotlib and scipy; NetLogo
6.4 is needed only for `--with-simulations`.

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

Nothing is withheld. `data/validation/` contains every raw BehaviorSpace export
behind every figure and table in the paper, including the 5 x 3 policy scan and
the five two-dimensional response-surface scans. The exports are stored
gzip-compressed (`*.csv.gz`, 178 MB in total) so that each file fits within
GitHub's size limit; `run_all.sh` unpacks them on its first run, which restores
the 516 MB of plain CSV the analysis scripts read.

To unpack them by hand instead:

    gunzip -k data/validation/*.csv.gz

## Policy-rate experiment

The one-at-a-time policy-rate experiment applies an additive shift to the historical
policy-rate path, `policy-rate-shift` in {-0.25, 0, +0.25, +0.5, +0.75} percentage
points, floored at zero. `data/validation/1994-2003 policy-rate-shift-table.csv` is
the raw export; `outputs/fig16_oat_count_shift.png` and
`outputs/tab15_oat_count_shift_{level,rmse}.csv` are produced from it.

## Licence

MIT. See `LICENSE`.
