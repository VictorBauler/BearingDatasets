"""CWRU: one .mat per recording with ``X<nnn>_{DE,FE,BA}_time`` arrays and ``X<nnn>RPM``.
The condition of each file is in files.csv, one row per file of the four index pages of
https://engineering.case.edu/bearingdatacenter."""

import csv
import re
from pathlib import Path

from bearing_datasets.io import read_mat

CHANNELS = {
    "DE": {"sensor_location": "bearing_de", "quantity": "acceleration"},
    "FE": {"sensor_location": "bearing_fe", "quantity": "acceleration"},
    "BA": {"sensor_location": "base", "quantity": "acceleration"},
}
CONDITION = {"inner_race": "inner", "outer_race": "outer", "rolling_element": "ball"}
# official CWRU table (orders of shaft speed); its "rolling element" column is 2 x BSF, halved
ORDERS = {
    "DE": {"bpfi": 5.4152, "bpfo": 3.5848, "ftf": 0.39828, "bsf": 4.7135 / 2},  # 6205-2RS
    "FE": {"bpfi": 4.9469, "bpfo": 3.0530, "ftf": 0.3817, "bsf": 3.9874 / 2},  # 6203-2RS
}
FILES = Path(__file__).with_name("files.csv")


def _arrays(mat, number):
    """Some files also hold arrays of another file number: prefer the file's own."""
    found = {}
    for key, value in mat.items():
        if m := re.match(r"^X(\d+)_(DE|FE|BA)_time$", key):
            found.setdefault(m[1], {})[m[2]] = value.ravel()
    var = f"{int(number):03d}" if f"{int(number):03d}" in found else next(iter(found))
    return var, found[var]


def recordings(raw_dir):
    with FILES.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        mat = read_mat(raw_dir / row["file"])
        var, signals = _arrays(mat, row["file"].removesuffix(".mat"))
        end = row["fault_end"]  # DE, FE, or "" for normal
        fs = float(row["fs"])
        rpm_key = f"X{var}RPM"
        # the bearing of each sensor; the base plate gets the tested (faulty) bearing
        bearing = {"DE": "DE", "FE": "FE", "BA": end or "DE"}
        orders = {k: {ch: ORDERS[bearing[ch]][k] for ch in signals} for k in ORDERS["DE"]}
        yield {
            "recording_id": f"{int(fs) // 1000}k_{end + '_' if end else ''}{row['native_label']}",
            "native_label": row["native_label"],
            "condition": CONDITION.get(row["sub_element"], "normal"),
            "fault_location": f"bearing_{end.lower()}" if end else "none",
            "fault_origin": "artificial" if end else "none",
            "fault_size_mm": round(float(row["fault_size_in"]) * 25.4, 4) if end else 0.0,
            "or_position": row["or_position"] or "none",  # outer race fault position
            "rpm": float(mat[rpm_key].squeeze()) if rpm_key in mat else float(row["rpm"]),
            "load": float(row["load_hp"]),
            "load_unit": "hp",
            # outer race positions (@3, @6, @12) may be one bearing reinstalled: same id
            "bearing_id": f"{end}_{row['native_label'].split('_')[0].split('@')[0]}"
            if end
            else "healthy",
            "source_file": row["file"],
            **orders,
            "fs": fs,
            "signals": signals,
        }
