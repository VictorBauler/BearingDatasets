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
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 200000,
    },
    "encoder": {"sensor_location": "shaft", "quantity": "encoder", "unit": "V", "fs": 200000},
}
CONDITION = {"H": "normal", "I": "inner", "O": "outer", "B": "ball", "C": "inner+outer+ball"}
PROFILE = {"A": "increasing", "B": "decreasing", "C": "inc_dec", "D": "dec_inc"}
NAME = re.compile(r"^(?P<fault>[HIOBC])-(?P<profile>[ABCD])-(?P<trial>\d)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("**/*.mat")):
        m = NAME.match(path.stem)
        mat = read_mat(path)
        condition = CONDITION[m["fault"]]
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "condition": condition,
            "fault_location": "none"
            if condition == "normal"
            else "+".join(["test_bearing"] * len(condition.split("+"))),
            "speed_profile": PROFILE[m["profile"]],
            "trial": int(m["trial"]),
            **ORDERS,
            "signals": {
                "accelerometer": mat["Channel_1"].ravel(),
                "encoder": mat["Channel_2"].ravel(),
            },
        }
