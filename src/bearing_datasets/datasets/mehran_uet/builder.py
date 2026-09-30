"""Mehran UET, two records. Vibration:
``<size>mm-bearing-faults/<size><race>-<load>watt[-xxxxxx].csv``
and ``Healthy bearing data/*.csv`` (Time Stamp, X-axis, Y-axis, Z-axis in g). Current:
``3-Phase-current-*/<name>.csv`` (Time Stamp, Current-A/B/C in A). Vibration and current files of
the same fault condition are one acquisition (same rows and time stamps) and form one recording;
the healthy and broken rotor bar files do not pair up."""

import re

import pandas as pd


def _ch(location, quantity, axis, unit):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 10000,
    }


CHANNELS = {
    "vibration_x": _ch("motor_de", "acceleration", "x", "g"),
    "vibration_y": _ch("motor_de", "acceleration", "y", "g"),
    "vibration_z": _ch("motor_de", "acceleration", "z", "g"),
    "current_a": _ch("motor", "current", "a", "A"),
    "current_b": _ch("motor", "current", "b", "A"),
    "current_c": _ch("motor", "current", "c", "A"),
}
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
            "condition": m["race"],
            "fault_location": "motor_de_bearing",
            "fault_size_mm": float(m["size"]),
            "load_condition": f"{m['load']} W",
            "signals": signals,
        }
    for path in sorted(raw_dir.glob("Healthy bearing data/*.csv")):
        yield {
            "recording_id": path.stem.lower().replace(" ", "_"),
            "native_label": path.stem,
            "condition": "normal",
            "fault_location": "none",
            "fault_size_mm": 0.0,
            "load_condition": "belt load, not stated"
            if "with pulley" in path.stem.lower()
            else "no load (without pulley)",
            "signals": _read(path, list(CHANNELS)[:3]),
        }
    for key in ("healthy", "BRB-12-4-100watt", "BRB-12-4-300watt"):
        brb = key.startswith("BRB")
        yield {
            "recording_id": f"current_{key.lower()}",
            "native_label": key,
            "condition": "electrical" if brb else "normal",
            "fault_location": "motor" if brb else "none",
            "fault_size_mm": 0.0,
            "load_condition": f"{key.split('-')[-1].removesuffix('watt')} W"
            if brb
            else "not stated",
            "signals": _read(cur[key], list(CHANNELS)[3:]),
        }
