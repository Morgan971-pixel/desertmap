#!/usr/bin/env bash
# setup_cron.sh
#
# Installs crontab entries that commit project work at real scheduled future times.
# Run this once after the initial commit is pushed to GitHub.
#
# Each cron entry fires bash scripts/scheduled_commits.sh <N> at a specific date and time.
# The symlink /Users/morgan/desertmap -> this repo is required (no spaces in cron paths).
#
# Usage: bash scripts/setup_cron.sh

set -euo pipefail

SYMLINK="/Users/morgan/desertmap"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Create symlink if it doesn't exist
if [ ! -L "$SYMLINK" ]; then
    ln -s "$REPO_DIR" "$SYMLINK"
    echo "Created symlink: $SYMLINK -> $REPO_DIR"
else
    echo "Symlink already exists: $SYMLINK"
fi

SCRIPT="$SYMLINK/scripts/scheduled_commits.sh"
LOG="$SYMLINK/scripts/commit.log"

# Export current crontab, append our entries, reload
TMPFILE=$(mktemp)

# Preserve any existing crontab entries
crontab -l 2>/dev/null > "$TMPFILE" || true

# Remove any previous desertmap entries to avoid duplicates
grep -v "desertmap" "$TMPFILE" > "${TMPFILE}.clean" && mv "${TMPFILE}.clean" "$TMPFILE" || true

cat >> "$TMPFILE" << CRON_ENTRIES
# DesertMap scheduled commits — do not edit manually
# Phase 1  — May 27, 10:00
0 10 27 5 * bash $SCRIPT 1 >> $LOG 2>&1
# Phase 2  — May 29, 09:00
0 9 29 5 * bash $SCRIPT 2 >> $LOG 2>&1
# Phase 3  — May 31, 14:00
0 14 31 5 * bash $SCRIPT 3 >> $LOG 2>&1
# Phase 4  — June 2, 10:00
0 10 2 6 * bash $SCRIPT 4 >> $LOG 2>&1
# Phase 5  — June 5, 11:00
0 11 5 6 * bash $SCRIPT 5 >> $LOG 2>&1
# Phase 6  — June 7, 14:00
0 14 7 6 * bash $SCRIPT 6 >> $LOG 2>&1
# Phase 7  — June 10, 10:00
0 10 10 6 * bash $SCRIPT 7 >> $LOG 2>&1
# Phase 8  — June 13, 15:00
0 15 13 6 * bash $SCRIPT 8 >> $LOG 2>&1
# Phase 9  — June 17, 11:00
0 11 17 6 * bash $SCRIPT 9 >> $LOG 2>&1
# Phase 10 — June 20, 10:00
0 10 20 6 * bash $SCRIPT 10 >> $LOG 2>&1
# Phase 11 — June 23, 14:00
0 14 23 6 * bash $SCRIPT 11 >> $LOG 2>&1
CRON_ENTRIES

crontab "$TMPFILE"
rm "$TMPFILE"

echo ""
echo "Crontab installed. Schedule:"
echo "  Phase 1  — May 27  10:00  project goals and bias docs"
echo "  Phase 2  — May 29  09:00  EDA notebook + class/feature plots"
echo "  Phase 3  — May 31  14:00  EDA correlation + demographic quartile"
echo "  Phase 4  — Jun 02  10:00  data cleaning notebook"
echo "  Phase 5  — Jun 05  11:00  logistic regression baseline"
echo "  Phase 6  — Jun 07  14:00  baseline coefficient plot"
echo "  Phase 7  — Jun 10  10:00  random forest notebook"
echo "  Phase 8  — Jun 13  15:00  RF metrics + SHAP figures"
echo "  Phase 9  — Jun 17  11:00  pre-computed predictions parquet"
echo "  Phase 10 — Jun 20  10:00  fairness audit notebook + figures"
echo "  Phase 11 — Jun 23  14:00  fairness audit documentation"
echo ""
echo "IMPORTANT: your laptop must be awake at each scheduled time."
echo "If it is asleep, run the missed phase manually:"
echo "  bash scripts/scheduled_commits.sh <phase_number>"
echo ""
echo "Check commit.log for execution status:"
echo "  tail -f scripts/commit.log"
