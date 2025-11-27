#!/usr/bin/env bash

echo "== xcommand-n8n-rental: safe push =="

# Make sure we're in a git repo
if [ ! -d ".git" ]; then
  echo "❌ This does not look like a git repo (no .git directory)."
  exit 1
fi

echo
echo "Current git status:"
git status

# Check for any local changes (staged or unstaged)
CHANGES=$(git status --porcelain)

if [ -n "$CHANGES" ]; then
  echo
  echo "You have local changes."
  echo "I can stage and commit ALL tracked changes for you."
  read -r -p "Stage and commit all tracked changes? (y/n): " ANSWER

  if [ "$ANSWER" != "y" ] && [ "$ANSWER" != "Y" ]; then
    echo "❌ Aborting. Nothing was pushed."
    exit 1
  fi

  echo
  echo "Staging all tracked changes..."
  git add -A

  echo
  read -r -p "Enter commit message: " COMMIT_MSG

  if [ -z "$COMMIT_MSG" ]; then
    echo "❌ Empty commit message is not allowed. Aborting."
    exit 1
  fi

  echo "Committing with message: $COMMIT_MSG"
  git commit -m "$COMMIT_MSG"
else
  echo
  echo "✅ No local changes to commit."
fi

echo
echo "Fetching and rebasing on top of origin/main..."
if ! git pull --rebase origin main; then
  echo
  echo "❌ Rebase failed due to conflicts."
  echo "Fix conflicts, then run:"
  echo "  git status"
  echo "  # edit conflicted files"
  echo "  git add <fixed-files>"
  echo "  git rebase --continue"
  echo "Then run this script again to push."
  exit 1
fi

echo
echo "Pushing to origin/main..."
if ! git push origin main; then
  echo
  echo "❌ Push failed."
  echo "Most common reasons:"
  echo "  - Someone pushed new commits after your rebase."
  echo "  - Remote branch was changed in a way that needs manual handling."
  echo
  echo "Try:"
  echo "  git pull --rebase origin main"
  echo "Then run this script again."
  exit 1
fi

echo
echo "✅ Successfully pushed to origin/main."
