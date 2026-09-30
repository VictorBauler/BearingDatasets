"""NEEPU: one ``.mat`` with structs ``load_0`` to ``load_3`` (0-0.3 Nm), each holding one
(660001, 1) signal per state: NB, IF, OF, BF, BO, IB, OI (12 kHz, 55 s)."""

import numpy as np

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "quantity": "acceleration",
        "axis": "none",
        "unit": "V/5",
        "fs": 12000,
    },
}
STATE = {  # native -> condition
    "NB": "normal",
    "IF": "inner",
    "OF": "outer",
    "BF": "ball",
    "BO": "outer+ball",
    "IB": "inner+ball",
    "OI": "inner+outer",
}


def recordings(raw_dir):
    (path,) = raw_dir.glob("*.mat")
    mat = read_mat(path)
    for load in range(4):
        struct = mat[f"load_{load}"][0, 0]
        for state in struct.dtype.names:
            condition = STATE[state]
            healthy = condition == "normal"
            yield {
                "recording_id": f"load{load}_{state}",
                "native_label": state,
                "condition": condition,
                "fault_location": "none" if healthy else "test_bearing",
                "fault_origin": "none" if healthy else "artificial",
                "load": load / 10,
                "load_unit": "Nm",
                "signals": {"vibration": np.asarray(struct[state]).ravel()},
            }
