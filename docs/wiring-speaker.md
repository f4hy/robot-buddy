# M2 — Wiring the speaker amp

The NS4168 board is an I2S amplifier: the Pi sends it digital audio on three
pins and it drives the 3 W speaker directly. No soldering needed if its header
pins came attached. Pin map: [DESIGN.md](DESIGN.md#pin-map).

**Wire with the Pi unplugged.**

## Wires

| Amp pin (label varies)      | Pi                  | Physical pin |
| --------------------------- | ------------------- | ------------ |
| VCC / VIN / VDD             | 5 V                 | 2            |
| GND                         | GND                 | 39           |
| BCLK / BCK                  | GPIO 18             | 12           |
| LRCLK / LRC / WS / LRCK     | GPIO 19             | 35           |
| DIN / DATA / SDATA / SD     | GPIO 21             | 40           |
| Speaker + / −               | the speaker's wires | —            |

- Pins 39 and 40 are the last pair at the far end of the header from the SD
  card. Pin 2 is the edge-row pin nearest the SD card.
- If the board also has a **CTRL** (or SD_MODE) pin, leave it unconnected
  at first. On the NS4168 it switches the amp on and picks the channel; many
  boards pull it up already. If you hear nothing, connect it to 3.3 V
  (pin 1).
- Speaker polarity doesn't matter for a single speaker.
- Use VCC from the Pi's 5 V, never from the AA pack.

## Software

With the Pi powered and on Wi-Fi, from the laptop:

```sh
ROBOT_HOST=robot@192.168.1.213 scripts/deploy.sh
```

Then on the Pi (interactive SSH, it asks for the sudo password):

```sh
bash ~/robot_buddy/scripts/provision.sh speaker
sudo reboot
```

The `speaker` step installs `alsa-utils` and `espeak-ng`, and edits
`/boot/firmware/config.txt` (backup at `config.txt.before-speaker`):

- `dtparam=audio=on` → commented out (onboard audio off)
- `dtoverlay=vc4-kms-v3d` → `dtoverlay=vc4-kms-v3d,noaudio` (HDMI audio off)
- adds `dtoverlay=hifiberry-dac` (the I2S amp becomes the sound card)

After the reboot:

```sh
aplay -l                                        # card sndrpihifiberry should be listed
python3 ~/robot_buddy/scripts/check_speaker.py  # beep beep, then "I am updog ... what's up with you?"
```

Once the speaker works, the service also greets at boot: "Hello Rowan, I am
ready to play. My name is updog." The names are `robot.kid_name` and
`robot.buddy_name` in `config/robot.yaml`; after changing them, deploy and
`sudo systemctl restart robot-buddy` to hear the new greeting. If the greeting fails (no sound
card yet), the service logs a warning and keeps running.

Volume is `audio.volume` in `config/robot.yaml` (0–1, default 0.4). The amp
has no volume control of its own; the code scales the sound.

## Troubleshooting

| You see / hear                         | Fix |
| -------------------------------------- | --- |
| `No sndrpihifiberry sound card`        | Did the reboot happen? `grep -n audio /boot/firmware/config.txt` should show `dtoverlay=hifiberry-dac` |
| Script runs, silence                   | Check VCC on pin 2 and GND; then BCLK/LRCLK/DIN aren't swapped; then try CTRL to 3.3 V |
| Hiss or crackle only                   | DIN on the wrong pin (must be pin 40, GPIO 21), or a loose jumper |
| Pop at start or end of each sound      | Normal for I2S amps when the clock starts and stops |
| Pi reboots or Wi-Fi drops on loud sound | Power bank can't supply the peak; lower `audio.volume` |

M2 hardware is done when `check_speaker.py` plays the beep and the sentence.
The phrase buttons and "say" box on the phone come in M3.
