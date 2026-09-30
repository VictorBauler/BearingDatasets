"""Paderborn: ``<bearing>/N15_M07_F04_<bearing>_<rep>.mat``, a nested struct whose ``Y``
field lists the channels (``Name``, ``Data``). Per-bearing facts are in bearings.csv."""

import csv
import re
import struct
from pathlib import Path

import numpy as np

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat


def _channel(location, quantity, unit, fs):
    return {"sensor_location": location, "quantity": quantity, "unit": unit, "fs": fs}


CHANNELS = {
    "vibration": _channel("bearing_module", "acceleration", "unknown", 64000),
    "phase_current_1": _channel("motor", "current", "A", 64000),
    "phase_current_2": _channel("motor", "current", "A", 64000),
    "force": _channel("shaft", "force", "N", 4000),
    "speed": _channel("shaft", "speed", "rpm", 4000),
    "torque": _channel("shaft", "torque", "Nm", 4000),
    "temperature": _channel("bearing_module", "temperature", "degC", 1),
}
RAW_NAMES = {"vibration_1": "vibration", "temp_2_bearing_module": "temperature"}
NAME = re.compile(
    r"^N(?P<n>\d\d)_M(?P<m>\d\d)_F(?P<f>\d\d)_(?P<bearing>K(?:[AIB]\d\d|\d{3}))_(?P<rep>\d+)$"
)
# the official KA08.rar has this file cut off after 8,192,000 bytes and zero-filled to its
# size: MATLAB/scipy cannot open it, but every channel before the cut is intact (the
# vibration, stored last, keeps its first 190,937 samples = 2.98 s)
TRUNCATED = {"N15_M01_F10_KA08_2"}
BEARINGS = Path(__file__).with_name("bearings.csv")


def recordings(raw_dir):
    with BEARINGS.open(encoding="utf-8") as fh:
        bearings = {r["bearing_id"]: r for r in csv.DictReader(fh)}
    # K001.rar is extracted to raw/K001/, which contains K001/*.mat
    for path in sorted(raw_dir.glob("*/*/*.mat")):
        m = NAME.match(path.stem)
        if m is None:
            continue
        b = bearings[m["bearing"]]
        if path.stem in TRUNCATED:
            signals = _read_truncated(path)
        else:
            mat = read_mat(path, squeeze_me=True, struct_as_record=False)[path.stem]
            signals = {y.Name: y.Data for y in mat.Y}
        signals = {RAW_NAMES.get(k, k): v for k, v in signals.items()}
        yield {
            "recording_id": path.stem,
            "native_label": m["bearing"],
            "condition": b["condition"],
            "fault_location": "none" if b["condition"] == "normal" else "bearing_module",
            "fault_origin": b["origin"] or "none",
            "severity": int(b["severity"]),
            "bearing_id": m["bearing"],
            "rpm": int(m["n"]) * 100.0,
            "load": int(m["m"]) / 10,
            "load_unit": "Nm",
            "radial_force_n": int(m["f"]) * 100.0,
            "repetition": int(m["rep"]),
            "damage": b["damage"],  # EDM, drilling, electric engraver, pitting, indentation
            "bearing_manufacturer": b["manufacturer"],
            # fact sheet of each bearing: 6203, 8 balls of 6.75 mm, 0 deg; pitch per manufacturer
            **fault_orders(8, 6.75, float(b["pitch_diameter_mm"])),
            "signals": {k: v for k, v in signals.items() if k in CHANNELS},
        }


def _read_truncated(path):
    """``{channel name: samples}`` of a MAT v5 file whose end was zero-filled: walks the
    structure (variable -> field Y -> each channel's Name and Data) and keeps only the
    samples stored before the zero-filled end."""
    raw = path.read_bytes()
    valid = len(raw.rstrip(b"\0"))

    def elements(start, end):  # (type, payload offset, payload size) of MAT data elements
        off = start
        while off + 8 <= end:
            kind, size = struct.unpack_from("<II", raw, off)
            if kind >> 16:  # small element: 4-byte payload in the tag
                yield kind & 0xFFFF, off + 4, kind >> 16
                off += 8
            elif kind == 0:  # zero-filled region
                return
            else:
                yield kind, off + 8, size
                off += 8 + size + (0 if kind == 14 else -size % 8)

    def fields(off, size):  # struct: {field name: [(offset, size) per element]}
        els = list(elements(off, off + size))
        n_elems = int(np.prod(struct.unpack_from(f"<{els[1][2] // 4}i", raw, els[1][1])))
        width = struct.unpack_from("<i", raw, els[3][1])[0]
        blob = raw[els[4][1] : els[4][1] + els[4][2]]
        names = [blob[i : i + width].split(b"\0")[0].decode() for i in range(0, len(blob), width)]
        values = [(o, n) for _, o, n in els[5:]]
        return {f: values[i :: len(names)][:n_elems] for i, f in enumerate(names)}

    def payload(off, size):  # the real part of a numeric or char matrix
        kind, start, n = list(elements(off, off + size))[-1]
        n = max(0, min(n, valid - start))
        dtype = {4: "<u2", 9: "<f8", 16: "u1"}[kind]
        return np.frombuffer(raw, dtype=dtype, count=n // np.dtype(dtype).itemsize, offset=start)

    (_, top, top_size), *_ = elements(128, len(raw))
    channels = fields(*fields(top, top_size)["Y"][0])
    out = {}
    for name, data in zip(channels["Name"], channels["Data"], strict=False):
        text = payload(*name)
        label = text.tobytes().decode("utf-16-le" if text.dtype == "<u2" else "utf-8")
        out[label] = payload(*data).copy()
    return out
