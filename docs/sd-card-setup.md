# M0 — SD card and first boot

Goal: the Pi Zero boots headless, joins Wi-Fi, and `ssh robot@robot-buddy.local`
works from the laptop. Nothing is wired to the GPIO header yet.

## 1. Flash the card with Raspberry Pi Imager

```sh
sudo pacman -S rpi-imager
rpi-imager
```

1. **Device:** Raspberry Pi Zero.
2. **OS:** Raspberry Pi OS (other) → **Raspberry Pi OS Lite (32-bit)**
   (Trixie, 2026-09-15 at the time of writing). Not the default
   "Raspberry Pi OS (32-bit)": that one is the desktop image, which boots to a
   GUI and wastes the Zero's RAM. Our first card was the desktop image by
   mistake.
3. **Storage:** the SD card. On this laptop the reader is `/dev/sde`
   (`SD/MMC CRW`); check the size matches your card before writing.
4. **Customisation:**
   - Hostname: `robot-buddy` (later renamed to `robot` with
     `sudo hostnamectl set-hostname robot`, so the phone can open `http://robot`)
   - Username `robot`, plus a password (needed for `sudo`)
   - Wi-Fi: your 2.4 GHz network (the Zero W has no 5 GHz), country `US`
   - Enable SSH, public-key only, using `~/.ssh/id_rsa.pub`
   - Time zone and keyboard layout
5. Write, and let Imager verify.
6. Before ejecting, enable the USB console (section 5) so there is a way in
   when Wi-Fi fails: `sudo bash scripts/sd-card-rescue.sh usb-console`.

## 2. First boot

1. Put the card in the Pi and power it from the USB power bank, using the
   **PWR** micro-USB port (the one at the corner).
2. First boot resizes the filesystem and applies settings. On a Zero W this
   takes about **10 minutes**, and it may reboot partway through. It shows up
   on the router's device list (MAC `b8:27:eb:…`) several minutes before SSH
   opens, so a "connection refused" in that window just means wait. A steady
   green LED means it is running and idle; it flickers during SD activity.
3. From the laptop:

   ```sh
   ping robot-buddy.local
   ssh robot@robot-buddy.local
   ```

   If `.local` doesn't resolve ("Name or service not known"), use the IP from
   the router's client list (ours is `192.168.1.213`). On Arch, `.local` names
   need `nss-mdns`, `avahi-daemon` running, and `mdns_minimal [NOTFOUND=return]`
   before `resolve` on the `hosts:` line of `/etc/nsswitch.conf`.

## 3. Quick checks on the Pi

```sh
cat /proc/device-tree/model   # Raspberry Pi Zero W Rev 1.1
free -h                       # ~430 MB total
nmcli -t -f active,ssid,freq dev wifi | grep ^yes   # Wi-Fi name, 24xx MHz
vcgencmd get_throttled        # 0x0 = power supply OK
```

`get_throttled` other than `0x0` means undervoltage: try another cable or
power bank before wiring motors.

## 4. Add an SSH shortcut on the laptop (optional)

```
# ~/.ssh/config
Host robot
    HostName robot-buddy.local   # or the IP until mDNS works on the laptop
    User robot
```

`sudo` on the Pi asks for the password you set in Imager, so run
`provision.sh` in an interactive SSH session.

## 5. When the Pi won't join Wi-Fi

The Zero has no keyboard port without an OTG adapter, so fix things from the
laptop. Shut the Pi down with `sudo poweroff` when you can; don't just pull
the power.

**What happened to our first card:** it joined Wi-Fi once, then never again.
NetworkManager on Trixie saves connections as `/etc/netplan/90-NM-*.yaml`;
both files were 0 bytes, written at 22:53. `cloud-init-output.log` shows the
boot that started then was cut off about 85 s in (the next boot begins 23 s
later on the Pi's clock, which has no RTC and resumes from its last saved
time), so a power cut or reset mid-boot left the files empty. Imager's cloud-init
config only applies on the first boot, so it never came back by itself.

