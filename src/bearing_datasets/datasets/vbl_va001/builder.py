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
    a: {"sensor_location": "pump", "sensor_mounting": "casing", "quantity": "acceleration",
        "axis": a, "unit": "g", "fs": 20000}  # taped to the pump
    for a in "xyz"
}  # fmt: skip
FAULT = {  # folder -> (fault_type, fault_location)
    "normal": ("normal", "none"),
    "bearing": ("bearing", "pump_bearing"),
    "misalignment": ("misalignment", "coupling"),
    "unbalance": ("unbalance", "pump_impeller"),
}
NAME = re.compile(r"^(?P<prefix>[a-z_]+?\d*(_z)?)_\d{3}(-\d)?_Ch08_100g_PE_Acceleration$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*/*/*.csv")):
        if path.stem.endswith(" - Copy"):
            continue
        prefix = NAME.match(path.stem)["prefix"]
        fault_type, location = FAULT[path.parent.name]
        x = pd.read_csv(path, header=None, engine="c", dtype="float64")
        ub = {"06": 6.0, "24": 27.0}.get(re.sub(r"\D", "", prefix), 0.0)
        yield {
            "recording_id": path.stem.removesuffix("_Ch08_100g_PE_Acceleration"),
            "native_label": prefix,
            "fault_type": fault_type,
            "fault_location": location,
            "fault_origin": "none" if fault_type == "normal" else "artificial",
            # unbalance 6 / 27 gram.cm: levels 1 / 2; the other faults are not graded
            "fault_severity_level": 0 if fault_type == "normal" else 2 if ub == 27.0 else 1,
            "unbalance_gcm": ub,
            "bearing_model": "6201",
            "file_series": "z" if prefix.endswith("_z") else "main",
            **ORDERS,
            "signals": {a: x[i + 1].to_numpy() for i, a in enumerate("xyz")},
        }
