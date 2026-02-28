#!/usr/bin/env bash
set -euo pipefail

cd /srv/xcommand-n8n-from-github

echo "[xcmd] Using project name: xcommand-n8n-rental"
export COMPOSE_PROJECT_NAME=xcommand-n8n-rental

echo "[xcmd] Pulling latest code from GitHub..."
git fetch origin main
git reset --hard origin/main

echo "[xcmd] Bringing up containers (build if needed)..."
docker compose up -d --build

echo "[xcmd] Current containers:"
docker compose ps

echo "[xcmd] Deploy complete."

echo "[deploy] Syncing landing (Lovable) into legacy n8n paths..."
mkdir -p /srv/n8n/landing /srv/n8n/site

# Copy the full landing bundle (index + assets + nginx.conf + robots.txt + support.html etc.)
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/. /srv/n8n/landing/
# Keep legacy /srv/n8n/site/index.html in sync too
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/index.html /srv/n8n/site/index.html

echo "[deploy] Landing sync complete."

echo "[deploy] Syncing app pages (pay/ready/support) into legacy n8n landing..."
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/pay.html     /srv/n8n/landing/pay.html
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/ready.html   /srv/n8n/landing/ready.html
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/support.html /srv/n8n/landing/support.html

echo "[deploy] App pages sync complete."