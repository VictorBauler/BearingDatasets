"""Checks against the real data, where the datasets are built:

    BEARING_DATASETS_ROOT=~/scratch uv run pytest -m integration

Datasets that are not built under the root are skipped. Signals are compared with the raw
files in the download cache (``<root>/_raw``), read independently of the builders.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.io import loadmat

import bearing_datasets as bd

pytestmark = pytest.mark.integration

COUNTS = {
    "cwru": (161, 411),
    "hust": (99, 99),
    "ottawa_uored": (60, 180),
    "paderborn": (2560, 17920),
    "bjtu_bogie": (459, 11016),
    "jnu": (12, 12),
    "mfpt": (23, 23),
    "ottawa_2018": (60, 120),
    "seu": (20, 160),
    "sca": (6644, 6644),
    "ims": (9464, 46480),
    "femto": (27907, 52796),
    "xjtu_sy": (9216, 18432),
    "phm09": (280, 840),
    "mafaulda": (1951, 15608),
}


def _open(name):
    if not os.environ.get("BEARING_DATASETS_ROOT"):
        pytest.skip("BEARING_DATASETS_ROOT not set")
    try:
        return bd.open(name)
    except FileNotFoundError:
        pytest.skip(f"{name} not built")


def _raw(name, file, member=None):
    """Path of a raw file of a package dataset in the download cache (``member``: inside the
    extracted archive ``file``). Skips if the downloads were cleaned."""
    spec_dir = Path(bd.__file__).parent / "datasets" / name
    lock = {e["name"]: e["sha256"] for e in json.loads((spec_dir / "files.lock.json").read_text())}
    path = Path(os.environ["BEARING_DATASETS_ROOT"]) / "_raw" / "sha256" / lock[file]
    path = path.with_name(f"{path.name}.d") / member if member else path
    if not path.exists():
        pytest.skip(f"raw file {file} of {name} not in the download cache")
    return path


def _built():
    root = os.environ.get("BEARING_DATASETS_ROOT")
    return sorted(p.parent.name for p in Path(root).glob("*/manifest.json")) if root else []


@pytest.mark.parametrize("name", _built())
def test_built_datasets_use_the_current_schema(name):
    """Every dataset built with this version passes today's validation."""
    from bearing_datasets.schema import validate

    ds = _open(name)
    if ds.outdated:
        pytest.skip(f"{name} was built before 0.2.0")
    notes = {c: d for c, d in zip(ds.columns().column, ds.columns().description, strict=True)}
    validate(ds.metadata(), notes)


@pytest.mark.parametrize("name", _built())
def test_readme_lists_the_standard_columns(name):
    """The README "Columns that only some datasets have" table lists this dataset for exactly
    the standard columns it has (a subset: those of the dataset it is taken from)."""
    from test_build import readme_columns

    from bearing_datasets.schema import OPTIONAL

    ds = _open(name)
    if ds.outdated:
        pytest.skip(f"{name} was built before 0.2.0")
    # a subset, or a copy built under another name (as_name): the dataset it comes from
    name = ds.manifest.get("selection", {}).get("of") or Path(ds.manifest["spec_dir"]).name
    _, table = readme_columns()
    columns = set(ds.metadata().columns)
    wrong = {c for c in OPTIONAL if (c in columns) != (name in table[c])}
    assert not wrong, f"README rows to fix for {name}: {sorted(wrong)}"


@pytest.mark.parametrize("name", _built())
def test_acceleration_units_are_plausible(name):
    """Accelerations that convert to g have an RMS a machine can have (a unit 9.81 or 1000 times
    off, or volts taken for g, shows here)."""
    ds = _open(name)
    meta = ds.metadata()
    if "unit" not in meta or ds.outdated:
        pytest.skip(f"{name} has no unit column, or was built before 0.2.0")
    acc = meta[meta.quantity == "acceleration"]
    rng = np.random.default_rng(0)
    for sid in rng.choice(acc.signal_id.to_numpy(), size=min(20, len(acc)), replace=False):
        try:
            x = ds.signal(sid, stop=200_000, unit="g")
        except ValueError:
            continue  # unit unknown, counts, or volts without a documented sensitivity
        x = x[np.isfinite(x)]
        rms = np.sqrt(np.mean((x - x.mean()) ** 2))
        assert 1e-4 < rms < 200, (sid, rms)


@pytest.mark.parametrize("name", sorted(COUNTS))
def test_counts(name):
    meta = _open(name).metadata()
    assert (meta.recording_id.nunique(), len(meta)) == COUNTS[name]


