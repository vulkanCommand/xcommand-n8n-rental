#!/usr/bin/env bash
set -e

echo "== xcommand-n8n-rental: safe update =="

# Make sure we're in the repo root
if [ ! -d ".git" ]; then
  echo "❌ This does not look like a git repo (no .git directory)."
  exit 1
fi

echo
echo "Current git status:"
git status

# Block if there are uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
  echo
  echo "❌ Local repo has uncommitted changes."
  echo "I will NOT touch anything automatically."
  echo
  echo "Fix this first by doing ONE of these:"
  echo "  1) Commit your work:"
  echo "       git add <files>"
  echo "       git commit -m \"your message\""
  echo
  echo "  2) Stash your work temporarily:"
  echo "       git stash"
  echo
  echo "  3) Discard local changes (DANGEROUS):"
  echo "       git restore <files>"
  echo "     or git reset --hard HEAD"
  echo
  exit 1
fi

echo
echo "✅ Working tree is clean. Updating from origin/main..."

git fetch origin
git pull --rebase origin main

echo
echo "✅ Local main is now up to date with origin/main."
