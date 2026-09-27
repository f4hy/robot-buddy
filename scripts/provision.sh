#!/usr/bin/env bash
# One-time Pi setup, run on the Pi, one step per milestone:
#   bash ~/robot_buddy/scripts/provision.sh base      # M1
# Later steps (web, speaker, camera, mic) are added with their milestones.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"

step_base() {
  sudo apt-get update
  sudo apt-get install -y git rsync python3-gpiozero python3-lgpio python3-yaml

  # Wi-Fi power saving adds latency spikes that would trip the motor watchdog.
  sudo tee /etc/NetworkManager/conf.d/wifi-powersave-off.conf >/dev/null <<'CONF'
[connection]
wifi.powersave = 2
CONF
  sudo systemctl reload NetworkManager || true

  sudo cp "$REPO/systemd/robot-buddy.service" /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable robot-buddy
  echo "base done; reboot, then: journalctl -u robot-buddy -b"
}

case "${1:-}" in
  base) step_base ;;
  *) echo "usage: $0 base" >&2; exit 1 ;;
esac
