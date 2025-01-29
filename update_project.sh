#!/bin/bash

# Ensure the script stops if any command fails
set -e

# Fetch and pull the latest changes from the current branch
git pull

echo "Project updated successfully."
