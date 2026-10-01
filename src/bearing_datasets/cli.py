"""Command line: ``bearing-datasets root | list | info | build | verify``."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging

from .build import build, clean_raw, list_datasets, load_spec
from .dataset import UnknownIdError, get_root, resolve_root, set_root
from .dataset import open as open_dataset
from .sources import DownloadError


def _print_clean(report: dict, dry_run: bool) -> None:
    verb = "would free" if dry_run else "freed"
    for name, r in report.items():
        kept = f" (kept {r['kept']} also used by other built datasets)" if r["kept"] else ""
        print(f"{name}: {verb} {r['bytes'] / 1e9:.2f} GB in {r['files']} raw files{kept}")
    if len(report) > 1:
        print(f"total: {verb} {sum(r['bytes'] for r in report.values()) / 1e9:.2f} GB")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="bearing-datasets")
    p.add_argument("--root", help="datasets folder (default: the one saved with `root`)")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("root", help="show or save the datasets folder")
    r.add_argument("folder", nargs="?", help="folder to use from now on")
    sub.add_parser("list", help="available datasets")
    sub.add_parser("info", help="sources, license and citation").add_argument("name")
    b = sub.add_parser("build", help="download and build one or more datasets")
    b.add_argument(
        "names",
        nargs="+",
        metavar="name",
        help="dataset names (see `list`), or paths to private dataset folders",
    )
    b.add_argument("--force", action="store_true", help="rebuild if already built")
    b.add_argument(
        "--channels", nargs="+", metavar="CH", help="subset: keep only these channels (needs --as)"
    )
    b.add_argument(
        "--where",
        action="append",
        default=[],
        metavar="COLUMN=V1,V2",
        help="subset: keep only recordings with these values, e.g. fault_type=normal,inner "
        "(repeatable; needs --as)",
    )
    b.add_argument(
        "--files",
        nargs="+",
        metavar="GLOB",
        help='subset: download only the raw files matching these globs, e.g. "B01*" (needs --as)',
    )
    b.add_argument("--as", dest="as_name", metavar="NAME", help="folder name of a subset build")
    b.add_argument(
        "--clean-raw",
        action="store_true",
        help="delete the downloaded raw files after building (a rebuild downloads them again)",
    )
    c = sub.add_parser(
        "clean-raw",
        help="delete the downloaded raw files of built datasets (they keep working)",
    )
    c.add_argument("names", nargs="*", metavar="name", help="built datasets to clean")
    c.add_argument("--all-built", action="store_true", help="every built dataset in the folder")
    c.add_argument("--dry-run", action="store_true", help="only show what would be deleted")
    sub.add_parser("verify", help="re-hash the stored signals").add_argument("name")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.cmd == "root":
        if args.folder:
            print(f"datasets folder saved: {set_root(args.folder)}")
        else:
            path, origin = get_root()
            print(
                f"{path}  (from {origin})"
                if path
                else "not set: run `bearing-datasets root <folder>`"
            )
    elif args.cmd == "list":
        try:
            root = resolve_root(args.root)
            built = {p.parent.name: p for p in root.glob("*/manifest.json")}
        except ValueError:
            built = {}
        for name in list_datasets():
            flag = "[built]" if name in built else ""
            print(f"{flag:<8} {name:<14} {load_spec(name).get('title', '')}")
        for name in sorted(set(built) - set(list_datasets())):  # private datasets built by path
            title = json.loads(built[name].read_text(encoding="utf-8")).get("title", "")
            print(f"{'[built]':<8} {name:<14} {title} (private, not part of the package)")
    elif args.cmd == "info":
        try:
            spec = load_spec(args.name, args.root)
        except UnknownIdError as e:
            raise SystemExit(str(e)) from None
        print(f"{spec['name']}: {spec.get('title', '')}\nlicense: {spec['license']}")
        if "size" in spec:
            print(f"size: {spec['size']}")
        print("sources: " + ", ".join(s.get("name", s["type"]) for s in spec["sources"]))
        print(f"\n{spec.get('description', '').strip()}\n\nCite:\n{spec['citation'].strip()}")
        try:
            cols = open_dataset(args.name, args.root).manifest["columns"]
            print("\nColumns:")
        except (ValueError, FileNotFoundError, KeyError):
            cols = spec.get("columns") or {}
            print("\nDataset-specific columns (build it to see all):")
        for col, desc in cols.items():
            print(f"  {col:<18} {desc}")
    elif args.cmd == "build":
        where = {}
        for item in args.where:
            column, _, values = item.partition("=")
            where[column] = values.split(",")
        if args.as_name and len(args.names) > 1:
            p.error("--as works with one dataset at a time")
        for name in args.names:
            try:
                path = build(
                    name,
                    args.root,
                    force=args.force,
                    channels=args.channels,
                    where=where or None,
                    as_name=args.as_name,
                    files=args.files,
                )
            except (DownloadError, UnknownIdError) as e:
                raise SystemExit(f"cannot build {name}: {e}") from None
            citation = load_spec(name, args.root)["citation"].strip()
            print(f"ready: {path}\n\nPlease cite:\n{citation}\n")
            if args.clean_raw:
                _print_clean(clean_raw([path.name], args.root), dry_run=False)
    elif args.cmd == "clean-raw":
        if bool(args.names) == args.all_built:
            p.error("give dataset names or --all-built")
        try:
            report = clean_raw(None if args.all_built else args.names, args.root, args.dry_run)
        except FileNotFoundError as e:
            raise SystemExit(str(e)) from None
        _print_clean(report, args.dry_run)
    elif args.cmd == "verify":
        ds = open_dataset(args.name, args.root)
        h = hashlib.sha256()
        for sid, x in ds.iter_signals(sorted(ds.metadata()["signal_id"])):  # one at a time
            digest = hashlib.sha256(x.dtype.name.encode() + x.tobytes()).hexdigest()
            h.update(f"{sid}:{digest}\n".encode())
        ok = h.hexdigest() == ds.manifest["content_hash"]
        print(f"{args.name}: {'OK' if ok else 'MISMATCH'}")
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
