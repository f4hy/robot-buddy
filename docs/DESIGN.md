# Robot Buddy — Design

Robot Buddy is a small 2WD robot driven from a phone. The software is one Python
program on a Raspberry Pi Zero WH. We build it in small milestones. Each one
ends with something working on the real robot before the next part is wired.

Original design notes: <https://claude.ai/artifact/XR3yUCmzKRNdBM7Q5GQAzP>.
This file replaces them. [Changes from the original](#changes-from-the-original-design)
are listed at the end.

## Hardware

| Part       | Hardware                                                   | Milestone |
| ---------- | ---------------------------------------------------------- | --------- |
| Computer   | Raspberry Pi Zero WH (single-core ARMv6, 512 MB, 2.4 GHz Wi-Fi only) | M0 |
| Motors     | XiaoR 2WD chassis, 2 TT motors, TB6612FNG driver, 4×AA box | M2        |
| Speaker    | NULLLAB NS4168 I2S amp + 3 W speaker                       | M5        |
| Camera     | Pi camera on the CSI port (Zero ribbon cable)              | M6        |
| Microphone | Adafruit I2S MEMS mic                                      | M7        |
| Power      | USB power bank (Pi) + 4×AA (motors), shared ground         | M2        |

The AA pack never powers the Pi. The only connection between the two supplies
is ground.

## Principles

- **One part at a time.** Wire one part, run its check script, then write the
  code that uses it. A wiring fault shows up in a 20-line script, not in the
  whole program.
- **Safe by default.** Motors stop within 0.5 s if the phone disconnects or
  goes quiet. Speed is capped in kid mode, which is on at boot.
- **Light.** The Zero W has one slow core. Use apt packages, not pip builds, on
  the Pi. No heavy frameworks.
- **Runs on a laptop.** Every hardware module has a mock, so the program and
  its tests run without the robot.
- **One config file.** Pins, speeds and devices live in `config/robot.yaml`.
- **Cloud does the heavy thinking.** Speech and AI go to an API in the last
  milestone. The Pi only runs moves from an allow-list.

## Milestones

Each milestone has a "done when" test on the real robot. Progress is tracked
in the checklist in [README.md](../README.md).

| #  | Milestone               | Adds                                                        | Done when |
| -- | ----------------------- | ----------------------------------------------------------- | --------- |
| M0 | Pi boots headless       | SD card, Wi-Fi, SSH                                         | `ssh robot@robot-buddy.local` works from the laptop |
| M1 | Code on the Pi          | `provision.sh` (base only), `deploy.sh`, a hello service    | `deploy.sh` copies code and the service logs "hello" after reboot |
| M2 | Motors on the bench     | Motor wiring, `check_motors.py`                             | Wheels off the ground: each wheel spins forward and back, right direction |
| M3 | Drive from the laptop   | `Drive`, `Safety` (watchdog, speed cap), keyboard teleop over SSH | Arrow keys drive it; killing the SSH session stops it within 0.5 s |
| M4 | Drive from the phone    | aiohttp server, WebSocket, joystick page, systemd at boot   | Phone drives it around the living room; STOP always works |
| M5 | Speaker                 | Amp wiring (speaker-only overlay), `check_speaker.py`, sounds, `say` | Sound buttons and a "say" box work from the phone |
| M6 | Camera                  | Camera ribbon, `check_camera.py`, MJPEG stream on the page  | Live video on the phone while driving, still responsive |
| M7 | Microphone              | Mic wiring, switch to the combined I2S overlay, `check_mic.py`, loudness meter | Speaker still works and a loudness bar moves on the page |
| M8 | Behaviours              | Scripted moves (spin, wiggle, dance), clap-to-go            | Two claps make it roll forward |
| M9 | Brain                   | Push-to-talk, snapshot, cloud AI → allow-listed moves + speech | "Robot, do a dance!" gets a spoken reply and a dance |

M0–M4 are the original phase 1 without video. M5 and M6 can swap order.

## Architecture

Everything runs in one async Python process (`python3 -m robot`), so there is
no inter-process plumbing on the single-core Pi.

```
 phone ──WebSocket──► web/server.py ──► router.py ──► hardware/motors.py ──► TB6612
                           │                │   ▲
                           │                │   └── safety.py (watchdog, speed cap)
                           │                ├──► hardware/audio.py   (M5, M7)
                           │                ├──► behaviors/          (M8)
                           │                └──◄ brain/cloud.py      (M9)
                           └── /stream.mjpg ◄── hardware/camera.py   (M6)
```

The router is the single entry point for the web page, keyboard teleop and the
brain, so safety rules apply to all of them.

## Repo layout

Files arrive with the milestone that needs them.

```
robot_buddy/
├── README.md                 # quick start + milestone checklist
├── pyproject.toml            # laptop dev deps, pytest + ruff settings
├── config/robot.yaml         # pins, speeds, devices
├── docs/
│   ├── DESIGN.md             # this file
│   └── sd-card-setup.md      # M0 step by step
├── robot/
│   ├── __main__.py           # entry point: python3 -m robot
│   ├── config.py             # loads robot.yaml
│   ├── router.py             # validates commands, sends them to modules (M3)
│   ├── safety.py             # watchdog, speed cap, emergency stop (M3)
│   ├── teleop.py             # keyboard driving over SSH (M3)
│   ├── hardware/
│   │   ├── motors.py         # Drive class, gpiozero (M3)
│   │   ├── audio.py          # play, say, record, loudness (M5, M7)
│   │   ├── camera.py         # MJPEG stream + snapshots (M6)
│   │   └── mocks.py          # fake audio + camera for laptop runs
│   ├── behaviors/            # moves.py, clap.py (M8)
│   ├── brain/cloud.py        # (M9)
│   └── web/                  # server.py + static/ (M4)
├── sounds/                   # short .wav effects (M5)
├── scripts/
│   ├── provision.sh          # one-time Pi setup, per-milestone steps
│   ├── deploy.sh             # rsync code to the Pi, restart the service
│   ├── check_motors.py       # M2
│   ├── check_speaker.py      # M5
│   ├── check_camera.py       # M6
│   └── check_mic.py          # M7
├── systemd/robot-buddy.service
└── tests/
```

## Pin map

GPIO 18–21 belong to I2S audio, so the motors use software PWM on GPIO 24 and
25. Code uses BCM numbers; physical pins are for wiring.

| Signal                 | BCM GPIO | Physical pin | Connects to                   | Milestone |
| ---------------------- | -------- | ------------ | ----------------------------- | --------- |
| Left motor forward     | 17       | 11           | TB6612 AIN1                   | M2 |
| Left motor backward    | 27       | 13           | TB6612 AIN2                   | M2 |
| Left motor speed (PWM) | 24       | 18           | TB6612 PWMA                   | M2 |
| Right motor forward    | 22       | 15           | TB6612 BIN1                   | M2 |
| Right motor backward   | 23       | 16           | TB6612 BIN2                   | M2 |
| Right motor speed (PWM)| 25       | 22           | TB6612 PWMB                   | M2 |
| Driver standby         | 5        | 29           | TB6612 STBY                   | M2 |
| Driver logic power     | 3.3 V    | 17           | TB6612 VCC                    | M2 |
| I2S bit clock          | 18       | 12           | Amp BCLK (+ mic BCLK in M7)   | M5 |
| I2S word select        | 19       | 35           | Amp LRCLK (+ mic LRCL in M7)  | M5 |
| I2S data out           | 21       | 40           | Amp DIN                       | M5 |
| Amp power              | 5 V      | 2            | Amp VCC                       | M5 |
| I2S data in            | 20       | 38           | Mic DOUT                      | M7 |
| Mic power              | 3.3 V    | 1            | Mic 3V; mic SEL to GND        | M7 |
| Ground                 | GND      | 6, 9, 39     | TB6612 GND, AA −, amp, mic    | M2 |

Header map (board face up, SD card slot on the left, header along the top).
Pin 1 has the square solder pad; odd pins are the inner row, even pins the
row at the board edge. Run `pinout` on the Pi for the same map.

```
 Robot use          Name     Pin  Pin  Name     Robot use
 Mic 3V (M7)        3V3        1    2  5V       Amp VCC (M5)
                    GPIO2      3    4  5V
                    GPIO3      5    6  GND      TB6612 GND + AA −
                    GPIO4      7    8  GPIO14
 (spare GND)        GND        9   10  GPIO15
 TB6612 AIN1        GPIO17    11   12  GPIO18   I2S BCLK (M5)
 TB6612 AIN2        GPIO27    13   14  GND
 TB6612 BIN1        GPIO22    15   16  GPIO23   TB6612 BIN2
 TB6612 VCC         3V3       17   18  GPIO24   TB6612 PWMA
                    GPIO10    19   20  GND
                    GPIO9     21   22  GPIO25   TB6612 PWMB
                    GPIO11    23   24  GPIO8
                    GND       25   26  GPIO7
                    GPIO0     27   28  GPIO1
 TB6612 STBY        GPIO5     29   30  GND
                    GPIO6     31   32  GPIO12
                    GPIO13    33   34  GND
 I2S LRCLK (M5)     GPIO19    35   36  GPIO16
                    GPIO26    37   38  GPIO20   I2S DIN, mic (M7)
 Amp/mic GND        GND       39   40  GPIO21   I2S DOUT, amp (M5)
```

The camera uses the CSI ribbon, not GPIO. AA + goes to TB6612 VM through the
chassis switch. Breadboard steps for the battery and motors:
[wiring-motors.md](wiring-motors.md). If a motor spins the wrong way, flip its `invert` flag in
`config/robot.yaml` instead of rewiring.

## Modules

**Drive — `robot/hardware/motors.py` (M3).** Two gpiozero `Motor(forward,
backward, enable=..., pwm=True)` objects plus a `DigitalOutputDevice` on STBY.
`tank(left, right)` sets each side from −1 to 1. `arcade(throttle, turn)` mixes
a joystick into `tank`. `stop()` zeroes both and drops STBY. Every call is
clamped to the Safety speed cap. Nothing else touches GPIO.

**Safety — `robot/safety.py` (M3).** `Watchdog.feed()` runs on every drive
command. A 100 ms loop calls `drive.stop()` when no feed arrives within
`watchdog_ms`. It also stops on client disconnect, a `stop` command, router
exceptions, SIGTERM/SIGINT and exit. `speed_cap` is `kid_mode_speed` in kid
mode, else `max_speed`.

**Teleop — `robot/teleop.py` (M3).** Arrow keys / WASD over SSH, sent through
the router as `drive` messages at 10 Hz while a key is held. Space is stop. It
proves Drive and Safety before any web code exists, and stays as a debug tool.

**Web server — `robot/web/server.py` (M4).** aiohttp: `GET /` (control page),
`GET /ws` (WebSocket), later `GET /stream.mjpg` (M6). The page has a large
touch joystick, a red STOP button, and picture buttons for sounds and moves.
The joystick sends at 10 Hz while held and sends `stop` on release. The robot
pushes `status` every second: kid mode, current action, viewers.

| Message (phone → robot) | Fields                         | Effect                           | From |
| ----------------------- | ------------------------------ | -------------------------------- | ---- |
| `drive`                 | `throttle`, `turn` (−1 to 1)   | Arcade drive; feeds the watchdog | M3 |
| `stop`                  | none                           | Motors off immediately           | M3 |
| `kid_mode`              | `on` (true/false)              | Switches the speed cap           | M4 |
| `sound`                 | `name`                         | Plays `sounds/<name>.wav`        | M5 |
| `say`                   | `text` (up to 80 characters)   | Robot voice speaks it            | M5 |
| `move`                  | `name` (spin, wiggle, dance)   | Runs a scripted move             | M8 |

**Router — `robot/router.py` (M3).** Parses each JSON message, rejects unknown
types and out-of-range values, then calls the module.

**Audio — `robot/hardware/audio.py` (M5, M7).** `play(name)` runs `aplay`;
`say(text)` pipes `espeak-ng` into `aplay`. One lock, so sounds never overlap.
M7 adds `record(seconds)` (`arecord -f S32_LE -r 48000 -c 1`) and a
`loudness()` async generator of RMS levels.

**Camera — `robot/hardware/camera.py` (M6).** Picamera2 with its MJPEG encoder
at 640×480, 15 fps. `frames()` yields the latest JPEG per viewer; `snapshot()`
returns one. It starts on the first viewer and stops when none remain.

**Behaviours — `robot/behaviors/` (M8).** A move is a list of
`(left, right, seconds)` steps, cancelled by `stop` or a new `drive`. Clap-to-go:
two claps within 1 s above a loudness threshold start a short forward drive.

**Brain — `robot/brain/cloud.py` (M9).** Push-to-talk records 4 s and takes a
snapshot, then sends both to a cloud API. The model must answer JSON like
`{"say": "...", "move": "wiggle"}`, which the router validates against the same
allow-list. The key lives in `.env`. Requests time out after 10 s and the robot
says "Hmm, I didn't get that."

## Pi setup and deployment

- **SD card (M0):** see [sd-card-setup.md](sd-card-setup.md). Raspberry Pi OS
  Lite 32-bit (Trixie), hostname `robot-buddy`, user `robot`, Wi-Fi, SSH key.
- **Provision:** `scripts/provision.sh <step>` runs on the Pi. `base` (M1)
  installs git, Python and gpiozero/lgpio, and turns off Wi-Fi power saving.
  Later steps add `web` (M4), `speaker` (M5), `camera` (M6) and `mic` (M7).
- **No venv on the Pi.** The program uses only apt packages
  (`python3-gpiozero`, `python3-aiohttp`, `python3-yaml`, …) and runs as
  `python3 -m robot` from the checkout. The laptop uses `uv` with the same
  libraries from PyPI.
- **Deploy:** `scripts/deploy.sh` rsyncs the working tree to
  `robot@robot-buddy.local:~/robot_buddy` and restarts the service. The Pi
  needs no GitHub access.
- **Logs:** `journalctl -u robot-buddy -f`.
- **Shutdown:** motor switch off, then `sudo shutdown now` (later a button on
  the page) before unplugging, to protect the SD card.

## Development and testing

- **Laptop run:** `ROBOT_FAKE_HW=1 uv run python -m robot` uses gpiozero's
  mock pin factory, a test-pattern camera and printed sounds.
- **Tests:** `uv run pytest`. Must-have tests: the watchdog stops the motors
  after 500 ms of silence; a disconnect stops the motors; speed never exceeds
  the cap; the router rejects unknown or out-of-range commands.
- **Style:** `ruff` for lint and format; CI runs ruff and pytest on push once
  there is a GitHub remote.
- **Branches:** `main` is what runs on the robot. Try new things on a branch.

## Changes from the original design

1. **Ten small milestones instead of four phases.** The original phase 1
   needed motors, web page and camera working at once. Now the Pi boots, then
   code deploys, then the motors spin on a bench script, then keyboard
   driving, then the phone. Camera and mic come after the robot already
   drives.
2. **Keyboard teleop over SSH (M3).** Tests Drive and Safety before any web
   code. Killing SSH is a natural test for the watchdog.
3. **Speaker before mic, with its own overlay.** M5 uses a speaker-only
   overlay (`hifiberry-dac`). M7 switches to `googlevoicehat-soundcard`,
   which drives both. If the combined overlay fails, you already know the
   speaker wiring is good.
4. **STBY on a GPIO (GPIO 5, pin 29) instead of tied to 3.3 V.** Software can
   then disable the driver outright. GPIO 5 has a default pull-up, so STBY is
   high whenever the program isn't driving it; the motors still stay stopped
   because the direction and PWM pins (17, 27, 22, 23, 24, 25) default low.
5. **One check script per part** (`check_motors.py`, `check_speaker.py`, …)
   instead of a single `hw_check.py`, matching the milestone order. It also
   fixes the original `python -m scripts.hw_check`, which would not run
   because `scripts/` is not a package.
6. **rsync deploy instead of `git pull` on the Pi.** No GitHub credentials on
   the robot, and you can try uncommitted changes.
7. **No venv on the Pi.** Everything needed is in apt, so a
   `--system-site-packages` venv plus `pip install -e` only added a slow step.
8. **Provisioning in steps.** Camera and audio packages and the audio overlay
   are installed when their milestone starts, not up front.
9. **Wi-Fi power saving off.** The Zero W's Wi-Fi power saving adds latency
   spikes of hundreds of ms, which would trip the 500 ms watchdog.
10. **Joystick sends `stop` on release**, not only by going quiet, so stopping
    doesn't rely on the watchdog.

## Open questions

- Phone page or a game controller for your son? A Bluetooth gamepad could
  plug into the router the same way as teleop. (From the comment on the
  original doc.)
- Android `.local` names: Android 12+ resolves `robot-buddy.local`; older
  phones need the IP address. Do we want the page to show a QR code of the IP?
- Driving away from home Wi-Fi: should the Pi host its own hotspot later?
- Which cloud AI and speech APIs for M9, and where the key lives.
- Battery-level readout later (needs an ADC or voltage sensor).
