"""Saarland University (ZeMA) NU206 inner ring dataset. ``info.csv`` lists the 1151 recordings of
the published design with their folder and all factors; each is a csv with the columns
Mod1/ai0, Mod1/ai1, Mod1/ai2 (x, y, z of the accelerometer), 60 s at 20 kHz. The recordings are
located through info.csv because the archive also holds misfiled copies (e.g. B10 files inside
B20 folders) and files at two speeds not in the design (201, 592 rpm), which are not used."""

import pandas as pd

# Schaeffler NU206-E-XL-TVP2 factors (Schnur et al. 2025, Table 1; BSFF, FTF of the inner ring)
ORDERS = {"bpfo": 5.24, "bpfi": 7.76, "bsf": 2.49, "ftf": 0.40}
CHANNELS = {
    axis: {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": axis,
        "unit": "unknown",
        "fs": 20000,
    }
    for axis in "xyz"
}
POSITION = {1: "A", 2: "B", 3: "C", 4: "D"}


def _text(value):
    return "unknown" if pd.isna(value) else str(int(value))


def recordings(raw_dir):
    info = pd.read_csv(raw_dir / "info.csv")
    for row in info.itertuples(index=False):
        folder = raw_dir / "Data" / row.FolderPath.replace("\\", "/")
        x = pd.read_csv(folder / row.Filename, engine="c")
        damaged = row.DamageState == 1
        yield {
            "recording_id": row.Filename.removesuffix(".csv"),
            "native_label": "DSmall" if damaged else "DNoD",
            "fault_type": "inner" if damaged else "normal",
            "fault_location": "test_bearing" if damaged else "none",
            "fault_origin": "artificial" if damaged else "none",
            "fault_size_mm": float(row.DamageWidthMM),
            "damage_length_mm": float(row.DamageLengthMM),
            "bearing_id": f"B{row.Bearing}",
            "speed_rpm": float(row.SpeedRPM),
            "speed_setpoint_rpm": float(row.SpeedTarget),
            "force_level": int(row.ForceLevel),
            "mounting_position": POSITION[row.Position],
            "run": int(row.Run),
            "worker": int(row.Worker),
            "sensor_mounting_deviation": _text(row.SensorMounting),
            "coupling_mounting": _text(row.CouplingMounting),
            "second_shaft": _text(row.SecondShaft),
            "measurement_batch": int(row.MeasurementBatch),
            "measurement_day": int(row.MeasurementDay),
            "bearing_model": "NU206-E-XL-TVP2",
            **ORDERS,
            "signals": {axis: x.iloc[:, i].to_numpy() for i, axis in enumerate("xyz")},
        }
