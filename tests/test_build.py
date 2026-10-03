import getpass
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import bearing_datasets as bd
from bearing_datasets.build import build, list_datasets, load_spec
from bearing_datasets.schema import REQUIRED, validate

PRIVATE_EXAMPLE = Path(__file__).parents[1] / "examples" / "private_datasets" / "my_cwru"


def test_layout_and_lock(toy_build, toy_dir):
    assert (toy_build / "metadata.parquet").exists()
    assert sorted(p.name for p in (toy_build / "signals").iterdir()) == [
        "part-float32.parquet",
        "part-float64.parquet",
        "part-int16.parquet",
    ]
    manifest = json.loads((toy_build / "manifest.json").read_text())
    assert manifest["n_recordings"] == 3 and manifest["n_signals"] == 15
    assert {f["source"] for f in manifest["raw_files"]} == {"primary"}
    # no user or machine name in a build (spec_dir is a path, which may hold the user name)
    text = json.dumps({k: v for k, v in manifest.items() if k != "spec_dir"})
    assert getpass.getuser() not in text and socket.gethostname() not in text
    assert len(json.loads((toy_dir / "files.lock.json").read_text())) == 3  # written on 1st build


def test_metadata_is_one_plain_table(toy_build):
    meta = pd.read_parquet(toy_build / "metadata.parquet")  # no package needed
    assert list(meta.columns[: len(REQUIRED)]) == list(REQUIRED)
    row = meta.set_index("signal_id").loc["compound_0/axle"]
    assert row.fault_type == "outer+electrical" and row.fault_location == "axle_bearing+motor"
    assert row.sensor_location == "axle_bearing" and row.fs == 2000 and row.n_samples == 1000
    assert meta[meta.sensor_location == "gearbox"].axis.tolist()[:3] == ["x", "y", "z"]


def test_signals_keep_dtype(toy_build, toy_dir):
    ds = bd.Dataset(toy_build)
    raw = np.load(toy_dir.parent / "raw_source" / "compound_0.npz")
    for ch in raw.files:
        x = ds.signal(f"compound_0/{ch}")
        assert x.dtype == raw[ch].dtype
        np.testing.assert_array_equal(x, raw[ch])
    np.testing.assert_array_equal(ds.signal("compound_0/axle", 10, 20), raw["axle"][10:20])
    rec = ds.recording("healthy_0", channels=["gb_x", "gb_y", "gb_z"])
    assert np.stack(list(rec.values())).shape == (3, 500)


def test_with_signals(toy_build):
    ds = bd.Dataset(toy_build)
    full = ds.with_signals()
    assert len(full) == 15 and full["signal"].dtype == object
    # a selection in any order keeps its rows and index; equal lengths stay one array per row
    meta = ds.metadata()
    rows = meta[meta.channel.isin(["gb_x", "gb_y", "gb_z", "current"])].iloc[::-1]
    out = ds.with_signals(rows)
    assert out.index.equals(rows.index) and "signal" not in rows.columns
    for sid, x in zip(out.signal_id, out.signal, strict=True):
        np.testing.assert_array_equal(x, ds.signal(sid))
        assert x.dtype == ds.signal(sid).dtype
    cut = ds.with_signals(rows.head(2), start=10, stop=20)
    assert [len(x) for x in cut.signal] == [10, 10]
    with pytest.raises(bd.dataset.UnknownIdError, match="Did you mean"):
        ds.with_signals(pd.DataFrame({"signal_id": ["gear_0/gb_q"]}))


