"""NEEPU: one ``.mat`` with structs ``load_0`` to ``load_3`` (0-0.3 Nm), each holding one
(660001, 1) signal per state: NB, IF, OF, BF, BO, IB, OI (12 kHz, 55 s)."""

import numpy as np

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": "none",
        "unit": "V/5",
        "fs": 12000,
    },
}
STATE = {  # native -> fault_type
    "NB": "normal",
    "IF": "inner",
    "OF": "outer",
    "BF": "rolling_element",
    "BO": "outer+rolling_element",
    "IB": "inner+rolling_element",
    "OI": "inner+outer",
}


def recordings(raw_dir):
    (path,) = raw_dir.glob("*.mat")
    mat = read_mat(path)
    for load in range(4):
        struct = mat[f"load_{load}"][0, 0]
        for state in struct.dtype.names:
            fault_type = STATE[state]
            healthy = fault_type == "normal"
            yield {
                "recording_id": f"load{load}_{state}",
                "native_label": state,
                "fault_type": fault_type,
                "fault_location": "none" if healthy else "test_bearing",
                "fault_origin": "none" if healthy else "artificial",
                "load": load / 10,
                "load_unit": "Nm",
                "signals": {"vibration": np.asarray(struct[state]).ravel()},
            }
