#!/usr/bin/env bash
# =============================================================================
# CAMPS-Japan - reproduce every figure and table
#
#   bash run_all_analysis.sh            run everything possible
#   bash run_all_analysis.sh --check    only check inputs and dependencies
#   bash run_all_analysis.sh --list     list the scripts and what they produce
#
# Reads   data/empirical/ and data/validation/
# Writes  outputs/
# Nothing outside outputs/ is modified. Re-running is safe; files are overwritten.
#
# Two of the analyses need BehaviorSpace exports that are too large to ship in
# this repository. They are skipped automatically, with a note saying which
# experiment regenerates the missing file. Everything else runs from the data
# included here.
# =============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"
export MPLBACKEND=Agg          # write figures to file, never open a window
export PYTHONWARNINGS=ignore

MODE="run"
case "${1:-}" in
  --check) MODE="check" ;;
  --list)  MODE="list" ;;
  -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "") ;;
  *) echo "unknown option: $1 (try --help)"; exit 2 ;;
esac

# ---- script | required input files (| separated) | what it produces ---------
JOBS=(
"validate_1994-2003_smoothed.py|data/validation/1994-2003-table.csv;data/empirical/real-data1.csv|Figure 7, Figure S7, Figure 8, Table 10"
"validate_2009-2018_smoothed_.py|data/validation/2009-2018-table.csv;data/empirical/real-data2.csv|Figure 9, Figure S9, Figure S-financial, Table 12"
"demographic_validation.py|data/validation/demographic validation-table.csv;data/empirical/population1994.csv;data/empirical/real death prob.csv|Figure 4, Figure 5"
"plot_theory_neutral_1000ticks_burn400.py|data/validation/1994-2003-theory.csv|Figure 6"
"plot_olg_results_fixed.py|data/validation/olg check-table.csv|Figure 10, Figure 11, Figure 12"
"scaling.py|data/validation/scaling-table.csv|Figure 13, Figure 14, Figure 15"
"rsa_all_v2.py|data/validation/1994-2003 policy-rate-shift-table.csv;data/empirical/real-data1.csv|Figure 16, Figure 17, Table 15, Table 16"
"policy_analysis.py|data/validation/complete scan 5x3-table.csv|Figure 19, Figure 20, Table 17"
"interaction_matrix.py|data/validation/complete scan 5x3-table.csv|Figure 18, Table 18"
"surface_figures.py|data/validation/1994-2003 surf mpc x retire-table.csv|Figure 21, Figure 22, Figure 23, and supplementary surfaces"
)

# how to regenerate each missing input
regen_hint () {
  case "$1" in
    *"complete scan 5x3"*)  echo "run the '1994-2003 complete scan 5x3' BehaviorSpace experiment (bash run_all_rsa.sh)" ;;
    *"surf "*)              echo "run the five surface scans (bash run_surfaces.sh)" ;;
    *)                      echo "see Data availability in README.md" ;;
  esac
}

rule () { printf '%.0s-' {1..74}; echo; }

# ---- listing ----------------------------------------------------------------
if [ "$MODE" = "list" ]; then
  printf '%-42s  %s\n' "SCRIPT" "PRODUCES"; rule
  for j in "${JOBS[@]}"; do
    IFS='|' read -r s _ o <<< "$j"
    printf '%-42s  %s\n' "$s" "$o"
  done
  exit 0
fi

# ---- interpreter and packages ----------------------------------------------
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "error: $PY not found. Install Python 3.9 or newer."; exit 1; }
echo "python  : $("$PY" -c 'import sys;print(sys.version.split()[0], "at", sys.executable)')"

MISSING_PKG=""
for pkg in pandas numpy matplotlib scipy; do
  "$PY" -c "import $pkg" 2>/dev/null || MISSING_PKG="$MISSING_PKG $pkg"
done
if [ -n "$MISSING_PKG" ]; then
  echo
  echo "error: missing Python packages:$MISSING_PKG"
  echo "install them with:"
  echo "    $PY -m pip install pandas numpy matplotlib scipy"
  exit 1
fi
echo "packages: pandas, numpy, matplotlib, scipy - all present"
echo "outputs : $REPO/outputs"
echo

# ---- input check ------------------------------------------------------------
RUNNABLE=(); SKIPPED=()
for j in "${JOBS[@]}"; do
  IFS='|' read -r script inputs _ <<< "$j"
  lack=""
  IFS=';' read -ra files <<< "$inputs"
  for f in "${files[@]}"; do [ -f "$REPO/$f" ] || lack="$f"; done
  if [ -n "$lack" ]; then SKIPPED+=("$script|$lack"); else RUNNABLE+=("$j"); fi
done

if [ ${#SKIPPED[@]} -gt 0 ]; then
  echo "The following analyses will be skipped - their input is not in this repository:"
  for s in "${SKIPPED[@]}"; do
    IFS='|' read -r script lack <<< "$s"
    echo "  - $script"
    echo "      needs : $lack"
    echo "      to get it: $(regen_hint "$lack")"
  done
  echo
fi

if [ "$MODE" = "check" ]; then
  echo "${#RUNNABLE[@]} of ${#JOBS[@]} analyses can run with the data present. No files were written."
  exit 0
fi

# ---- run --------------------------------------------------------------------
mkdir -p "$REPO/outputs" "$REPO/logs"
BEFORE=$(ls -1 "$REPO/outputs" 2>/dev/null | wc -l | tr -d ' ')
START=$(date +%s)
OK=0; FAILED=()

for j in "${RUNNABLE[@]}"; do
  IFS='|' read -r script _ produces <<< "$j"
  log="$REPO/logs/${script%.py}.log"
  printf '%-42s ' "$script"
  t0=$(date +%s)
  if "$PY" "$REPO/analysis/$script" > "$log" 2>&1; then
    printf 'ok   %3ds   %s\n' "$(( $(date +%s) - t0 ))" "$produces"
    OK=$((OK+1))
  else
    printf 'FAILED    see logs/%s\n' "$(basename "$log")"
    tail -n 3 "$log" | sed 's/^/      | /'
    FAILED+=("$script")
  fi
done

# ---- summary ----------------------------------------------------------------
AFTER=$(ls -1 "$REPO/outputs" 2>/dev/null | wc -l | tr -d ' ')
echo; rule
echo "ran      : $OK of ${#JOBS[@]} analyses   (${#SKIPPED[@]} skipped for missing data, ${#FAILED[@]} failed)"
echo "elapsed  : $(( ($(date +%s) - START) / 60 ))m $(( ($(date +%s) - START) % 60 ))s"
echo "outputs/ : $BEFORE files before, $AFTER after"
echo "logs     : logs/  (one per analysis)"
rule
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "failed:"; for f in "${FAILED[@]}"; do echo "  - $f  ->  logs/${f%.py}.log"; done
  exit 1
fi
echo "Done. Every figure and table in outputs/ was regenerated from the data in this repository."
