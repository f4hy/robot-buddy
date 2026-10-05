#!/usr/bin/env bash
# One-time Pi setup, run on the Pi, one step per milestone:
#   bash ~/robot_buddy/scripts/provision.sh base      # M1
#   bash ~/robot_buddy/scripts/provision.sh speaker   # M2, then reboot
#   bash ~/robot_buddy/scripts/provision.sh web       # M3
#   bash ~/robot_buddy/scripts/provision.sh fastboot  # any time, then reboot
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

step_fastboot() {
  # Wi-Fi as a plain NetworkManager keyfile. Imager's netplan profiles make
  # NetworkManager rewrite /etc/netplan and reload systemd at every boot
  # (~12 s per reload on the Zero, ~65 s per boot), and a power cut during
  # that write is what emptied our first card's Wi-Fi config.
  local nm=/etc/NetworkManager/system-connections/home-wifi.nmconnection
  if compgen -G '/etc/netplan/90-NM-*.yaml' >/dev/null; then
    local old ssid psk
    old=$(nmcli -t -f NAME,TYPE connection show --active |
      awk -F: '$2 == "802-11-wireless" { print $1; exit }')
    [ -n "$old" ] || { echo "no active Wi-Fi connection to copy" >&2; exit 1; }
    ssid=$(nmcli -e no -g 802-11-wireless.ssid connection show "$old")
    psk=$(sudo nmcli -e no -s -g 802-11-wireless-security.psk connection show "$old")
    [ -n "$ssid" ] && [ -n "$psk" ] || { echo "could not read SSID/PSK of $old" >&2; exit 1; }
    sudo install -m 600 /dev/null "$nm"
    sudo tee "$nm" >/dev/null <<EOF
[connection]
id=home-wifi
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid=$ssid

[wifi-security]
key-mgmt=wpa-psk
psk=$psk

[ipv4]
method=auto

[ipv6]
method=auto
EOF
    sudo nmcli connection load "$nm"
    # Switch over outside this SSH session, falling back to the old profile;
    # the DHCP lease keeps the same address, so SSH should survive the blip.
    echo "switching Wi-Fi from '$old' to home-wifi (SSH may pause a few seconds)"
    sudo systemd-run --quiet --wait --collect --unit=robot-wifi-switch \
      sh -c 'nmcli connection up home-wifi || nmcli connection up "$1"' _ "$old" || true
    if ! nmcli -t -f NAME connection show --active | grep -qx home-wifi; then
      sudo rm -f "$nm" && sudo nmcli connection reload
      echo "home-wifi did not come up; still on '$old', nothing changed" >&2
      exit 1
    fi
    if ! nmcli -t -f NAME,FILENAME connection show | grep -qx "home-wifi:$nm"; then
      echo "NetworkManager moved home-wifi out of $nm; check before rebooting" >&2
      exit 1
    fi
    sudo mkdir -p /root/netplan-backup
    sudo sh -c 'mv /etc/netplan/90-NM-*.yaml /root/netplan-backup/'
    echo "Wi-Fi now from $nm (netplan files in /root/netplan-backup)"
  fi

  # cloud-init only matters for Imager's first boot; it costs ~30 s on every boot.
  sudo touch /etc/cloud/cloud-init.disabled

  # zram swap only: no /var/swap file to mkswap at every boot.
  sudo mkdir -p /etc/rpi/swap.conf.d
  printf '[Main]\nMechanism=zram\n' | sudo tee /etc/rpi/swap.conf.d/robot-buddy.conf >/dev/null
  if [ -f /var/swap ] && [ -z "$(sudo losetup -j /var/swap)" ]; then
    sudo rm /var/swap # left from zram+file, no longer in use after the reboot
  fi

  # Services and timers a headless robot doesn't need. The timers matter
  # while driving too: the Zero has one core.
  local unit
  for unit in bluetooth.service hciuart.service avahi-daemon.service avahi-daemon.socket \
    udisks2.service rpi-eeprom-update.service keyboard-setup.service console-setup.service \
    apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
    sudo systemctl disable --now "$unit" 2>/dev/null || true
  done

  # Firmware and kernel: Bluetooth off, no display probe or splash, quiet
  # kernel log (it goes to the serial console at 115200 baud). Camera
  # auto-detect stays on for M7.
  local cfg=/boot/firmware/config.txt cmd=/boot/firmware/cmdline.txt
  sudo cp -n "$cfg" "$cfg.before-fastboot"
  sudo cp -n "$cmd" "$cmd.before-fastboot"
  sudo sed -i 's/^display_auto_detect=1$/display_auto_detect=0/' "$cfg"
  if ! grep -q '^dtoverlay=disable-bt' "$cfg"; then
    printf '\n[all]\n# Robot Buddy fast boot\ndtoverlay=disable-bt\ndisable_splash=1\n' |
      sudo tee -a "$cfg" >/dev/null
  fi
  grep -qw quiet "$cmd" || sudo sed -i '1 s/$/ quiet/' "$cmd"

  # The service no longer waits for network-online.target.
  sudo cp "$REPO/systemd/robot-buddy.service" /etc/systemd/system/
  sudo systemctl daemon-reload
  echo "fastboot done; sudo reboot, then: systemd-analyze && systemd-analyze blame | head"
}

case "${1:-}" in
  base) step_base ;;
  speaker) step_speaker ;;
  web) step_web ;;
  fastboot) step_fastboot ;;
  *) echo "usage: $0 base|speaker|web|fastboot" >&2; exit 1 ;;
esac
