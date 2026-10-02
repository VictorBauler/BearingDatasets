"""The standardized metadata table: one row per signal (one channel of one recording).

Column names follow one pattern, ``<subject>_<attribute>[_<unit>]``: related columns share a
prefix (``fault_*``, ``bearing_*``, ``speed_*``, ``sensor_*``), numeric columns with a fixed
unit end in it (``fault_size_mm``, ``time_s``, ``speed_rpm``), ``_id`` marks an identifier of a
physical or experimental entity, ``_level`` an ordinal integer (0 = healthy) and ``_setpoint`` a
nominal, not measured, value. Categorical values come from fixed vocabularies (VOCABULARIES),
checked by ``validate()``.
"""

from __future__ import annotations

import pandas as pd

# Version of this table's layout, saved in manifest.json (no value: 1, before 0.2.0).
SCHEMA_VERSION = 2

# Columns of every dataset: {name: description}.
REQUIRED = {
    "dataset": "dataset name",
    "signal_id": "unique id of the signal (one channel of one recording)",
    "recording_id": "id of the acquisition; groups the channels recorded at the same time",
    "native_label": "label exactly as the dataset names it (to reproduce papers)",
    "channel": "channel name, as the dataset names it",
    "sensor_location": "the bearing or machine part the sensor measures (see LOCATIONS)",
    "fs": "sampling rate in Hz",
    "n_samples": "number of samples",
    "fault_type": "fault(s) in the machine, '+'-joined (see FAULT_TYPES)",
    "fault_location": "monitored position of the faulty part(s), in the sensor_location "
    "vocabulary and in the order of fault_type; 'none' if normal",
    "sensor_at_fault": "True when the sensor is at a faulty position: its sensor_location is a "
    "fault_location part or contains it, or the reverse (a fault in the gearbox and a sensor at "
    "gearbox_bearing_input); never for unknown positions, and the motor supply only matches a "
    "motor_supply fault; computed from the two",
    "signal_file": "signals/ file holding the samples",
    "signal_row_group": "row group of signal_file holding the samples",
    "signal_row": "row inside that row group",
}

# Standard names for columns that only some datasets have: {name: description}.
# A column that exists must be filled for every row: use "none" when a value does not apply
# (e.g. fault_origin of a healthy bearing), "unknown" when the dataset does not say, and leave
# the column out when it only applies to some rows. dataset.yaml can add a dataset-specific
# note to any of them (e.g. what "fault_severity" means in that dataset) under `columns:`.
OPTIONAL = {
    # sensor
    "quantity": "physical quantity measured (see QUANTITIES)",
    "unit": "unit of the signal ('unknown' if the dataset does not say)",
    "axis": "measurement direction of the sensor (x/y/z, horizontal/vertical, axial/radial/"
    "tangential) or phase (a/b/c); 'none' for single-axis sensors",
    "sensor_mounting": "surface the sensor is on (ISO 20816-1): pedestal (stand-alone bearing "
    "housing), casing (machine casing at the bearing, e.g. a motor end shield), outer_ring, "
    "shaft (non-contact probe), base; 'none' without mechanical mounting (current, microphone)",
    # operating
    "speed_rpm": "shaft speed in revolutions per minute (measured, or documented as constant)",
    "speed_setpoint_rpm": "nominal or set speed in revolutions per minute (not measured)",
    "speed_profile": "how the speed changes during the recording: constant, increasing, "
    "decreasing, inc_dec (increasing then decreasing), dec_inc, or varying (shape not given)",
    "load": "load applied to the machine, in load_unit",
    "load_unit": "unit of load (e.g. hp, W, N, Nm)",
    "operating_condition": "the dataset's own id of the operating regime (speed, load, ...); "
    "use it to test generalisation across conditions",
    # fault
    "fault_origin": "how the fault was made: artificial (seeded) or real (grown in operation); "
    "'none' if healthy",
    "fault_size_mm": "size of the fault in mm; 0 if healthy",
    "fault_severity": "severity of the fault, in the dataset's own words; 'not graded' for a "
    "fault the dataset does not grade, 'none' if healthy",
    "fault_severity_level": "severity rank: 0 healthy, then 1, 2, ... from the mildest, within "
    "this dataset and fault (fault_type, or the finer fault the dataset names); 1 for a fault "
    "that is not graded (not comparable across datasets)",
    # bearing
    "bearing_id": "physical bearing tested: the same id means the same bearing (use it for "
    "grouped train/test splits)",
    "bearing_model": "bearing designation (e.g. 6205-2RS) of the bearing the frequencies refer to",
    "bpfo": "ball pass frequency of the outer race, in orders of the shaft speed (Hz = order x "
    "rpm / 60), of the test bearing (of the bearing nearest the sensor when the dataset "
    "documents several bearings)",
    "bpfi": "ball pass frequency of the inner race, in orders of the shaft speed, of the same "
    "bearing",
    "bsf": "ball spin frequency (not 2 x BSF), in orders of the shaft speed, of the same bearing; "
    "rolling element defects mostly show at 2 x bsf",
    "ftf": "fundamental train (cage) frequency, in orders of the shaft speed, of the same bearing",
    # experiment
    "repetition": "index of acquisitions repeated with the same settings",
    "run_id": "run-to-failure experiment the recording belongs to",
    "time_s": "time since the start of the run-to-failure experiment, in s",
    "rul_s": "remaining useful life at this recording (end of life - time_s), in s",
}

