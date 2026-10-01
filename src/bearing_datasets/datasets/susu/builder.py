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
        "sensor_location": "rig_shaft",  # fixed on the rotating shaft, near the test bearing
        "sensor_mounting": "shaft",
        "quantity": "acceleration",
        "axis": "unknown",
        "unit": "unknown",
        "fs": 31175,
    }
    for i in (1, 2, 3)
}
FAULT_TYPE = {
    "Normal": "normal",
    "Inner": "inner",
    "Outer": "outer",
    "Ball": "rolling_element",
    "Combination": "inner+outer+rolling_element",
}
NAME = re.compile(r"^(?P<state>[A-Za-z]+)_1_inch_(?P<hz>\d+)Hz$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Data_*Hz/*.mat")):
        m = NAME.match(path.stem)
        fault_type = FAULT_TYPE[m["state"]]
        (x,) = read_mat(path).values()
        yield {
            "recording_id": path.stem,
            "native_label": m["state"],
            "fault_type": fault_type,
            "fault_location": "none"
            if fault_type == "normal"
            else "+".join(["test_bearing"] * len(fault_type.split("+"))),
            "fault_origin": "none" if fault_type == "normal" else "artificial",
            "bearing_model": "ER-16K",
            "speed_rpm": int(m["hz"]) * 60.0,
            **ORDERS,
            "signals": {f"ch{i + 1}": x[i] for i in range(3)},
        }
