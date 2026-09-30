"""Ottawa UORED-VAFCLS: ``<folder>/<H|I|O|B|C>_<bearing>_<stage>.mat``, one (n, 5) matrix:
accelerometer, acoustic, speed, load, temperature difference (speed/load only in row 0)."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

CHANNELS = {
    "accelerometer": {
        "sensor_location": "test_bearing",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 42000,
    },
    "acoustic": {
        "sensor_location": "test_bearing",
        "quantity": "sound_pressure",
        "unit": "unknown",
        "fs": 42000,
    },
    "temperature_difference": {
        "sensor_location": "test_bearing",
        "quantity": "temperature",
        "unit": "degC",
        "fs": 42000,
    },
}
CONDITION = {"H": "normal", "I": "inner", "O": "outer", "B": "ball", "C": "cage"}
NAME = re.compile(r"^(?P<code>[HIOBC])_(?P<bearing>\d+)_(?P<stage>[012])$")


# Sehri et al. (2023), Table 2: NSK 6203ZZ and FAFNIR 203KD, 8 balls of 6.77 mm, pitch 28.50 mm
ORDERS = fault_orders(8, 6.77, 28.50)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.mat")):
        m = NAME.match(path.stem)
        (x,) = read_mat(path).values()
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "condition": CONDITION[m["code"]],
            "fault_location": "none" if m["code"] == "H" else "test_bearing",
            "rpm": float(x[0, 2]),
            **ORDERS,
            "load": float(x[0, 3]),
            "load_unit": "N",
            "bearing_id": m["bearing"],
            "severity": ["healthy", "developing", "faulty"][int(m["stage"])],
            "signals": {
                "accelerometer": x[:, 0],
                "acoustic": x[:, 1],
                "temperature_difference": x[:, 4],
            },
        }
