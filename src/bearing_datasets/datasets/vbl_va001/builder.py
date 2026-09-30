"""VBL-VA001: ``VBL-VA001/VBL-VA001/<condition>/<prefix>_<nnn>[-k]_Ch08_100g_PE_Acceleration.csv``
with no header: time (s), x, y, z at 20 kHz, blank lines between rows. Prefixes: bearing,
bearng_z, misalign, misalg_z, normal, normal_z, ub_06, ub06_z, ub_24, ub24_z. Files ending in
" - Copy.csv" duplicate other files and are skipped."""

import re

import pandas as pd

# NTN 6201: BPFO 2.62 and BPFI 4.38 from the datasheet (authors' README); FTF and BSF derived
# from them (7 balls, d/D = 0.25143, 0 deg)
ORDERS = {"bpfo": 2.62, "bpfi": 4.38, "bsf": 1.86292, "ftf": 0.37429}
CHANNELS = {
    a: {"sensor_location": "pump", "quantity": "acceleration", "axis": a, "unit": "g",
        "fs": 20000}
    for a in "xyz"
}  # fmt: skip
CONDITION = {  # folder -> (condition, fault_location)
    "normal": ("normal", "none"),
    "bearing": ("bearing", "pump_bearing"),
    "misalignment": ("misalignment", "shaft"),
    "unbalance": ("unbalance", "impeller"),
}
NAME = re.compile(r"^(?P<prefix>[a-z_]+?\d*(_z)?)_\d{3}(-\d)?_Ch08_100g_PE_Acceleration$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*/*/*.csv")):
        if path.stem.endswith(" - Copy"):
            continue
        prefix = NAME.match(path.stem)["prefix"]
        condition, location = CONDITION[path.parent.name]
        x = pd.read_csv(path, header=None, engine="c", dtype="float64")
        ub = {"06": 6.0, "24": 27.0}.get(re.sub(r"\D", "", prefix), 0.0)
        yield {
            "recording_id": path.stem.removesuffix("_Ch08_100g_PE_Acceleration"),
            "native_label": prefix,
            "condition": condition,
            "fault_location": location,
            "fault_origin": "none" if condition == "normal" else "artificial",
            "unbalance_gcm": ub,
            "file_series": "z" if prefix.endswith("_z") else "main",
            **ORDERS,
            "signals": {a: x[i + 1].to_numpy() for i, a in enumerate("xyz")},
        }
