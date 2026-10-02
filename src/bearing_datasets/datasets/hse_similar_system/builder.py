"""HSE similar system, extended: one ``data.csv`` (from Kaggle) with one row per sample: Time,
Acceleration (V), Fault (OK/IR/OR/RE), Spead_Real (Hz, sic), Speed_Set (rpm), Force (1 or 2),
Bearing+Rig, Data_No (recording 1-600). Everything but Time and Acceleration is constant within
a recording. The 300 recordings of the original (non-extended) set are recordings 1-5, 11-15,
21-25, ... (checked against the original file: same signals and labels)."""

import pandas as pd

CHANNELS = {
    "acceleration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",  # on the bearing socket, opposite the load zone
        "quantity": "acceleration",
        "unit": "V",
        "fs": 15625,
    },
}
FAULT_TYPE = {"OK": "normal", "IR": "inner", "OR": "outer", "RE": "rolling_element"}
BEARING = {  # Bearing+Rig -> (bearing model, cage, rig)
    "NU204_E_plastic_a": ("NU204-E", "plastic", "a"),
    "NU204_E_plastic_b": ("NU204-E", "plastic", "b"),
    "NU204_E_metal_b": ("NU204-E", "metal", "b"),
    "STO20_b": ("STO20", "metal", "b"),
}


def _original(number):
    """Number of the recording in the original 300-recording set, 0 if it is new."""
    block, i = divmod(number - 1, 5)
    return 0 if block % 2 else (number - 1) // 10 * 5 + i + 1


def recordings(raw_dir):
    data = pd.read_csv(raw_dir / "data.csv", engine="pyarrow")
    for number, rec in data.groupby("Data_No", sort=True):
        first = rec.iloc[0]
        model, cage, rig = BEARING[first["Bearing+Rig"]]
        fault = first["Fault"]
        yield {
            "recording_id": f"{int(number):03d}",
            "native_label": fault,
            "fault_type": FAULT_TYPE[fault],
            "fault_location": "none" if fault == "OK" else "test_bearing",
            "fault_origin": "none" if fault == "OK" else "artificial",
            "speed_rpm": float(first["Spead_Real"]) * 60,
            "load": float(first["Force"]),
            "load_unit": "level",
            "bearing_id": f"{model}_{cage}_{fault}",
            "bearing_model": model,
            "cage": cage,
            "rig": rig,
            "operating_condition": f"{int(float(first['Speed_Set']))} rpm",
            "original_recording": _original(int(number)),
            "signals": {"acceleration": rec["Acceleration"].to_numpy()},
        }
