# Robot Buddy

A Raspberry Pi Zero WH 2WD robot, driven from a phone. Design, wiring and
milestone plan: [docs/DESIGN.md](docs/DESIGN.md).

## Progress

- [x] **M0** Pi boots headless: SD card, Wi-Fi, SSH ([guide](docs/sd-card-setup.md))
- [x] **M1** Code on the Pi: `deploy.sh`, `provision.sh base`, hello service logs at boot
- [ ] **M2** Motors on the bench: `check_motors.py` spins each wheel the right way
- [ ] **M3** Drive from the laptop: keyboard teleop over SSH, watchdog stops it
- [ ] **M4** Drive from the phone: joystick page, STOP button, starts at boot
- [ ] **M5** Speaker: sound buttons and "say" box
- [ ] **M6** Camera: live video on the page
- [ ] **M7** Microphone: loudness meter, speaker still works
- [ ] **M8** Behaviours: spin, wiggle, dance, clap-to-go
- [ ] **M9** Brain: push-to-talk to a cloud AI

## Quick start

Laptop:

```sh
uv run --group dev pytest                                   # tests
ROBOT_FAKE_HW=1 uv run python scripts/check_motors.py       # mock motor check
scripts/deploy.sh                                           # copy to the Pi, restart
ROBOT_HOST=robot@192.168.1.213 scripts/deploy.sh            # if .local doesn't resolve
```

Pi (`ssh robot@robot-buddy.local`):

```sh
bash ~/robot_buddy/scripts/provision.sh base   # once, then sudo reboot
journalctl -u robot-buddy -f                    # logs
python3 ~/robot_buddy/scripts/check_motors.py   # M2, wheels off the ground
```
