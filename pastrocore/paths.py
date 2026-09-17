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

#: Each catalogue the application keeps: the setting that names its file, and the file that came
#: with the application for it. Said once, because the window read both in six places.
CATALOGUES = {"sources": ("sources_catalog_path", "sources.json"),
              "telescopes": ("telescopes_catalog_path", "telescopes.json")}

#: What the settings are called, in the user's directory and in a working directory left over
#: from before they moved there.
SETTINGS = "settings.pastro"


def shipped_catalog(name: str) -> Path:
    """Return the path to a catalogue that came with the application.

    Args:
        name (str): The file, such as `sources.json`.

    Returns:
        Path: Absolute, so it resolves from any working directory.
    """
    return CATALOGS / name


def is_shipped(path: str) -> bool:
    """Report whether a path is in the folder the application's own catalogues are in.

    Notes:
        - That folder is part of the install: an upgrade replaces it and an install may not be
          writable at all, so a catalogue there is read and never written.
    """
    return bool(path) and Path(portable(path)).resolve().parent == CATALOGS.resolve()


def user_catalogs() -> Path:
    """Return the folder a catalogue the user edited is saved to, creating it.

    Notes:
        - Beside the settings, so an upgrade that replaces the shipped catalogues leaves the
          user's own alone.
    """
    folder = data_home() / "catalogs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def is_leftover(path: str) -> bool:
    """Report whether a stored catalogue path is from an earlier layout rather than a choice.

    Returns:
        bool: True for a relative path -- from before the catalogues moved into the package, it
            can never resolve from a per-user settings file -- and for a file that is not in the
            shipped folder any more, which is what the `.dat` catalogues became when they were
            converted to JSON. Neither is something a user can act on.
    """
    if not path:
        return False
    resolved = portable(path)
    if not Path(resolved).is_absolute():
        return True
    return is_shipped(resolved) and not Path(resolved).is_file()


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
    if is_leftover(resolved):
        # A relative path, or a shipped `.dat` that became JSON: a leftover of an earlier layout.
        # `load_settings` corrects it, so this is said once rather than on every start.
        logger.debug("Replacing the leftover catalogue path '%s'", resolved)
    elif resolved:
        # Somebody chose this and it is not there now -- a drive not mounted, a file moved.
        # Worth saying every time, because it is a real problem and it may come back.
        logger.warning("Catalogue '%s' is not there; using the one shipped at '%s'",
                       resolved, fallback)
    return str(fallback)
