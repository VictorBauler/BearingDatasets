import textwrap
from pathlib import Path

import numpy as np
import pytest

SPEC = """
name: toyrig
title: Synthetic rig
license: CC0-1.0
citation: Toy rig, test fixture.
sources:
  - {{type: local, name: primary, path: "{raw}"}}
"""

BUILDER = """
import numpy as np

GB = {"sensor_location": "gearbox", "quantity": "acceleration", "unit": "g",
      "sensitivity": "none", "fs": 1000}
CHANNELS = {
    "gb_x": {**GB, "axis": "x"},
    "gb_y": {**GB, "axis": "y"},
    "gb_z": {**GB, "axis": "z"},
    "axle": {"sensor_location": "axle_bearing", "quantity": "acceleration", "axis": "none",
             "unit": "V", "sensitivity": "100 mV/g", "fs": 2000},
    "current": {"sensor_location": "motor_supply", "quantity": "current", "axis": "none",
                "unit": "unknown", "sensitivity": "none", "fs": 1000},
}
LABELS = {"healthy": ("normal", "none"), "gear": ("gear", "gearbox"),
          "compound": ("outer+electrical", "axle_bearing+motor")}


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.npz")):
        label = path.stem.rsplit("_", 1)[0]
        data = np.load(path)
        fault_type, location = LABELS[label]
        yield {"recording_id": path.stem, "native_label": label, "fault_type": fault_type,
               "fault_location": location, "speed_rpm": 1200.0, "run_id": "run1",
               "bpfo": {ch: 4.0 if ch == "axle" else 3.0 for ch in data.files},  # per channel
               "signals": {ch: data[ch] for ch in data.files}}
"""


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory, monkeypatch):
    """Never read or write the real user settings file during tests."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path_factory.mktemp("config")))


@pytest.fixture
def toy_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw_source"
    raw.mkdir()
    rng = np.random.default_rng(0)
    for name in ["healthy_0", "gear_0", "compound_0"]:
        np.savez(
            raw / f"{name}.npz",
            gb_x=rng.normal(size=500),
            gb_y=rng.normal(size=500),
            gb_z=rng.normal(size=500),
            axle=rng.normal(size=1000).astype(np.float32),
            current=(rng.normal(size=500) * 1000).astype(np.int16),
        )
    spec = tmp_path / "toyrig"
    spec.mkdir()
    (spec / "dataset.yaml").write_text(textwrap.dedent(SPEC.format(raw=raw)))
    (spec / "builder.py").write_text(BUILDER)
    return spec


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "root"


@pytest.fixture
def toy_build(toy_dir: Path, root: Path) -> Path:
    from bearing_datasets.build import build

    return build(toy_dir, root)
