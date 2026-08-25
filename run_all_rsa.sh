#!/bin/bash
# ============================================================
# CAMPS-Japan — run all 22 OAT sensitivity experiments headless
#
#   bash run_all_rsa.sh              # run everything, skip finished ones
#   FORCE=1 bash run_all_rsa.sh      # re-run everything from scratch
#   THREADS=4 bash run_all_rsa.sh    # limit parallelism
#   bash run_all_rsa.sh mpc-income credit-thre    # run only these
#
# Output goes to  data/validation/1994-2003 <param>-table.csv
# which is exactly what analysis/rsa_all_v2.py expects.
# ============================================================
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$REPO/data/validation"
LOG="$REPO/rsa_run.log"

# ---------- locate the model ----------
MODEL="${MODEL:-}"
if [[ -z "$MODEL" ]]; then
  for cand in "$REPO/model/CAPMSJapan_v2.nlogo" \
              "$REPO/model/CAPMS-Japan_v2.nlogo" \
              "$HOME/Downloads/CAPMSJapan_v2.nlogo"; do
    [[ -f "$cand" ]] && MODEL="$cand" && break
  done
fi
if [[ ! -f "$MODEL" ]]; then
  echo "ERROR: model file not found. Set it explicitly:"
  echo "  MODEL=/path/to/CAPMSJapan_v2.nlogo bash run_all_rsa.sh"
  exit 1
fi

# ---------- locate NetLogo ----------
NETLOGO="${NETLOGO:-}"
if [[ -z "$NETLOGO" ]]; then
  for cand in "$HOME/Downloads/NetLogo 6.4.0" \
              "/Applications/NetLogo 6.4.0" \
              "$HOME/Applications/NetLogo 6.4.0"; do
    [[ -x "$cand/netlogo-headless.sh" ]] && NETLOGO="$cand" && break
  done
fi
if [[ ! -x "${NETLOGO:-}/netlogo-headless.sh" ]]; then
  echo "ERROR: netlogo-headless.sh not found. Set it explicitly:"
  echo "  NETLOGO='/path/to/NetLogo 6.4.0' bash run_all_rsa.sh"
  exit 1
fi

# ---------- locate a JVM ----------
# The runtime bundled with NetLogo has no launcher, so a system JDK is required.
if [[ -z "${JAVA_HOME:-}" ]]; then
  if [[ -x /usr/libexec/java_home ]] && /usr/libexec/java_home >/dev/null 2>&1; then
    JAVA_HOME="$(/usr/libexec/java_home)"
    export JAVA_HOME
  fi
fi
JAVA_BIN="${JAVA_HOME:+$JAVA_HOME/bin/}java"
if ! command -v "$JAVA_BIN" >/dev/null 2>&1 && ! [[ -x "$JAVA_BIN" ]]; then
  echo "ERROR: no Java runtime found."
  echo "  Install one, e.g.:  brew install --cask temurin"
  echo "  or download from https://adoptium.net , then re-run."
  exit 1
fi

# ---------- the 22 parameters ----------
PARAMS=(
  birth-count-shift
  lend-rate-shift
  deposit-rate-shift
  credit-thre
  default-tole
  debt-repayment-rate
  consumer-choices
  job-applications
  retirement-ages
  death-prob-shift
  productivity-growth-scale
  wage-growth-scale
  pension-replace-scale
  paygo-rate-scale
  mpc-income
  mpc-wealth
  reorganization-prob
  profit-tax-rate
  credit-memory-window
  contract-length
  price-adjustment
  production-adjustment
)
# command-line arguments override the full list
if [[ $# -gt 0 ]]; then PARAMS=("$@"); fi

THREAD_ARG=()
[[ -n "${THREADS:-}" ]] && THREAD_ARG=(--threads "$THREADS")

mkdir -p "$OUT"
echo "model   : $MODEL"          | tee    "$LOG"
echo "netlogo : $NETLOGO"        | tee -a "$LOG"
echo "java    : ${JAVA_HOME:-(from PATH)}" | tee -a "$LOG"
echo "output  : $OUT"            | tee -a "$LOG"
echo "count   : ${#PARAMS[@]} experiments" | tee -a "$LOG"
echo "started : $(date '+%F %T')" | tee -a "$LOG"
echo "------------------------------------------------------------" | tee -a "$LOG"

BATCH_START=$SECONDS
declare -a FAILED=() SKIPPED=() DONE_LIST=()
i=0
for p in "${PARAMS[@]}"; do
  i=$((i+1))
  exp="1994-2003 $p"
  csv="$OUT/1994-2003 $p-table.csv"

  if [[ -s "$csv" && -z "${FORCE:-}" ]]; then
    echo "[$i/${#PARAMS[@]}] SKIP  $p  (output exists; FORCE=1 to redo)" | tee -a "$LOG"
    SKIPPED+=("$p"); continue
  fi

  echo "[$i/${#PARAMS[@]}] RUN   $p  ($(date '+%H:%M:%S'))" | tee -a "$LOG"
  t0=$SECONDS
  if "$NETLOGO/netlogo-headless.sh" \
        --model "$MODEL" \
        --experiment "$exp" \
        --table "$csv" \
        "${THREAD_ARG[@]}" >>"$LOG" 2>&1; then
    dt=$((SECONDS-t0))
    sz=$(du -h "$csv" 2>/dev/null | cut -f1)
    printf '            done in %dm%02ds  (%s)\n' $((dt/60)) $((dt%60)) "${sz:-?}" | tee -a "$LOG"
    DONE_LIST+=("$p")
  else
    dt=$((SECONDS-t0))
    printf '            FAILED after %dm%02ds  — see %s\n' $((dt/60)) $((dt%60)) "$LOG" | tee -a "$LOG"
    rm -f "$csv"       # never leave a truncated table behind
    FAILED+=("$p")
  fi
done

TOT=$((SECONDS-BATCH_START))
echo "------------------------------------------------------------" | tee -a "$LOG"
printf 'finished: %s   total %dh%02dm%02ds\n' "$(date '+%F %T')" $((TOT/3600)) $(((TOT%3600)/60)) $((TOT%60)) | tee -a "$LOG"
echo "  ran     : ${#DONE_LIST[@]}"  | tee -a "$LOG"
echo "  skipped : ${#SKIPPED[@]}"    | tee -a "$LOG"
echo "  failed  : ${#FAILED[@]} ${FAILED[*]:-}" | tee -a "$LOG"
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo "" | tee -a "$LOG"
  echo "Next:  python analysis/rsa_all_v2.py" | tee -a "$LOG"
else
  exit 1
fi
