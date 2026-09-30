"""UAQ/UPC: one headerless single-column CSV per channel, ``<STATE>_F<hz>_<S|T>_<ch>[_<k>].csv``:
state H, BD, HB, OB, U, M, W25, W50, W75; supply 5/15/50/60 Hz; S = stationary test (one per
state and frequency), T = start-up test (repetitions k = 1-5); channels C1-C3 (4 kHz), Vx, Vy,
Vz (3 kHz), T1-T6 (1 kHz, stationary only) and RPM (1/30 Hz stationary, 100 Hz start-up)."""

import re
from collections import defaultdict

import pandas as pd


def _ch(location, quantity, axis, unit, fs):
    return {"sensor_location": location, "quantity": quantity, "axis": axis, "unit": unit,
            "fs": fs}  # fmt: skip


CHANNELS = {
    "current_1": _ch("motor_supply", "current", "a", "A", 4000),
    "current_2": _ch("motor_supply", "current", "b", "A", 4000),
    "current_3": _ch("motor_supply", "current", "c", "A", 4000),
    "vibration_x": _ch("gearbox", "acceleration", "x", "g", 3000),
    "vibration_y": _ch("gearbox", "acceleration", "y", "g", 3000),
    "vibration_z": _ch("gearbox", "acceleration", "z", "g", 3000),
    **{f"temperature_{i}": _ch("motor", "temperature", "none", "degC", 1000) for i in range(1, 7)},
    "speed": _ch("generator_shaft", "speed", "none", "rpm", 100),
}
FILE_CHANNEL = {"C1": "current_1", "C2": "current_2", "C3": "current_3", "Vx": "vibration_x",
                "Vy": "vibration_y", "Vz": "vibration_z", "RPM": "speed",
                **{f"T{i}": f"temperature_{i}" for i in range(1, 7)}}  # fmt: skip
STATE = {  # native -> (condition, fault_location, severity)
    "H": ("normal", "none", "none"),
    "BD": ("outer", "motor_bearing", "none"),
    "HB": ("electrical", "rotor", "half broken bar"),
    "OB": ("electrical", "rotor", "one broken bar"),
    "U": ("unbalance", "coupling", "none"),
    "M": ("misalignment", "coupling", "none"),
    "W25": ("gear", "gearbox", "25% wear"),
    "W50": ("gear", "gearbox", "50% wear"),
    "W75": ("gear", "gearbox", "75% wear"),
}
NAME = re.compile(
    r"^(?P<state>[A-Z]+\d*)_F(?P<hz>\d+)_(?P<test>[ST])_(?P<ch>C\d|V[xyz]|T\d|RPM)(?:_(?P<k>\d))?$"
)


def recordings(raw_dir):
    tests = defaultdict(dict)
    for path in raw_dir.glob("*.csv"):
        m = NAME.match(path.stem)
        tests[(m["state"], int(m["hz"]), m["test"], int(m["k"] or 0))][m["ch"]] = path
    for (state, hz, test, k), files in sorted(tests.items()):
        stationary = test == "S"
        condition, location, severity = STATE[state]
        signals = {
            FILE_CHANNEL[ch]: pd.read_csv(path, header=None, engine="pyarrow")[0].to_numpy()
            for ch, path in sorted(files.items())
        }
        fs = {ch: CHANNELS[ch]["fs"] for ch in signals}
        if stationary:
            fs["speed"] = 1 / 30
        yield {
            "recording_id": f"{state}_F{hz}_S" if stationary else f"{state}_F{hz}_T_{k}",
            "native_label": state,
            "condition": condition,
            "fault_location": location,
            "fault_origin": "none" if state == "H" else "artificial",
            "severity": severity,
            "speed_profile": "constant" if stationary else "increasing",
            "supply_hz": float(hz),
            "test": "stationary" if stationary else "start-up",
            "repetition": k,
            "fs": fs,
            "signals": signals,
        }