def test_signals_in_a_chosen_unit(toy_build):
    ds = bd.Dataset(toy_build)
    x = ds.signal("gear_0/gb_x")
    assert ds.signal("gear_0/gb_x", unit="g").dtype == np.float64
    np.testing.assert_allclose(ds.signal("gear_0/gb_x", unit="m/s^2"), x * 9.80665)
    np.testing.assert_allclose(ds.signal("gear_0/gb_x", 5, 9, unit="mm/s^2"), x[5:9] * 9806.65)
    assert ds.signal("gear_0/gb_x", unit="g", dtype=np.float32).dtype == np.float32
    # volts of a 100 mV/g sensor
    v = ds.signal("gear_0/axle")
    np.testing.assert_allclose(ds.signal("gear_0/axle", unit="g"), v / 0.1, rtol=1e-6)
    with pytest.raises(ValueError, match="'g' \\(acceleration\\) to 'mV'"):
        ds.signal("gear_0/axle", unit="mV")  # the sensor volts are ds.signal(..., unit=None)
    with pytest.raises(ValueError, match="does not document the unit"):
        ds.signal("gear_0/current", unit="A")
    with pytest.raises(ValueError, match=r"acceleration\) to 'mm/s' \(velocity"):
        ds.signal("gear_0/gb_x", unit="mm/s")
    with pytest.raises(ValueError, match="unknown unit 'G'"):
        ds.signal("gear_0/gb_x", unit="G")
    with pytest.raises(ValueError, match="keys are quantities"):
        ds.signal("gear_0/gb_x", unit={"vibration": "g"})
    # {quantity: unit} converts the signals of that quantity and keeps the others
    rec = ds.recording("gear_0", unit={"acceleration": "m/s^2"})
    np.testing.assert_allclose(rec["axle"], v * 98.0665, rtol=1e-6)
    assert rec["current"].dtype == np.int16
    assert dict(ds.iter_signals(["gear_0/gb_y"], unit="g"))["gear_0/gb_y"].dtype == np.float64
    # with_signals gives the units it converted to
    out = ds.with_signals(unit={"acceleration": "m/s^2"})
    assert set(out.loc[out.quantity == "acceleration", "unit"]) == {"m/s^2"}
    assert set(out.loc[out.quantity == "current", "unit"]) == {"unknown"}
    assert set(out.loc[out.channel == "axle", "sensitivity"]) == {"none"}
    with pytest.raises(ValueError, match="current"):
        ds.with_signals(unit="g")  # one unit for every signal: the current is not in g


def test_units_vocabulary_and_conversions():
    from bearing_datasets.units import UNITS, allowed_units, convert, parse_sensitivity

    assert convert(np.array([1.0]), "in/s", "mm/s")[0] == pytest.approx(25.4)
    assert convert(np.array([60.0]), "rpm", "Hz")[0] == pytest.approx(1.0)
    assert convert(np.array([1.0]), "mil", "um")[0] == pytest.approx(25.4)
    assert convert(np.array([2.0]), "V", "m/s^2", "10.2 mV/(m/s^2)")[0] == pytest.approx(
        196.08, 1e-3
    )
    assert convert(np.array([3], dtype=np.int16), "counts", "counts").tolist() == [3.0]
    divider = convert(np.array([1.5]), "V", "V", "5 mV/V")  # line voltage through a 1:200 divider
    assert divider[0] == pytest.approx(300.0)
    with pytest.raises(ValueError, match="sensor sensitivity"):
        convert(np.array([1.0]), "V", "g")
    with pytest.raises(ValueError, match="raw ADC"):
        convert(np.array([1]), "counts", "g")
    with pytest.raises(ValueError, match="cannot convert from 'raw"):
        convert(np.array([1]), "raw (int16)", "g")  # free text of older builds
    assert parse_sensitivity("none") is None
    with pytest.raises(ValueError, match="100 mV/g"):
        parse_sensitivity("100mV/g")
    assert {"g", "m/s^2", "V", "counts", "unknown"} <= allowed_units("acceleration")
    assert "A" not in allowed_units("acceleration") and allowed_units("unknown") == set(UNITS)


def test_open_polars_and_rebuild(toy_build, toy_dir, root):
    pl = pytest.importorskip("polars")
    ds = bd.open("toyrig", root)
    assert isinstance(ds.metadata("polars"), pl.DataFrame)
    lazy = pl.scan_parquet(ds.path / "signals" / "part-float64.parquet")
    assert lazy.filter(pl.col("signal_id") == "gear_0/gb_x").collect().height == 1
    mtime = (toy_build / "manifest.json").stat().st_mtime_ns
    assert build(toy_dir, root) == toy_build  # already built: skipped
    assert (toy_build / "manifest.json").stat().st_mtime_ns == mtime
    with pytest.raises(FileNotFoundError):
        bd.open("nope", root)


