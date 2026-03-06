#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend-lovable"
WEB_DIR="$ROOT_DIR/web"
LANDING_DIR="$ROOT_DIR/infra/n8n/landing"

echo "==> Syncing lovable submodule..."
cd "$ROOT_DIR"
git submodule sync --recursive
git submodule update --init --recursive

echo "==> Pulling latest lovable code..."
cd "$FRONTEND_DIR"
git fetch origin

if git show-ref --verify --quiet refs/remotes/origin/main; then
  git checkout main >/dev/null 2>&1 || true
  git pull --ff-only origin main
else
  git checkout master >/dev/null 2>&1 || true
  git pull --ff-only origin master
fi

cd "$ROOT_DIR"

echo "==> Updating lovable submodule pointer in parent repo..."
git add frontend-lovable || true

echo "==> Building lovable frontend..."
cd "$FRONTEND_DIR"

echo "==> Installing dependencies..."
set +e
if [ -f package-lock.json ]; then
  npm ci
  CI_STATUS=$?
else
  CI_STATUS=1
fi
set -e

if [ "${CI_STATUS}" -ne 0 ]; then
  echo "npm ci failed (lockfile mismatch or missing). Falling back to npm install..."
  npm install
fi

npm run build

if [ ! -d "$FRONTEND_DIR/dist" ]; then
  echo "ERROR: dist/ not found after build"
  exit 1
fi

echo "==> Copying build output into web/ (app.xcommand.cloud)..."
mkdir -p "$WEB_DIR"

rm -rf "$WEB_DIR/assets" 2>/dev/null || true
rm -f  "$WEB_DIR/index.html" \
       "$WEB_DIR/pay.html" \
       "$WEB_DIR/ready.html" \
       "$WEB_DIR/support.html" \
       "$WEB_DIR/robots.txt" \
       "$WEB_DIR/favicon.ico" \
       "$WEB_DIR/og.png" \
       "$WEB_DIR/placeholder.svg" 2>/dev/null || true

cp -R "$FRONTEND_DIR/dist/"* "$WEB_DIR/"

echo "==> Copying build output into infra/n8n/landing (landing site + legacy sync)..."
mkdir -p "$LANDING_DIR"

rm -rf "$LANDING_DIR/assets" 2>/dev/null || true
rm -f  "$LANDING_DIR/index.html" \
       "$LANDING_DIR/pay.html" \
       "$LANDING_DIR/ready.html" \
       "$LANDING_DIR/support.html" \
       "$LANDING_DIR/robots.txt" \
       "$LANDING_DIR/favicon.ico" \
       "$LANDING_DIR/og.png" \
       "$LANDING_DIR/placeholder.svg" 2>/dev/null || true

cp -R "$FRONTEND_DIR/dist/"* "$LANDING_DIR/"

echo "==> Done."
echo " - frontend-lovable updated to latest remote commit"
echo " - submodule pointer staged in parent repo"
echo " - web/ updated (app.xcommand.cloud)"
echo " - infra/n8n/landing updated (landing + legacy sync)"
echo "Next: commit frontend-lovable, web/, and infra/n8n/landing in main repo."