"""URMA-CRTI: one ``URMA_Database.mat`` with a time vector ``t`` and one variable per
recording, ``<state><supply Hz>`` (French codes): s (sain, healthy), ci / ce (inner / outer
ring), b (bille, ball), c (combined), e.g. ``ci45``."""

import re

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 25600,
    },
}
FAULT_TYPE = {"s": "normal", "ci": "inner", "ce": "outer", "b": "rolling_element", "c": "bearing"}
NAME = re.compile(r"^(?P<state>s|ci|ce|b|c)(?P<hz>\d{2})$")


def recordings(raw_dir):
    mat = read_mat(raw_dir / "URMA_Database.mat")
    for name, x in mat.items():
        if not (m := NAME.match(name)):
            continue  # the time vector t
        healthy = m["state"] == "s"
        yield {
            "recording_id": name,
            "native_label": name,
            "fault_type": FAULT_TYPE[m["state"]],
            "fault_location": "none" if healthy else "test_bearing",
            "supply_hz": int(m["hz"]),
            "signals": {"vibration": x.ravel()},
        }
