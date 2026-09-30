"""Build a dataset: download raw files, run its builder, write metadata + signals."""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import importlib.util
import json
import logging
import os
import re
import shutil
import socket
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from tqdm import tqdm

from ._version import __version__
from .dataset import UnknownIdError, _close, resolve_root
from .schema import describe, order_columns, validate
from .sources import Cache, Sources, archive_role, archive_stem, fetch_all, make_lock

log = logging.getLogger(__name__)
DATASETS_DIR = Path(__file__).parent / "datasets"
SPEC_KEYS = ("name", "license", "citation", "sources")


# --------------------------------------------------------------------------- specs


def list_datasets() -> list[str]:
    return sorted(p.parent.name for p in DATASETS_DIR.glob("*/dataset.yaml"))


def load_spec(name_or_path: str | Path, root: str | Path | None = None) -> dict:
    """Read ``dataset.yaml`` of a dataset given by name or by folder/file path.

    Names are the package's datasets, or private datasets already built in ``root``
    (their build remembers the folder they were built from).
    """
    path = Path(name_or_path)
    if str(name_or_path) in list_datasets():
        path = DATASETS_DIR / str(name_or_path)
    elif not path.exists():
        path = _built_from(str(name_or_path), root) or path
    if path.is_dir():
        path = path / "dataset.yaml"
    if not path.exists():
        raise UnknownIdError(
            f"unknown dataset {str(name_or_path)!r}.{_close(str(name_or_path), list_datasets())} "
            "`bearing-datasets list` shows the datasets; a private dataset is given by the path "
            "of its folder the first time."
        )
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if missing := [k for k in SPEC_KEYS if k not in spec]:
        raise ValueError(f"{path}: missing keys {missing}")
    spec["dir"] = path.parent
    return spec


def _built_from(name: str, root: str | Path | None) -> Path | None:
    """Folder a private dataset was built from, as recorded in its manifest."""
    try:
        manifest = resolve_root(root) / name / "manifest.json"
    except ValueError:
        return None
    if manifest.exists():
        spec_dir = json.loads(manifest.read_text(encoding="utf-8")).get("spec_dir")
        return Path(spec_dir) if spec_dir else None
    return None


def _builder(spec: dict):
    module_spec = importlib.util.spec_from_file_location(
        f"bearing_datasets_builder_{spec['name']}", spec["dir"] / "builder.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- signals


class SignalWriter:
    """Long-format Parquet: one row per signal, ~8 MB row groups, one file per dtype."""

    def __init__(self, folder: Path, row_group_bytes: int = 8 << 20) -> None:
        self.folder = folder
        folder.mkdir(parents=True)
        self.row_group_bytes = row_group_bytes
        self.buffers: dict[str, list[tuple[str, np.ndarray]]] = {}
        self.writers: dict[str, pq.ParquetWriter] = {}
        self.row_groups: dict[str, int] = {}
        self.locations: dict[str, tuple[str, int, int]] = {}
        self.digests: dict[str, str] = {}

    def add(self, signal_id: str, x: np.ndarray) -> None:
        x = np.ascontiguousarray(x)
        if x.dtype.byteorder == ">":
            x = x.astype(x.dtype.newbyteorder("<"))
        self.digests[signal_id] = hashlib.sha256(x.dtype.name.encode() + x.tobytes()).hexdigest()
        buf = self.buffers.setdefault(x.dtype.name, [])
        buf.append((signal_id, x))
        if sum(a.nbytes for _, a in buf) >= self.row_group_bytes:
            self._flush(x.dtype.name)

    def _flush(self, dtype: str) -> None:
        buf = self.buffers.pop(dtype, [])
        if not buf:
            return
        offsets = np.concatenate([[0], np.cumsum([len(a) for _, a in buf])]).astype(np.int32)
        values = pa.array(np.concatenate([a for _, a in buf]))
        table = pa.table(
            {
                "signal_id": [w for w, _ in buf],
                "signal": pa.ListArray.from_arrays(pa.array(offsets), values),
            }
        )
        file = f"part-{dtype}.parquet"
        if dtype not in self.writers:
            self.writers[dtype] = pq.ParquetWriter(
                self.folder / file, table.schema, compression="zstd", compression_level=7
            )
            self.row_groups[dtype] = 0
        self.writers[dtype].write_table(table, row_group_size=len(buf))
        for row, (sid, _) in enumerate(buf):
            self.locations[sid] = (file, self.row_groups[dtype], row)
        self.row_groups[dtype] += 1

    def close(self) -> str:
        """Flush everything; returns a content hash of all signals (order independent)."""
        for dtype in list(self.buffers):
            self._flush(dtype)
        for w in self.writers.values():
            w.close()
        h = hashlib.sha256()
        for sid in sorted(self.digests):
            h.update(f"{sid}:{self.digests[sid]}\n".encode())
        return h.hexdigest()


# --------------------------------------------------------------------------- build


def _link(target: Path, link: Path) -> None:
    """Expose ``target`` at ``link`` without copying.

    Symlinks need admin rights or Developer Mode on Windows; there, fall back to a hard link
    (files) or a directory junction (folders), and copy only if both fail (other drive).
    """
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
        return
    except OSError:
        pass
    if target.is_dir():
        try:
            import _winapi  # Windows only; junctions need no privilege

            _winapi.CreateJunction(str(target), str(link))
        except (ImportError, OSError):
            shutil.copytree(target, link)
    else:
        try:
            os.link(target, link)
        except OSError:
            shutil.copyfile(target, link)


def _stage_raw(spec: dict, cache: Cache, lock: list[dict], raw: Path) -> dict[str, str]:
    """Fetch every locked file and expose it under its name in ``raw`` (archives extracted)."""
    sources = Sources(spec["sources"], cache.root)
    total = sum(e["size"] for e in lock)
    with tqdm(total=total, unit="B", unit_scale=True, desc=f"{spec['name']}: download") as bar:
        files = [(e["name"], e["size"], e["sha256"]) for e in lock]
        fetched = fetch_all(cache, files, sources, bar.update)  # a few files at once
        used = {name: label for name, (_, label) in fetched.items()}
        for entry in lock:
            link = raw / entry["name"]
            link.parent.mkdir(parents=True, exist_ok=True)
            _link(fetched[entry["name"]][0], link)
        if spec.get("extract", True):  # after staging: multi-volume archives are complete
            for entry in lock:
                if archive_role(entry["name"]) == "first":
                    bar.set_postfix_str(f"extracting {entry['name']}")
                    link = raw / entry["name"]
                    folder = cache.extract(link, entry["sha256"])
                    _link(folder, link.with_name(archive_stem(link.name)))
    return used


def _tree_size(path: Path) -> int:
    if path.is_symlink() or path.is_file():
        return path.lstat().st_size if path.is_symlink() else path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink())


