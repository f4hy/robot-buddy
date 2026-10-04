#!/usr/bin/env bash
# Repair the Pi's SD card from the laptop when the Pi can't get on Wi-Fi.
# Run as root with the card mounted (udisks mounts it under /run/media/$USER):
#   sudo bash scripts/sd-card-rescue.sh <step>...
# Steps:
#   logs         copy the Pi's logs to pi-logs/<timestamp>/ (gitignored)
#   wifi         move aside empty netplan files and write a NetworkManager
#                Wi-Fi profile from the SSID/PSK Imager left in network-config
#   usb-console  login prompt over the middle micro-USB port (/dev/ttyACM0 on
#                the laptop); safe on a freshly flashed card
# BOOTFS / ROOTFS override the mount points.
set -euo pipefail
OWNER="${SUDO_USER:-$USER}"
B="${BOOTFS:-/run/media/$OWNER/bootfs}"
R="${ROOTFS:-/run/media/$OWNER/rootfs}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

step_logs() {
  OUT="$REPO/pi-logs/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$OUT"
  cp "$R"/var/log/boot.log "$R"/var/log/cloud-init-output.log "$R"/var/log/cloud-init.log "$OUT"/
  cp -a "$R/etc/netplan" "$R/etc/NetworkManager/system-connections" "$OUT"/
  chown -R "$OWNER:" "$REPO/pi-logs"
  echo "logs in $OUT"
}

step_wifi() {
  # Move empty netplan files aside (kept in /root on the card).
  mkdir -p "$R/root/netplan-empty-backup"
  find "$R/etc/netplan" -name '90-NM-*.yaml' -size 0 -exec mv {} "$R/root/netplan-empty-backup/" \;

  # Wi-Fi profile for NetworkManager, using the SSID and PSK Imager wrote.
  SSID=$(sed -n 's/^ *"\(.*\)":$/\1/p' "$B/network-config" | head -1)
  PSK=$(sed -n 's/^ *password: *"\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' "$B/network-config" | head -1)
  [ -n "$SSID" ] && [ -n "$PSK" ] || { echo "could not read SSID/PSK" >&2; exit 1; }
  F="$R/etc/NetworkManager/system-connections/home-wifi.nmconnection"
  cat >"$F" <<EOF
[connection]
id=home-wifi
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid=$SSID

[wifi-security]
key-mgmt=wpa-psk
psk=$PSK

[ipv4]
method=auto

[ipv6]
method=auto
EOF
  chown root:root "$F"
  chmod 600 "$F"
  echo "wifi profile for '$SSID' written"
}

step_usb_console() {
  # Load the serial gadget at boot, and run a login on it (/dev/ttyGS0).
  grep -q 'modules-load=dwc2,g_serial' "$B/cmdline.txt" ||
    sed -i '1 s/rootwait/rootwait modules-load=dwc2,g_serial/' "$B/cmdline.txt"
  if ! grep -q '^dtoverlay=dwc2,dr_mode=peripheral' "$B/config.txt"; then
    # Append under [all]; only add the header if the last section isn't [all].
    grep '^\[' "$B/config.txt" | tail -1 | grep -qx '\[all\]' || echo '[all]' >>"$B/config.txt"
    echo 'dtoverlay=dwc2,dr_mode=peripheral' >>"$B/config.txt"
  fi
  # Fresh images have no getty.target.wants/ until first boot.
  mkdir -p "$R/etc/systemd/system/getty.target.wants"
  ln -sf /usr/lib/systemd/system/serial-getty@.service \
    "$R/etc/systemd/system/getty.target.wants/serial-getty@ttyGS0.service"

  echo "usb console enabled"
}

[ $# -gt 0 ] || { echo "usage: $0 logs|wifi|usb-console..." >&2; exit 1; }
for step in "$@"; do
  case "$step" in
    logs) step_logs ;;
    wifi) step_wifi ;;
    usb-console) step_usb_console ;;
    *) echo "unknown step: $step" >&2; exit 1 ;;
  esac
done
sync
