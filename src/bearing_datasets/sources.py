"""Downloading raw files: sources, shared cache, checksums, mirror fallback, archives.

Source types (in ``dataset.yaml``), tried in order for every file:

* ``http``:     ``base_url`` + file name (needs ``files:`` in dataset.yaml), or ``urls``:
                an explicit ``{file name: url}`` map (e.g. Google Drive links)
* ``mendeley``: ``id``, ``version``, optional ``include`` glob (Mendeley Data public API)
* ``zenodo``:   ``record``, optional ``include`` glob
* ``kaggle``:   ``dataset`` (``owner/slug``), ``version``, optional ``include`` glob; public
                datasets need no Kaggle account. ``bundle: true`` fetches the whole version as
                one zip (``<slug>.zip``) instead of file by file (for datasets of many files)
* ``dataverse``: ``server``, ``doi``, ``version``, optional ``include`` glob (any Dataverse
                repository); tables that Dataverse converted to .tab are fetched as uploaded
* ``local``:    ``path``, optional ``include`` glob (data already on the server); ``{root}`` in
                the path is the datasets folder, e.g. ``{root}/_manual/<name>`` for data that
                must be downloaded by hand (e.g. behind a login)

Any source can have ``manual``: instructions shown when no source could provide a file.

A file can come from any source that has it, so a dataset split over several records lists
them all.

Downloads go to ``<root>/_raw/<sha256>``, shared by every build and every user.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlencode

import pandas as pd

from ._version import __version__

USER_AGENT = f"bearing-datasets/{__version__}"
CHUNK = 1 << 20
ARCHIVES = (".zip", ".rar", ".7z")
KAGGLE_API = "https://www.kaggle.com/api/v1/datasets"
DOWNLOAD_WORKERS = 4  # files fetched at once (some servers cap each connection at ~1 MB/s)
VOLUME = re.compile(r"\.part(\d+)\.rar$", re.IGNORECASE)  # multi-volume rar: x.part01.rar ...


def archive_role(name: str) -> str | None:
    """'first' for an archive to extract, 'volume' for a later part of a multi-volume rar."""
    if m := VOLUME.search(name):
        return "first" if int(m[1]) == 1 else "volume"
    return "first" if name.lower().endswith(ARCHIVES) else None


def archive_stem(name: str) -> str:
    """Folder name an archive is exposed as: K001.rar -> K001, x.part01.rar -> x."""
    return VOLUME.sub("", name) if VOLUME.search(name) else name.rsplit(".", 1)[0]


class DownloadError(RuntimeError):
    pass


# --------------------------------------------------------------------------- http


def _open(url: str, headers: dict | None = None):
    # urllib, not requests: some hosts (e.g. Mendeley Data) reject requests
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    return urllib.request.urlopen(req, timeout=120)


def get_json(url: str):
    for attempt in range(3):
        try:
            with _open(url) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError) as e:
            if attempt == 2:
                raise DownloadError(f"GET {url}: {e}") from e
            time.sleep(2**attempt)


def download(url: str, dest: Path, size: int | None = None, progress=None) -> None:
    """Download to ``dest``, resuming a partial file and checking the length.

    A dropped connection is retried (resuming) as long as the retries bring new bytes; it
    gives up after 3 retries in a row without progress. ``progress(n)`` is called with the
    number of bytes of the file downloaded so far.
    """
    stalls = 0
    while True:
        have = dest.stat().st_size if dest.exists() else 0
        try:
            with _open(url, {"Range": f"bytes={have}-"} if have else None) as r:
                resumed = have and r.status == 206
                done = have if resumed else 0
                total = int(r.headers.get("Content-Length", -1)) + done
                with dest.open("ab" if resumed else "wb") as fh:
                    while chunk := r.read(CHUNK):
                        fh.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done)
            got = dest.stat().st_size
            if (total >= 0 and got != total) or (size is not None and got != size):
                raise DownloadError(f"incomplete download ({got} bytes)")
            return
        except urllib.error.HTTPError as e:
            if e.code == 416 and size == have:
                return
            error = DownloadError(f"{url}: HTTP {e.code}")
            if e.code in (401, 403, 404, 410):
                raise error from e
        except (urllib.error.URLError, OSError, DownloadError) as e:
            error = DownloadError(f"{url}: {e}")
        grew = dest.exists() and dest.stat().st_size > have
        stalls = 0 if grew else stalls + 1
        if stalls == 3:
            raise error
        time.sleep(min(2**stalls, 30))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- sources


def _included(name: str, src: dict) -> bool:
    patterns = src.get("include", "*")
    patterns = [patterns] if isinstance(patterns, str) else patterns
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def list_source(src: dict) -> dict[str, dict] | None:
    """``{name: {size, sha256?, url?, path?}}`` for listable sources, else None."""
    kind = src["type"]
    if kind == "mendeley":
        api = f"https://data.mendeley.com/public-api/datasets/{src['id']}"
        folders = {f["id"]: f for f in get_json(f"{api}/folders/{src['version']}")}

        def folder_path(fid):
            parts = []
            while fid in folders:
                parts.append(folders[fid]["name"])
                fid = folders[fid].get("parent_id")
            return "/".join(reversed(parts))

        out = {}
        for fid in ["root", *folders]:
            prefix = "" if fid == "root" else folder_path(fid) + "/"
            for f in get_json(f"{api}/files?folder_id={fid}&version={src['version']}"):
                name, cd = prefix + f["filename"], f["content_details"]
                if _included(name, src):
                    name = name.removeprefix(src.get("strip_prefix", ""))
                    out[name] = {
                        "size": cd["size"],
                        "sha256": cd["sha256_hash"],
                        "url": cd["download_url"],
                    }
        return out
    if kind == "zenodo":
        rec = get_json(f"https://zenodo.org/api/records/{src['record']}")
        return {
            f["key"]: {"size": f["size"], "url": f["links"]["self"]}
            for f in rec["files"]
            if _included(f["key"], src)
        }
    if kind == "kaggle":
        ref, version = src["dataset"], src["version"]
        if src.get("bundle"):  # stored once per version, so its checksum is stable
            url = f"{KAGGLE_API}/download/{ref}?datasetVersionNumber={version}"
            return {ref.split("/")[1] + ".zip": {"size": None, "url": url}}
        out, token = {}, ""
        while True:  # paged, 200 files at most per page
            query = {"datasetVersionNumber": version, "pageSize": 200}
            page = get_json(f"{KAGGLE_API}/list/{ref}?" + urlencode(query | {"pageToken": token}))
            for f in page["datasetFiles"]:
                if _included(f["name"], src):
                    # a "/" in the file name must be encoded too
                    url = f"{KAGGLE_API}/download/{ref}/{quote(f['name'], safe='')}"
                    out[f["name"]] = {
                        "size": f["totalBytes"],
                        "url": f"{url}?datasetVersionNumber={version}",
                    }
            if not (token := page.get("nextPageToken")):
                return out
    if kind == "dataverse":
        server, query = src["server"].rstrip("/"), urlencode({"persistentId": f"doi:{src['doi']}"})
        version = get_json(f"{server}/api/datasets/:persistentId/versions/{src['version']}?{query}")
        out = {}
        for f in version["data"]["files"]:
            df = f["dataFile"]
            converted = "originalFileName" in df  # ingested table: fetch the uploaded file
            name = df["originalFileName"] if converted else df["filename"]
            name = f"{f['directoryLabel']}/{name}" if f.get("directoryLabel") else name
            if _included(name, src):
                url = f"{server}/api/access/datafile/{df['id']}"
                out[name] = {
                    "size": df["originalFileSize"] if converted else df["filesize"],
                    "url": url + "?format=original" if converted else url,
                }
        return out
    if kind == "local":
        base = Path(os.path.expanduser(src["path"]))
        return {
            p.relative_to(base).as_posix(): {"size": p.stat().st_size, "path": p}
            for p in sorted(base.rglob("*"))
            if p.is_file() and _included(p.relative_to(base).as_posix(), src)
        }
    return None


class Sources:
    """The sources of one dataset, listed lazily."""

    def __init__(self, specs: list[dict], root: Path | None = None) -> None:
        self.specs = [
            {**s, "path": s["path"].replace("{root}", str(root))}
            if root is not None and "path" in s
            else s
            for s in specs
        ]
        self._listings: dict[int, dict | None] = {}
        self._lock = threading.Lock()  # listed once even when files are fetched in parallel

    def listing(self, i: int) -> dict | None:
        with self._lock:
            if i not in self._listings:
                self._listings[i] = list_source(self.specs[i])
            return self._listings[i]

    def locations(self, name: str):
        """Yield ``(label, url or local path)`` for a file, in source order."""
        for i, src in enumerate(self.specs):
            label = src.get("name", src["type"])
            if src["type"] == "http":
                if "urls" in src:
                    if name in src["urls"]:
                        yield label, src["urls"][name]
                else:
                    yield label, src["base_url"].rstrip("/") + "/" + quote(name)
                continue
            try:
                hit = (self.listing(i) or {}).get(name)
            except DownloadError:
                continue
            if hit:
                yield label, hit.get("url") or hit["path"]


_digest_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)
_digest_locks_guard = threading.Lock()


def _digest_lock(digest: str) -> threading.Lock:
    with _digest_locks_guard:
        return _digest_locks[digest]


def fetch_all(cache: Cache, files: list[tuple], sources: Sources, progress=None) -> dict:
    """``cache.fetch`` every ``(name, size, sha256 or None)``, DOWNLOAD_WORKERS at a time.

    Returns ``{name: (cached file, source label)}``; ``progress(n)`` gets byte increments.
    """
    lock, seen = threading.Lock(), {}

    def one(name, size, digest):
        def file_progress(n):
            with lock:
                if progress:
                    progress(n - seen.get(name, 0))
                seen[name] = n

        path, label = cache.fetch(name, size, digest, sources, file_progress)
        file_progress(path.stat().st_size)  # files already cached count too
        return name, (path, label)

    out = {}
    with ThreadPoolExecutor(DOWNLOAD_WORKERS) as pool:
        futures = [pool.submit(one, *f) for f in files]
        try:
            for future in as_completed(futures):
                name, result = future.result()
                out[name] = result
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    return out


def _unwrap_kaggle(tmp: Path, name: str, size: int | None) -> None:
    """Kaggle serves some files inside a zip holding just that file: keep the file itself."""
    if zipfile.is_zipfile(tmp) and not name.lower().endswith(".zip"):
        with zipfile.ZipFile(tmp) as z:
            members = z.infolist()
            if len(members) == 1 and PurePosixPath(members[0].filename).name == Path(name).name:
                with z.open(members[0]) as src, tmp.with_suffix(".unzip").open("wb") as dst:
                    shutil.copyfileobj(src, dst, CHUNK)
                tmp.with_suffix(".unzip").replace(tmp)
    if size is not None and tmp.stat().st_size != size:
        raise DownloadError(f"incomplete download ({tmp.stat().st_size} bytes)")


# --------------------------------------------------------------------------- cache


class Cache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "_raw" / "sha256"
        (self.dir / "tmp").mkdir(parents=True, exist_ok=True)

    def origin(self, digest: str) -> str:
        p = self.dir / f"{digest}.origin"
        return p.read_text(encoding="utf-8").strip() if p.exists() else "cache"

    def fetch(
        self, name: str, size: int | None, digest: str | None, sources: Sources, progress=None
    ) -> tuple[Path, str]:
        """Return ``(cached file, source label)``; tries every source until one verifies."""
        with _digest_lock(digest) if digest else nullcontext():  # one download per file
            return self._fetch(name, size, digest, sources, progress)

    def _fetch(self, name, size, digest, sources, progress):
        if digest and (self.dir / digest).exists():
            return self.dir / digest, self.origin(digest)
        errors = []
        # a digest keeps the name across runs (resume); else unique, also for equal basenames
        unique = f"{os.getpid()}-{hashlib.sha1(name.encode()).hexdigest()[:10]}-{Path(name).name}"
        for label, loc in sources.locations(name):
            tmp = self.dir / "tmp" / (digest or unique)
            try:
                if isinstance(loc, Path):
                    shutil.copyfile(loc, tmp)
                elif loc.startswith(KAGGLE_API):
                    download(loc, tmp, None, progress)
                    _unwrap_kaggle(tmp, name, size)
                else:
                    download(loc, tmp, size, progress)
                got = sha256(tmp)
                if digest and got != digest:
                    tmp.unlink()
                    raise DownloadError(f"checksum mismatch (got {got})")
            except (DownloadError, OSError) as e:
                errors.append(f"{label}: {e}")
                continue
            tmp.replace(self.dir / got)
            (self.dir / f"{got}.origin").write_text(label, encoding="utf-8")
            return self.dir / got, label
        hints = [
            s["manual"].strip().replace("\n", "\n  ") for s in sources.specs if s.get("manual")
        ]
        raise DownloadError(f"{name}: no source could provide it\n  " + "\n  ".join(errors + hints))

    def extract(self, archive: Path, digest: str) -> Path:
        """Extract an archive once into ``_raw/sha256/<digest>.d/`` (refusing unsafe paths).

        ``archive`` is the staged file (with its real name, so the other volumes of a
        multi-volume rar are found next to it); archives inside it are extracted too.
        """
        out = self.dir / f"{digest}.d"
        if not out.exists():
            tmp = self.dir / f"{digest}.tmp-{os.getpid()}"
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir()
            _extract(archive, tmp)
            _extract_nested(tmp)
            tmp.rename(out)
        return out


def _check_member(name: str) -> None:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        raise DownloadError(f"refusing to extract unsafe path {name!r}")


def _extract(archive: Path, dest: Path) -> None:
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                _check_member(member)
            zf.extractall(dest)
    elif archive.name.lower().endswith(".rar") and shutil.which("unrar"):
        # unrar handles RAR5 and multi-volume archives (the other parts must sit next to it)
        names = subprocess.run(
            ["unrar", "lb", archive], check=True, capture_output=True, text=True
        ).stdout.splitlines()
        for member in names:
            _check_member(member)
        subprocess.run(["unrar", "x", "-y", "-idq", archive, f"{dest}/"], check=True)
    elif tool := shutil.which("bsdtar"):  # 7z, rar, tar, ... via libarchive
        names = subprocess.run(
            [tool, "-tf", archive], check=True, capture_output=True, text=True
        ).stdout.splitlines()
        for member in names:
            _check_member(member)
        subprocess.run([tool, "-xf", archive, "-C", dest], check=True)
    else:
        raise DownloadError(f"cannot extract {archive}: install unrar or bsdtar (libarchive)")
    _fix_permissions(dest)


def _fix_permissions(dest: Path) -> None:
    """Make extracted files usable whatever the archive recorded: owner read/write (some
    archives store unreadable folders), what the user's umask grants the group (e.g. write
    with umask 002, for a shared root) and the group of a setgid folder (some extractors do
    not inherit it)."""
    umask = os.umask(0)
    os.umask(umask)
    info = os.stat(dest)
    group = info.st_gid if info.st_mode & stat.S_ISGID else -1
    for root, dirs, files in os.walk(dest):
        for name, bits in [(d, 0o700 | (0o777 & ~umask)) for d in dirs] + [
            (f, 0o600 | (0o666 & ~umask)) for f in files
        ]:
            path = os.path.join(root, name)
            os.chmod(path, os.stat(path).st_mode | bits)
            if group != -1 and os.stat(path).st_gid != group:
                with contextlib.suppress(OSError):
                    os.chown(path, -1, group)


def _extract_nested(folder: Path) -> None:
    """Extract archives found inside an extracted archive (e.g. zip -> 7z -> rar)."""
    found = True
    while found:
        found = False
        for path in sorted(folder.rglob("*")):
            if path.is_file() and archive_role(path.name) == "first":
                target = path.with_name(archive_stem(path.name))
                target.mkdir(exist_ok=True)
                _extract(path, target)
                for part in [path, *path.parent.glob(VOLUME.sub("", path.name) + ".part*.rar")]:
                    part.unlink(missing_ok=True)
                found = True


# --------------------------------------------------------------------------- lock


def make_lock(spec: dict, cache: Cache, progress=None) -> list[dict]:
    """Pin name, size and sha256 of every raw file (downloads the ones without a checksum)."""
    sources = Sources(spec["sources"], cache.root)
    names = spec.get("files")
    if isinstance(names, str):  # "side_table.csv:column"
        table, _, column = names.partition(":")
        names = pd.read_csv(spec["dir"] / table)[column].tolist()
    listing = {}  # union of the listable sources (a dataset split over several records)
    for i in reversed(range(len(spec["sources"]))):  # the first source wins for a name
        try:
            listing.update(sources.listing(i) or {})
        except DownloadError:
            continue
    names = sorted(names or listing)
    missing = [(n, listing.get(n, {}).get("size"), None) for n in names
               if listing.get(n, {}).get("sha256") is None]  # fmt: skip
    done = [0]

    def add(n):
        done[0] += n
        if progress:
            progress(done[0])

    fetched = fetch_all(cache, missing, sources, add)
    entries = []
    for name in names:
        info = listing.get(name, {})
        digest = info.get("sha256") or fetched[name][0].name
        entries.append(
            {
                "name": name,
                "size": info.get("size") or (cache.dir / digest).stat().st_size,
                "sha256": digest,
            }
        )
    return entries
