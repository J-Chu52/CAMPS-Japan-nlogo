#!/bin/bash
# ============================================================
# CAMPS-Japan — run the four 2-parameter response-surface scans headless
#
#   bash run_surfaces.sh                  # run all four, skip finished ones
#   FORCE=1 bash run_surfaces.sh          # re-run everything
#   THREADS=4 bash run_surfaces.sh        # limit parallelism
#   bash run_surfaces.sh "surf mpc x retire"    # run only matching ones
#
# 34,500 runs total (1,150 parameter cells x 30 repetitions).
# Output: data/validation/1994-2003 surf <a> x <b>-table.csv
# Detection logic is identical to run_all_rsa.sh.
# ============================================================
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$REPO/data/validation"
LOG="$REPO/surfaces_run.log"

MODEL="${MODEL:-}"
if [[ -z "$MODEL" ]]; then
  for cand in "$REPO/model/CAPMSJapan_v2.nlogo" \
              "$REPO/model/CAPMS-Japan_v2.nlogo" \
              "$HOME/Downloads/CAPMSJapan_v2.nlogo"; do
    [[ -f "$cand" ]] && MODEL="$cand" && break
  done
fi
[[ -f "$MODEL" ]] || { echo "ERROR: model not found. MODEL=/path/to/CAPMSJapan_v2.nlogo bash run_surfaces.sh"; exit 1; }

NETLOGO="${NETLOGO:-}"
if [[ -z "$NETLOGO" ]]; then
  for cand in "$HOME/Downloads/NetLogo 6.4.0" \
              "/Applications/NetLogo 6.4.0" \
              "$HOME/Applications/NetLogo 6.4.0"; do
    [[ -x "$cand/netlogo-headless.sh" ]] && NETLOGO="$cand" && break
  done
fi
[[ -x "${NETLOGO:-}/netlogo-headless.sh" ]] || { echo "ERROR: netlogo-headless.sh not found. NETLOGO='/path/to/NetLogo 6.4.0' bash run_surfaces.sh"; exit 1; }

# JAVA_VERSION=17 bash run_surfaces.sh  -> pick a specific installed JDK
if [[ -z "${JAVA_HOME:-}" ]]; then
  if [[ -x /usr/libexec/java_home ]]; then
    if [[ -n "${JAVA_VERSION:-}" ]]; then
      JAVA_HOME="$(/usr/libexec/java_home -v "$JAVA_VERSION" 2>/dev/null || true)"
    else
      JAVA_HOME="$(/usr/libexec/java_home 2>/dev/null || true)"
    fi
    [[ -n "$JAVA_HOME" ]] && export JAVA_HOME
  fi
fi
JAVA_BIN="${JAVA_HOME:+$JAVA_HOME/bin/}java"
# macOS ships a /usr/bin/java stub that exists but is not a JDK, so actually RUN it
if ! "$JAVA_BIN" -version >/dev/null 2>&1; then
  echo "ERROR: no working Java runtime."
  echo "  JAVA_BIN tried : $JAVA_BIN"
  echo "  Install one    : brew install --cask temurin@17"
  echo "                   or https://adoptium.net  (Temurin 17, macOS aarch64)"
  echo "  Then re-run. To pick a version: JAVA_VERSION=17 bash run_surfaces.sh"
  exit 1
fi
JAVA_DESC="$("$JAVA_BIN" -version 2>&1 | head -1)"

# smallest first, so a configuration error surfaces in minutes, not hours
SCANS=(
  "surf mpc x birth"
  "surf mpc x retire"
  "surf replace x paygo"
  "surf mpc x productivity"
  "surf replace x retire"
  "cube mpc x retire x replace"
)
if [[ $# -gt 0 ]]; then SCANS=("$@"); fi

THREAD_ARG=()
[[ -n "${THREADS:-}" ]] && THREAD_ARG=(--threads "$THREADS")

mkdir -p "$OUT"
{
  echo "model   : $MODEL"
  echo "netlogo : $NETLOGO"
  echo "java    : ${JAVA_HOME:-(from PATH)}"
  echo "          $JAVA_DESC"
  echo "output  : $OUT"
  echo "count   : ${#SCANS[@]} scans, 34500 runs total"
  echo "started : $(date '+%F %T')"
  echo "------------------------------------------------------------"
} | tee "$LOG"

BATCH_START=$SECONDS
declare -a FAILED=() SKIPPED=() DONE_LIST=()
i=0
for sc in "${SCANS[@]}"; do
  i=$((i+1))
  exp="1994-2003 $sc"
  csv="$OUT/$exp-table.csv"

  if [[ -s "$csv" && -z "${FORCE:-}" ]]; then
    echo "[$i/${#SCANS[@]}] SKIP  $sc  (output exists; FORCE=1 to redo)" | tee -a "$LOG"
    SKIPPED+=("$sc"); continue
  fi

  echo "[$i/${#SCANS[@]}] RUN   $sc  ($(date '+%H:%M:%S'))" | tee -a "$LOG"
  t0=$SECONDS
  if "$NETLOGO/netlogo-headless.sh" \
        --model "$MODEL" --experiment "$exp" --table "$csv" \
        ${THREAD_ARG[@]+"${THREAD_ARG[@]}"} >>"$LOG" 2>&1; then
    dt=$((SECONDS-t0)); sz=$(du -h "$csv" 2>/dev/null | cut -f1)
    printf '            done in %dh%02dm%02ds  (%s)\n' $((dt/3600)) $(((dt%3600)/60)) $((dt%60)) "${sz:-?}" | tee -a "$LOG"
    DONE_LIST+=("$sc")
  else
    dt=$((SECONDS-t0))
    printf '            FAILED after %dm%02ds — see %s\n' $((dt/60)) $((dt%60)) "$LOG" | tee -a "$LOG"
    rm -f "$csv"
    FAILED+=("$sc")
    # fail fast: if the very first scan dies, the config is wrong — do not burn the night
    if [[ $i -eq 1 ]]; then
      echo "First scan failed; aborting so the rest of the batch is not wasted." | tee -a "$LOG"
      exit 1
    fi
  fi
done

TOT=$((SECONDS-BATCH_START))
{
  echo "------------------------------------------------------------"
  printf 'finished: %s   total %dh%02dm%02ds\n' "$(date '+%F %T')" $((TOT/3600)) $(((TOT%3600)/60)) $((TOT%60))
  echo "  ran     : ${#DONE_LIST[@]}"
  echo "  skipped : ${#SKIPPED[@]}"
  echo "  failed  : ${#FAILED[@]} ${FAILED[*]:-}"
} | tee -a "$LOG"
[[ ${#FAILED[@]} -eq 0 ]] || exit 1
