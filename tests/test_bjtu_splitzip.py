"""The BJTU builder reads a split zip in place; check it on a small one made with `zip -s`."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

BUILDER = Path(__file__).parents[1] / "src/bearing_datasets/datasets/bjtu_bogie/builder.py"


def _builder():
    spec = importlib.util.spec_from_file_location("bjtu_builder", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not shutil.which("zip"), reason="needs the zip command")
@pytest.mark.parametrize("zip64", [False, True])
def test_split_zip_reader(tmp_path, zip64):
    rng = np.random.default_rng(0)
    src = tmp_path / "data"
    files = {}
    for i in range(6):
        f = src / f"folder{i % 2}" / f"file{i}.csv"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("CH1,CH2\n" + "\n".join(f"{a},{b}" for a, b in rng.normal(size=(3000, 2))))
        files[f"data/{f.relative_to(src).as_posix()}"] = f.read_bytes()
    flags = ["-fz"] if zip64 else []
    subprocess.run(
        ["zip", "-q", "-r", *flags, "-s", "64k", "all.zip", "data"], cwd=tmp_path, check=True
    )
    parts = sorted(tmp_path.glob("all.z[0-9]*")) + [tmp_path / "all.zip"]
    assert len(parts) > 2  # really split
    archive = _builder().SplitZip(parts)
    for name, content in files.items():
        assert archive.read(name) == content
    archive.close()


def test_labels():
    label = _builder()._label
    assert label("M0_G0_LA0_RA0") == ("normal", "none", "none")
    fault_type, location, _ = label("M1_G1+G5_LA1_RA0")
    assert fault_type == "electrical+gear+inner+inner"
    assert location == "motor_stator+gearbox+gearbox_bearing+axle_bearing_left"
