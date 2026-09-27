from robot import config


def test_config_loads_motor_pins():
    cfg = config.load()
    motors = cfg["motors"]
    pins = [
        motors[side][k] for side in ("left", "right") for k in ("forward", "backward", "enable")
    ]
    pins.append(motors["standby"])
    assert len(set(pins)) == len(pins)
    assert not set(pins) & {18, 19, 20, 21}, "GPIO 18-21 are reserved for I2S audio"
