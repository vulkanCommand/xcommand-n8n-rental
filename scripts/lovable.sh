#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend-lovable"
WEB_DIR="$ROOT_DIR/web"

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

echo "==> Copying build output into web/ (static hosting)..."
mkdir -p "$WEB_DIR/static"

# Wipe previous generated static assets (safe)
rm -rf "$WEB_DIR/static/"*

# Copy new build output
cp -R "$FRONTEND_DIR/dist/"* "$WEB_DIR/"

echo "==> Done. web/ now contains latest lovable build."
echo "Next: commit web/ changes in main repo if you want them versioned."