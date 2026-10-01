"""Reading a built dataset."""

from __future__ import annotations

import difflib
import json
import os
import warnings
from collections.abc import Iterable, Iterator, Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .schema import RENAMED, SCHEMA_VERSION, upgrade

ENV_ROOT = "BEARING_DATASETS_ROOT"


def config_file() -> Path:
    """Per-user settings file (Windows: %APPDATA%, Linux/macOS: ~/.config)."""
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(base).expanduser() / "bearing_datasets" / "config.json"


def set_root(root: str | Path) -> Path:
    """Remember the datasets folder for this user (used when no root is given)."""
    path = Path(root).expanduser().resolve()
    file = config_file()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({"root": str(path)}, indent=1), encoding="utf-8")
    return path


def get_root() -> tuple[Path | None, str]:
    """The datasets folder used when no root is given, and where the setting comes from."""
    if os.environ.get(ENV_ROOT):
        return Path(os.environ[ENV_ROOT]).expanduser().resolve(), f"${ENV_ROOT}"
    if config_file().exists():
        root = json.loads(config_file().read_text(encoding="utf-8")).get("root")
        if root:
            return Path(root), str(config_file())
    return None, "not set"


def resolve_root(root: str | Path | None = None) -> Path:
    """``root`` if given, else $BEARING_DATASETS_ROOT, else the folder saved with set_root."""
    if root:
        return Path(root).expanduser().resolve()
    path, _ = get_root()
    if path is None:
        raise ValueError(
            "no datasets folder: run `bearing-datasets root <folder>` once "
            "(or bd.set_root(folder)), or pass root=..."
        )
    return path


class UnknownIdError(KeyError):
    """A signal, recording or channel that is not in the dataset (a KeyError, readable)."""

    def __str__(self) -> str:
        return self.args[0]


def _close(word: str, options: Iterable[str]) -> str:
    matches = difflib.get_close_matches(word, list(options), n=3, cutoff=0.6)
    return f" Did you mean {', '.join(repr(m) for m in matches)}?" if matches else ""


