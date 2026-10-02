"""VibroBox bearing 6213: five records, each a folder of 96 kHz int32 wav files (raw
accelerometer output) and, for the two varying-speed records, a tachometer csv per file (Unix
time, speed / 30, irregularly sampled). Labels and speeds come from the records' docx tables,
copied to meta.csv."""

from pathlib import Path

import pandas as pd
from scipy.io import wavfile

CHANNELS = {
    "vibration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",  # stud mounted on the housing
        "quantity": "acceleration",
        "unit": "raw (32 mV/g sensor)",
        "fs": 96000,
    },
    # irregularly sampled: fs is the mean rate, the exact times are in tach_time_unix
    "tach_speed": {"sensor_location": "rig_shaft", "sensor_mounting": "shaft", "quantity": "speed",
                   "unit": "rpm / 30", "fs": 1},
    "tach_time_unix": {"sensor_location": "rig_shaft", "sensor_mounting": "shaft",
                       "quantity": "time", "unit": "s", "fs": 1},
}  # fmt: skip
SUBSET = {
    "Bearing 6213 Norm-OR Dataset": "const_973rpm",
    "Bearing 6213 OR Dataset": "const_800_900rpm",
    "Constant speed dataset": "const_50_900rpm",
    "Vibration of bearing under conditions of moderately variated shaft speed": "moderate_ramps",
    "Variated speed dataset": "varying_0_900rpm",
}
META = Path(__file__).with_name("meta.csv")


def recordings(raw_dir):
    meta = pd.read_csv(META, dtype=str)
    for row in meta.itertuples(index=False):
        path = raw_dir / row.folder / row.file
        fs, x = wavfile.read(path)
        signals, rates = {"vibration": x}, {"vibration": fs}
        tach = path.with_suffix(".csv")
        if tach.exists():
            t = pd.read_csv(tach, header=None).to_numpy()
            rate = len(t) / (t[-1, 0] - t[0, 0])
            signals |= {"tach_speed": t[:, 1], "tach_time_unix": t[:, 0]}
            rates |= {"tach_speed": rate, "tach_time_unix": rate}
        subset = SUBSET[row.folder]
        yield {
            "recording_id": f"{subset}_{row.file.split('.')[0]}",
            "native_label": row.state,
            "fault_type": row.state,
            "fault_location": "none"
            if row.state == "normal"
            else "+".join(["test_bearing"] * len(row.state.split("+"))),
            "subset": subset,
            "speed_setting": row.speed_setting,
            "speed_profile": row.speed_profile,
            "bearing_model": "6213",
            "fs": rates,
            "signals": signals,
        }
