"""IM-VACD: ``<n>_<Hand_Held|Rigid>_Mounting_10_seconds/<n>_<Unloaded|Loaded>/<n>_<phone>/
<P>-<S>-<C>-<speed>-<load>.csv`` (phone letter, two state letters, speed 1-4 = 15-30 Hz, load
0/1). Columns acoustic, x, y, z (the accelerometer columns are shorter and padded with
blanks), then settings (set and measured sampling rates, units, device) in the first row
only; their column order varies between files."""

import pandas as pd

# the phone's microphone and accelerometer, the phone on the motor (held or mounted)
CHANNELS = {
    "acoustic": {"sensor_location": "ambient", "sensor_mounting": "none",
                 "quantity": "sound_pressure", "axis": "none", "unit": "normalized", "fs": 44100},
    **{a: {"sensor_location": "motor", "quantity": "acceleration", "axis": a,
           "unit": "m/s^2", "fs": 200} for a in "xyz"},
}  # fmt: skip
STATE = {  # state letters -> (native label, fault_type, fault_location)
    "H-H": ("healthy", "normal", "none"),
    "F-B": ("faulty bearing", "bearing", "motor_bearing"),
    "B-R": ("bowed rotor", "shaft", "motor_rotor"),
    "K-A": ("broken rotor bars", "electrical", "motor_rotor"),
    "R-U": ("rotor unbalance", "unbalance", "motor_rotor"),
    "R-M": ("rotor misalignment", "misalignment", "motor_rotor"),
    "S-W": ("stator winding fault", "electrical", "motor_stator"),
    "V-U": ("voltage unbalance", "electrical", "motor_supply"),
}
PHONE = {"A": "iphone_13", "B": "galaxy_s6", "C": "galaxy_a50"}


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*/*/*.csv")):
        phone, s1, s2, speed, load = path.stem.split("-")
        label, fault_type, location = STATE[f"{s1}-{s2}"]
        mounting = "hand_held" if "Hand_Held" in path.parts[-4] else "rigid"
        x = pd.read_csv(path, engine="c", dtype=str, keep_default_na=False)
        meta = x.iloc[0]
        sig = {c: pd.to_numeric(x[c].replace("", None)).dropna().to_numpy("float64")
               for c in ("acoustic", "x", "y", "z")}  # fmt: skip
        fs_ac = round(float(meta["acoustic_sampling_frequency_real"]))
        fs_acc = round(float(meta["accelerometer_sampling_frequency_real"]))
        yield {
            "recording_id": f"{mounting}_{'loaded' if load == '1' else 'unloaded'}_{path.stem}",
            "native_label": label,
            "fault_type": fault_type,
            "fault_location": location,
            "fault_origin": "none" if fault_type == "normal" else "artificial",
            "speed_rpm": 60.0 * {"1": 15, "2": 20, "3": 25, "4": 30}[speed],
            "load": float(load),
            "load_unit": "loaded (1) or not (0)",
            "phone": PHONE[phone],
            "phone_mounting": mounting,
            # a rigidly mounted phone is on the casing; a hand-held one is not mounted
            "sensor_mounting": {
                "acoustic": "none",
                **dict.fromkeys("xyz", "casing" if mounting == "rigid" else "unknown"),
            },
            "acoustic_fs_set": int(float(meta["acoustic_sampling_frequency_set"])),
            "accelerometer_fs_set": int(float(meta["accelerometer_sampling_frequency_set"])),
            "fs": {"acoustic": fs_ac, "x": fs_acc, "y": fs_acc, "z": fs_acc},
            "signals": sig,
        }
