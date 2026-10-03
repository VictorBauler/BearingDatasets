"""University of Adelaide defect slope and length series (figshare), files
``Bearing<slope>EDM[<n>]or_1000degree_110depth_<load>N_<Hz>Hz.mat`` (slope series) and
``BallBearing90EDM[<n>]or_<length>degree_100depth_<load>N_<Hz>Hz.mat`` (length series). Each
holds the raw ``data`` (256000 x 8, V: tacho, eddy x, eddy y, acc x, acc y, "Wenglor", load,
SPL) and the authors' scaled copies Ex, Ey, Ax, Ay, Wenglor, Load, SPL, which are stored here,
plus the raw tacho column."""

import re

from bearing_datasets.io import read_mat


def _ch(location, mounting, quantity, axis="none", unit="V"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 25600,
    }


CHANNELS = {
    "Ex": _ch("test_bearing", "outer_ring", "displacement", "x", "um"),  # eddy-current probes
    "Ey": _ch("test_bearing", "outer_ring", "displacement", "y", "um"),
    "Ax": _ch("test_bearing", "pedestal", "acceleration", "x", "m/s^2"),
    "Ay": _ch("test_bearing", "pedestal", "acceleration", "y", "m/s^2"),
    "Wenglor": _ch("unknown", "unknown", "unknown"),
    "Load": _ch("test_bearing", "unknown", "force", unit="N"),
    "SPL": _ch("ambient", "none", "sound_pressure"),
    "tacho": _ch("rig_shaft", "shaft", "tachometer"),
}
NAME = re.compile(
    r"^(?P<specimen>(?:Ball)?Bearing(?P<slope>\d+)EDM(?P<n>\d*)or)_(?P<len>[\d.]+)degree_"
    r"(?P<depth>\d+)depth_(?P<load>\d+)N_(?P<hz>[\d.]+)Hz$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        length_series = path.stem.startswith("Ball")
        mat = read_mat(path)
        signals = {ch: mat[ch].ravel() for ch in list(CHANNELS)[:-1]}
        signals["tacho"] = mat["data"][:, 0]
        yield {
            "recording_id": path.stem,
            "native_label": m["specimen"],
            "fault_type": "outer",
            "fault_location": "test_bearing",
            "fault_origin": "artificial",
            "series": "length" if length_series else "slope",
            "defect_slope_deg": float(m["slope"]),
            "defect_length_deg": float(m["len"]) if length_series else 0.0,
            "defect_depth_um": float(m["depth"]),
            "speed_rpm": float(m["hz"]) * 60,
            "load": float(m["load"]),
            "load_unit": "N",
            "fs": float(mat["Fs"].item()),
            "signals": signals,
        }