**Repair from the laptop:** put the card in the reader (it auto-mounts under
`/run/media/$USER/{bootfs,rootfs}`) and run
`sudo bash scripts/sd-card-rescue.sh <step>...`:

- `logs`: copy the Pi's logs and network config to `pi-logs/` (gitignored).
- `wifi`: move empty netplan files aside and write a NetworkManager profile
  from the SSID and PSK in `bootfs/network-config`.
- `usb-console`: add `modules-load=dwc2,g_serial` to `cmdline.txt` and
  `dtoverlay=dwc2,dr_mode=peripheral` to `config.txt`, and enable
  `serial-getty@ttyGS0`. Plug a data cable from the laptop into the middle
  **USB** port (it also powers the Pi); once it boots, `screen /dev/ttyACM0
  115200` gives a login prompt (not yet tested on our Pi).

## 6. Faster boot (`provision.sh fastboot`)

Measured on 2026-10-04 with `systemd-analyze`: 2 min 39 s to
`multi-user.target`, and `robot-buddy` started about 2 min after power-on.
The Zero has one slow core, so everything at boot queues behind everything
else. Where the time went:

| Cost | Cause |
|---|---|
| ~65 s | NetworkManager rewrote its `/etc/netplan/90-NM-*.yaml` profiles at every boot, each time running `netplan generate` and a systemd daemon-reload (~12 s each, 4 per boot). This is also the write a power cut caught on our first card (section 5). |
| ~34 s | cloud-init on the critical path, though it only matters for Imager's first boot |
| ~20 s CPU | `rpi-resize-swap-file` re-running `mkswap` on `/var/swap` (zram+file swap) |
| ~6 s | `robot-buddy` waiting for `network-online.target` |
| a few s each | bluetooth, avahi, udisks2, rpi-eeprom-update (the Zero has no EEPROM), keyboard/console setup |
| ~5 s | Python start, mostly `import aiohttp` (not changed) |

`bash ~/robot_buddy/scripts/provision.sh fastboot` (then `sudo reboot`):

- copies the live Wi-Fi SSID/PSK into
  `/etc/NetworkManager/system-connections/home-wifi.nmconnection` (the same
  profile `sd-card-rescue.sh wifi` writes), switches to it, and only once it is
  up moves the netplan files to `/root/netplan-backup/`;
- disables cloud-init (`/etc/cloud/cloud-init.disabled`);
- sets zram-only swap (`/etc/rpi/swap.conf.d/robot-buddy.conf`); running the
  step again after the reboot deletes the unused `/var/swap`;
- disables bluetooth, avahi (`robot.local` stops resolving; the router's DNS
  name `robot` still works), udisks2, rpi-eeprom-update, keyboard/console
  setup, and the apt-daily and man-db timers;
- adds `dtoverlay=disable-bt` and `disable_splash=1`, sets
  `display_auto_detect=0`, and adds `quiet` to `cmdline.txt` (originals
  saved as `*.before-fastboot`);
- installs the unit without the `network-online.target` wait.

Result after the reboot: 1 min 4 s to `multi-user.target` (was 2 min 39 s);
Wi-Fi up at 67 s, "ready to play" at 70 s after power-on (was ~2 min 15 s).
What's left: NetworkManager still runs `netplan generate` plus one
daemon-reload (~8 s) at startup even with `/etc/netplan` empty. It is built
into Debian's NetworkManager, which depends on `netplan.io`, so it stays.
Python import (~10 s on a cold boot) and the kernel (~11 s) are the next
biggest pieces.

To undo a piece: `sudo systemctl enable <unit>`, restore the
`*.before-fastboot` files, or `sudo rm /etc/cloud/cloud-init.disabled`. If
Wi-Fi fails after the reboot, `sd-card-rescue.sh wifi` writes the same
keyfile from the laptop.

M0 is done when `ssh robot@robot-buddy.local` works. Next is M1:
`scripts/deploy.sh` then `ssh robot@robot-buddy.local 'bash ~/robot_buddy/scripts/provision.sh base'`.
