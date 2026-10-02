"""HUST: one .mat per recording, named ``{fault}{bearing type}0{load}``, e.g. ``IB704.mat``."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {"sensor_location": "test_bearing", "sensor_mounting": "unknown",
                  "quantity": "acceleration", "fs": 51200},
}  # fmt: skip
FAULT_TYPE = {
    "N": "normal",
    "I": "inner",
    "O": "outer",
    "B": "rolling_element",
    "IB": "inner+rolling_element",
    "IO": "inner+outer",
    "OB": "outer+rolling_element",
}
# Thuan & Hong (2023), KG bearings: (bore, outer diameter, ball diameter in mm, balls); the
# paper gives no pitch diameter, taken as (bore + outer) / 2
GEOMETRY = {"4": (20, 47, 7.6, 8), "5": (25, 52, 7.8, 9), "6": (30, 62, 9.0, 9),
            "7": (35, 72, 11.0, 9), "8": (40, 80, 12.0, 9)}  # fmt: skip

NAME = re.compile(r"^(?P<fault>N|I|O|B|IB|IO|OB)(?P<type>[4-8])0(?P<load>[024])$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        mat = read_mat(path)
        yield {
            "recording_id": path.stem,
            "native_label": m["fault"],
            "fault_type": FAULT_TYPE[m["fault"]],
            "fault_location": "none"
            if m["fault"] == "N"
            else "+".join(["test_bearing"] * len(FAULT_TYPE[m["fault"]].split("+"))),
            "fault_origin": "none" if m["fault"] == "N" else "artificial",
            "speed_rpm": float(mat["fs"].squeeze()) * 60,  # the file's `fs` is the shaft frequency
            "load": int(m["load"]) * 100.0,
            "load_unit": "W",
            "bearing_id": m["fault"] + m["type"],
            "bearing_model": f"620{m['type']}",
            **_orders(m["type"]),
            "signals": {"vibration": mat["data"].ravel()},
        }


def _orders(bearing_type):
    bore, outer, ball, balls = GEOMETRY[bearing_type]
    return fault_orders(balls, ball, (bore + outer) / 2)
