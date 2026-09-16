import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "ev3-studio" / "robot.json"
DEFAULT_CONFIG = {
    "left_motor": "B", "right_motor": "C", "wheel_diameter_mm": 56.0,
    "axle_track_mm": 120.0, "connection": "ble", "device_name": "", "device_address": ""
}

def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **data}
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({**DEFAULT_CONFIG, **data}, indent=2), encoding="utf-8")

def distance_to_degrees(distance_mm, wheel_diameter_mm):
    if wheel_diameter_mm <= 0:
        raise ValueError("O diâmetro da roda deve ser maior que zero")
    return distance_mm / (3.141592653589793 * wheel_diameter_mm) * 360

def turn_to_degrees(angle, wheel_diameter_mm, axle_track_mm):
    if wheel_diameter_mm <= 0 or axle_track_mm <= 0:
        raise ValueError("As dimensões do robô devem ser maiores que zero")
    arc = 3.141592653589793 * axle_track_mm * angle / 360
    return distance_to_degrees(arc, wheel_diameter_mm)
