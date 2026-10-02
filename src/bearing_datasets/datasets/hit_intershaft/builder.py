"""HIT inter-shaft bearing: ``data1.npy`` ... ``data5.npy``, one test (bearing) each, arrays of
shape (segments, 8, 20480) at 25 kHz. Rows 0-1: LP rotor displacement (horizontal, vertical);
rows 2-5: casing accelerations (measuring points 3-6); row 6 starts with the LP and HP speeds
(rpm), row 7 with the label (0 healthy, 1 inner ring, 2 outer ring)."""

from collections import Counter

import numpy as np


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 25000,
    }


CHANNELS = {
    # eddy current probes on the LP rotor; accelerometers at casing measuring points 3-6
    "displacement_lp_h": _ch("rig_rotor", "shaft", "displacement", "horizontal"),
    "displacement_lp_v": _ch("rig_rotor", "shaft", "displacement", "vertical"),
    **{f"acceleration_{p}": _ch("machine", "casing", "acceleration") for p in (3, 4, 5, 6)},
}
TESTS = {  # file -> (fault_type, fault depth mm, fault length mm, severity level)
    "data1": ("normal", 0.0, 0.0, 0),
    "data2": ("normal", 0.0, 0.0, 0),
    "data3": ("inner", 0.5, 0.5, 1),
    "data4": ("inner", 0.5, 1.0, 2),
    "data5": ("outer", 0.5, 0.5, 1),
}
LABEL = {0: "normal", 1: "inner", 2: "outer"}


def recordings(raw_dir):
    for name, (fault_type, depth, length, level) in TESTS.items():
        a = np.load(raw_dir / f"{name}.npy", mmap_mode="r")
        seen = Counter()
        for i in range(a.shape[0]):
            lp, hp = (float(v) for v in a[i, 6, :2])
            assert LABEL[int(a[i, 7, 0])] == fault_type, f"{name} row {i}: unexpected label"
            seen[(lp, hp)] += 1
            yield {
                "recording_id": f"{name}_{i:03d}",
                "native_label": str(int(a[i, 7, 0])),
                "fault_type": fault_type,
                "fault_location": "none" if level == 0 else "test_bearing",  # inter-shaft
                "fault_origin": "none" if level == 0 else "artificial",
                "fault_depth_mm": depth,
                "fault_length_mm": length,
                "fault_severity": f"{length} mm long" if level else "none",
                "fault_severity_level": level,
                "bearing_id": name,
                "lp_rpm": lp,
                "hp_rpm": hp,
                "segment": seen[(lp, hp)],
                "signals": {ch: np.array(a[i, j]) for j, ch in enumerate(CHANNELS)},
            }