def _remove(path: Path) -> None:
    """Delete a cache entry; a link (symlink, junction) is removed, never what it points to."""
    is_junction = getattr(os.path, "isjunction", lambda _: False)(path)
    if path.is_symlink() or is_junction:
        path.unlink() if path.is_symlink() else os.rmdir(path)
    elif path.is_dir():
        # extracted archives can hold read-only folders: make them writable, then retry
        def retry(func, target, _exc):
            os.chmod(target, 0o700)
            func(target)

        shutil.rmtree(path, onerror=retry)
    else:
        path.unlink(missing_ok=True)


def clean_raw(
    names: list[str] | None = None, root: str | Path | None = None, dry_run: bool = False
) -> dict[str, dict]:
    """Delete the downloaded raw files (and extracted archives) of built datasets.

    The built datasets keep working; only rebuilding them (or building another subset) has
    to download again. ``names=None`` cleans every built dataset in the folder. A raw file
    also used by a built dataset that is not being cleaned is kept. Returns
    ``{name: {"files": n, "bytes": freed, "kept": n}}``; ``dry_run`` deletes nothing.
    """
    root = resolve_root(root)
    built = {p.parent.name: p for p in root.glob("*/manifest.json")}
    names = sorted(built) if names is None else list(names)
    missing = [n for n in names if n not in built]
    if missing:
        raise FileNotFoundError(f"not built in {root}: {', '.join(missing)}")

    def digests(name):
        manifest = json.loads(built[name].read_text(encoding="utf-8"))
        found = {f["sha256"] for f in manifest.get("raw_files", [])}
        # only cache entries named by a checksum: never a path outside <root>/_raw/sha256
        return {d for d in found if re.fullmatch(r"[0-9a-f]{64}", d)}

    keep = set().union(*(digests(n) for n in built if n not in names))
    raw, report, removed = Cache(root).dir, {}, set()
    for name in names:
        files = freed = kept = 0
        for digest in sorted(digests(name)):
            if digest in keep:
                kept += 1
                continue
            paths = [raw / digest, raw / f"{digest}.d", raw / f"{digest}.origin"]
            paths = [p for p in paths if p.exists() or p.is_symlink()]
            if digest in removed or not paths:
                continue
            files += 1
            freed += sum(_tree_size(p) for p in paths)
            removed.add(digest)
            if not dry_run:
                for p in paths:
                    _remove(p)
        report[name] = {"files": files, "bytes": freed, "kept": kept}
    return report


