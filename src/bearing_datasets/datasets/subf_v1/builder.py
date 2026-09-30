"""SUBF v1: ``<bundle>/MAT Files/<Normal|Inner Race Fault|Outer Race Fault>/XYZ_<N|IR|OR>(<k>).mat``
with variables X, Y, Z of (10000, 1) at 1 kHz. The CSV Files folder repeats the same values."""

import re

import numpy as np

from bearing_datasets.io import read_mat

CHANNELS = {
    a.lower(): {"sensor_location": "test_bearing", "quantity": "acceleration", "axis": a.lower(),
                "unit": "g", "fs": 1000}
    for a in "XYZ"
}  # fmt: skip
STATE = {"N": "normal", "IR": "inner", "OR": "outer"}
NAME = re.compile(r"^XYZ_(?P<state>N|IR|OR)\((?P<k>\d+)\)$")


def recordings(raw_dir):
    paths = [(NAME.match(p.stem), p) for p in raw_dir.glob("*/MAT Files/*/*.mat")]
    for m, path in sorted(paths, key=lambda t: (t[0]["state"], int(t[0]["k"]))):
        mat = read_mat(path)
        healthy = m["state"] == "N"
        yield {
            "recording_id": f"{m['state']}_{int(m['k']):04d}",
            "native_label": m["state"],
            "condition": STATE[m["state"]],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "unknown",
            "rpm": 1440.0,
            "segment": int(m["k"]),
            "signals": {a.lower(): np.asarray(mat[a]).ravel() for a in "XYZ"},
        }
