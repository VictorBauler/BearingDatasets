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
        "sensor_mounting": "outer_ring",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 25600,
    },
}
# spall width (mm) -> severity level, per race
LEVEL = {"1.0": 1, "2.1": 2, "3.8": 3, "1.4": 1, "2.4": 2, "4.0": 3}
NAME = re.compile(r"^N(?P<load>[\d.]+)k_(?P<rpm>\d+)_(?P<width>[\d.]+)(?:_(?P<race>inner|outer))?$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        healthy = m["race"] is None
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "fault_type": "normal" if healthy else m["race"],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": float(m["width"]),
            "fault_severity": "none" if healthy else f"{m['width']} mm",
            "fault_severity_level": 0 if healthy else LEVEL[m["width"]],
            "bearing_model": "QJ212TVP",
            "speed_rpm": float(m["rpm"]),
            "load": float(m["load"]),
            "load_unit": "kN",
            **ORDERS,
            "signals": {"vibration": read_mat(path)["y_ini"].ravel()},
        }
