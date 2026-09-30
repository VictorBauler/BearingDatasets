"""HIT inter-shaft bearing: ``data1.npy`` ... ``data5.npy``, one test (bearing) each, arrays of
shape (segments, 8, 20480) at 25 kHz. Rows 0-1: LP rotor displacement (horizontal, vertical);
rows 2-5: casing accelerations (measuring points 3-6); row 6 starts with the LP and HP speeds
(rpm), row 7 with the label (0 healthy, 1 inner ring, 2 outer ring)."""

from collections import Counter

import numpy as np


def _ch(location, quantity, axis="none"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 25000,
    }


CHANNELS = {
    "displacement_lp_h": _ch("lp_rotor", "displacement", "horizontal"),
    "displacement_lp_v": _ch("lp_rotor", "displacement", "vertical"),
    **{f"acceleration_{p}": _ch(f"casing_point_{p}", "acceleration") for p in (3, 4, 5, 6)},
}
TESTS = {  # file -> (condition, fault depth mm, fault length mm)
    "data1": ("normal", 0.0, 0.0),
    "data2": ("normal", 0.0, 0.0),
    "data3": ("inner", 0.5, 0.5),
    "data4": ("inner", 0.5, 1.0),
    "data5": ("outer", 0.5, 0.5),
}
LABEL = {0: "normal", 1: "inner", 2: "outer"}


def recordings(raw_dir):
    for name, (condition, depth, length) in TESTS.items():
        a = np.load(raw_dir / f"{name}.npy", mmap_mode="r")
        seen = Counter()
        for i in range(a.shape[0]):
            lp, hp = (float(v) for v in a[i, 6, :2])
            assert LABEL[int(a[i, 7, 0])] == condition, f"{name} row {i}: unexpected label"
            seen[(lp, hp)] += 1
            yield {
                "recording_id": f"{name}_{i:03d}",
                "native_label": str(int(a[i, 7, 0])),
                "condition": condition,
                "fault_location": "none" if condition == "normal" else "inter_shaft_bearing",
                "fault_origin": "none" if condition == "normal" else "artificial",
                "fault_depth_mm": depth,
                "fault_length_mm": length,
                "bearing_id": name,
                "lp_rpm": lp,
                "hp_rpm": hp,
                "segment": seen[(lp, hp)],
                "signals": {ch: np.array(a[i, j]) for j, ch in enumerate(CHANNELS)},
            }
