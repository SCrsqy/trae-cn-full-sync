#!/bin/bash

REPO_DIR="/Users/rs/AI"
LOG_FILE="$REPO_DIR/git_sync.log"

cd "$REPO_DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting git sync..." >> "$LOG_FILE"

git add .
git commit -m "Auto sync: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    git push origin main >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync successful" >> "$LOG_FILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Push failed" >> "$LOG_FILE"
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Nothing to commit" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
