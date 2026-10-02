"""CUMTB pitch bearing: ``Cond_<k>/Cond_<k>/<1|3>rpm/<state>/vibandacoustic/va (<n>).csv``, the
10 min acquisition of each condition split into chunks of 1,000,000 samples (38.5 kHz, ~26 s).
Columns, no header: serial number, vib_y_A, vib_x_A, vib_y_B, vib_x_B, acoustic (trailing
comma). Each chunk is a recording; ``chunk`` gives its place in the acquisition."""

import re

import pandas as pd


def _ch(location, mounting, quantity, axis):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 38500,
    }


CHANNELS = {
    "vib_y_A": _ch("test_bearing", "outer_ring", "acceleration", "y"),  # point A
    "vib_x_A": _ch("test_bearing", "outer_ring", "acceleration", "x"),
    "vib_y_B": _ch("test_bearing", "outer_ring", "acceleration", "y"),  # point B
    "vib_x_B": _ch("test_bearing", "outer_ring", "acceleration", "x"),
    "acoustic": _ch("ambient", "none", "sound_pressure", "none"),  # near the outer ring
}
STATE = {  # code -> (fault_type, fault_detail); every fault is in the pitch bearing
    "Health": ("normal", "none"),
    "IRC": ("inner", "crack"),
    "IRS": ("inner", "spalling"),
    "IRW": ("inner", "wear"),
    "ORC": ("outer", "crack"),
    "ORS": ("outer", "spalling"),
    "ORW": ("outer", "wear"),
    "IORC": ("inner+outer", "crack"),
    "IORS": ("inner+outer", "spalling"),
    "IORW": ("inner+outer", "wear"),
    "RBC": ("rolling_element", "crack"),
    "ITRC": ("gear", "crack"),  # at the root of the inner ring's gear teeth
}
CHUNK = re.compile(r"\((\d+)\)")


def recordings(raw_dir):
    for folder in sorted(raw_dir.glob("Cond_*/Cond_*/*rpm/*/vibandacoustic")):
        state, speed, cond = folder.parent.name, folder.parent.parent.name, folder.parts[-5]
        fault_type, detail = STATE[state]
        parts = fault_type.split("+")
        location = "none" if fault_type == "normal" else "+".join(["test_bearing"] * len(parts))
        for path in sorted(folder.glob("va (*).csv"), key=lambda p: int(CHUNK.search(p.name)[1])):
            chunk = int(CHUNK.search(path.name)[1])
            x = pd.read_csv(path, header=None, usecols=range(1, 6), engine="c")
            yield {
                "recording_id": f"{cond}_{speed}_{state}_{chunk:02d}",
                "native_label": state,
                "fault_type": fault_type,
                "fault_location": location,
                "fault_origin": "none" if state == "Health" else "artificial",
                "fault_detail": detail,
                "speed_rpm": float(speed.removesuffix("rpm")),
                "operating_condition": cond,
                "chunk": chunk,
                "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
            }
