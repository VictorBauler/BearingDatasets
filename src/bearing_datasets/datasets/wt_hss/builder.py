"""Wind turbine high-speed shaft bearing: ``data-<YYYYmmddTHHMMSS>Z.mat``, one per day, with
``vibration`` (585936 samples at 97656 Hz, about 6 s) and ``tach`` (times of the
tachometer pulses in s, not a sampled signal)."""

from datetime import datetime

from bearing_datasets.io import read_mat

CHANNELS = {
    "vibration": {
        "sensor_location": "gearbox_bearing_output",  # the high-speed shaft bearing
        "sensor_mounting": "casing",
        "quantity": "acceleration",
        "unit": "g",  # as in MathWorks' example on this data
        "fs": 97656,
    },
    # pulse times, not samples: fs is the mean pulse rate of each recording
    "tach_times_s": {
        "sensor_location": "gearbox_shaft_output",
        "sensor_mounting": "shaft",
        "quantity": "time",
        "unit": "s",
        "fs": 1,
    },  # fmt: skip
}


def recordings(raw_dir):
    files = sorted(raw_dir.glob("data-*.mat"))
    times = [datetime.strptime(p.stem, "data-%Y%m%dT%H%M%SZ") for p in files]
    end_of_life = (times[-1] - times[0]).total_seconds()
    for path, t in zip(files, times, strict=True):
        mat = read_mat(path)
        tach = mat["tach"].ravel()
        time_s = (t - times[0]).total_seconds()
        yield {
            "recording_id": path.stem,
            "native_label": "unknown",
            "fault_type": "unknown",
            "fault_location": "unknown",
            "run_id": "wind_turbine",
            "time_s": time_s,
            "rul_s": end_of_life - time_s,
            "fs": {"vibration": 97656, "tach_times_s": len(tach) / (tach[-1] - tach[0])},
            "signals": {"vibration": mat["vibration"].ravel(), "tach_times_s": tach},
        }