def test_private_dataset_by_name_after_first_build(toy_build, toy_dir, root):
    # built once from its folder: afterwards the name is enough
    assert load_spec("toyrig", root)["dir"] == toy_dir.resolve()
    mtime = (toy_build / "manifest.json").stat().st_mtime_ns
    build("toyrig", root, force=True)
    assert (toy_build / "manifest.json").stat().st_mtime_ns != mtime
    run = subprocess.run(
        [sys.executable, "-m", "bearing_datasets.cli", "--root", str(root), "info", "toyrig"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0 and "Synthetic rig" in run.stdout, run.stderr
    with pytest.raises(KeyError, match="unknown dataset"):
        load_spec("not_built_anywhere", root)


def test_saved_root(toy_build, root, monkeypatch):
    monkeypatch.delenv("BEARING_DATASETS_ROOT", raising=False)
    assert bd.get_root() == (None, "not set")
    with pytest.raises(ValueError, match="bearing-datasets root"):
        bd.open("toyrig")
    cli = [sys.executable, "-m", "bearing_datasets.cli"]
    run = subprocess.run([*cli, "root", str(root)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert bd.open("toyrig").name == "toyrig"  # no root argument needed
    run = subprocess.run([*cli, "list"], capture_output=True, text=True)
    assert "[built]  toyrig" in run.stdout
    monkeypatch.setenv("BEARING_DATASETS_ROOT", "/somewhere/else")  # the variable wins
    assert bd.get_root()[1] == "$BEARING_DATASETS_ROOT"


def test_subset_build(toy_build, toy_dir, root):
    with pytest.raises(ValueError, match="own name"):
        build(toy_dir, root, channels=["axle"])
    path = build(
        toy_dir,
        root,
        channels=["axle", "gb_x"],
        where={"fault_type": ["normal", "gear"]},
        as_name="toy_small",
    )
    meta = bd.open("toy_small", root).metadata()
    assert set(meta.channel) == {"axle", "gb_x"} and set(meta.fault_type) == {"normal", "gear"}
    assert (root / "toyrig" / "manifest.json").exists()  # the full build is untouched
    # rebuilding the subset by its name reproduces the same selection
    build("toy_small", root, force=True)
    assert set(bd.open("toy_small", root).metadata().channel) == {"axle", "gb_x"}
    assert json.loads((path / "manifest.json").read_text())["selection"]["of"] == "toyrig"


def test_download_subset(toy_build, toy_dir, root):
    with pytest.raises(ValueError, match="matches"):
        build(toy_dir, root, files=["nothing*"], as_name="toy_none")
    path = build(toy_dir, root, files=["gear*", "healthy*"], as_name="toy_files")
    meta = bd.open("toy_files", root).metadata()
    assert set(meta.native_label) == {"gear", "healthy"}
    manifest = json.loads((path / "manifest.json").read_text())
    assert {f["name"] for f in manifest["raw_files"]} == {"gear_0.npz", "healthy_0.npz"}
    build("toy_files", root, force=True)  # rebuilding by name keeps the file selection
    assert set(bd.open("toy_files", root).metadata().native_label) == {"gear", "healthy"}


def test_cli_verify(toy_build, root):
    run = subprocess.run(
        [sys.executable, "-m", "bearing_datasets.cli", "--root", str(root), "verify", "toyrig"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0 and "OK" in run.stdout, run.stderr


def test_cli_unknown_dataset_is_a_short_message(root):
    for cmd in (["info", "cwrru"], ["build", "cwrru"]):
        run = subprocess.run(
            [sys.executable, "-m", "bearing_datasets.cli", "--root", str(root), *cmd],
            capture_output=True,
            text=True,
        )
        assert run.returncode != 0 and "Traceback" not in run.stderr, run.stderr
        assert "unknown dataset 'cwrru'. Did you mean 'cwru'?" in run.stderr


def _row(**values):
    return {c: "x" for c in REQUIRED} | {
        "fault_type": "normal",
        "fault_location": "none",
        "sensor_location": "test_bearing",
        "sensor_at_fault": False,
        **values,
    }


def test_validate_reports_problems():
    with pytest.raises(ValueError, match="unknown fault_type"):
        validate(pd.DataFrame([_row(fault_type="inner+ball")]))
    with pytest.raises(ValueError, match="null values"):
        validate(pd.DataFrame([_row(speed_rpm=None)]))
    for column, value in [
        ("sensor_location", "test_bearing_housing"),
        ("fault_location", "test_bearing+bearing_de"),
        ("sensor_mounting", "magnet"),
        ("quantity", "acceleraton"),
        ("axis", "1"),
        ("speed_profile", "ramp"),
        ("fault_origin", "seeded"),
        ("unit", "m/s2"),
    ]:
        with pytest.raises(ValueError, match=f"unknown {column} value"):
            validate(pd.DataFrame([_row(**{column: value})]))
    with pytest.raises(ValueError, match="'none' exactly for fault_type 'normal'"):
        validate(pd.DataFrame([_row(fault_location="test_bearing")]))
    with pytest.raises(ValueError, match="'none' exactly for fault_type 'normal'"):
        validate(pd.DataFrame([_row(fault_type="inner")]))
    with pytest.raises(ValueError, match="one '\\+'-joined part per fault_type part"):
        validate(pd.DataFrame([_row(fault_type="inner+gear", fault_location="test_bearing")]))
    validate(pd.DataFrame([_row(fault_type="unknown+inner", fault_location="unknown")]))
    with pytest.raises(ValueError, match="sensor_at_fault must be"):
        validate(pd.DataFrame([_row(sensor_at_fault="no")]))
    faulty = _row(signal_id="y", fault_type="inner", fault_location="test_bearing")
    with pytest.raises(ValueError, match="0 exactly for fault_type 'normal'"):
        validate(pd.DataFrame([_row(fault_severity_level=1), faulty | {"fault_severity_level": 0}]))
    with pytest.raises(ValueError, match="integer >= 0"):
        validate(pd.DataFrame([_row(fault_severity_level=0.5)]))
    validate(pd.DataFrame([_row(fault_severity_level=0), faulty | {"fault_severity_level": 2}]))
    with pytest.raises(ValueError, match=r"do not fit the quantity.*'acceleration', 'A'"):
        validate(pd.DataFrame([_row(quantity="acceleration", unit="A")]))
    with pytest.raises(ValueError, match="'<value> <stored unit>/<physical unit>'"):
        validate(pd.DataFrame([_row(quantity="acceleration", unit="V", sensitivity="0.1")]))
    validate(pd.DataFrame([_row(quantity="acceleration", unit="V", sensitivity="10 mV/(m/s^2)")]))


def test_sensor_at_fault(toy_build):
    meta = bd.Dataset(toy_build).metadata().set_index("signal_id")
    assert meta.sensor_at_fault.dtype == bool
    at = set(meta.index[meta.sensor_at_fault])
    # nested locations match (gearbox); the motor supply is not a part of the faulty motor
    assert at == {"gear_0/gb_x", "gear_0/gb_y", "gear_0/gb_z", "compound_0/axle"}
    from bearing_datasets.schema import at_fault

    pairs = [  # sensor, fault, at fault
        ("test_bearing_de", "test_bearing_de", True),
        ("test_bearing_nde", "test_bearing_de", False),
        ("gearbox_bearing_input", "gearbox", True),
        ("motor_bearing", "motor_bearing_de", True),
        ("base", "test_bearing", False),
        ("motor_supply", "motor", False),
        ("motor", "motor_supply", False),
        ("motor_supply", "motor_rotor+motor_supply", True),
        ("unknown", "unknown", False),
        ("motor", "unknown", False),
        ("unknown", "motor", False),
    ]
    sensors, faults, expected = (pd.Series(x) for x in zip(*pairs, strict=True))
    assert at_fault(sensors, faults).tolist() == expected.tolist()


def test_old_builds_read_with_new_names(toy_build, toy_dir, root):
    """A build made before 0.2.0 (schema version 1) opens with today's names and values."""
    build(toy_dir, root, as_name="toy_new", where={"fault_type": ["gear"]})
    manifest_file, meta_file = toy_build / "manifest.json", toy_build / "metadata.parquet"
    manifest = json.loads(manifest_file.read_text())
    del manifest["schema_version"]
    manifest["columns"] = {
        {"fault_type": "condition", "speed_rpm": "rpm"}.get(k, k): v
        for k, v in manifest["columns"].items()
        if k != "sensor_at_fault"
    }
    manifest_file.write_text(json.dumps(manifest))
    meta = pd.read_parquet(meta_file).drop(columns="sensor_at_fault")
    meta = meta.rename(columns={"fault_type": "condition", "speed_rpm": "rpm"})
    meta.loc[meta.native_label == "compound", "condition"] = "ball+electrical"
    meta.to_parquet(meta_file)
    with pytest.warns(UserWarning, match="renamed on read"):
        ds = bd.Dataset(toy_build)
    for m in [ds.metadata(), ds.metadata("polars").to_pandas()]:
        assert "condition" not in m.columns and "rpm" not in m.columns
        assert set(m.fault_type) == {"normal", "gear", "rolling_element+electrical"}
        assert (m.speed_rpm == 1200.0).all()
    assert {"fault_type", "speed_rpm"} <= set(ds.columns().column)
    # old and new builds together: the shared columns keep today's names
    with pytest.warns(UserWarning, match="renamed on read"):
        both = bd.load_metadata(["toyrig", "toy_new"], root)
    assert {"fault_type", "speed_rpm"} <= set(both.columns)
    assert "sensor_at_fault" not in both.columns  # only in builds made with 0.2


def test_old_build_with_a_column_named_like_a_new_one():
    """cumtb_pitch 0.1 had its own fault_type column next to condition: it becomes
    fault_detail, and condition becomes fault_type."""
    from bearing_datasets.schema import renamed_columns, upgrade

    old = pd.DataFrame({"condition": ["normal", "ball"], "fault_type": ["none", "crack"]})
    new = upgrade(old)
    assert new.fault_type.tolist() == ["normal", "rolling_element"]
    assert new.fault_detail.tolist() == ["none", "crack"]
    assert renamed_columns(["fault_type", "rpm"]) == {"rpm": "speed_rpm"}  # no clash


def test_where_accepts_old_column_names(toy_dir, root):
    with pytest.warns(DeprecationWarning, match="now 'fault_type'"):
        build(toy_dir, root, where={"condition": ["normal", "gear"]}, as_name="old_where")
    assert set(bd.open("old_where", root).metadata().fault_type) == {"normal", "gear"}
    with pytest.raises(ValueError, match="both 'condition' and 'fault_type'"):
        build(toy_dir, root, where={"condition": ["gear"], "fault_type": ["normal"]}, as_name="x")


def test_where_rejects_per_channel_columns(toy_dir, root):
    with pytest.raises(ValueError, match="not set per recording"):
        build(toy_dir, root, where={"sensor_location": ["gearbox"]}, as_name="by_sensor")
    assert not (root / "by_sensor").exists()


@pytest.mark.parametrize("name", [*list_datasets(), PRIVATE_EXAMPLE])
def test_channel_values_use_the_vocabularies(name):
    """The per-channel defaults of every builder use the standard vocabularies."""
    import importlib.util

    from bearing_datasets.schema import VOCABULARIES
    from bearing_datasets.units import allowed_units, parse_sensitivity

    path = load_spec(name)["dir"] / "builder.py"
    spec = importlib.util.spec_from_file_location(f"_builder_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for channel, values in module.CHANNELS.items():
        for column, value in values.items():
            allowed = VOCABULARIES.get(column)
            assert allowed is None or value in allowed, (channel, column, value)
        if "unit" in values:
            assert values["unit"] in allowed_units(values.get("quantity", "unknown")), channel
        parse_sensitivity(values.get("sensitivity", "none"))


def test_every_column_is_described(toy_build):
    cols = bd.Dataset(toy_build).columns()
    assert set(cols.column) == set(pd.read_parquet(toy_build / "metadata.parquet").columns)
    assert cols.description.str.len().gt(0).all()
    row = _row(mystery=1)
    with pytest.raises(ValueError, match="without a description"):
        validate(pd.DataFrame([row]))
    validate(pd.DataFrame([row]), notes={"mystery": "a documented extra column"})


def test_no_nulls_in_metadata(toy_build):
    assert not pd.read_parquet(toy_build / "metadata.parquet").isna().any().any()


@pytest.mark.parametrize("name", [*list_datasets(), PRIVATE_EXAMPLE])
def test_dataset_definitions(name):
    spec = load_spec(name)
    assert spec["license"] and spec["citation"].strip()
    lock = json.loads((spec["dir"] / "files.lock.json").read_text())
    assert lock and all(f["sha256"] and f["size"] for f in lock)
    builder = (spec["dir"] / "builder.py").read_text()
    assert "CHANNELS" in builder and "def recordings(" in builder


def test_readme_lists_every_dataset():
    """The README count, group counts and table rows stay in sync with the package."""
    import re

    text = (Path(__file__).parent.parent / "README.md").read_text()
    section = text[text.index("## Datasets") : text.index("*download* is what is fetched")]
    rows = re.findall(r"^\| `([^`]+)` \|", section, flags=re.M)
    assert sorted(rows) == sorted(list_datasets())
    assert int(re.search(r"\*\*(\d+) datasets\*\*", section).group(1)) == len(rows)
    head = text[: text.index("## Datasets")]  # title, badges, headline
    assert text.startswith("# bearing-datasets\n") and f"\n**{len(rows)} public" in head
    assert f"badge/datasets-{len(rows)}-" in head
    for count, body in re.findall(r"^### .* \((\d+)\)\n(.*?)(?=^### |\Z)", section, re.M | re.S):
        assert int(count) == len(re.findall(r"^\| `", body, flags=re.M))


def test_diversity_lists_every_dataset_once():
    import re

    text = (Path(__file__).parent.parent / "docs" / "diversity.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \|", text, flags=re.M)
    assert sorted(rows) == sorted(list_datasets())
    for count, body in re.findall(r"^## .* \((\d+)\)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        assert int(count) == len(re.findall(r"^\| `", body, flags=re.M))


def readme_columns() -> tuple[set[str], dict[str, set[str]]]:
    """The README column tables: the columns of every dataset, and {column: datasets that have
    it} for the others ("all", "all except a, b", "a, b", each optionally "(and my_cwru)")."""
    import re

    text = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    every = text[text.index("in **every** dataset") : text.index("Columns that only some")]
    some = text[text.index("Columns that only some") : text.index("`ds.columns()` (or")]
    required = {
        c for row in re.findall(r"^\| (.*?) \|", every, re.M) for c in re.findall(r"`(\w+)`", row)
    }
    package = set(list_datasets())
    table = {}
    for cols, cell in re.findall(r"^\| ((?:`\w+`(?:, )?)+) \| .* \| (.*) \|$", some, re.M):
        extra = (
            set(re.findall(r"\(and ([a-z0-9_, ]+)\)", cell)[0].split(", "))
            if "(and" in cell
            else set()
        )
        cell = re.sub(r"\(and [^)]*\)", "", cell).strip()
        if cell.startswith("all"):
            names = package - set(re.findall(r"[a-z0-9_]+", cell.removeprefix("all")))
            names.discard("except")
        else:
            names = set(re.findall(r"[a-z0-9_]+", cell))
        for c in re.findall(r"`(\w+)`", cols):
            table[c] = names | extra
    return required, table


def test_readme_lists_the_columns():
    """The README tables list every column: the required ones, then every other column with the
    datasets that have it (exactly for dataset-specific columns; standard columns are checked
    exactly against built datasets by test_integration, here from the dataset.yaml notes)."""
    from bearing_datasets.schema import OPTIONAL

    required, table = readme_columns()
    assert required == set(REQUIRED)
    assert set(OPTIONAL) <= set(table)
    noted, own = {}, {}
    for name in [*list_datasets(), PRIVATE_EXAMPLE]:
        spec = load_spec(name)
        for c in set(spec.get("columns") or {}) - set(REQUIRED):
            (noted if c in OPTIONAL else own).setdefault(c, set()).add(spec["name"])
    for c, names in own.items():
        assert table.get(c) == names, c
    for c, names in noted.items():  # a note on a standard column: the dataset has it
        assert names <= table[c], (c, names - table[c])
    assert set(table) == set(OPTIONAL) | set(own)


def test_no_platform_default_encoding(toy_dir, root, tmp_path):
    """Text files are read and written as UTF-8 (Windows would otherwise use cp1252)."""
    script = f"""
import bearing_datasets as bd
from bearing_datasets.build import build, list_datasets, load_spec
from bearing_datasets.cli import main
for name in list_datasets():
    load_spec(name)
build({str(toy_dir)!r}, {str(root)!r})
bd.open("toyrig", {str(root)!r}).metadata()
main(["--root", {str(root)!r}, "list"])
"""
    run = subprocess.run(
        [sys.executable, "-X", "warn_default_encoding", "-W", "error::EncodingWarning",
         "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path)},
    )  # fmt: skip
    assert run.returncode == 0, run.stderr[-2000:]


def test_build_without_symlinks(toy_dir, root, tmp_path, monkeypatch):
    """Windows without admin rights refuses symlinks: files are hard-linked, folders joined."""
    from bearing_datasets.build import _link

    def refuse(*args, **kwargs):
        raise OSError(1314, "A required privilege is not held by the client")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    blob, folder = tmp_path / "blob", tmp_path / "extracted"
    blob.write_bytes(b"raw")
    (folder / "sub").mkdir(parents=True)
    (folder / "sub" / "a.txt").write_bytes(b"a")
    _link(blob, tmp_path / "file_link")
    _link(folder, tmp_path / "dir_link")
    assert (tmp_path / "file_link").stat().st_ino == blob.stat().st_ino  # no copy
    assert (tmp_path / "dir_link" / "sub" / "a.txt").read_bytes() == b"a"
    meta = bd.open(build(toy_dir, root).name, root).metadata()
    assert meta.recording_id.nunique() == 3
    assert blob.read_bytes() == b"raw"  # cleaning the build left the cache alone


def test_unknown_ids_explain_themselves(toy_build):
    ds = bd.Dataset(toy_build)
    with pytest.raises(KeyError, match=r"'gear_0' is a recording.*'gear_0/gb_x'.*ds.recording"):
        ds.signal("gear_0")  # a recording id where a signal id is expected
    with pytest.raises(KeyError, match=r"Did you mean 'gear_0/gb_x'"):
        ds.signal("gear_0/gbx")
    with pytest.raises(KeyError, match=r"no recording 'gear_1'.*Did you mean 'gear_0'"):
        ds.recording("gear_1")
    with pytest.raises(KeyError, match=r"no channel 'gb_w'; its channels are .*'gb_x'"):
        ds.recording("gear_0", channels=["gb_x", "gb_w"])


def test_clean_raw_keeps_private_originals(toy_build, toy_dir, root):
    """Cleaning deletes only the cache copies: a private dataset's own files stay untouched."""
    from bearing_datasets.build import clean_raw

    originals = {p: p.read_bytes() for p in (toy_dir.parent / "raw_source").iterdir()}
    cache = root / "_raw" / "sha256"
    blobs = {p.name for p in cache.iterdir() if len(p.name) == 64}
    assert len(blobs) == 3
    preview = clean_raw(["toyrig"], root, dry_run=True)
    assert preview["toyrig"]["files"] == 3 and preview["toyrig"]["bytes"] > 0
    assert {p.name for p in cache.iterdir() if len(p.name) == 64} == blobs  # dry run: nothing
    clean_raw(["toyrig"], root)
    assert not any(len(p.name) == 64 for p in cache.iterdir())
    assert {p: p.read_bytes() for p in originals} == originals  # originals intact
    ds = bd.open("toyrig", root)  # the built dataset keeps working
    assert ds.signal("gear_0/gb_x").size == 500
    build("toyrig", root, force=True)  # a rebuild copies the files again
    assert {p.name for p in cache.iterdir() if len(p.name) == 64} == blobs


def test_clean_raw_keeps_files_of_other_built_datasets(toy_build, toy_dir, root):
    from bearing_datasets.build import clean_raw

    build(toy_dir, root, files=["gear*"], as_name="toy_gear")  # shares gear_0.npz with toyrig
    report = clean_raw(["toyrig"], root)
    assert report["toyrig"] == {**report["toyrig"], "files": 2, "kept": 1}
    left = [p for p in (root / "_raw" / "sha256").iterdir() if len(p.name) == 64]
    assert len(left) == 1  # gear_0.npz, still needed by toy_gear
    assert clean_raw(None, root)["toy_gear"]["files"] == 1  # --all-built cleans the rest
    with pytest.raises(FileNotFoundError, match="not built"):
        clean_raw(["nope"], root)


def test_clean_raw_cli(toy_build, root):
    cli = [sys.executable, "-m", "bearing_datasets.cli", "--root", str(root)]
    run = subprocess.run([*cli, "clean-raw", "toyrig", "--dry-run"], capture_output=True, text=True)
    assert run.returncode == 0 and "toyrig: would free" in run.stdout, run.stderr
    run = subprocess.run([*cli, "clean-raw"], capture_output=True, text=True)
    assert run.returncode != 0 and "--all-built" in run.stderr
    run = subprocess.run([*cli, "clean-raw", "--all-built"], capture_output=True, text=True)
    assert run.returncode == 0 and "toyrig: freed" in run.stdout, run.stderr


def test_build_clean_raw_flag_and_links(toy_build, toy_dir, root, tmp_path):
    from bearing_datasets.build import _remove

    cli = [sys.executable, "-m", "bearing_datasets.cli", "--root", str(root)]
    run = subprocess.run(
        [*cli, "build", str(toy_dir), "--force", "--clean-raw"], capture_output=True, text=True
    )
    assert run.returncode == 0 and "toyrig: freed" in run.stdout, run.stderr
    assert not any(len(p.name) == 64 for p in (root / "_raw" / "sha256").iterdir())
    outside = tmp_path / "outside"
    (outside / "sub").mkdir(parents=True)
    (outside / "sub" / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    _remove(link)  # a link in the cache: only the link goes
    assert not link.exists() and (outside / "sub" / "keep.txt").exists()


def test_values_per_channel(toy_build):
    """A column given as {channel: value} differs per channel (e.g. the bearing of a sensor)."""
    meta = pd.read_parquet(toy_build / "metadata.parquet")
    assert set(meta.loc[meta.channel == "axle", "bpfo"]) == {4.0}
    assert set(meta.loc[meta.channel != "axle", "bpfo"]) == {3.0}


def test_fault_orders_match_the_cwru_table():
    """From CWRU's published geometry, the formulas give CWRU's published orders (bsf plain)."""
    from bearing_datasets.bearings import fault_orders

    de = fault_orders(9, 0.3126, 1.537)  # 6205-2RS
    assert de == pytest.approx({"bpfi": 5.4152, "bpfo": 3.5848, "ftf": 0.39828,
                                "bsf": 4.7135 / 2}, abs=1e-4)  # fmt: skip
    fe = fault_orders(8, 0.2656, 1.122)  # 6203-2RS
    assert fe == pytest.approx({"bpfi": 4.9469, "bpfo": 3.0530, "ftf": 0.3817,
                                "bsf": 3.9874 / 2}, abs=1e-3)  # fmt: skip
    # a contact angle shortens the effective ball ratio: the outer race sees more passes
    assert fault_orders(10, 1, 5, contact_deg=40)["bpfo"] > fault_orders(10, 1, 5)["bpfo"]
