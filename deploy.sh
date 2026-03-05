#!/usr/bin/env bash
set -euo pipefail

cd /srv/xcommand-n8n-from-github

echo "[xcmd] Using project name: xcommand-n8n-rental"
export COMPOSE_PROJECT_NAME=xcommand-n8n-rental

SUPPORT_API_BASE="https://api.app.xcommand.cloud"

echo "[xcmd] Pulling latest code from GitHub..."
git fetch origin main
git reset --hard origin/main

echo "[xcmd] Syncing git submodules..."
git submodule sync --recursive

# If submodule has untracked changes (like images/components you edited on server),
# back them up so deploy won't fail, then clean to allow checkout.
BACKUP_DIR="/srv/_deploy_backups/frontend-lovable-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d "frontend-lovable/.git" ]; then
  echo "[xcmd] Checking submodule frontend-lovable for local/untracked files..."
  pushd frontend-lovable >/dev/null

  # backup untracked + modified files (best effort)
  if ! git diff --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "[xcmd] Detected local changes in frontend-lovable. Backing up to: $BACKUP_DIR"
    # tracked modified
    git diff --name-only | while read -r f; do
      [ -z "$f" ] && continue
      mkdir -p "$BACKUP_DIR/$(dirname "$f")"
      [ -f "$f" ] && cp -a "$f" "$BACKUP_DIR/$f" || true
    done
    # untracked
    git ls-files --others --exclude-standard | while read -r f; do
      [ -z "$f" ] && continue
      mkdir -p "$BACKUP_DIR/$(dirname "$f")"
      [ -f "$f" ] && cp -a "$f" "$BACKUP_DIR/$f" || true
    done
  fi

  # force clean so submodule update never conflicts
  git reset --hard || true
  git clean -fd || true
  popd >/dev/null
fi

# force submodule checkout
git submodule update --init --recursive --force

echo "[xcmd] Building Lovable frontend and syncing into web/..."
# Don’t break deploy if Node/npm isn’t installed.
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

# Copy landing bundle
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/. /srv/n8n/landing/
cp -a /srv/xcommand-n8n-from-github/infra/n8n/landing/index.html /srv/n8n/site/index.html

echo "[deploy] Landing sync complete."

echo "[deploy] Syncing app pages (pay/ready/support) into legacy n8n landing..."
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/pay.html     /srv/n8n/landing/pay.html
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/ready.html   /srv/n8n/landing/ready.html
cp -a /srv/xcommand-n8n-from-github/infra/app-pages/support.html /srv/n8n/landing/support.html
echo "[deploy] App pages sync complete."

# HARD-FORCE support API_BASE so it never regresses after deploy
echo "[deploy] Forcing support API_BASE => ${SUPPORT_API_BASE}"
if grep -qE 'const API_BASE' /srv/n8n/landing/support.html; then
  sed -i -E "s|const API_BASE = \".*\";|const API_BASE = \"${SUPPORT_API_BASE}\";|g" /srv/n8n/landing/support.html
fi

# Restart landing container if it exists (so latest HTML is served)
if docker ps -a --format '{{.Names}}' | grep -qx 'landing'; then
  echo "[deploy] Restarting landing container..."
  docker restart landing >/dev/null
fi

echo "[deploy] Final check (served file):"
grep -n 'const API_BASE' /srv/n8n/landing/support.html | head -n 3 || true