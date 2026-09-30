"""DLR axial ball bearings: ``N<load>k_<rpm>_<spall width mm>[_<inner|outer>].mat``, e.g.
``N8.8k_60_2.4_outer.mat``, one (1, 768000) vector ``y_ini`` (30 s at 25.6 kHz)."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# FAG QJ212TVP (Ismail et al. 2023, Table 1): 15 balls of 15.87 mm, pitch 85.15 mm; 35 deg
# (not stated; matches the published BPFO/BPFI)
ORDERS = fault_orders(15, 15.87, 85.15, 35)
CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 25600,
    },
}
NAME = re.compile(r"^N(?P<load>[\d.]+)k_(?P<rpm>\d+)_(?P<width>[\d.]+)(?:_(?P<race>inner|outer))?$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        healthy = m["race"] is None
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "condition": "normal" if healthy else m["race"],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": float(m["width"]),
            "rpm": float(m["rpm"]),
            "load": float(m["load"]),
            "load_unit": "kN",
            **ORDERS,
            "signals": {"vibration": read_mat(path)["y_ini"].ravel()},
        }
