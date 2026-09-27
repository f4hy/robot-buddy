"""M2 bench test: spin each wheel forward then backward. Wheels off the ground!

On the Pi:     python3 scripts/check_motors.py
On a laptop:   ROBOT_FAKE_HW=1 uv run python scripts/check_motors.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gpiozero import Device, DigitalOutputDevice, Motor  # noqa: E402
from gpiozero.pins.mock import MockFactory, MockPWMPin  # noqa: E402

from robot import config  # noqa: E402

if os.environ.get("ROBOT_FAKE_HW"):
    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

SPEED = 0.5
SECONDS = 1.5


def main() -> None:
    cfg = config.load()["motors"]
    standby = DigitalOutputDevice(cfg["standby"])
    motors = {
        side: Motor(
            cfg[side]["forward"], cfg[side]["backward"], enable=cfg[side]["enable"], pwm=True
        )
        for side in ("left", "right")
    }
    input("Wheels off the ground and motor switch ON? Press Enter to start...")
    standby.on()
    try:
        for side, motor in motors.items():
            speed = -SPEED if cfg[side]["invert"] else SPEED
            print(f"{side}: forward")
            motor.forward(speed) if speed > 0 else motor.backward(-speed)
            time.sleep(SECONDS)
            motor.stop()
            time.sleep(0.5)
            print(f"{side}: backward")
            motor.backward(speed) if speed > 0 else motor.forward(-speed)
            time.sleep(SECONDS)
            motor.stop()
            time.sleep(0.5)
    finally:
        for motor in motors.values():
            motor.stop()
        standby.off()
    print("Did each wheel turn forward, then backward? If one is reversed, set its invert flag.")


if __name__ == "__main__":
    main()
