"""JNU: one single-column CSV (no header) per recording, named ``<fault><rpm>_...csv``:
n normal, ib inner race, ob outer race, tb roller."""

import re

import numpy as np

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": "vertical",
        "unit": "unknown",
        "fs": 50000,
    },
}
FAULT_TYPE = {"n": "normal", "ib": "inner", "ob": "outer", "tb": "rolling_element"}
NAME = re.compile(r"^(?P<fault>n|ib|ob|tb)(?P<rpm>\d+)_")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.csv")):
        m = NAME.match(path.name)
        fault = m["fault"]
        yield {
            "recording_id": path.stem,
            "native_label": fault,
            "fault_type": FAULT_TYPE[fault],
            "fault_location": "none" if fault == "n" else "test_bearing",
            "fault_origin": "none" if fault == "n" else "artificial",
            "fault_size_mm": 0.0 if fault == "n" else 0.3,
            "speed_rpm": float(m["rpm"]),
            "signals": {"vibration": np.loadtxt(path, dtype=np.float64)},
        }
