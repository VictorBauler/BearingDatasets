"""SCA: ``<case>/{train,test}.mat``. Each file has one struct per sensor position (DS/FS,
or Upper/Lower) holding N measurements: ``rawData`` (N x L, or a cell array of
different lengths), ``samplingRate``, ``RPM``, ``time`` and ``label`` per measurement."""

import numpy as np

from bearing_datasets.io import read_mat

# sensor_location and fs are given per measurement (each measurement has its position)
CHANNELS = {"vibration": {"sensor_mounting": "unknown", "quantity": "acceleration",
                          "unit": "m/s^2"}}  # fmt: skip
# the bearing at each sensor position of the machine (drive side, free side, upper, lower)
POSITION = {"DS": "machine_bearing_de", "FS": "machine_bearing_nde", "Upper": "machine_bearing",
            "Lower": "machine_bearing"}  # fmt: skip
FAULT_TYPE = {-1: "unknown", 0: "normal", 1: "inner", 2: "rolling_element", 3: "outer"}


def _rows(raw):
    """``rawData`` as a list of 1-D signals (matrix rows or cell array items)."""
    raw = np.asarray(raw)
    if raw.dtype == object:
        return [np.asarray(x, dtype=np.float64).ravel() for x in raw.ravel()]
    return list(np.atleast_2d(raw))


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.mat"), key=lambda p: (int(p.parent.name), p.name)):
        mat = read_mat(path, squeeze_me=True, struct_as_record=False)
        case, split = int(path.parent.name), path.stem
        for pos in [k for k in POSITION if k in mat]:
            s = mat[pos]
            freqs = s.faultFrequencies
            orders = {
                "bpfo": float(freqs.BPFOMultiple),
                "bpfi": float(freqs.BPFIMultiple),
                "bsf": float(freqs.BPFMultiple),
                "ftf": float(freqs.FTFMultiple),
            }
            fs = np.atleast_1d(s.samplingRate).astype(float)
            rpm = np.atleast_1d(s.RPM).astype(float)
            times = np.atleast_1d(s.time)
            labels = np.atleast_1d(s.label).astype(int)
            for i, x in enumerate(_rows(s.rawData)):
                label = int(labels[i])
                location = POSITION[pos]
                yield {
                    "recording_id": f"c{case}_{split}_{pos}_{i:04d}",
                    "native_label": str(label),
                    "fault_type": FAULT_TYPE[label],
                    "fault_location": location
                    if label > 0
                    else ("unknown" if label < 0 else "none"),
                    "sensor_location": location,
                    "speed_rpm": float(rpm[i]),
                    "case": case,
                    "sensor_position": pos,
                    "asset": str(mat["assetDescription"]),
                    "bearing_model": str(s.assetName),
                    "measured_at": str(times[i]).strip(),
                    "machine_running": label >= 0,
                    "fixed_speed": bool(mat["fixedSpeed"]),
                    "source_file": f"{case}/{path.name}",
                    "sca_label": label,
                    **orders,
                    "fs": float(fs[i]),
                    "signals": {"vibration": x},
                }
