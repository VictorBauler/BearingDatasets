"""SUBF v2: ``<bundle>/Dataset/<Normal|Inner Race Fault|Outer Race Fault>/S_<N|IR|OR>(<k>).csv``,
one column without header: 100000 sound samples at 10 kHz."""

import re

import pandas as pd

CHANNELS = {
    "sound": {
        "sensor_location": "rig",
        "quantity": "sound_pressure",
        "axis": "none",
        "unit": "normalized",
        "fs": 10000,
    },
}
STATE = {"N": "normal", "IR": "inner", "OR": "outer"}
NAME = re.compile(r"^S_(?P<state>N|IR|OR)\((?P<k>\d+)\)$")


def recordings(raw_dir):
    paths = [(NAME.match(p.stem), p) for p in raw_dir.glob("*/Dataset/*/*.csv")]
    for m, path in sorted(paths, key=lambda t: (t[0]["state"], int(t[0]["k"]))):
        healthy = m["state"] == "N"
        yield {
            "recording_id": f"{m['state']}_{int(m['k']):04d}",
            "native_label": m["state"],
            "condition": STATE[m["state"]],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "unknown",
            "rpm": 1440.0,
            "segment": int(m["k"]),
            "signals": {"sound": pd.read_csv(path, header=None, engine="c")[0].to_numpy()},
        }
