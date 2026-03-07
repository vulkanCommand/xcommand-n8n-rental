#!/usr/bin/env bash
set -euo pipefail

echo "== xcommand-n8n-rental: safe local update =="

if [ ! -d ".git" ] && [ ! -f ".git" ]; then
  echo "❌ This does not look like the repo root."
  echo "Run this script from the root of xcommand-n8n-rental."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "❌ git is not installed or not available in PATH."
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo
echo "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "❌ This script only updates the main branch."
  echo "Run:"
  echo "  git checkout main"
  exit 1
fi

echo
echo "Current git status:"
git status --short || true

if [[ -n "$(git status --porcelain)" ]]; then
  echo
  echo "❌ Local repo has uncommitted or untracked changes."
  echo "I will NOT touch anything automatically."
  echo
  echo "Fix this first by doing ONE of these:"
  echo "  1) Commit your work:"
  echo "       git add ."
  echo "       git commit -m \"your message\""
  echo
  echo "  2) Stash your work temporarily:"
  echo "       git stash -u"
  echo
  echo "  3) Discard local changes carefully:"
  echo "       git restore <files>"
  echo "       git clean -fd"
  echo
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "❌ Remote 'origin' is not configured."
  exit 1
fi

echo
echo "Fetching latest changes from origin..."
git fetch --all --prune --tags

if ! git rev-parse --verify origin/main >/dev/null 2>&1; then
  echo "❌ origin/main not found."
  exit 1
fi

echo
echo "Fast-forwarding local main to origin/main..."
git merge --ff-only origin/main

if [ -f ".gitmodules" ]; then
  echo
  echo "Syncing submodules..."
  git submodule sync --recursive
  git submodule update --init --recursive
fi

echo
echo "Final status:"
git status --short || true

echo
echo "✅ Local main is now up to date with origin/main."
if [ -f ".gitmodules" ]; then
  echo "✅ Submodules are synced to the exact commits recorded in the repo."
fi