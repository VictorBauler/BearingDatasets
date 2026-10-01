"""SQV: ``<NC|IF_k|OF_k>/REC<n>_ch2.txt`` (vibration, g) and ``..._ch3.txt`` (speed pulses, V),
Crystal Instruments CoCo text exports at 25.6 kHz: 16 header lines, then time and value
columns. ``SpeedExtraction/data`` holds example copies and is skipped."""

import re

import pandas as pd

CHANNELS = {
    "vibration": {
        "sensor_location": "motor_bearing_de",
        "sensor_mounting": "casing",  # on the drive-end cover
        "quantity": "acceleration",
        "unit": "g",
        "fs": 25600,
    },
    "speed_pulse": {
        "sensor_location": "rig_shaft",
        "sensor_mounting": "shaft",
        "quantity": "tachometer",
        "unit": "V",
        "fs": 25600,
    },
}
FOLDER = re.compile(r"^(?P<state>NC|IF|OF)(?:_(?P<level>[123]))?$")
FAULT_TYPE = {"NC": "normal", "IF": "inner", "OF": "outer"}
SEVERITY = {"1": "mild", "2": "moderate", "3": "severe", None: "none"}


def _read(path):
    return pd.read_csv(path, sep="\t", skiprows=16, header=None, usecols=[1]).iloc[:, 0]


def recordings(raw_dir):
    for vib in sorted(raw_dir.glob("*/REC*_ch2.txt")):
        m = FOLDER.match(vib.parent.name)
        if not m:
            continue
        rec = vib.name.removesuffix("_ch2.txt")
        yield {
            "recording_id": rec,
            "native_label": vib.parent.name,
            "fault_type": FAULT_TYPE[m["state"]],
            "fault_location": "none" if m["state"] == "NC" else "motor_bearing_de",
            "fault_origin": "none" if m["state"] == "NC" else "artificial",
            "fault_severity": SEVERITY[m["level"]],
            "fault_severity_level": int(m["level"] or 0),
            "bearing_model": "6203",
            "speed_profile": "inc_dec",
            "signals": {
                "vibration": _read(vib).to_numpy(),
                "speed_pulse": _read(vib.with_name(f"{rec}_ch3.txt")).to_numpy(),
            },
        }
