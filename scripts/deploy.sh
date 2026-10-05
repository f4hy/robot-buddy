#!/usr/bin/env bash
# Copy the working tree to the Pi and restart the service.
#   scripts/deploy.sh            # uses robot@robot
#   ROBOT_HOST=robot@192.168.1.213 scripts/deploy.sh
set -euo pipefail

HOST="${ROBOT_HOST:-robot@robot}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# First deploy: make sure rsync exists on the Pi.
ssh -t "$HOST" 'command -v rsync >/dev/null || sudo apt-get install -y rsync'

rsync -az --delete \
  --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  --exclude .ruff_cache --exclude .env --exclude pi-logs \
  "$REPO/" "$HOST:robot_buddy/"

ssh "$HOST" 'systemctl is-enabled --quiet robot-buddy 2>/dev/null && sudo systemctl restart robot-buddy || true'
echo "deployed to $HOST"
