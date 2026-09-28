# CLAUDE.md

Robot Buddy: software and progress tracking for a Raspberry Pi Zero WH 2WD
robot driven from a phone. Design, pin map and milestone plan are in
`docs/DESIGN.md`; progress is the checklist in `README.md`.

## Working rules

- **Never commit.** Make changes, tick README checkboxes when a milestone is
  verified, then stop and let the user review. Commit only when asked.
- **One milestone at a time.** Don't add code or packages for a later
  milestone (camera, audio, mic, brain) before the current one works on the
  real robot.
- Keep `docs/DESIGN.md` current when a decision changes, and record what we
  learn on real hardware in the relevant doc (e.g. `docs/sd-card-setup.md`).
- `sudo` on the Pi needs a password: anything requiring it (`provision.sh`,
  reboots) is for the user to run in an interactive SSH session.
- Before moving motors, confirm with the user that the wheels are off the
  ground or the robot has room.

## The Pi

- `ssh robot@192.168.1.213` (hostname `robot-buddy`; `.local` doesn't resolve
  on this laptop yet). Raspberry Pi OS Lite 13 (Trixie), armv6l, 426 MB RAM,
  Python 3.13, NetworkManager.
- Code lives at `~/robot_buddy`, copied by `scripts/deploy.sh`
  (`ROBOT_HOST=robot@192.168.1.213`). No git pull, no venv on the Pi.
- Service: `robot-buddy.service`; logs with `journalctl -u robot-buddy -f`.

## Code conventions

- Python, one async process: `python3 -m robot`. Pins and speeds only in
  `config/robot.yaml` (BCM numbers).
- On the Pi use apt packages only (`python3-gpiozero`, `python3-yaml`, …);
  the laptop uses `uv` with the same libraries from PyPI.
- Every hardware module needs a mock so it runs on the laptop.
  `ROBOT_FAKE_HW=1` selects mocks; gpiozero needs
  `MockFactory(pin_class=MockPWMPin)` for motors.
- Check before handing back:
  `uv run --group dev pytest && uv run --group dev ruff check . && uv run --group dev ruff format --check .`
- Scripts in `scripts/` run as files (`python3 scripts/check_motors.py`), not
  as modules.
