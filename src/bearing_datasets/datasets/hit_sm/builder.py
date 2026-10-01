"""HIT-SM: ``<SpectraQuest MFS dataset|Self-built dataset>/<state>_<rpm>.mat``, state Normal,
IR2/5/8 or OR2/5/8 (fault arc of 2, 5 or 8 degrees of the raceway). Each file holds one
(262144, 1) vector at 51.2 kHz under an irregular variable name."""

import re

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": "vertical",
        "unit": "unknown",
        "fs": 51200,
    },
}
RIG = {"SpectraQuest MFS dataset": "spectraquest", "Self-built dataset": "self_built"}
SEVERITY = {"2": "slight", "5": "moderate", "8": "severe"}
NAME = re.compile(r"^(?P<state>Normal|IR|OR)(?P<deg>[258])?_(?P<rpm>\d+)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.mat")):
        m = NAME.match(path.stem)
        rig = RIG[path.parent.name]
        healthy = m["state"] == "Normal"
        (x,) = read_mat(path).values()
        yield {
            "recording_id": f"{rig}_{path.stem}",
            "native_label": path.stem.rsplit("_", 1)[0],
            "fault_type": "normal" if healthy else {"IR": "inner", "OR": "outer"}[m["state"]],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_arc_deg": 0.0 if healthy else float(m["deg"]),
            "fault_severity": "none" if healthy else SEVERITY[m["deg"]],
            "fault_severity_level": 0 if healthy else list(SEVERITY).index(m["deg"]) + 1,
            "speed_rpm": float(m["rpm"]),
            "rig": rig,
            "bearing_model": "6205" if rig == "spectraquest" else "unknown",
            "signals": {"vibration": x.ravel()},
        }
