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
    row = ds.metadata().set_index("signal_id").loc["12k_FE_IR007_2/DE"]
    assert (row.condition, row.fault_location, row.sensor_location) == (
        "inner",
        "bearing_fe",
        "bearing_de",
    )


def test_hust_sampling_rate_fixed():
    meta = _open("hust").metadata()
    assert set(meta.fs) == {51200} and meta.rpm.between(1000, 1600).all()


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
    assert (row.condition, row.bearing_id) == ("outer", "KA08")


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
    assert (row.condition, row.fault_location) == (
        "shaft+gear+inner+inner",
        "motor+gearbox+axlebox_left+axlebox_right",
    )
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
