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

echo "[xcmd] Checking if node/npm exist..."
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  if [ -x "./scripts/lovable.sh" ]; then
    echo "[xcmd] Building lovable frontend..."
    ./scripts/lovable.sh
  else
    echo "[xcmd] WARNING: ./scripts/lovable.sh not executable."
  fi
else
  echo "[xcmd] Node/npm not installed on server. Using committed build output."
fi

echo "[xcmd] Starting containers..."
docker compose up -d --build

echo "[xcmd] Containers:"
docker compose ps

echo "[deploy] Preparing landing directories..."
mkdir -p /srv/n8n/landing
mkdir -p /srv/n8n/site

echo "[deploy] Syncing web build to landing..."

if [ -d "/srv/xcommand-n8n-from-github/web" ] && [ -f "/srv/xcommand-n8n-from-github/web/index.html" ]; then
  cp -a /srv/xcommand-n8n-from-github/web/. /srv/xcommand-n8n-from-github/infra/n8n/landing/
fi

cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/. /srv/n8n/landing/
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/index.html /srv/n8n/site/index.html

echo "[deploy] Fixing API_BASE in support.html"

if [ -f "/srv/n8n/landing/support.html" ]; then
  sed -i -E 's|^const API_BASE = .*;|const API_BASE = "https://api.app.xcommand.cloud";|g' /srv/n8n/landing/support.html || true
fi

echo "[deploy] Restart landing container..."
docker restart landing >/dev/null 2>&1 || true

echo "[deploy] Checking deployed hashes..."

sha256sum /srv/n8n/landing/pay.html | awk '{print "[deploy] landing pay.html sha256:", $1}'

curl -s https://www.xcommand.cloud/pay.html | sha256sum | awk '{print "[deploy] public pay.html sha256:", $1}'

echo "[deploy] Checking support API_BASE..."

curl -s https://www.xcommand.cloud/support.html | grep -m1 "const API_BASE" || true

echo "[deploy] Deployment complete."