"""University of Ferrara run-to-failure: ``E<t>/E<t>/E<t>_<n>.mat`` (n = 1, 2, ... in time
order), each with ``y`` (5 s of acceleration in g) and ``Fs`` (25.6 kHz). Snapshots every
5 min, except the first 453 files of E4 (one per hour)."""

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# SKF 1205 ETN9 (Arpa et al. 2024, Table 2): 12 balls per row of 7.12 mm, 10.2 deg, pitch
# 38.09 mm (from the race radii); matches the paper's Table 3
ORDERS = fault_orders(12, 7.12, 38.09, 10.2)
CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": "radial",
        "unit": "g",
        "fs": 25600,
    },
}
LOAD_KN = {"E1": 4.0, "E2": 4.0, "E3": 4.0, "E4": 3.0, "E5": 4.7, "E6": 5.0}
HOURLY = {"E4": 453}  # number of hourly files at the start of the test


def _time_s(test, i):
    """Nominal time of the i-th file (0-based) from the documented intervals."""
    hourly = HOURLY.get(test, 0)
    if i < hourly:
        return i * 3600.0
    return max(hourly - 1, 0) * 3600.0 + (i - max(hourly - 1, 0)) * 300.0


def recordings(raw_dir):
    for test in sorted(LOAD_KN):
        files = sorted((raw_dir / test).glob("*/*.mat"), key=lambda p: int(p.stem.split("_")[1]))
        end_of_life = _time_s(test, len(files) - 1)
        for i, path in enumerate(files):
            mat = read_mat(path)
            yield {
                "recording_id": path.stem,
                "native_label": "unknown",
                "fault_type": "unknown",
                "fault_location": "unknown",
                "speed_rpm": 2400.0,
                "load": LOAD_KN[test],
                "load_unit": "kN",
                "bearing_model": "1205 ETN9",
                "run_id": test,
                "time_s": _time_s(test, i),
                "rul_s": end_of_life - _time_s(test, i),
                "fs": float(mat["Fs"].item()),
                **ORDERS,
                "signals": {"vibration": mat["y"].ravel()},
            }
