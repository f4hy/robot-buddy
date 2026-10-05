#!/usr/bin/env bash
# One-time Pi setup, run on the Pi, one step per milestone:
#   bash ~/robot_buddy/scripts/provision.sh base      # M1
#   bash ~/robot_buddy/scripts/provision.sh speaker   # M2, then reboot
#   bash ~/robot_buddy/scripts/provision.sh web       # M3
# Later steps (camera, mic) are added with their milestones.
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

step_speaker() {
  sudo apt-get install -y alsa-utils espeak-ng

  # The I2S amp becomes the only sound card: onboard and HDMI audio off,
  # hifiberry-dac overlay on. M8 swaps the overlay for the combined one.
  local cfg=/boot/firmware/config.txt
  sudo cp -n "$cfg" "$cfg.before-speaker"
  sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$cfg"
  sudo sed -i 's/^dtoverlay=vc4-kms-v3d$/dtoverlay=vc4-kms-v3d,noaudio/' "$cfg"
  if ! grep -q '^dtoverlay=hifiberry-dac' "$cfg"; then
    printf '\n[all]\n# Robot Buddy I2S speaker amp (M2)\ndtoverlay=hifiberry-dac\n' | sudo tee -a "$cfg" >/dev/null
  fi
  echo "speaker done; sudo reboot, then: python3 ~/robot_buddy/scripts/check_speaker.py"
}

step_web() {
  sudo apt-get install -y python3-aiohttp
  # Pick up any change to the unit file (e.g. Restart=always for the server).
  sudo cp "$REPO/systemd/robot-buddy.service" /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl restart robot-buddy
  echo "web done; journalctl -u robot-buddy -n 20 shows the phone page address"
}

case "${1:-}" in
  base) step_base ;;
  speaker) step_speaker ;;
  web) step_web ;;
  *) echo "usage: $0 base|speaker|web" >&2; exit 1 ;;
esac
