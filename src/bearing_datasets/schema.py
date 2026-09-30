"""The standardized metadata table: one row per signal (one channel of one recording)."""

from __future__ import annotations

import pandas as pd

# Columns of every dataset: {name: description}.
REQUIRED = {
    "dataset": "dataset name",
    "signal_id": "unique id of the signal (one channel of one recording)",
    "recording_id": "id of the acquisition; groups the channels recorded at the same time",
    "native_label": "label exactly as the dataset names it (to reproduce papers)",
    "channel": "channel name",
    "sensor_location": "where the sensor is mounted (e.g. bearing_de, motor)",
    "fs": "sampling rate in Hz",
    "n_samples": "number of samples",
    "condition": "fault(s) in the machine, '+'-joined (see CONDITIONS)",
    "fault_location": "where the fault(s) are, in the order of condition; 'none' if normal",
    "signal_file": "signals/ file holding the samples",
    "signal_row_group": "row group of signal_file holding the samples",
    "signal_row": "row inside that row group",
}

# Standard names for columns that only some datasets have: {name: description}.
# A column that exists must be filled for every row: use "none" when a value does not apply
# (e.g. fault_origin of a healthy bearing), "unknown" when the dataset does not say, and leave
# the column out when it only applies to some rows. dataset.yaml can add a dataset-specific
# note to any of them (e.g. what "severity" means in that dataset) under `columns:`.
OPTIONAL = {
    "quantity": "physical quantity: acceleration, current, sound_pressure, speed, torque, force, "
    "temperature, tachometer (pulses), encoder (pulses), ...",
    "unit": "unit of the signal ('unknown' if the dataset does not say)",
    "axis": "axis of a multi-axis sensor (x/y/z) or phase (a/b/c); 'none' for single-axis sensors",
    "rpm": "shaft speed in revolutions per minute",
    "load": "load applied to the machine, in load_unit",
    "load_unit": "unit of load (e.g. hp, W, N, Nm)",
    "bearing_id": "physical bearing tested: the same id means the same bearing (use it for "
    "grouped train/test splits)",
    "fault_origin": "how the fault was made: artificial (seeded) or real (grown in operation); "
    "'none' if healthy",
    "fault_size_mm": "size of the fault in mm; 0 if healthy",
    "severity": "severity of the fault, as the dataset defines it",
    "speed_profile": "how the speed changes during the recording: constant, increasing, "
    "decreasing, inc_dec (increasing then decreasing) or dec_inc",
    "bpfo": "ball pass frequency of the outer race, in orders of the shaft speed (Hz = order x "
    "rpm / 60), of the test bearing (of the bearing nearest the sensor when the dataset "
    "documents several bearings)",
    "bpfi": "ball pass frequency of the inner race, in orders of the shaft speed, of the same "
    "bearing",
    "bsf": "ball spin frequency (not 2 x BSF), in orders of the shaft speed, of the same bearing; "
    "ball defects mostly show at 2 x bsf",
    "ftf": "fundamental train (cage) frequency, in orders of the shaft speed, of the same bearing",
    "run_id": "run-to-failure experiment the recording belongs to",
    "time_s": "time since the start of the run-to-failure experiment, in s",
    "rul_s": "remaining useful life at this recording (end of life - time_s), in s",
}

CONDITIONS = set(
    "normal inner outer ball cage bearing gear shaft "
    "unbalance misalignment looseness electrical other unknown".split()
)


def order_columns(df: pd.DataFrame) -> pd.DataFrame:
    std = [c for c in [*REQUIRED, *OPTIONAL] if c in df.columns]
    return df[std + [c for c in df.columns if c not in std]]


def describe(df: pd.DataFrame, notes: dict[str, str] | None = None) -> dict[str, str]:
    """Description of every column: standard description, plus the dataset's own note."""
    notes = notes or {}
    out = {}
    for col in df.columns:
        std = REQUIRED.get(col) or OPTIONAL.get(col)
        out[col] = f"{std}. {notes[col]}" if std and col in notes else std or notes.get(col)
    return out


def validate(df: pd.DataFrame, notes: dict[str, str] | None = None) -> None:
    """Raise ``ValueError`` listing every problem of a metadata table."""
    errors = []
    undocumented = [c for c, d in describe(df, notes).items() if not d]
    if undocumented:
        errors.append(
            f"columns without a description {undocumented}: describe them in "
            "dataset.yaml under `columns:`"
        )
    if df.empty:
        errors.append("no signals (check the raw file patterns in the builder)")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        errors.append(f"missing required columns: {missing}")
    if nulls := [c for c in df.columns if df[c].isna().any()]:
        errors.append(f"null values in {nulls}: use 'none' / 'unknown' or drop the column")
    if "condition" in df:
        parts = {p for c in df["condition"].dropna() for p in str(c).split("+")}
        if bad := parts - CONDITIONS:
            errors.append(f"unknown condition(s) {sorted(bad)}; allowed: {sorted(CONDITIONS)}")
    if "signal_id" in df and df["signal_id"].duplicated().any():
        errors.append("duplicated signal_id")
    if errors:
        raise ValueError("invalid metadata:\n  " + "\n  ".join(errors))
