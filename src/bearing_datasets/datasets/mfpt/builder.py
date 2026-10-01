"""MFPT: each .mat holds a struct ``bearing`` with ``gs`` (g), ``sr`` (Hz), ``load`` (lbs)
and ``rate`` (shaft Hz). The field types vary between files, so they are cast."""

import numpy as np

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {"sensor_location": "test_bearing", "sensor_mounting": "unknown",
                  "quantity": "acceleration", "unit": "g"}
}  # fmt: skip
FOLDERS = {  # folder prefix -> (fault_type, real-world data)
    "1 - ": ("normal", False),
    "2 - ": ("outer", False),
    "3 - ": ("outer", False),
    "4 - ": ("inner", False),
    "6 - ": ("bearing", True),  # the element is not documented
}


def _number(value):
    """Numbers are stored as int, float, uint arrays or strings depending on the file."""
    array = np.asarray(value).squeeze()
    return float(str(array).strip()) if array.size and str(array).strip() else 0.0


def recordings(raw_dir):
    root = raw_dir / "MFPT-Fault-Data-Sets-20200227T131140Z-001" / "MFPT Fault Data Sets"
    for folder in sorted(root.iterdir()):
        kind = FOLDERS.get(folder.name[:4])
        if kind is None:  # "5 - Analyses" holds scripts and a duplicate file
            continue
        fault_type, field = kind
        for path in sorted(folder.glob("*.mat")):
            b = read_mat(path, squeeze_me=True, struct_as_record=False)["bearing"]
            yield {
                "recording_id": path.stem,
                "native_label": path.stem,
                "fault_type": fault_type,
                "fault_location": "none" if fault_type == "normal" else "test_bearing",
                "speed_rpm": _number(b.rate) * 60,
                "load": _number(b.load) if hasattr(b, "load") else 0.0,
                "load_unit": "lbs",
                "field_data": field,
                "bearing_model": "unknown" if field else "NICE",
                "source_file": f"{folder.name}/{path.name}",
                "fs": _number(b.sr),
                "signals": {"vibration": b.gs},
            }