def build(
    name_or_path: str | Path,
    root: str | Path | None = None,
    force: bool = False,
    channels: list[str] | None = None,
    where: dict[str, list] | None = None,
    as_name: str | None = None,
    files: list[str] | None = None,
) -> Path:
    """Download (if needed) and build a dataset into ``<root>/<name>``.

    A subset can be built instead of the whole dataset, to save disk:

    * ``channels``: keep only these channels (e.g. ``["CH1", "CH2", "CH3"]``);
    * ``where``: keep only recordings whose values are in the lists, e.g.
      ``{"condition": ["normal", "inner"], "load": [0]}`` (values compared as text);
    * ``files``: download only the raw files matching these globs (e.g. ``["B01*"]``),
      for datasets too big to download whole;
    * ``as_name``: folder name of the subset (required with a subset, so it never
      replaces the full dataset).

    Without ``files`` the download is the same; only what is stored changes. The selection
    is saved in the build, so rebuilding the subset by its name reproduces it.
    """
    root_path = resolve_root(root)
    previous = root_path / str(name_or_path) / "manifest.json"
    no_selection = channels is None and where is None and files is None
    if previous.exists() and no_selection and as_name is None:
        selection = json.loads(previous.read_text(encoding="utf-8")).get("selection")
        if selection:  # rebuilding a subset by its name
            channels, where = selection.get("channels"), selection.get("where")
            files = selection.get("files")
            as_name = str(name_or_path)
    spec = load_spec(name_or_path, root)
    subset = channels is not None or where is not None or files is not None
    if subset and not as_name:
        raise ValueError("a subset needs its own name: pass as_name=... (CLI: --as NAME)")
    root = root_path
    name = as_name or spec["name"]
    out = root / name
    if (out / "manifest.json").exists() and not force:
        log.info("%s is already built at %s (rebuild with --force / force=True)", name, out)
        return out

    cache = Cache(root)
    lock_file = spec["dir"] / "files.lock.json"
    if not lock_file.exists():
        log.info("writing %s (keep it next to dataset.yaml)", lock_file)
        with tqdm(unit="B", unit_scale=True, desc=f"{spec['name']}: download + checksum") as bar:
            entries = make_lock(spec, cache, progress=lambda n: bar.update(n - bar.n))
        lock_file.write_text(json.dumps(entries, indent=1) + "\n", encoding="utf-8")
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    if files is not None:
        lock = [e for e in lock if any(fnmatch.fnmatch(e["name"], g) for g in files)]
        if not lock:
            raise ValueError(f"no raw file of {spec['name']} matches {files}")
    wanted = {k: {str(v) for v in vs} for k, vs in (where or {}).items()}

    tmp = root / f".{name}.tmp-{socket.gethostname()}-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        used = _stage_raw(spec, cache, lock, tmp / "raw")
        builder = _builder(spec)
        writer, rows = SignalWriter(tmp / "signals"), []
        for rec in tqdm(
            builder.recordings(tmp / "raw"), desc=f"{name}: convert", unit=" recordings"
        ):
            if any(str(rec.get(k)) not in vs for k, vs in wanted.items()):
                continue
            signals, fs = rec.pop("signals"), rec.pop("fs", None)
            for channel, x in signals.items():
                if channels is not None and channel not in channels:
                    continue
                x = np.asarray(x() if callable(x) else x).squeeze()  # a callable loads lazily
                sid = f"{rec['recording_id']}/{channel}"
                row = {
                    "dataset": name,
                    "signal_id": sid,
                    "channel": channel,
                    **builder.CHANNELS[channel],  # channel defaults ...
                    # ... that a recording can override (e.g. its sensor_location); a value
                    # given as {channel: value} differs per channel (e.g. the bearing's bpfo)
                    **{k: v[channel] if isinstance(v, dict) else v for k, v in rec.items()},
                    "n_samples": len(x),
                }
                if fs is not None:
                    row["fs"] = fs[channel] if isinstance(fs, dict) else fs
                writer.add(sid, x)
                rows.append(row)
        content_hash = writer.close()
        meta = pd.DataFrame(rows)
        loc = pd.DataFrame.from_dict(
            writer.locations,
            orient="index",
            columns=["signal_file", "signal_row_group", "signal_row"],
        )
        meta = order_columns(meta.join(loc, on="signal_id"))
        notes = spec.get("columns") or {}
        validate(meta, notes)
        pq.write_table(
            pa.Table.from_pandas(meta, preserve_index=False),
            tmp / "metadata.parquet",
            compression="zstd",
        )
        manifest = {
            "dataset": name,
            "title": spec.get("title", ""),
            "license": spec["license"],
            "spec_dir": str(Path(spec["dir"]).resolve()),  # to rebuild private datasets by name
            "citation": spec["citation"],
            "package_version": __version__,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "content_hash": content_hash,
            "n_recordings": int(meta["recording_id"].nunique()),
            "n_signals": len(meta),
            "columns": describe(meta, notes),
            **(
                {
                    "selection": {
                        "of": spec["name"],
                        "channels": channels,
                        "where": where,
                        "files": files,
                    }
                }
                if subset
                else {}
            ),
            "raw_files": [{**e, "source": used[e["name"]]} for e in lock],
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        shutil.rmtree(tmp / "raw")
        if out.exists():
            shutil.rmtree(out)
        tmp.rename(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _group_writable(out)
    return out


def _group_writable(path: Path) -> None:
    """Make a build group-writable so every user of the group can rebuild it."""
    for p in [path, *path.rglob("*")]:
        with contextlib.suppress(OSError):
            p.chmod(p.stat().st_mode | 0o060 | (0o010 if p.is_dir() else 0))
