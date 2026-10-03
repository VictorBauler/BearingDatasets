"""Download bearing datasets and read them in one standardized format.

>>> import bearing_datasets as bd
>>> ds = bd.open("cwru", root="/data/bearing_datasets")
>>> meta = ds.metadata()                  # one row per signal
>>> x = ds.signal(meta.signal_id[0])    # numpy array
"""

# imported here, so that importing the submodule later cannot replace the build() function below
from . import build as _build
from ._version import __version__
from .dataset import Dataset, get_root, load_metadata, open, set_root


def build(name, root=None, force=False, channels=None, where=None, as_name=None, files=None):
    """Download (if needed) and build a dataset, or a subset of it (see build.build)."""
    return _build.build(
        name, root, force, channels=channels, where=where, as_name=as_name, files=files
    )


def clean_raw(names=None, root=None, dry_run=False):
    """Delete the downloaded raw files of built datasets (see build.clean_raw)."""
    return _build.clean_raw(names, root, dry_run)


def list_datasets():
    return _build.list_datasets()


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
