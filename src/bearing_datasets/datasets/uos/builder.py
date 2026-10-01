"""University of Seoul multi-domain compound faults: three records, one per bearing type,
``BearingType_<type>/SamplingRate_<8000|16000>/RotatingSpeed_<rpm>/
<rotor>_<bearing>_<8|16>_<model>_<rpm>.mat``. Rotor condition: H, M1-3 (misalignment), U1-3
(unbalance), L (looseness); bearing condition: H, B, IR, OR. Each file holds ``Data``
(1,280,000 samples in g) and precomputed spectrograms (not stored)."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# data paper, Table 2: 6204 8 x 7.94 on 34.57 mm; N204/NJ204 11 x 7.50 on 34; 30204 15 x 6.20
# on 35.8 at 12.6 deg
ORDERS = {
    "deep groove ball": fault_orders(8, 7.94, 34.57),
    "cylindrical roller": fault_orders(11, 7.50, 34),
    "tapered roller": fault_orders(15, 6.20, 35.8, 12.6),
}
CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",  # on top of its housing, at the shaft end
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": "vertical",
        "unit": "g",
        "fs": 16000,
    },
}
ROTOR = {"M": ("misalignment", "rig_shaft"), "U": ("unbalance", "rig_rotor"),
         "L": ("looseness", "rig")}  # fmt: skip
BEARING = {"B": "rolling_element", "IR": "inner", "OR": "outer"}
TYPE = {"DeepGrooveBall": "deep groove ball", "CylindricalRoller": "cylindrical roller",
        "TaperedRoller": "tapered roller"}  # fmt: skip
NAME = re.compile(
    r"^(?P<rotor>H|L|[MU][123])_(?P<bearing>H|B|IR|OR)_(?P<khz>8|16)_(?P<model>\w+)_(?P<rpm>\d+)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("BearingType_*/SamplingRate_*/RotatingSpeed_*/*.mat")):
        m = NAME.match(path.stem)
        conditions, locations = [], []
        if m["rotor"] != "H":
            c, loc = ROTOR[m["rotor"][0]]
            conditions.append(c)
            locations.append(loc)
        if m["bearing"] != "H":
            conditions.append(BEARING[m["bearing"]])
            locations.append("test_bearing")
        yield {
            "recording_id": path.stem,
            "native_label": f"{m['rotor']}_{m['bearing']}",
            "fault_type": "+".join(conditions) or "normal",
            "fault_location": "+".join(locations) or "none",
            "fault_origin": "artificial" if conditions else "none",
            "fault_severity": m["rotor"][1:] or "none",
            # misalignment and unbalance levels 1-3; other faults are not graded (1)
            "fault_severity_level": int(m["rotor"][1:] or 1) if conditions else 0,
            "speed_rpm": float(m["rpm"]),
            "bearing_model": m["model"],
            "bearing_type": TYPE[path.parts[-4].removeprefix("BearingType_")],
            "fs": int(m["khz"]) * 1000,
            **ORDERS[TYPE[path.parts[-4].removeprefix("BearingType_")]],
            "signals": {"vibration": read_mat(path)["Data"].ravel()},
        }
