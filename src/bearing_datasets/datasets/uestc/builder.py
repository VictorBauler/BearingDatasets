"""UESTC: ``Data/<S>_<rpm>/<S>_<rpm>_<k>.mat``, state N, B, I or O. The five files of a
condition are consecutive pieces of one recording (``Data`` vector at ``SampleFrequency``)
and are joined back in order."""

import numpy as np

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": "unknown",
        "unit": "unknown",
        "fs": 20000,
    },
}
STATE = {"N": "normal", "B": "rolling_element", "I": "inner", "O": "outer"}


def recordings(raw_dir):
    for folder in sorted(raw_dir.glob("Data/*_*")):
        state, rpm = folder.name.split("_")
        parts = sorted(folder.glob("*.mat"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        mats = [read_mat(p) for p in parts]
        assert all(int(m["SampleFrequency"].item()) == 20000 for m in mats)
        healthy = state == "N"
        yield {
            "recording_id": folder.name,
            "native_label": state,
            "fault_type": STATE[state],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "speed_rpm": float(rpm),
            "n_files": len(parts),
            "bearing_model": "UCPH 20",
            "signals": {"vibration": np.concatenate([m["Data"].ravel() for m in mats])},
        }
