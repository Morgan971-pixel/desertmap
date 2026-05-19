#!/usr/bin/env bash
# scheduled_commits.sh
#
# Commits pre-built project work to GitHub at real scheduled times via cron.
# Each phase stages a specific set of files and pushes with no date manipulation.
#
# Usage: bash scripts/scheduled_commits.sh <phase_number>
#
# Cron entries are installed by scripts/setup_cron.sh.
# Do not invoke this script directly unless manually triggering a phase.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GIT="/usr/bin/git"
LOG="$REPO_DIR/scripts/commit.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

cd "$REPO_DIR" || { echo "ERROR: cannot cd to $REPO_DIR"; exit 1; }

already_committed() {
    # Returns 0 (true) if the given file is already tracked by git
    $GIT ls-files --error-unmatch "$1" > /dev/null 2>&1
}

safe_add() {
    # Adds a file only if it exists and is not already committed
    local file="$1"
    if [ ! -e "$file" ]; then
        log "SKIP: $file does not exist yet"
        return 0
    fi
    if already_committed "$file"; then
        log "SKIP: $file already in git"
        return 0
    fi
    $GIT add "$file"
    log "STAGED: $file"
}

commit_and_push() {
    local msg="$1"
    if $GIT diff --cached --quiet; then
        log "Nothing staged — phase already committed or files missing. Skipping."
        return 0
    fi
    $GIT commit -m "$msg"
    $GIT push origin main
    log "PUSHED: $msg"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — May 27, 10:00
# Project goals and bias documentation
# ─────────────────────────────────────────────────────────────────────────────
phase_1() {
    log "=== Phase 1: project goals and bias documentation ==="
    safe_add "docs/smart_goals.md"
    safe_add "docs/bias_identification.md"
    commit_and_push "add project goals, SMART milestones, and bias identification"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — May 29, 09:00
# EDA notebook — class distribution and feature plots
# ─────────────────────────────────────────────────────────────────────────────
phase_2() {
    log "=== Phase 2: EDA notebook and initial figures ==="
    safe_add "notebooks/01_eda.ipynb"
    safe_add "outputs/figures/01_class_distribution.png"
    safe_add "outputs/figures/01_feature_distributions.png"
    commit_and_push "add EDA — class balance and feature distributions across 72k tracts"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — May 31, 14:00
# EDA — correlation matrix and demographic stratification
# ─────────────────────────────────────────────────────────────────────────────
phase_3() {
    log "=== Phase 3: EDA correlation and demographic quartile preview ==="
    safe_add "outputs/figures/01_correlation_matrix.png"
    safe_add "outputs/figures/01_demographic_quartile_preview.png"
    commit_and_push "extend EDA — correlation matrix and demographic stratification by food desert status"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — June 2, 10:00
# Data cleaning notebook and post-cleaning plots
# ─────────────────────────────────────────────────────────────────────────────
phase_4() {
    log "=== Phase 4: cleaning notebook ==="
    safe_add "notebooks/02_cleaning.ipynb"
    safe_add "outputs/figures/02_post_cleaning_boxplots.png"
    commit_and_push "add data cleaning — median imputation, IQR capping, null audit"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5 — June 5, 11:00
# Baseline logistic regression — metrics and evaluation plots
# ─────────────────────────────────────────────────────────────────────────────
phase_5() {
    log "=== Phase 5: logistic regression baseline ==="
    safe_add "notebooks/03_baseline_model.ipynb"
    safe_add "outputs/baseline_metrics.json"
    safe_add "outputs/figures/03_confusion_matrix.png"
    safe_add "outputs/figures/03_roc_pr_curves.png"
    commit_and_push "add logistic regression baseline — F1 0.438, ROC-AUC 0.838"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6 — June 7, 14:00
# Baseline — coefficient analysis
# ─────────────────────────────────────────────────────────────────────────────
phase_6() {
    log "=== Phase 6: baseline coefficient plot ==="
    safe_add "outputs/figures/03_logistic_coefficients.png"
    commit_and_push "add coefficient analysis — income and racial features among top predictors"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 7 — June 10, 10:00
# Random forest — model and initial evaluation
# ─────────────────────────────────────────────────────────────────────────────
phase_7() {
    log "=== Phase 7: random forest notebook ==="
    safe_add "notebooks/04_random_forest.ipynb"
    safe_add "outputs/figures/04_confusion_matrix_rf.png"
    commit_and_push "add random forest with grid search over depth and estimator count"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 8 — June 13, 15:00
# RF metrics and SHAP figures
# ─────────────────────────────────────────────────────────────────────────────
phase_8() {
    log "=== Phase 8: RF metrics and SHAP figures ==="
    safe_add "outputs/rf_metrics.json"
    safe_add "outputs/figures/04_shap_bar.png"
    safe_add "outputs/figures/04_shap_summary.png"
    commit_and_push "evaluate random forest — F1 0.525, SHAP bar and beeswarm for feature importance"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 9 — June 17, 11:00
# Pre-computed SHAP predictions parquet
# ─────────────────────────────────────────────────────────────────────────────
phase_9() {
    log "=== Phase 9: pre-computed predictions parquet ==="
    safe_add "outputs/tract_predictions_shap.parquet"
    commit_and_push "pre-compute SHAP values for all 72k tracts — export for Streamlit lookup"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 10 — June 20, 10:00
# Fairness audit notebook and figures
# ─────────────────────────────────────────────────────────────────────────────
phase_10() {
    log "=== Phase 10: fairness audit notebook and figures ==="
    safe_add "notebooks/05_fairness_audit.ipynb"
    safe_add "data/raw/holc_tract_crosswalk.csv"
    safe_add "outputs/figures/05_quartile_black.png"
    safe_add "outputs/figures/05_quartile_hispanic.png"
    safe_add "outputs/figures/05_holc_audit.png"
    commit_and_push "add fairness audit — quartile analysis, counterfactual probe, HOLC overlay"
}

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 11 — June 23, 14:00
# Fairness documentation and metrics JSON
# ─────────────────────────────────────────────────────────────────────────────
phase_11() {
    log "=== Phase 11: fairness audit documentation ==="
    safe_add "docs/fairness_audit.md"
    safe_add "outputs/fairness_metrics.json"
    commit_and_push "document fairness findings — 5.9x FPR disparity, HOLC odds ratio 1.57x"
}

# ─────────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────────
PHASE="${1:-}"
if [ -z "$PHASE" ]; then
    echo "Usage: bash scripts/scheduled_commits.sh <phase_number>"
    echo "Phases: 1 through 11"
    exit 1
fi

case "$PHASE" in
    1)  phase_1  ;;
    2)  phase_2  ;;
    3)  phase_3  ;;
    4)  phase_4  ;;
    5)  phase_5  ;;
    6)  phase_6  ;;
    7)  phase_7  ;;
    8)  phase_8  ;;
    9)  phase_9  ;;
    10) phase_10 ;;
    11) phase_11 ;;
    *)  echo "Unknown phase: $PHASE. Valid: 1-11"; exit 1 ;;
esac
