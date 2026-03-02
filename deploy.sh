#!/usr/bin/env bash
set -euo pipefail

cd /srv/xcommand-n8n-from-github

echo "[xcmd] Using project name: xcommand-n8n-rental"
export COMPOSE_PROJECT_NAME=xcommand-n8n-rental

echo "[xcmd] Pulling latest code from GitHub..."
git fetch origin main
git reset --hard origin/main

echo "[xcmd] Syncing git submodules..."
git submodule sync --recursive
git submodule update --init --recursive

echo "[xcmd] Building Lovable frontend and syncing into web/..."
# Don’t break the whole deploy if Node/npm isn’t installed on the server.
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  if [ -x "./scripts/lovable.sh" ]; then
    ./scripts/lovable.sh
  else
    echo "[xcmd] WARNING: ./scripts/lovable.sh not found or not executable. Skipping lovable build."
    echo "[xcmd] Fix: chmod +x ./scripts/lovable.sh"
  fi
else
  echo "[xcmd] WARNING: node/npm not found on server. Skipping lovable build."
  echo "[xcmd] Current deploy will continue using whatever frontend is already in web/."
fi

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