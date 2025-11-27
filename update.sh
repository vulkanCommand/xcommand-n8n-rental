#!/usr/bin/env bash
set -e

# Always run from repo root
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# Make sure we are on main
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "You are on branch '$CURRENT_BRANCH'. This script assumes 'main'."
  echo "Switch to main or update the script if you want to use another branch."
  exit 1
fi

# Only care about tracked-file changes, ignore untracked ones like update.sh
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "❌ Local repo has uncommitted tracked changes."
  echo "Commit, stash, or discard them before syncing."
  exit 1
fi

echo "✅ Fetching latest changes from origin..."
git fetch origin

echo "✅ Pulling origin/main into local main..."
git pull origin main

echo "✅ Done. Local repo is now up to date with GitHub."
