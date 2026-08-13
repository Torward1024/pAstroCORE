# paths.py
"""Where the application's own files are, wherever it was started from.

Every path here used to be relative to the working directory. In a checkout that is the
repository and everything is found; installed with `pip install .` and started from anywhere
else, `catalogs/sources.dat` names nothing and `settings.pastro` is written into whichever
directory the user happened to be in -- so the catalogs come up empty and the settings are lost
the next time they start from somewhere else.

Two kinds of file, and they belong in different places:

- **Shipped**: the source and telescope catalogues. Read-only, part of the install, found beside
  the package.
- **The user's**: settings. Written, kept per user, and the same file every time.
"""
import os
from pathlib import Path

from msb_arch.utils.logging_setup import logger

from pastrocore.base.scratch import data_home

#: The catalogues that come with the application, inside the package so they reach the wheel.
CATALOGS = Path(__file__).resolve().parent / "catalogs"

#: What the settings are called, in the user's directory and in a working directory left over
#: from before they moved there.
SETTINGS = "settings.pastro"


def shipped_catalog(name: str) -> Path:
    """Return the path to a catalogue that came with the application.

    Args:
        name (str): The file, such as `sources.dat`.

    Returns:
        Path: Absolute, so it resolves from any working directory.
    """
    return CATALOGS / name


def settings_file() -> Path:
    """Return the one file the settings are read from and written to."""
    return data_home() / SETTINGS


def portable(path: str) -> str:
    r"""Return a path that resolves on the platform it is read on.

    Args:
        path (str): A path as stored in the settings file.

    Returns:
        str: The same path with separators the running platform understands.

    Notes:
        - Settings are saved with the separator of whichever platform wrote them, and the file
          the repository shipped was written on Windows. On Linux `catalogs\sources.dat` is not
          a directory and a file: it is one filename containing a backslash, so the catalogs
          silently failed to load.
    """
    return os.path.normpath(path.replace("\\", "/")) if path else path


def existing_or_shipped(path: str, name: str) -> str:
    """Return the configured catalogue if it is there, and what was shipped if it is not.

    Args:
        path (str): What the settings say, which may be from another machine or another install.
        name (str): The shipped file to fall back to.

    Returns:
        str: A path to a file that exists, unless nothing does.

    Notes:
        - A settings file records absolute paths, so an install that moves invalidates them.
          Starting with empty catalogues and one line in the log is how that used to present,
          and it looks like data loss rather than like a stale setting.
    """
    resolved = portable(path)
    if resolved and Path(resolved).is_file():
        return resolved

    fallback = shipped_catalog(name)
    if resolved:
        logger.warning("Catalogue '%s' is not there; using the one shipped at '%s'",
                       resolved, fallback)
    return str(fallback)
