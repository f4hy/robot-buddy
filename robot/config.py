"""Load config/robot.yaml."""

from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "robot.yaml"


def load(path: Path = DEFAULT_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
