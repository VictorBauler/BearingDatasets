"""HAUST-LDV: ``Axial100-Radial<0|50>...-1800rpm-48khz-6206/<A|B>-<state>.csv``, state H, I02,
I03, I05, O02, O03, O05, R05, R08, R10 (fault and pitting size in tenths of mm). Semicolon
separated: time; side1 (laser Doppler velocity of the outer ring); env1 (undocumented)."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders

# SKF 6206: 9 balls of 9.525 mm on a 46 mm pitch (from published studies of this bearing)
ORDERS = fault_orders(9, 9.525, 46)
CHANNELS = {
    "ldv_velocity": {
        "sensor_location": "test_bearing_outer_ring",
        "quantity": "velocity",
        "axis": "radial",
        "unit": "unknown",
        "fs": 48000,
    },
    "env1": {
        "sensor_location": "test_bearing_outer_ring",
        "quantity": "unknown",
        "axis": "radial",
        "unit": "unknown",
        "fs": 48000,
    },
}
CONDITION = {"H": "normal", "I": "inner", "O": "outer", "R": "ball"}
NAME = re.compile(r"^(?P<load>[AB])-(?P<code>[HIOR])(?P<size>\d\d)?$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Axial100-*/*.csv")):
        m = NAME.match(path.stem)
        healthy = m["code"] == "H"
        x = pd.read_csv(path, sep=";", usecols=[1, 2], engine="c")
        yield {
            "recording_id": path.stem,
            "native_label": path.stem.split("-")[1],
            "condition": CONDITION[m["code"]],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": 0.0 if healthy else int(m["size"]) / 10,
            "rpm": 1800.0,
            "load_case": m["load"],
            "radial_load_n": 0.0 if m["load"] == "A" else 50.0,
            **ORDERS,
            "signals": {"ldv_velocity": x["side1"].to_numpy(), "env1": x["env1"].to_numpy()},
        }
