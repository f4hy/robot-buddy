# Robot Buddy

A Raspberry Pi Zero WH 2WD robot, driven from a phone. Design, wiring and
milestone plan: [docs/DESIGN.md](docs/DESIGN.md).

## Progress

- [x] **M0** Pi boots headless: SD card, Wi-Fi, SSH ([guide](docs/sd-card-setup.md))
- [x] **M1** Code on the Pi: `deploy.sh`, `provision.sh base`, hello service logs at boot
- [x] **M2** Speaker on the bench: `check_speaker.py` beeps and talks, `say.py` over SSH ([wiring](docs/wiring-speaker.md))
- [x] **M3** Phone app: control page with joystick (logged only, no motors yet), STOP, phrase buttons and "say" box, starts at boot
- [ ] **M4** Motors on the bench: `check_motors.py` spins each wheel the right way ([wiring](docs/wiring-motors.md))
- [ ] **M5** Drive from the laptop: keyboard teleop over SSH, watchdog stops it
- [ ] **M6** Drive from the phone: joystick moves the wheels, STOP always works, kid mode
- [ ] **M7** Camera: live video on the page
- [ ] **M8** Microphone: loudness meter, speaker still works
- [ ] **M9** Behaviours: spin, wiggle, dance, clap-to-go
- [ ] **M10** Brain: push-to-talk to a cloud AI

## Quick start

Laptop:

```sh
uv run --group dev pytest                                   # tests
ROBOT_FAKE_HW=1 ROBOT_PORT=8080 uv run python -m robot      # phone page at http://localhost:8080
ROBOT_FAKE_HW=1 uv run python scripts/check_motors.py       # mock motor check
scripts/deploy.sh                                           # copy to the Pi, restart
ROBOT_HOST=robot@192.168.1.213 scripts/deploy.sh            # if the name doesn't resolve
```

Pi (`ssh robot@robot`). Phone page: <http://robot>.

```sh
bash ~/robot_buddy/scripts/provision.sh base   # once, then sudo reboot
journalctl -u robot-buddy -f                    # logs
bash ~/robot_buddy/scripts/provision.sh speaker  # M2, once, then sudo reboot
python3 ~/robot_buddy/scripts/check_speaker.py  # M2, beep + speech
python3 ~/robot_buddy/scripts/say.py            # type a line, the robot says it
bash ~/robot_buddy/scripts/provision.sh web      # M3, once
python3 ~/robot_buddy/scripts/check_motors.py   # M4, wheels off the ground
```
