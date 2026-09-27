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
   (Trixie, 2026-09-15 at the time of writing).
3. **Storage:** the SD card. On this laptop the reader is `/dev/sde`
   (`SD/MMC CRW`); check the size matches your card before writing.
4. **Customisation:**
   - Hostname: `robot-buddy`
   - Username `robot`, plus a password (needed for `sudo`)
   - Wi-Fi: your 2.4 GHz network (the Zero W has no 5 GHz), country `US`
   - Enable SSH, public-key only, using `~/.ssh/id_rsa.pub`
   - Time zone and keyboard layout
5. Write, and let Imager verify.

## 2. First boot

1. Put the card in the Pi and power it from the USB power bank, using the
   **PWR** micro-USB port (the one at the corner).
2. First boot resizes the filesystem and applies settings. On a Zero W allow
   3–5 minutes; the green LED flickers while it works.
3. From the laptop:

   ```sh
   ping robot-buddy.local
   ssh robot@robot-buddy.local
   ```

   If `.local` doesn't resolve, find the Pi's IP in the router's client list.
   On Arch, `.local` names need `nss-mdns` and `avahi-daemon` running.

## 3. Quick checks on the Pi

```sh
cat /proc/device-tree/model   # Raspberry Pi Zero W Rev 1.1
free -h                       # ~430 MB total
iwgetid -r                    # your Wi-Fi name
vcgencmd get_throttled        # 0x0 = power supply OK
```

`get_throttled` other than `0x0` means undervoltage: try another cable or
power bank before wiring motors.

## 4. Add an SSH shortcut on the laptop (optional)

```
# ~/.ssh/config
Host robot
    HostName robot-buddy.local
    User robot
```

M0 is done when `ssh robot@robot-buddy.local` works. Next is M1:
`scripts/deploy.sh` then `ssh robot@robot-buddy.local 'bash ~/robot_buddy/scripts/provision.sh base'`.
