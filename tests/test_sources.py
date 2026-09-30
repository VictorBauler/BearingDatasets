import hashlib
import http.server
import io
import shutil
import tarfile
import threading
import zipfile
from functools import partial

import pytest

from bearing_datasets.sources import Cache, DownloadError, Sources, _extract, make_lock


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def server(tmp_path):
    site = tmp_path / "site"
    (site / "mirror").mkdir(parents=True)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=site))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield site, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _sources(url):
    return Sources(
        [
            {"type": "http", "name": "official", "base_url": f"{url}/missing/"},
            {"type": "http", "name": "mirror", "base_url": f"{url}/mirror/"},
        ]
    )


def test_fallback_to_mirror_and_cache(server, tmp_path):
    site, url = server
    data = b"x" * 5000
    (site / "mirror" / "a.bin").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path, used = Cache(tmp_path).fetch("a.bin", len(data), digest, _sources(url))
    assert used == "mirror" and path.read_bytes() == data
    assert Cache(tmp_path).fetch("a.bin", len(data), digest, _sources(url)) == (path, "mirror")


def test_checksum_mismatch(server, tmp_path):
    site, url = server
    (site / "mirror" / "a.bin").write_bytes(b"corrupted!")
    with pytest.raises(DownloadError, match="checksum mismatch"):
        Cache(tmp_path).fetch("a.bin", 10, "0" * 64, _sources(url))


def test_resume(server, tmp_path):
    site, url = server
    data = bytes(range(256)) * 100
    (site / "mirror" / "a.bin").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    cache = Cache(tmp_path)
    (cache.dir / "tmp" / digest).write_bytes(data[:1000])
    path, _ = cache.fetch("a.bin", len(data), digest, _sources(url))
    assert path.read_bytes() == data


