"""Small helpers for reading raw files in builders."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat


def read_mat(path: str | Path, **kwargs) -> dict:
    """Variables of a MATLAB (v5) file, without the ``__header__``-like entries."""
    return {k: v for k, v in loadmat(path, **kwargs).items() if not k.startswith("__")}


def read_csv_columns(path: str | Path, **kwargs) -> dict[str, np.ndarray]:
    """Columns of a numeric CSV as ``{name: array}`` (numbers parsed exactly)."""
    df = pd.read_csv(path, encoding="utf-8-sig", float_precision="round_trip", **kwargs)
    return {str(c).strip(): df[c].to_numpy() for c in df.columns}
