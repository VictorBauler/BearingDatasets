"""CUMTB pitch bearing: ``Cond_<k>/Cond_<k>/<1|3>rpm/<state>/vibandacoustic/va (<n>).csv``, the
10 min acquisition of each condition split into chunks of 1,000,000 samples (38.5 kHz, ~26 s).
Columns, no header: serial number, vib_y_A, vib_x_A, vib_y_B, vib_x_B, acoustic (trailing
comma). Each chunk is a recording; ``chunk`` gives its place in the acquisition."""

import re

import pandas as pd


def _ch(location, quantity, axis):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 38500,
    }


CHANNELS = {
    "vib_y_A": _ch("outer_ring_A", "acceleration", "y"),
    "vib_x_A": _ch("outer_ring_A", "acceleration", "x"),
    "vib_y_B": _ch("outer_ring_B", "acceleration", "y"),
    "vib_x_B": _ch("outer_ring_B", "acceleration", "x"),
    "acoustic": _ch("near_outer_ring", "sound_pressure", "none"),
}
STATE = {  # code -> (condition, fault_location, fault type)
    "Health": ("normal", "none", "none"),
    "IRC": ("inner", "inner_raceway", "crack"),
    "IRS": ("inner", "inner_raceway", "spalling"),
    "IRW": ("inner", "inner_raceway", "wear"),
    "ORC": ("outer", "outer_raceway", "crack"),
    "ORS": ("outer", "outer_raceway", "spalling"),
    "ORW": ("outer", "outer_raceway", "wear"),
    "IORC": ("inner+outer", "inner_raceway+outer_raceway", "crack"),
    "IORS": ("inner+outer", "inner_raceway+outer_raceway", "spalling"),
    "IORW": ("inner+outer", "inner_raceway+outer_raceway", "wear"),
    "RBC": ("ball", "rolling_element", "crack"),
    "ITRC": ("gear", "inner_ring_gear_teeth", "crack"),
}
CHUNK = re.compile(r"\((\d+)\)")


def recordings(raw_dir):
    for folder in sorted(raw_dir.glob("Cond_*/Cond_*/*rpm/*/vibandacoustic")):
        state, speed, cond = folder.parent.name, folder.parent.parent.name, folder.parts[-5]
        condition, location, fault_type = STATE[state]
        for path in sorted(folder.glob("va (*).csv"), key=lambda p: int(CHUNK.search(p.name)[1])):
            chunk = int(CHUNK.search(path.name)[1])
            x = pd.read_csv(path, header=None, usecols=range(1, 6), engine="c")
            yield {
                "recording_id": f"{cond}_{speed}_{state}_{chunk:02d}",
                "native_label": state,
                "condition": condition,
                "fault_location": location,
                "fault_origin": "none" if state == "Health" else "artificial",
                "fault_type": fault_type,
                "rpm": float(speed.removesuffix("rpm")),
                "load_condition": cond,
                "chunk": chunk,
                "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
            }
