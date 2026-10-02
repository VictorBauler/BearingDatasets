"""Ottawa 2018: ``<folder>/<H|I|O|B|C>-<A|B|C|D>-<trial>.mat`` with ``Channel_1``
(accelerometer) and ``Channel_2`` (encoder pulses)."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# ER16K test bearing, Huang & Baddour (2018): 9 balls of 7.94 mm, pitch diameter 38.52 mm
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    "accelerometer": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 200000,
    },
    "encoder": {
        "sensor_location": "rig_shaft",
        "sensor_mounting": "shaft",
        "quantity": "encoder",
        "unit": "V",
        "fs": 200000,
    },  # fmt: skip
}
FAULT_TYPE = {
    "H": "normal",
    "I": "inner",
    "O": "outer",
    "B": "rolling_element",
    "C": "inner+outer+rolling_element",
}
PROFILE = {"A": "increasing", "B": "decreasing", "C": "inc_dec", "D": "dec_inc"}
NAME = re.compile(r"^(?P<fault>[HIOBC])-(?P<profile>[ABCD])-(?P<trial>\d)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("**/*.mat")):
        m = NAME.match(path.stem)
        mat = read_mat(path)
        fault_type = FAULT_TYPE[m["fault"]]
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "fault_type": fault_type,
            "fault_location": "none"
            if fault_type == "normal"
            else "+".join(["test_bearing"] * len(fault_type.split("+"))),
            "speed_profile": PROFILE[m["profile"]],
            "repetition": int(m["trial"]),
            "bearing_model": "ER16K",
            **ORDERS,
            "signals": {
                "accelerometer": mat["Channel_1"].ravel(),
                "encoder": mat["Channel_2"].ravel(),
            },
        }