# Fault types, '+'-joined when a machine has several faults. Bearing parts follow ISO 5593
# (inner ring, outer ring, rolling elements, cage); "bearing" is a bearing fault of
# undocumented part.
FAULT_TYPES = (
    "normal inner outer rolling_element cage bearing gear shaft "
    "unbalance misalignment looseness electrical other unknown".split()
)

# Positions of sensors and faults: <unit>_<item>[_<position>], position last. Units and items
# follow ISO 14224 (equipment unit, maintainable item); de/nde the drive end / non-drive end of
# IEC 60034-7 (de: towards the driver); input/intermediate/output the gearbox shaft stages;
# left/right the sides of a vehicle.
# test_bearing is the bearing under study on a test rig, support_bearing the rig's own bearings.
LOCATIONS = set(
    """
    motor motor_bearing motor_bearing_de motor_bearing_nde motor_shaft motor_rotor
    motor_stator motor_supply
    gearbox gearbox_bearing gearbox_bearing_input gearbox_bearing_intermediate
    gearbox_bearing_output gearbox_shaft gearbox_shaft_input gearbox_shaft_intermediate
    gearbox_shaft_output gearbox_gear gearbox_gear_input gearbox_gear_intermediate
    gearbox_gear_output
    pump pump_bearing pump_bearing_de pump_bearing_nde pump_shaft pump_impeller
    generator generator_bearing generator_shaft
    axle axle_bearing axle_bearing_left axle_bearing_right
    test_bearing test_bearing_de test_bearing_nde
    support_bearing support_bearing_de support_bearing_nde
    rig rig_shaft rig_rotor coupling
    machine machine_bearing machine_bearing_de machine_bearing_nde
    base ambient unknown
    """.split()
)

QUANTITIES = set(
    """
    acceleration velocity displacement force torque current voltage sound_pressure
    speed angle temperature tachometer encoder time unknown
    """.split()
)

VOCABULARIES = {
    "fault_type": set(FAULT_TYPES),
    "fault_location": LOCATIONS | {"none"},
    "sensor_location": LOCATIONS,
    "sensor_mounting": {"pedestal", "casing", "outer_ring", "shaft", "base", "none", "unknown"},
    "quantity": QUANTITIES,
    "axis": set("x y z horizontal vertical axial radial tangential a b c none unknown".split()),
    "speed_profile": {
        "constant",
        "increasing",
        "decreasing",
        "inc_dec",
        "dec_inc",
        "varying",
        "unknown",
    },
    "fault_origin": {"artificial", "real", "none", "unknown"},
}
JOINED = {"fault_type", "fault_location"}  # '+'-joined values

