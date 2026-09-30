"""SUSU: ``Data_<18|20>Hz/<State>_1_inch_<Hz>Hz.mat``, one (3, n) matrix from the wireless
sensor on the shaft (31.175 kHz). The rows hold linear and angular acceleration; their order
is not documented, so they are stored as ch1-ch3."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# ER-16K: 9 balls of 7.94 mm, pitch diameter 38.52 mm (Huang & Baddour 2018, as ottawa_2018)
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    f"ch{i}": {
        "sensor_location": "shaft",
        "quantity": "acceleration",
        "axis": "unknown",
        "unit": "unknown",
        "fs": 31175,
    }
    for i in (1, 2, 3)
}
CONDITION = {
    "Normal": "normal",
    "Inner": "inner",
    "Outer": "outer",
    "Ball": "ball",
    "Combination": "inner+outer+ball",
}
NAME = re.compile(r"^(?P<state>[A-Za-z]+)_1_inch_(?P<hz>\d+)Hz$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Data_*Hz/*.mat")):
        m = NAME.match(path.stem)
        condition = CONDITION[m["state"]]
        (x,) = read_mat(path).values()
        yield {
            "recording_id": path.stem,
            "native_label": m["state"],
            "condition": condition,
            "fault_location": "none"
            if condition == "normal"
            else "+".join(["test_bearing"] * len(condition.split("+"))),
            "fault_origin": "none" if condition == "normal" else "artificial",
            "rpm": int(m["hz"]) * 60.0,
            **ORDERS,
            "signals": {f"ch{i + 1}": x[i] for i in range(3)},
        }
