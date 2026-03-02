#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[xcmd] Build lovable -> sync into web/ and infra/n8n/landing"
"$ROOT_DIR/scripts/lovable.sh"

echo "[xcmd] Commit build output and push"
cd "$ROOT_DIR"

# Stage both app bundle and landing bundle
git add web infra/n8n/landing

# If nothing changed, don’t error out
if git diff --cached --quiet; then
  echo "[xcmd] No frontend changes to commit."
  exit 0
fi

git commit -m "Update frontend build from lovable"
git push origin main

echo "[xcmd] Done. Now SSH to server and run ./deploy.sh"