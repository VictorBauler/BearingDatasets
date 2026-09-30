"""MAFAULDA: ``<class>.zip`` holding ``<class>[/<fault>]/<severity>/<speed Hz>.csv``, no header,
8 columns: tachometer, underhang axial/radial/tangential, overhang axial/radial/tangential,
microphone. The CSVs are read straight from the zips."""

import io
import re
import zipfile

import pandas as pd


def _ch(location, quantity, axis="none"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "fs": 50000,
    }


# official MAFAULDA page (CPM/rpm = orders), both bearings: 8 balls of 0.7145 cm, cage
# diameter 2.8519 cm
ORDERS = {"bpfo": 2.998, "bpfi": 5.002, "bsf": 1.871, "ftf": 0.375}
CHANNELS = {
    "tachometer": _ch("shaft", "tachometer"),
    "underhang_axial": _ch("bearing_underhang", "acceleration", "axial"),
    "underhang_radial": _ch("bearing_underhang", "acceleration", "radial"),
    "underhang_tangential": _ch("bearing_underhang", "acceleration", "tangential"),
    "overhang_axial": _ch("bearing_overhang", "acceleration", "axial"),
    "overhang_radial": _ch("bearing_overhang", "acceleration", "radial"),
    "overhang_tangential": _ch("bearing_overhang", "acceleration", "tangential"),
    "microphone": _ch("machine", "sound_pressure"),
}
BEARING_FAULT = {"ball_fault": "ball", "cage_fault": "cage", "outer_race": "outer"}


def _label(parts):
    """Folder parts (without the file) -> recording columns."""
    out = {"imbalance_g": 0.0, "misalignment_mm": 0.0, "misalignment_direction": "none"}
    kind = parts[0]
    if kind == "normal":
        return {**out, "condition": "normal", "fault_location": "none"}
    if kind == "imbalance":
        grams = float(parts[1].rstrip("g"))
        return {**out, "condition": "unbalance", "fault_location": "rotor", "imbalance_g": grams}
    if kind.endswith("misalignment"):
        return {
            **out,
            "condition": "misalignment",
            "fault_location": "shaft",
            "misalignment_mm": float(parts[1].rstrip("m")),
            "misalignment_direction": kind.split("-")[0],
        }
    # underhang / overhang bearing faults, possibly with an unbalance mass
    grams = float(parts[2].rstrip("g"))
    condition, location = BEARING_FAULT[parts[1]], f"bearing_{kind}"
    if grams:
        condition, location = f"{condition}+unbalance", f"{location}+rotor"
    return {**out, "condition": condition, "fault_location": location, "imbalance_g": grams}


def recordings(raw_dir):
    for archive in sorted(raw_dir.glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            for name in sorted(n for n in zf.namelist() if n.endswith(".csv")):
                parts = name.split("/")
                table = pd.read_csv(
                    io.BytesIO(zf.read(name)), header=None, engine="pyarrow", dtype="float64"
                )
                yield {
                    "recording_id": re.sub(r"[/]", "_", name.removesuffix(".csv")),
                    "native_label": "/".join(parts[:-1]),
                    **_label(parts[:-1]),
                    "rpm": float(parts[-1].removesuffix(".csv")) * 60,
                    **ORDERS,
                    "signals": {ch: table[i].to_numpy() for i, ch in enumerate(CHANNELS)},
                }
