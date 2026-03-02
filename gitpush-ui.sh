#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[xcmd] UI pipeline starting..."

# Build + sync to web/ and infra/n8n/landing
"$ROOT_DIR/scripts/lovable.sh"

# Commit + push (web + infra/n8n/landing)
"$ROOT_DIR/scripts/push-frontend.sh"

echo "[xcmd] UI pipeline finished."
echo "[xcmd] Next: run deploy on server: /srv/xcommand-n8n-from-github/deploy.sh"