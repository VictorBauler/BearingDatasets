"""JNU: one single-column CSV (no header) per recording, named ``<fault><rpm>_...csv``:
n normal, ib inner race, ob outer race, tb roller."""

import re

import numpy as np

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "quantity": "acceleration",
        "axis": "vertical",
        "fs": 50000,
    },
}
CONDITION = {"n": "normal", "ib": "inner", "ob": "outer", "tb": "ball"}
NAME = re.compile(r"^(?P<fault>n|ib|ob|tb)(?P<rpm>\d+)_")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.csv")):
        m = NAME.match(path.name)
        fault = m["fault"]
        yield {
            "recording_id": path.stem,
            "native_label": fault,
            "condition": CONDITION[fault],
            "fault_location": "none" if fault == "n" else "test_bearing",
            "fault_origin": "none" if fault == "n" else "artificial",
            "fault_size_mm": 0.0 if fault == "n" else 0.3,
            "rpm": float(m["rpm"]),
            "signals": {"vibration": np.loadtxt(path, dtype=np.float64)},
        }
