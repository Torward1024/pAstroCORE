# updates.py
"""Whether a newer version has been released, and fetching the one for this machine.

The window asks three questions and shows the answer: is there something newer, which file
belongs to this platform, and may that file be downloaded. The third is the one that matters,
because what comes down is run: only this project's own release assets, over https, are taken.

Nothing here opens a window, so it can be checked without one.
"""
import json
import os
import pathlib
import platform
import re
import sys
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from msb_arch.utils.logging_setup import logger

#: Where the releases are. The only place anything is fetched from.
OWNER, PROJECT = "Torward1024", "pAstroCORE"
SITE = f"https://github.com/{OWNER}/{PROJECT}"
API = f"https://api.github.com/repos/{OWNER}/{PROJECT}/releases/latest"

#: What this platform's download is called, by the suffix each build carries.
SUFFIXES = {"win32": ".exe", "darwin": ".dmg", "linux": ".AppImage"}

#: How long to wait for an answer. A laboratory network that filters this should not hold
#: the window.
PATIENCE = 20


@dataclass
class Found:
    """What a check came back with."""

    version: str = ""
    newer: bool = False
    page: str = SITE + "/releases/latest"
    notes: str = ""
    asset: Optional[dict] = None
    error: str = ""


def _numbers(version: str):
    """Return a version as numbers to compare, or None when it is not one."""
    said = (version or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+(\.\d+)*", said):
        return None
    return tuple(int(part) for part in said.split("."))


def is_newer(found: str, running: str) -> bool:
    """Whether `found` is a later version than `running`.

    Notes:
        - Compared as numbers: as text, 1.9.0 sorts after 1.10.0.
        - A tag that is not a version is never newer, there being nothing to compare.
    """
    there, here = _numbers(found), _numbers(running)
    if there is None or here is None:
        return False
    return there > here


def asset_for(release: dict, where: str = None) -> Optional[dict]:
    """Return the file of a release that belongs to this platform, or None."""
    where = where or ("linux" if sys.platform.startswith("linux") else sys.platform)
    suffix = SUFFIXES.get(where)
    if not suffix:
        return None
    for asset in release.get("assets", []):
        if str(asset.get("name", "")).endswith(suffix):
            return asset
    return None


def may_fetch(url: str) -> bool:
    """Whether a URL is this project's own release asset, over https, and so may be run."""
    wanted = f"{SITE}/releases/download/"
    return isinstance(url, str) and url.startswith(wanted) and len(url) > len(wanted)


def _ask_github() -> dict:
    """Return what the API says about the latest release."""
    request = urllib.request.Request(
        API, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": f"{PROJECT}-update-check"})
    with urllib.request.urlopen(request, timeout=PATIENCE) as answer:
        return json.loads(answer.read().decode("utf-8"))


def _in_words(why: Exception) -> str:
    """Return what to show somebody for a question that could not be asked.

    Notes:
        - GitHub allows sixty questions an hour from one address, and a department behind
          one address reaches that between them. The limit is a wait, not a failure.
    """
    import urllib.error

    if isinstance(why, urllib.error.HTTPError) and why.code == 403:
        return ("too many checks from this network in the last hour. Try later, or look at "
                f"{SITE}/releases")
    return f"{why}. The releases are at {SITE}/releases"


def check(running: str, where: str = None) -> Found:
    """Ask whether anything newer has been released.

    Args:
        running (str): The version in hand.
        where (str): The platform to find a file for; this one by default.

    Returns:
        Found: What there is, and `error` where the question could not be asked.
    """
    try:
        release = _ask_github()
    except Exception as why:                        # noqa: BLE001 - reported, never raised
        logger.warning("Could not ask about releases: %s", str(why))
        return Found(error=_in_words(why))

    tag = str(release.get("tag_name", ""))
    return Found(version=tag.lstrip("vV"), newer=is_newer(tag, running),
                 page=release.get("html_url") or SITE + "/releases/latest",
                 notes=str(release.get("body") or ""), asset=asset_for(release, where))


def _read(url: str, report: Optional[Callable[[int, int], None]]) -> bytes:
    """Return what a URL holds, telling `report` how far it has got."""
    request = urllib.request.Request(url, headers={"User-Agent": f"{PROJECT}-update"})
    held = bytearray()
    with urllib.request.urlopen(request, timeout=PATIENCE) as answer:
        total = int(answer.headers.get("Content-Length") or 0)
        while True:
            block = answer.read(256 * 1024)
            if not block:
                break
            held += block
            if report:
                report(len(held), total)
    return bytes(held)


def fetch(asset: dict, into, report: Optional[Callable[[int, int], None]] = None):
    """Download one release asset, and return where it was written.

    Args:
        asset (dict): As the API describes it: `name`, `size`, `browser_download_url`.
        into (str | Path): The directory to write it into.
        report (Optional[Callable]): Told `(so far, total)` as it goes.

    Raises:
        ValueError: If the URL is not this project's own, or what arrived is not the length
            that was offered -- in which case nothing is kept.
    """
    url = asset.get("browser_download_url", "")
    if not may_fetch(url):
        raise ValueError(f"not a {PROJECT} release asset: {url}")

    held = _read(url, report)
    offered = int(asset.get("size") or 0)
    if offered and len(held) != offered:
        raise ValueError(f"the download is {len(held)} bytes against the {offered} offered: "
                         "its length does not match what was described")

    written = pathlib.Path(into) / str(asset["name"])
    written.write_bytes(held)
    logger.info("Downloaded '%s' (%s bytes)", written.name, len(held))
    return written
