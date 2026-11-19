#!/usr/bin/env bash
# Re-run the analysis and rebuild everything the site shows.
#
# Stage 1, in parallel (each step reads only committed inputs):
#   nb04 tuning + metrics, nb05 fairness audit, nb06 XAI figures, scripts/tract_shap.py
# Stage 2, in order: consistency check, site export, tests, model card, old-vs-new numbers.
#
#   scripts/refresh.sh                 # SHAP_JOBS=6 by default
#   SHAP_JOBS=4 scripts/refresh.sh     # cooler laptop, slower
#
# Logs go to logs/refresh-<time>/. Exit code is non-zero if any step fails.
set -euo pipefail
cd "$(dirname "$0")/.."

SHAP_JOBS=${SHAP_JOBS:-6}
LOG="logs/refresh-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG"
cp site/data/summary.json "$LOG/summary.before.json"
caffeinate -i -w $$ &   # keep the Mac awake while this script runs
start=$(date +%s)

nbx() { uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "notebooks/$1"; }
step() {  # step NAME CMD...: run CMD, log to $LOG/NAME.log, report one line
  local name=$1; shift
  local t0; t0=$(date +%s)
  if "$@" >"$LOG/$name.log" 2>&1; then
    echo "done  $name ($(( $(date +%s) - t0 ))s)"
  else
    echo "FAIL  $name, last lines of $LOG/$name.log:"; tail -n 15 "$LOG/$name.log"; return 1
  fi
}

echo "stage 1 (parallel), logs in $LOG"
pids=()
step tract_shap uv run python scripts/tract_shap.py --jobs "$SHAP_JOBS" & pids+=($!)
step nb04 nbx 04_random_forest.ipynb & pids+=($!)
step nb05 nbx 05_fairness_audit.ipynb & pids+=($!)
step nb06 nbx 06_xai.ipynb & pids+=($!)
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
[ "$fail" = 0 ] || { echo "stage 1 failed"; exit 1; }

echo "stage 2"
step check uv run python scripts/check_consistency.py && cat "$LOG/check.log"
step export uv run python scripts/export_static_data.py
step pytest uv run pytest -q
step node_tests node --test tests/js/*.test.js
if command -v tectonic >/dev/null; then
  step model_card sh -c 'uv run python docs/model_card/make_assets.py && tectonic docs/model_card/model_card.tex \
    && cp docs/model_card/model_card.pdf docs/model_card/desertmap_model_card.pdf \
    && cp docs/model_card/model_card.pdf site/model-card.pdf'
else
  echo "skip  model_card (tectonic not installed)"
fi

echo "numbers that changed in site/data/summary.json:"
uv run python - "$LOG/summary.before.json" site/data/summary.json <<'EOF'
import json, sys
def flat(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f"{p}.{k}" if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f"{p}[{i}]")
    else:
        yield p, x
old, new = (dict(flat(json.load(open(f)))) for f in sys.argv[1:3])
rows = [(k, old.get(k), v) for k, v in new.items() if old.get(k) != v]
for k, a, b in rows[:40]:
    print(f"  {k}: {a} -> {b}")
print(f"  ({len(rows)} changed, {len(set(old) - set(new))} removed)")
EOF
echo "total $(( ($(date +%s) - start) / 60 )) min"
