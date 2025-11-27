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

echo "Current git status:"
git status

read -p "Stage and push ALL tracked changes to origin/main? (y/n): " ANSWER
if [[ "$ANSWER" != "y" && "$ANSWER" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

echo "Staging all tracked changes..."
git add -A

# Check if anything is actually staged
if [ -z "$(git diff --cached --name-only)" ]; then
  echo "No changes staged. Nothing to commit."
  exit 0
fi

read -p "Enter commit message: " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
  COMMIT_MSG="Update from local"
fi

echo "Committing with message: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "Pushing to origin/main..."
git push origin main

echo "✅ Done. Local changes are now in GitHub (origin/main)."