# Builds made before 0.2.0 (schema version 1), read with today's names.
RENAMED = {"condition": "fault_type", "severity": "fault_severity", "rpm": "speed_rpm"}
RENAMED_VALUES = {"fault_type": {"ball": "rolling_element"}}
# 0.1 dataset columns whose name is now standard: moved aside first (cumtb_pitch fault_type)
DISPLACED = {"fault_type": "fault_detail"}


def renamed_columns(columns) -> dict[str, str]:
    """0.1 column name -> today's name, for the columns of a build made before 0.2.0."""
    columns = set(columns)
    out = {
        c: DISPLACED[c]
        for c in columns & set(DISPLACED)
        if any(RENAMED.get(old) == c for old in columns)
    }
    taken = (columns - set(out)) | set(out.values())
    return out | {old: new for old, new in RENAMED.items() if old in columns and new not in taken}


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


def _contains(a: str, b: str) -> bool:
    """``a`` is ``b`` or a less specific location containing it (gearbox, gearbox_bearing). The
    motor supply (currents, voltages) is not a part of the motor."""
    return a == b or (b.startswith(a + "_") and not b.endswith("_supply"))


def at_fault(sensor_location: pd.Series, fault_location: pd.Series) -> pd.Series:
    """True where the sensor is at one of the '+'-joined fault locations (or contains it)."""
    parts = fault_location.astype(str).str.split("+")
    return pd.Series(
        [
            s != "unknown"
            and any(_contains(s, f) or _contains(f, s) for f in p if f not in ("none", "unknown"))
            for s, p in zip(sensor_location.astype(str), parts, strict=True)
        ],
        index=sensor_location.index,
        dtype=bool,
    )


def upgrade(df: pd.DataFrame) -> pd.DataFrame:
    """Metadata of a build made before 0.2.0, with today's column names and fault types."""
    df = df.rename(columns=renamed_columns(df.columns))
    for col, mapping in RENAMED_VALUES.items():
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.split("+")
                .map(lambda parts, m=mapping: "+".join(m.get(p, p) for p in parts))
            )
    return df


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
    for col, allowed in VOCABULARIES.items():
        if col not in df:
            continue
        values = df[col].dropna().astype(str)
        parts = {p for v in values for p in v.split("+")} if col in JOINED else set(values)
        if bad := parts - allowed:
            errors.append(f"unknown {col} value(s) {sorted(bad)}; allowed: {sorted(allowed)}")
    if "fault_type" in df and "fault_location" in df:
        ft, loc = df["fault_type"].astype(str), df["fault_location"].astype(str)
        if ((ft == "normal") != (loc == "none")).any():
            errors.append("fault_location must be 'none' exactly for fault_type 'normal'")
        n_parts = ft.str.count(r"\+") != loc.str.count(r"\+")
        if (n_parts & (loc != "unknown")).any():
            errors.append(
                "fault_location must have one '+'-joined part per fault_type part (or be 'unknown')"
            )
    if "sensor_at_fault" in df and not pd.api.types.is_bool_dtype(df["sensor_at_fault"]):
        errors.append("sensor_at_fault must be True/False")
    if "fault_severity_level" in df:
        level = df["fault_severity_level"]
        if not pd.api.types.is_integer_dtype(level) or (level < 0).any():
            errors.append("fault_severity_level must be an integer >= 0")
        elif "fault_type" in df and ((level == 0) != (df["fault_type"] == "normal")).any():
            errors.append("fault_severity_level must be 0 exactly for fault_type 'normal'")
    if "signal_id" in df and df["signal_id"].duplicated().any():
        errors.append("duplicated signal_id")
    if errors:
        raise ValueError("invalid metadata:\n  " + "\n  ".join(errors))
