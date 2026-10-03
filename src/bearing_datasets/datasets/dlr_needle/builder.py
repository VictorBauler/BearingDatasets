"""DLR oscillating needle bearing endurance tests: ``Test_<n>[_Data_<a>_to_<b>]/Test_<n>/
Test<n>_<oil>_<amplitude>-<load>-<frequency>_Data_<a>_to_<b>_<sensor>.mat`` (decimal comma in
the parameters, e.g. 10-19,4-5). Each file holds one (time, value) matrix with all the 10 s
snapshots of the test (one every ~15 min) one after the other; snapshots are split at gaps in
the time vector. Sensors ending in _1 / _2 are on needle bearing 1 / 2."""

import re

import numpy as np

from bearing_datasets.io import read_mat

# angle from the file suffix, force matching the load in the file name, temperatures 20-48
UNIT = {"angle": "deg", "force": "kN", "temperature": "degC"}


def _ch(location, mounting, quantity, fs):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "unit": UNIT.get(quantity, "unknown"),
        "fs": fs,
    }


# both needle bearings are test bearings (the channel's _1 / _2 tells which)
SENSORS = {  # file suffix -> (channel, location, mounting, quantity, fs)
    "Acc_Sensor_1": ("acc_1", "test_bearing", "unknown", "acceleration", 10000),
    "Acc_Sensor_2": ("acc_2", "test_bearing", "unknown", "acceleration", 10000),
    "Distance_Sensor_1": ("distance_1", "test_bearing", "unknown", "displacement", 10000),
    "Distance_Sensor_2": ("distance_2", "test_bearing", "unknown", "displacement", 10000),
    "Torque": ("torque", "rig_shaft", "shaft", "torque", 10000),
    "Position_deg": ("position_deg", "rig_shaft", "shaft", "angle", 1000),
    "Force_Sensor_1": ("force_1", "test_bearing", "unknown", "force", 100),
    "Force_Sensor_2": ("force_2", "test_bearing", "unknown", "force", 100),
    "Temp_Sensor_1": ("temperature_1", "test_bearing", "unknown", "temperature", 10),
    "Temp_Sensor_2": ("temperature_2", "test_bearing", "unknown", "temperature", 10),
    "Ambient_Temp": ("temperature_ambient", "ambient", "none", "temperature", 10),
}
CHANNELS = {ch: _ch(loc, mnt, q, fs) for ch, loc, mnt, q, fs in SENSORS.values()}
LAST_SNAPSHOT = {3: 4951}  # tests split over several zips: the last snapshot number
NAME = re.compile(
    r"^Test(?P<test>\d)_(?P<oil>[A-Za-z0-9]+)_(?P<amp>[\d,]+)-(?P<load>[\d,]+)-(?P<freq>[\d,]+)"
    r"_Data_(?P<a>\d+)_to_(?P<b>\d+)_(?P<sensor>.+)$"
)


def _num(text):
    return float(text.replace(",", "."))


def _split(mat):
    """Snapshots of a (time, value) matrix: [(start time, values)], split at gaps > 1 s."""
    t = mat[:, 0]
    cuts = np.flatnonzero(np.diff(t) > 1.0) + 1
    return [
        (float(t[s]), v) for s, v in zip(np.r_[0, cuts], np.split(mat[:, 1], cuts), strict=True)
    ]


def recordings(raw_dir):
    groups = {}  # (test, first snapshot) -> [(name match, path)]
    for path in raw_dir.glob("Test_*/Test_*/*.mat"):
        m = NAME.match(path.stem)
        groups.setdefault((int(m["test"]), int(m["a"])), []).append((m, path))
    for test, last in LAST_SNAPSHOT.items():
        parts = [g for g in groups if g[0] == test]
        names = [m["b"] for g in parts for m, _ in groups[g][:1]]
        if parts and str(last) not in names:
            raise ValueError(f"Test {test} is split over several zips: include all of them")
    end_of_life = {}
    # the last group of a test first: its last snapshot is the end of the test
    for test, first in sorted(groups, key=lambda k: (k[0], -k[1])):
        files = groups[(test, first)]
        snaps = {m["sensor"]: _split(read_mat(p).popitem()[1]) for m, p in files}
        starts = [t for t, _ in snaps["Acc_Sensor_1"]]
        end_of_life.setdefault(test, starts[-1])
        m = files[0][0]
        for i, start in enumerate(starts):
            yield {
                "recording_id": f"test{test}_{first + i:04d}",
                "native_label": "unknown",
                "fault_type": "unknown",
                "fault_location": "unknown",
                "run_id": f"test{test}",
                "time_s": start,
                "rul_s": end_of_life[test] - start,
                "lubrication": m["oil"],
                "amplitude_deg": _num(m["amp"]),
                "load": _num(m["load"]),
                "load_unit": "kN",
                "oscillation_hz": _num(m["freq"]),
                "snapshot": first + i,
                "signals": {SENSORS[s][0]: snaps[s][i][1] for s in snaps},
            }
