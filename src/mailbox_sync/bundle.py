"""Locating the engine shipped next to the application, when there is one.

A packaged build places imapsync and its dependencies in an `engine` folder next
to the executable. Nothing is downloaded and nothing is executed at import time:
this only reports a path the user can still replace.
"""
import os
from pathlib import Path
import sys


def application_directory() -> Path:
    """Folder of the running application: the executable's folder once frozen,
    the project root when running from sources."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def bundled_engine(directory=None) -> Path | None:
    """Path of the engine shipped with the application, or None."""
    base = Path(directory) if directory is not None else application_directory()
    for name in ("imapsync.exe", "imapsync"):
        candidate = base / "engine" / name
        try:
            if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return candidate
        except OSError:
            continue
    return None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
