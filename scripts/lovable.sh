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

# Pull latest from the submodule's default branch (main)
cd "$FRONTEND_DIR"
git fetch origin

# Try main first, fall back to master if needed
if git show-ref --verify --quiet refs/remotes/origin/main; then
  git checkout main >/dev/null 2>&1 || true
  git pull --ff-only origin main
else
  git checkout master >/dev/null 2>&1 || true
  git pull --ff-only origin master
fi

echo "==> Building lovable frontend..."

echo "==> Installing dependencies..."
# Try npm ci first (fast + reproducible). If lockfile is out of sync, fall back to npm install.
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

# Remove old Vite build artifacts from web/ (but do NOT touch your python backend files)
rm -rf "$WEB_DIR/assets" 2>/dev/null || true
rm -f  "$WEB_DIR/index.html" \
       "$WEB_DIR/robots.txt" \
       "$WEB_DIR/favicon.ico" \
       "$WEB_DIR/og.png" \
       "$WEB_DIR/placeholder.svg" 2>/dev/null || true

cp -R "$FRONTEND_DIR/dist/"* "$WEB_DIR/"

echo "==> Copying build output into infra/n8n/landing (landing site + legacy sync)..."
mkdir -p "$LANDING_DIR"

# Replace landing bundle with latest build
rm -rf "$LANDING_DIR/assets" 2>/dev/null || true
rm -f  "$LANDING_DIR/index.html" \
       "$LANDING_DIR/robots.txt" \
       "$LANDING_DIR/favicon.ico" \
       "$LANDING_DIR/og.png" \
       "$LANDING_DIR/placeholder.svg" 2>/dev/null || true

cp -R "$FRONTEND_DIR/dist/"* "$LANDING_DIR/"

echo "==> Done."
echo " - web/ updated (app.xcommand.cloud)"
echo " - infra/n8n/landing updated (landing + legacy sync)"
echo "Next: commit web/ and infra/n8n/landing changes in main repo if you want them versioned."