#!/bin/bash

# Ensure the script stops if any command fails
set -e

# Check if a commit message is provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 \"Your commit message\""
  exit 1
fi

# Add all changes
git add .

# Commit with the provided message
git commit -m "$1"

# Push to the current branch
git push

echo "Changes have been committed and pushed successfully."
