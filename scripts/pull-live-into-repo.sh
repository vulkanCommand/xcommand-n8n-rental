#!/usr/bin/env bash
set -euo pipefail

REPO="/srv/xcommand-n8n-from-github"

echo "[pull-live] Sync landing (xcommand.cloud) from /srv/n8n/landing -> repo..."
mkdir -p "$REPO/infra/n8n/landing"
rsync -av --delete /srv/n8n/landing/ "$REPO/infra/n8n/landing/"

echo "[pull-live] Pull app pages (app.xcommand.cloud) from container -> repo..."
mkdir -p "$REPO/infra/app-pages"
docker cp xcommand-n8n-rental-web-1:/app/index.html   "$REPO/infra/app-pages/index.html"
docker cp xcommand-n8n-rental-web-1:/app/ready.html   "$REPO/infra/app-pages/ready.html"
docker cp xcommand-n8n-rental-web-1:/app/support.html "$REPO/infra/app-pages/support.html"
docker cp xcommand-n8n-rental-web-1:/app/pay.html     "$REPO/infra/app-pages/pay.html"

echo
echo "[pull-live] Done. Git status:"
cd "$REPO"
git status --porcelain