class Dataset:
    """A built dataset: ``metadata()`` for the table, ``signal()`` for the samples."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.manifest = json.loads((self.path / "manifest.json").read_text(encoding="utf-8"))
        self.name = self.manifest["dataset"]
        # built before 0.2.0: read with today's column names (see schema.upgrade)
        self.outdated = self.manifest.get("schema_version", 1) < SCHEMA_VERSION
        if self.outdated:
            warnings.warn(
                f"{self.name} was built with bearing-datasets "
                f"{self.manifest.get('package_version', '<0.2')}: its columns are renamed on "
                "read (condition -> fault_type, ...); rebuild it (`bearing-datasets build "
                f"{self.name} --force`) for the standard locations, sensor_at_fault, "
                "sensor_mounting and severity levels",
                stacklevel=2,
            )
        self._meta: pd.DataFrame | None = None
        self._loc: pd.DataFrame | None = None

    def __repr__(self) -> str:
        m = self.manifest
        return f"<Dataset {self.name}: {m['n_recordings']} recordings, {m['n_signals']} signals>"

    def metadata(self, backend: str = "pandas"):
        """One row per signal (see ``bearing_datasets.schema``). backend: pandas or polars."""
        if backend == "polars":
            import polars as pl

            if self.outdated:
                return pl.from_pandas(self.metadata())
            return pl.read_parquet(self.path / "metadata.parquet")
        if self._meta is None:
            self._meta = pd.read_parquet(self.path / "metadata.parquet")
            if self.outdated:
                self._meta = upgrade(self._meta)
        return self._meta.copy()

    def columns(self) -> pd.DataFrame:
        """Description of every metadata column of this dataset."""
        cols = self.manifest.get("columns", {})
        if self.outdated:
            new = {k: v for k, v in RENAMED.items() if v not in cols}
            cols = {new.get(k, k): v for k, v in cols.items()}
        return pd.DataFrame({"column": list(cols), "description": list(cols.values())})

    def cite(self) -> str:
        return self.manifest["citation"]

    def signal_files(self) -> list[Path]:
        """Signal Parquet files (one per dtype), e.g. for ``pl.scan_parquet``."""
        return sorted((self.path / "signals").glob("part-*.parquet"))

    # ---------------------------------------------------------------- signals
    def _locations(self) -> pd.DataFrame:
        if self._loc is None:
            cols = ["signal_id", "signal_file", "signal_row_group", "signal_row"]
            self._loc = pd.read_parquet(self.path / "metadata.parquet", columns=cols)
            self._loc = self._loc.set_index("signal_id")
        return self._loc

    def signal(self, signal_id: str, start: int = 0, stop: int | None = None) -> np.ndarray:
        """Samples of one signal, in the original dtype."""
        locations = self._locations()
        if signal_id not in locations.index:
            raise self._unknown_signal(signal_id)
        file, group, row = locations.loc[signal_id]
        offsets, values = _row_group(str(self.path / "signals" / file), int(group), os.getpid())
        return values[offsets[row] : offsets[row + 1]][start:stop]

    def _unknown_signal(self, signal_id: str) -> UnknownIdError:
        meta = self.metadata()
        rows = meta[meta["recording_id"] == signal_id]
        if len(rows):
            ids = ", ".join(repr(w) for w in rows["signal_id"][:6])
            return UnknownIdError(
                f"{signal_id!r} is a recording of {self.name}, not a signal. A signal id is "
                f"'<recording_id>/<channel>': {ids}{', ...' if len(rows) > 6 else ''}. Use "
                f"ds.signal({rows['signal_id'].iloc[0]!r}) for one channel, or "
                f"ds.recording({signal_id!r}) for all of them."
            )
        return UnknownIdError(
            f"no signal {signal_id!r} in {self.name}."
            f"{_close(signal_id, meta['signal_id'])} "
            "The ids are in ds.metadata()['signal_id'] ('<recording_id>/<channel>')."
        )

    def iter_signals(self, signal_ids: Iterable[str]) -> Iterator[tuple[str, np.ndarray]]:
        """Yield ``(signal_id, samples)`` one at a time (the dataset never has to fit in RAM)."""
        for sid in signal_ids:
            yield sid, self.signal(sid)

    def with_signals(
        self, meta: pd.DataFrame | None = None, start: int = 0, stop: int | None = None
    ) -> pd.DataFrame:
        """``meta`` (default: all the metadata) with a ``signal`` column of numpy arrays.

        Loads the signals in memory: on large datasets, select rows first, e.g.
        ``ds.with_signals(meta[meta.fault_type == "inner"])``. ``start``/``stop`` cut every signal.
        """
        meta = self.metadata() if meta is None else meta.copy()
        if "signal_id" not in meta.columns:
            raise ValueError("meta needs a signal_id column (rows of ds.metadata())")
        ids = meta["signal_id"].tolist()
        locations = self._locations()
        if unknown := [w for w in ids if w not in locations.index]:
            raise self._unknown_signal(unknown[0])
        loc = locations.loc[ids]
        # read in storage order, so each row group is decoded once
        order = np.lexsort((loc["signal_row"], loc["signal_row_group"], loc["signal_file"]))
        signals = np.empty(len(ids), dtype=object)
        for i in order:
            signals[i] = self.signal(ids[i], start, stop)
        meta["signal"] = pd.Series(signals, index=meta.index)
        return meta

    def recording(
        self, recording_id: str, channels: Sequence[str] | None = None
    ) -> dict[str, np.ndarray]:
        """All (or some) channels of one recording, e.g. the 3 axes of a triaxial sensor."""
        meta = self.metadata()
        rows = meta[meta["recording_id"] == recording_id]
        if rows.empty:
            raise UnknownIdError(
                f"no recording {recording_id!r} in {self.name}."
                f"{_close(recording_id, meta['recording_id'].unique())} "
                "The ids are in ds.metadata()['recording_id']."
            )
        if channels is not None:
            missing = [c for c in channels if c not in set(rows["channel"])]
            if missing:
                raise UnknownIdError(
                    f"recording {recording_id!r} has no channel {', '.join(map(repr, missing))};"
                    f" its channels are {', '.join(map(repr, rows['channel']))}."
                )
            rows = rows[rows["channel"].isin(channels)]
        return {c: self.signal(w) for c, w in zip(rows["channel"], rows["signal_id"], strict=True)}


@lru_cache(maxsize=4)
def _row_group(file: str, group: int, pid: int) -> tuple[np.ndarray, np.ndarray]:
    # pid in the key: each DataLoader worker process reads with its own handles
    col = pq.ParquetFile(file).read_row_group(group, columns=["signal"]).column(0).combine_chunks()
    return col.offsets.to_numpy(), col.values.to_numpy(zero_copy_only=False)


def open(name: str, root: str | Path | None = None) -> Dataset:  # noqa: A001
    """Open a built dataset (never downloads; build it with ``bearing-datasets build``)."""
    path = resolve_root(root) / name
    if not (path / "manifest.json").exists():
        raise FileNotFoundError(
            f"{name} is not built in {path.parent}: "
            f"run `bearing-datasets build {name} --root {path.parent}`"
        )
    return Dataset(path)


def load_metadata(names: Sequence[str], root: str | Path | None = None) -> pd.DataFrame:
    """Metadata of several datasets in one table, with the columns they all have (no NaNs)."""
    frames = [open(n, root).metadata() for n in names]
    common = [c for c in frames[0].columns if all(c in f.columns for f in frames)]
    return pd.concat([f[common] for f in frames], ignore_index=True)
