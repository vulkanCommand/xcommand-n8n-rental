#!/usr/bin/env bash
set -euo pipefail

# Paths
REPO_LANDING="/srv/xcommand-n8n-from-github/landing/index.html"
LIVE_LANDING="/srv/landing/index.html"

echo "[sync] Backing up live landing page..."
cp "$LIVE_LANDING" "${LIVE_LANDING}.bak-$(date +%Y%m%d-%H%M%S)"

echo "[sync] Copying repo landing -> live..."
cp "$REPO_LANDING" "$LIVE_LANDING"

echo "[sync] Done. Refresh your browser (Ctrl+F5) to see changes."
