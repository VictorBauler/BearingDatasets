"""ESTOGU: ``<With_Driver_Dataset|Without_Driver_Dataset>/.../<machine>/<machine>_<load>_<Hz>.csv``,
machine N, BB, BR, RB3, RB5, SW; load code 000-555 (resistor bank position 0-5); columns
Timestamp, VibrationX/Y/Z, Current1-3, Voltage (all V), 35 kHz, 20 s."""

import re

import pandas as pd


def _ch(location, mounting, quantity, axis, unit):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 35000,
    }


CHANNELS = {
    "vibration_x": _ch("motor", "casing", "acceleration", "x", "V"),  # on the fan cover
    "vibration_y": _ch("motor", "casing", "acceleration", "y", "V"),
    "vibration_z": _ch("motor", "casing", "acceleration", "z", "V"),
    "current_1": _ch("motor_supply", "none", "current", "a", "V (100 mV/div)"),
    "current_2": _ch("motor_supply", "none", "current", "b", "V (100 mV/div)"),
    "current_3": _ch("motor_supply", "none", "current", "c", "V (100 mV/div)"),
    "voltage_uv": _ch("motor_supply", "none", "voltage", "none", "V (200 V/div)"),
}
MACHINE = {  # code -> (fault_type, fault_location, fault_origin)
    "N": ("normal", "none", "none"),
    "BB": ("rolling_element", "motor_bearing", "unknown"),
    "BR": ("bearing", "motor_bearing", "unknown"),
    "RB3": ("electrical", "motor_rotor", "artificial"),
    "RB5": ("electrical", "motor_rotor", "artificial"),
    "SW": ("electrical", "motor_stator", "artificial"),
}
RESISTANCE = {0: "no load", 1: "111 ohm", 2: "56 ohm", 3: "38 ohm", 4: "29 ohm", 5: "23 ohm"}
NAME = re.compile(r"^(?P<machine>N|BB|BR|RB3|RB5|SW)_(?P<load>\d{3})_(?P<hz>[\d.]+)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("With*_Dataset/*/*/*.csv")):
        m = NAME.match(path.stem)
        fault_type, location, origin = MACHINE[m["machine"]]
        inverter = path.parts[-4].startswith("With_")
        x = pd.read_csv(path, engine="c").iloc[:, 1:8]
        yield {
            "recording_id": f"{'inverter' if inverter else 'grid'}_{path.stem}",
            "native_label": m["machine"],
            "fault_type": fault_type,
            "fault_location": location,
            "fault_origin": origin,
            "supply": "inverter" if inverter else "grid",
            "supply_hz": float(m["hz"]),
            "speed_setpoint_rpm": float(m["hz"]) * 60,
            "load_position": int(m["load"][0]),
            "load_resistance": RESISTANCE[int(m["load"][0])],
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
