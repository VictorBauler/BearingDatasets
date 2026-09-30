"""Download bearing datasets and read them in one standardized format.

>>> import bearing_datasets as bd
>>> ds = bd.open("cwru", root="/data/bearing_datasets")
>>> meta = ds.metadata()                  # one row per signal
>>> x = ds.signal(meta.signal_id[0])    # numpy array
"""

from ._version import __version__
from .dataset import Dataset, get_root, load_metadata, open, set_root


def build(name, root=None, force=False, channels=None, where=None, as_name=None, files=None):
    """Download (if needed) and build a dataset, or a subset of it (see build.build)."""
    from .build import build as _build

    return _build(name, root, force, channels=channels, where=where, as_name=as_name, files=files)


def clean_raw(names=None, root=None, dry_run=False):
    """Delete the downloaded raw files of built datasets (see build.clean_raw)."""
    from .build import clean_raw as _clean

    return _clean(names, root, dry_run)


def list_datasets():
    from .build import list_datasets as _list

    return _list()


__all__ = [
    "__version__",
    "Dataset",
    "open",
    "build",
    "clean_raw",
    "list_datasets",
    "load_metadata",
    "set_root",
    "get_root",
]
