#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[xcmd] Build lovable -> sync into web/ and infra/n8n/landing"
"$ROOT_DIR/scripts/lovable.sh"

cd "$ROOT_DIR"

echo "[xcmd] Staging frontend build + lovable submodule"
git add frontend-lovable
git add web
git add infra/n8n/landing

if git diff --cached --quiet; then
  echo "[xcmd] No frontend changes to commit."
  exit 0
fi

git commit -m "Update frontend build from lovable"
git push origin main

echo "[xcmd] Done. Now SSH to server and run:"
echo "cd /srv/xcommand-n8n-from-github && ./deploy.sh"