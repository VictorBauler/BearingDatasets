"""Mehran UET, two records. Vibration:
``<size>mm-bearing-faults/<size><race>-<load>watt[-xxxxxx].csv``
and ``Healthy bearing data/*.csv`` (Time Stamp, X-axis, Y-axis, Z-axis in g). Current:
``3-Phase-current-*/<name>.csv`` (Time Stamp, Current-A/B/C in A). Vibration and current files of
the same fault condition are one acquisition (same rows and time stamps) and form one recording;
the healthy and broken rotor bar files do not pair up."""

import re

import pandas as pd


def _ch(location, mounting, quantity, axis, unit):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 10000,
    }


CHANNELS = {
    # on the motor housing near the drive-end bearing
    "vibration_x": _ch("motor_bearing_de", "casing", "acceleration", "x", "g"),
    "vibration_y": _ch("motor_bearing_de", "casing", "acceleration", "y", "g"),
    "vibration_z": _ch("motor_bearing_de", "casing", "acceleration", "z", "g"),
    "current_a": _ch("motor_supply", "none", "current", "a", "V"),
    "current_b": _ch("motor_supply", "none", "current", "b", "V"),
    "current_c": _ch("motor_supply", "none", "current", "c", "V"),
}
SIZES = ["0.7", "0.9", "1.1", "1.3", "1.5", "1.7"]  # fault width, mm: levels 1-6
FAULT = re.compile(r"^(?P<size>\d\.\d)(?P<race>inner|outer)-(?P<load>\d+)watt(?:-\w{6})?$")


def _read(path, names):
    x = pd.read_csv(path, skipinitialspace=True)
    return {n: x.iloc[:, i + 1].to_numpy() for i, n in enumerate(names)}


def recordings(raw_dir):
    vib = {
        FAULT.sub(lambda m: f"{m['size']}{m['race']}-{m['load']}watt", p.stem): p
        for p in raw_dir.glob("*mm-bearing-faults/*.csv")
    }
    cur = {p.stem: p for p in raw_dir.glob("3-Phase-current-*/*.csv")}
    for key in sorted(vib):
        m = FAULT.match(key)
        signals = _read(vib[key], list(CHANNELS)[:3])
        if key in cur:
            signals |= _read(cur[key], list(CHANNELS)[3:])
        yield {
            "recording_id": key,
            "native_label": key,
            "fault_type": m["race"],
            "fault_location": "motor_bearing_de",
            "fault_size_mm": float(m["size"]),
            "fault_severity": f"{m['size']} mm",
            "fault_severity_level": SIZES.index(m["size"]) + 1,
            "operating_condition": f"{m['load']} W",
            "bearing_model": "6204-2Z/C3",
            "signals": signals,
        }
    for path in sorted(raw_dir.glob("Healthy bearing data/*.csv")):
        yield {
            "recording_id": path.stem.lower().replace(" ", "_"),
            "native_label": path.stem,
            "fault_type": "normal",
            "fault_location": "none",
            "fault_size_mm": 0.0,
            "fault_severity": "none",
            "fault_severity_level": 0,
            "operating_condition": "belt load, not stated"
            if "with pulley" in path.stem.lower()
            else "no load (without pulley)",
            "bearing_model": "6204-2Z/C3",
            "signals": _read(path, list(CHANNELS)[:3]),
        }
    for key in ("healthy", "BRB-12-4-100watt", "BRB-12-4-300watt"):
        brb = key.startswith("BRB")
        yield {
            "recording_id": f"current_{key.lower()}",
            "native_label": key,
            "fault_type": "electrical" if brb else "normal",
            "fault_location": "motor_rotor" if brb else "none",
            "fault_size_mm": 0.0,
            "fault_severity": "not graded" if brb else "none",
            "fault_severity_level": 1 if brb else 0,
            "operating_condition": f"{key.split('-')[-1].removesuffix('watt')} W"
            if brb
            else "not stated",
            "bearing_model": "6204-2Z/C3",
            "signals": _read(cur[key], list(CHANNELS)[3:]),
        }
