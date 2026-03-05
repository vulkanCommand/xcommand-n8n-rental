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

echo "[deploy] Syncing landing to /srv/n8n/landing (THIS is what public site serves)..."
mkdir -p /srv/n8n/landing /srv/n8n/site

# If Lovable build produced /web, make infra/n8n/landing reflect it
# (so we have one canonical copy), then publish to /srv/n8n/landing
if [ -d "/srv/xcommand-n8n-from-github/web" ] && [ -f "/srv/xcommand-n8n-from-github/web/index.html" ]; then
  echo "[deploy] Updating infra/n8n/landing from web/ build output..."
  # Keep infra/n8n/landing extra files, but overwrite the pages/assets from web/
  cp -a /srv/xcommand-n8n-from-github/web/. /srv/xcommand-n8n-from-github/infra/n8n/landing/
fi

# Publish the canonical landing bundle
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/. /srv/n8n/landing/
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/index.html /srv/n8n/site/index.html

echo "[deploy] Landing sync complete."

echo "[deploy] Force support API_BASE => https://api.app.xcommand.cloud (prevents CORS issues)"
if [ -f "/srv/n8n/landing/support.html" ]; then
  # Replace any existing API_BASE assignment line
  sed -i -E 's|^const API_BASE = .*;|const API_BASE = "https://api.app.xcommand.cloud";|g' /srv/n8n/landing/support.html || true
fi

echo "[deploy] Restarting landing container to serve latest HTML..."
docker restart landing >/dev/null 2>&1 || true

echo "[deploy] Final check (public pay.html hash should match /srv/n8n/landing/pay.html):"
sha256sum /srv/n8n/landing/pay.html | awk '{print "[deploy] /srv/n8n/landing/pay.html sha256:", $1}'
curl -s https://www.xcommand.cloud/pay.html | sha256sum | awk '{print "[deploy] public /pay.html sha256:", $1}'

echo "[deploy] Final check (public support API_BASE line):"
curl -s https://www.xcommand.cloud/support.html | grep -m1 "const API_BASE" || true