# diagnostics.py
"""One file to send when something goes wrong, and nothing in it that names the sender.

A report needs the version, the platform, the settings and the end of the log. Asking for them
one at a time is three exchanges before anybody looks at the problem.

What the log carries besides is where projects were opened from, which is under a home
directory named after a person. Every path and every user name is replaced on the way in, so
what is sent says what happened and not who it happened to.
"""
import json
import os
import platform
import re
import sys
import zipfile
from pathlib import Path
from typing import Optional

from msb_arch.utils.logging_setup import logger

from pastrocore.base.scratch import data_home

#: How many lines of the log to keep. What went wrong is at the end, and a session's log is
#: megabytes.
TAIL = 2000

#: What is written instead of a home directory and of whoever it belongs to.
HOME = "<home>"
PERSON = "<user>"


def _short(path: Path) -> Optional[str]:
    """Return a path's 8.3 form on Windows, which is how half a log spells it.

    Notes:
        - `C:\\Users\\SOMEBO~1` is the same directory as `C:\\Users\\Somebody`, and scrubbing
          the long form alone left the short one in every path that came from a temp dir.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes

        held = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(str(path), held, 1024):
            return held.value
    except Exception as why:                        # noqa: BLE001 - scrubbing never raises
        logger.debug("Could not ask for the short form of %s: %s", path, str(why))
    return None


def _homes() -> list:
    """Return every spelling of this user's home directory, longest first."""
    home = Path.home()
    found = {str(home), str(home).replace("\\", "/"), str(home).replace("/", "\\")}
    short = _short(home)
    if short:
        found.update({short, short.replace("\\", "/"), short.replace("/", "\\")})
    return sorted(found, key=len, reverse=True)


def _names() -> list:
    """Return the ways this machine spells the person using it, longest first."""
    found = {Path.home().name}
    short = _short(Path.home())
    if short:
        found.add(Path(short).name)
    for variable in ("USERNAME", "USER", "LOGNAME"):
        said = os.environ.get(variable)
        if said:
            found.add(said)
    return sorted((name for name in found if len(name) > 2), key=len, reverse=True)


def without_identity(text: str) -> str:
    """Return the text with home directories and user names taken out.

    Args:
        text (str): Anything on its way into the file -- a log, the settings, a report.

    Returns:
        str: The same text, with what is useful kept and who it belongs to gone.

    Notes:
        - The home directories go first, longest first, in both separators and in Windows'
          8.3 form; the names go after, for what mentions a person outside a path.
    """
    for spelling in _homes():
        text = text.replace(spelling, HOME)
    for name in _names():
        text = re.sub(rf"{re.escape(name)}", PERSON, text)
    return text


def report(manipulator=None, project=None) -> str:
    """Return what is running, and what it is holding.

    Args:
        manipulator (Optional[ScheduleManipulator]): Asked what it offers, where there is one.
        project (Optional[ScheduleProject]): Asked what it holds, where there is one.

    Returns:
        str: Lines of `name: value`, which is what a person pastes into a message.
    """
    import msb_arch

    from pastrocore import __version__

    said = [f"pAstroCORE: {__version__}",
            f"msb_arch: {msb_arch.__version__}",
            f"Python: {sys.version.split()[0]}",
            f"platform: {platform.platform()} ({platform.machine()})",
            f"a build: {bool(getattr(sys, 'frozen', False))}"]

    if manipulator is not None:
        try:
            catalogue = manipulator.inspect(obj=None, method="catalogue") or []
            said.append(f"calculations offered: {sum(1 for e in catalogue if e['offer'])}")
        except Exception as why:                    # noqa: BLE001 - a report never raises
            said.append(f"calculations offered: could not be asked -- {why}")

    if project is not None:
        try:
            held = project.get_observations()
            said.append(f"observations: {len(held)}")
            for observation in held:
                said.append(f"  {observation.get_observation_code()}: "
                            f"{len(observation.get_scans().get_items())} scan(s), "
                            f"{len(observation.get_telescopes().get_items())} station(s)")
        except Exception as why:                    # noqa: BLE001 - a report never raises
            said.append(f"observations: could not be read -- {why}")

    log = data_home() / "output.log"
    if not log.is_file():
        said.append("log: no output.log yet")
    return "\n".join(said)


def _tail(path: Path) -> str:
    """Return the end of a file, or an empty string if it cannot be read."""
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError as why:
        logger.warning("Could not read %s: %s", path.name, str(why))
        return ""
    return "\n".join(lines[-TAIL:])


def collect(into, manipulator=None, project=None) -> Path:
    """Write the one file to send, and return where it was written.

    Args:
        into (str | Path): The file to write, which the caller has asked the user for.
        manipulator (Optional[ScheduleManipulator]): Passed to `report`.
        project (Optional[ScheduleProject]): Passed to `report`.

    Returns:
        Path: What was written.

    Notes:
        - Everything goes through `without_identity`, including the settings, which name the
          catalogue files a person chose.
    """
    written = Path(into)
    home = data_home()
    with zipfile.ZipFile(written, "w", zipfile.ZIP_DEFLATED) as holding:
        holding.writestr("report.txt", without_identity(report(manipulator, project)))

        settings = home / "settings.pastro"
        if settings.is_file():
            holding.writestr("settings.pastro",
                             without_identity(settings.read_text(encoding="utf-8-sig",
                                                                errors="replace")))
        log = home / "output.log"
        if log.is_file():
            holding.writestr("output.log", without_identity(_tail(log)))
    logger.info("Wrote a diagnostic report to '%s'", written.name)
    return written