def test_cwru_matches_raw_files():
    ds = _open("cwru")
    pairs = {  # raw file and variable -> signal
        ("105.mat", "X105_DE_time"): "12k_DE_IR007_0/DE",
        ("100.mat", "X100_FE_time"): "48k_Normal_3/FE",
        ("130.mat", "X130_BA_time"): "12k_DE_OR007@6_0/BA",
    }
    for (file, var), sid in pairs.items():
        np.testing.assert_array_equal(loadmat(_raw("cwru", file))[var].ravel(), ds.signal(sid))
    meta = ds.metadata().set_index("signal_id")
    row = meta.loc["12k_FE_IR007_2/DE"]
    assert (row.fault_type, row.fault_location, row.sensor_location) == (
        "inner",
        "motor_bearing_nde",
        "motor_bearing_de",
    )
    # a fan-end fault: only the fan-end sensor is at the fault
    rec = meta[meta.recording_id == "12k_FE_IR007_2"]
    assert rec.sensor_at_fault.to_dict() == {
        "12k_FE_IR007_2/DE": False,
        "12k_FE_IR007_2/FE": True,
        "12k_FE_IR007_2/BA": False,
    }
    levels = meta.groupby("fault_severity").fault_severity_level.unique().map(list).to_dict()
    assert levels == {"none": [0], "0.007 in": [1], "0.014 in": [2], "0.021 in": [3],
                      "0.028 in": [4]}  # fmt: skip


def test_hust_sampling_rate_fixed():
    meta = _open("hust").metadata()
    assert set(meta.fs) == {51200} and meta.speed_rpm.between(1000, 1600).all()


def test_ottawa_matches_raw_file():
    ds = _open("ottawa_uored")
    raw = loadmat(_raw("ottawa_uored", "3_Outer_Race_Faults/O_9_1.mat"))["O_9_1"]
    np.testing.assert_array_equal(raw[:, 0], ds.signal("O_9_1/accelerometer"))


def test_paderborn_matches_raw_file():
    ds = _open("paderborn")
    sid = "N15_M07_F04_KA08_16"
    mat = loadmat(_raw("paderborn", "KA08.rar", f"KA08/{sid}.mat"), simplify_cells=True)[sid]
    raw = {y["Name"]: y["Data"] for y in mat["Y"]}
    np.testing.assert_array_equal(raw["vibration_1"], ds.signal(f"{sid}/vibration"))
    row = ds.metadata().set_index("signal_id").loc[f"{sid}/vibration"]
    assert (row.fault_type, row.bearing_id, row.sensor_at_fault) == ("outer", "KA08", True)
    assert row.operating_condition == "N15_M07_F04"


def test_my_cwru_matches_cwru():
    """The private-dataset example reads the same signals as the package's cwru."""
    ds, cwru = _open("my_cwru"), _open("cwru")
    np.testing.assert_array_equal(ds.signal("IR007_0/DE"), cwru.signal("12k_DE_IR007_0/DE"))
    assert (ds.metadata().recording_id.nunique(), len(ds.metadata())) == (4, 8)


def test_bjtu_matches_the_csv_in_the_zip():
    import importlib.util
    import io
    import json
    from pathlib import Path

    ds = _open("bjtu_bogie")
    spec_dir = Path(bd.__file__).parent / "datasets" / "bjtu_bogie"
    spec = importlib.util.spec_from_file_location("bjtu", spec_dir / "builder.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    lock = {e["name"]: e["sha256"] for e in json.loads((spec_dir / "files.lock.json").read_text())}
    raw = Path(os.environ["BEARING_DATASETS_ROOT"]) / "_raw" / "sha256"
    archive = builder.SplitZip([raw / lock[p] for p in builder.PARTS])
    member = next(n for n in archive.members if "M4_G3_LA1_RA1/Sample_9/data_gearbox" in n)
    csv = pd.read_csv(io.BytesIO(archive.read(member)), float_precision="round_trip")
    np.testing.assert_array_equal(csv["CH14"].to_numpy(), ds.signal("M4_G3_LA1_RA1_S9/CH14"))
    row = ds.metadata().set_index("signal_id").loc["M4_G3_LA1_RA1_S9/CH14"]
    assert (row.fault_type, row.fault_location) == (
        "shaft+gear+inner+inner",
        "motor_shaft+gearbox+axle_bearing_left+axle_bearing_right",
    )
    assert row.sensor_location == "gearbox_bearing_output" and row.sensor_at_fault
    archive.close()


def test_femto_rul_matches_the_official_values():
    meta = _open("femto").metadata()
    official = {
        "Bearing1_3": 5730,
        "Bearing1_5": 1610,
        "Bearing1_6": 1460,
        "Bearing1_7": 7570,
        "Bearing2_3": 7530,
        "Bearing2_4": 1390,
        "Bearing2_5": 3090,
        "Bearing2_6": 1290,
        "Bearing2_7": 580,
        "Bearing3_3": 820,
    }  # Bearing1_4 is a known inconsistency
    test = meta[(meta.official_set == "test") & (meta.channel == "horizontal")]
    for run, rul in official.items():
        assert test[test.run_id == run].rul_s.min() == rul
