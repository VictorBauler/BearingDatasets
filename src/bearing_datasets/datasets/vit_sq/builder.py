"""VIT Vellore SpectraQuest: two records, ``<state>_<rpm>_<mass>gms.mat`` (1000-2000 rpm, 0/6/12
g) and ``<state>_<rpm>_SR12800.mat``; the second record's 1000-2000 rpm files are byte-for-byte
the 0 g files of the first, so only its 2500 rpm files are used. Each file holds
Data1_AI_1_Xaxis, _2_Yaxis, _3_Zaxis and a time vector, 12.8 kHz."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# MB ER-10K (paper, Table 2): 8 balls of 7.939 mm, pitch 33.503 mm (the text disagrees; the
# table matches MB's ER-12K/ER-10K multipliers)
ORDERS = fault_orders(8, 7.939, 33.503)
CHANNELS = {
    axis.lower(): {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": axis.lower(),
        "unit": "g",
        "fs": 12800,
    }
    for axis in "XYZ"
}
STATE = {
    "HB": "normal",
    "IRF": "inner",
    "ORF": "outer",
    "BF": "rolling_element",
    "CF": "inner+outer+rolling_element",
}
NAME = re.compile(r"^(?P<state>HB|IRF|ORF|BF|CF)_(?P<rpm>\d+)_(?:(?P<mass>\d+)gms|SR12800)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        if m["mass"] is None and m["rpm"] != "2500":
            continue  # duplicate of the 0 g file of the first record
        fault_type = STATE[m["state"]]
        mat = read_mat(path)
        yield {
            "recording_id": f"{m['state']}_{m['rpm']}_{m['mass'] or 0}g",
            "native_label": m["state"],
            "fault_type": fault_type,
            "fault_location": "none"
            if fault_type == "normal"
            else "+".join(["test_bearing"] * len(fault_type.split("+"))),
            "fault_origin": "none" if fault_type == "normal" else "artificial",
            "bearing_model": "ER-10K",
            "speed_rpm": float(m["rpm"]),
            "added_mass_g": float(m["mass"] or 0),
            **ORDERS,
            "signals": {
                a.lower(): mat[f"Data1_AI_{i + 1}_{a}axis"].ravel() for i, a in enumerate("XYZ")
            },
        }
