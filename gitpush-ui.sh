#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[xcmd] ========================================="
echo "[xcmd] UI pipeline starting..."
echo "[xcmd] ========================================="

echo "[xcmd] Step 1: Build Lovable frontend and sync to repo..."
"$ROOT_DIR/scripts/lovable.sh"

echo "[xcmd] Step 2: Commit frontend build + submodule pointer..."
"$ROOT_DIR/scripts/push-frontend.sh" "Update frontend build from lovable"

echo "[xcmd] ========================================="
echo "[xcmd] UI pipeline finished."
echo "[xcmd] ========================================="

echo
echo "[xcmd] NEXT STEP:"
echo "SSH to server and run:"
echo
echo "cd /srv/xcommand-n8n-from-github"
echo "./deploy.sh"
echo