def test_zip_slip_is_rejected(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("../evil.txt", "boom")
    with pytest.raises(DownloadError, match="unsafe"):
        _extract(bad, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_nested_archives_are_extracted(tmp_path):
    from bearing_datasets.sources import Cache

    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("run1/data.csv", "1,2,3")
    outer = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer, "w") as zf:
        zf.write(inner, "wrapper/inner.zip")
    folder = Cache(tmp_path / "root").extract(outer, "0" * 64)
    assert (folder / "wrapper" / "inner" / "run1" / "data.csv").read_text() == "1,2,3"
    assert not (folder / "wrapper" / "inner.zip").exists()  # nested archive removed


def test_archive_names():
    from bearing_datasets.sources import archive_role, archive_stem

    assert archive_role("K001.rar") == "first" and archive_stem("K001.rar") == "K001"
    assert archive_role("x.part01.rar") == "first" and archive_stem("x.part01.rar") == "x"
    assert archive_role("x.part02.rar") == "volume"
    assert archive_role("data.csv") is None
    assert archive_stem("4. Bearings.zip") == "4. Bearings"


def test_lock_joins_records(tmp_path):
    """A dataset split over several records: the lock lists the files of all of them."""
    for part, name in [("part1", "a.bin"), ("part2", "b.bin")]:
        (tmp_path / part).mkdir()
        (tmp_path / part / name).write_bytes(name.encode())
    spec = {
        "sources": [
            {"type": "local", "path": str(tmp_path / "part1")},
            {"type": "local", "path": str(tmp_path / "part2")},
        ]
    }
    lock = make_lock(spec, Cache(tmp_path / "root"))
    assert [e["name"] for e in lock] == ["a.bin", "b.bin"]


@pytest.mark.skipif(not shutil.which("bsdtar"), reason="needs bsdtar")
def test_unreadable_folders_are_fixed(tmp_path):
    """Some archives store folders without read/execute permission (NLN-EMP)."""
    archive = tmp_path / "a.tar"
    with tarfile.open(archive, "w") as tf:
        folder = tarfile.TarInfo("data")
        folder.type, folder.mode = tarfile.DIRTYPE, 0o200
        tf.addfile(folder)
        member = tarfile.TarInfo("data/x.txt")
        member.size = 1
        tf.addfile(member, io.BytesIO(b"1"))
    dest = tmp_path / "out"
    dest.mkdir()
    _extract(archive, dest)
    assert (dest / "data" / "x.txt").read_text() == "1"


def test_manual_download_under_root(tmp_path):
    """Data behind a login: a local source under {root}, with instructions if it is missing."""
    spec = {"type": "local", "path": "{root}/_manual/x", "manual": "Download x.bin from the site."}
    cache = Cache(tmp_path)
    with pytest.raises(DownloadError, match="Download x.bin"):
        cache.fetch("x.bin", None, None, Sources([spec], tmp_path))
    (tmp_path / "_manual" / "x").mkdir(parents=True)
    (tmp_path / "_manual" / "x" / "x.bin").write_bytes(b"data")
    path, label = cache.fetch("x.bin", None, None, Sources([spec], tmp_path))
    assert path.read_bytes() == b"data" and label == "local"


def test_kaggle_listing_pages_and_bundle(monkeypatch):
    import bearing_datasets.sources as src

    pages = {
        "": {"datasetFiles": [{"name": "a/x(1).csv", "totalBytes": 3}], "nextPageToken": "t2"},
        "t2": {"datasetFiles": [{"name": "b.pdf", "totalBytes": 5}], "nextPageToken": ""},
    }
    urls = []

    def fake_get_json(url):
        urls.append(url)
        return pages[url.partition("pageToken=")[2]]

    monkeypatch.setattr(src, "get_json", fake_get_json)
    spec = {"type": "kaggle", "dataset": "me/set", "version": 2}
    listing = src.list_source(spec)
    assert len(urls) == 2 and all("datasetVersionNumber=2" in u for u in urls)
    assert listing["a/x(1).csv"] == {
        "size": 3,
        "url": f"{src.KAGGLE_API}/download/me/set/a%2Fx%281%29.csv?datasetVersionNumber=2",
    }
    assert list(src.list_source(spec | {"include": "*.csv"})) == ["a/x(1).csv"]
    bundle = src.list_source(spec | {"bundle": True})
    assert bundle == {
        "set.zip": {"size": None, "url": f"{src.KAGGLE_API}/download/me/set?datasetVersionNumber=2"}
    }


def test_kaggle_zip_wrapper_is_unwrapped(tmp_path):
    from bearing_datasets.sources import _unwrap_kaggle

    wrapped = tmp_path / "123-data.mat"
    with zipfile.ZipFile(wrapped, "w") as z:
        z.writestr("data.mat", b"signal")
    _unwrap_kaggle(wrapped, "sub/data.mat", 6)
    assert wrapped.read_bytes() == b"signal"
    sheet = tmp_path / "book.xlsx"  # a zip-based format served as is: left alone
    with zipfile.ZipFile(sheet, "w") as z:
        z.writestr("xl/workbook.xml", b"<x/>")
        z.writestr("[Content_Types].xml", b"<y/>")
    before = sheet.read_bytes()
    _unwrap_kaggle(sheet, "book.xlsx", None)
    assert sheet.read_bytes() == before
    with pytest.raises(DownloadError, match="incomplete"):
        _unwrap_kaggle(sheet, "book.xlsx", 1)


def test_download_resumes_a_flaky_connection(tmp_path, monkeypatch):
    import bearing_datasets.sources as src

    payload = bytes(range(256)) * 4  # 1024 bytes, sent at most `per_request` bytes at a time
    per_request = {"n": 100}

    class Flaky(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            start = int(self.headers.get("Range", "bytes=0-")[6:].rstrip("-"))
            self.send_response(206 if start else 200)
            self.send_header("Content-Length", str(len(payload) - start))
            if start:
                self.send_header(
                    "Content-Range", f"bytes {start}-{len(payload) - 1}/{len(payload)}"
                )
            self.end_headers()
            self.wfile.write(payload[start : start + per_request["n"]])  # then drop

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Flaky)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/f.bin"
    monkeypatch.setattr(src.time, "sleep", lambda s: None)
    try:
        src.download(url, tmp_path / "f.bin", len(payload))  # 11 requests, never 3 stalls
        assert (tmp_path / "f.bin").read_bytes() == payload
        per_request["n"] = 0
        with pytest.raises(DownloadError, match="incomplete"):
            src.download(url, tmp_path / "g.bin", len(payload))
    finally:
        httpd.shutdown()


def test_dataverse_listing_fetches_uploaded_tables(monkeypatch):
    import bearing_datasets.sources as src

    version = {"data": {"files": [
        {"dataFile": {"id": 7, "filename": "a.tab", "filesize": 90, "originalFileName": "a.csv",
                      "originalFileSize": 100}},
        {"directoryLabel": "docs", "dataFile": {"id": 8, "filename": "b.txt", "filesize": 5}},
    ]}}  # fmt: skip
    urls = []
    monkeypatch.setattr(src, "get_json", lambda url: urls.append(url) or version)
    spec = {"type": "dataverse", "server": "https://dv.org/", "doi": "10.1/x", "version": "2.1"}
    assert src.list_source(spec) == {
        "a.csv": {"size": 100, "url": "https://dv.org/api/access/datafile/7?format=original"},
        "docs/b.txt": {"size": 5, "url": "https://dv.org/api/access/datafile/8"},
    }
    assert urls[0] == (
        "https://dv.org/api/datasets/:persistentId/versions/2.1?persistentId=doi%3A10.1%2Fx"
    )
    assert list(src.list_source(spec | {"include": "*.csv"})) == ["a.csv"]


def test_parallel_fetch(tmp_path):
    import time as _time

    import bearing_datasets.sources as src

    state = {"now": 0, "max": 0}
    guard = threading.Lock()

    class Slow(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            with guard:
                state["now"] += 1
                state["max"] = max(state["max"], state["now"])
            _time.sleep(0.2)
            body = b"same" if "dup" in self.path else self.path.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            with guard:
                state["now"] -= 1

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    names = ["x/data.csv", "y/data.csv", "dup1.bin", "dup2.bin", "c.bin", "d.bin"]
    sources = Sources([{"type": "http", "base_url": url, "urls": {n: f"{url}/{n}" for n in names}}])
    try:
        got = src.fetch_all(Cache(tmp_path), [(n, None, None) for n in names], sources)
    finally:
        httpd.shutdown()
    assert state["max"] > 1  # downloads overlapped
    assert got["x/data.csv"][0].read_bytes() == b"/x/data.csv"  # same basename, no mix-up
    assert got["y/data.csv"][0].read_bytes() == b"/y/data.csv"
    assert got["dup1.bin"][0] == got["dup2.bin"][0]  # equal content, one cache file


def test_extracted_files_follow_the_umask(tmp_path):
    """In a shared root (umask 002) extracted files are group-writable, whatever the archive."""
    import os
    import stat

    from bearing_datasets.sources import _fix_permissions

    dest = tmp_path / "out"
    (dest / "sub").mkdir(parents=True)
    doc = dest / "sub" / "doc.pdf"
    doc.write_bytes(b"1")
    doc.chmod(0o644)  # as recorded in the archive
    (dest / "sub").chmod(0o755)
    old = os.umask(0o002)
    try:
        _fix_permissions(dest)
    finally:
        os.umask(old)
    assert stat.S_IMODE(doc.stat().st_mode) & 0o660 == 0o660
    assert stat.S_IMODE((dest / "sub").stat().st_mode) & 0o770 == 0o770
