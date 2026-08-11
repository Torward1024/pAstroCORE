"""Where calculated results live before a project is saved.

A result used to be held in memory and marked unwritten until somebody pressed save. That was
true whether or not the project had a directory: a project never saved had nowhere to write,
and a project opened from a directory still did not write a freshly computed result until the
next save. In both, the result was on no disk and counted zero bytes against the residency
ceiling -- so a session was unprotected *and* ungoverned, and a day of calculation was lost to
a crash, a power cut or the memory running out.

A scratch directory is where they go instead. One per running session, because two windows must
not adopt and evict each other's results -- and because the same rule is what lets a server run
sessions for several people at once.

The cleanup rule is the part most easily got wrong, so it is stated plainly: a scratch
directory left behind by a previous run **is not litter**. It is the day of calculation this
module exists to protect. It is offered back. Deleting on a clean exit is right; deleting
whatever is lying around at startup would be the very failure this prevents.
"""
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional

from msb_arch.utils.logging_setup import logger

from pastrocore.base.result_store import ResultStore

#: Written beside the results so an abandoned session can describe itself.
MARKER = "session.json"


def data_home() -> Path:
    """Return the per-user directory for application data on this platform.

    Returns:
        Path: Somewhere durable and writable by this user.

    Notes:
        - Deliberately not the system temporary directory. Results have to survive a crash and
          be findable afterwards, and temporary directories are exactly what gets swept.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "pAstroCORE"


def _process_is_alive(pid: int) -> bool:
    """Report whether a process is still running, erring towards "yes".

    Args:
        pid (int): The process that owned a scratch directory.

    Returns:
        bool: True if it is running, or if the question cannot be answered.

    Notes:
        - The bias matters and is deliberate. Answering "no" wrongly means treating a live
          session's results as abandoned, and offering to recover a directory that is being
          written to. Answering "yes" wrongly means one stale directory survives until the user
          is asked about it, which costs disk and nothing else.
    """
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        logger.debug("Cannot tell whether process %s is alive; assuming it is", pid)
        return True


def _is_a_scratch_directory(candidate: Path, root: Path) -> bool:
    """Report whether a path is safe to delete as scratch.

    Args:
        candidate (Path): What is about to be removed.
        root (Path): The directory scratch sessions live in.

    Returns:
        bool: True only for a direct child of the scratch root carrying a session marker.

    Notes:
        - Two conditions, both required, and neither is satisfied by a project directory: it
          is not inside the scratch root, and it holds `project.json` rather than
          `session.json`. Deleting a project would be the worst failure this module could
          have, so it is made unreachable rather than merely avoided.
        - A project saved *into* the scratch root -- which nothing invites but nothing
          forbids -- still fails the marker test.
    """
    try:
        candidate, root = Path(candidate).resolve(), Path(root).resolve()
    except OSError:
        return False

    if candidate == root or root not in candidate.parents:
        return False
    if not (candidate / MARKER).is_file():
        return False
    if (candidate / "project.json").is_file():
        logger.error("'%s' holds a project; it will not be treated as scratch", candidate)
        return False
    return True


class AbandonedSession:
    """A scratch directory whose session is no longer running.

    Attributes:
        path (Path): The directory.
        pid (int): The process that owned it.
        started (float): When it was created, as a Unix timestamp.
        project (Optional[str]): The project being worked on, if it had been saved and so had
            a name to record.
        results (int): How many results it holds.
    """

    def __init__(self, path: Path, marker: dict):
        self.path = path
        self.pid = marker.get("pid", 0)
        self.started = marker.get("started", 0.0)
        self.project = marker.get("project")
        self.results = sum(1 for _ in path.rglob("*.parquet"))

    @property
    def age_hours(self) -> float:
        """How long ago the session started."""
        return max(0.0, (time.time() - self.started) / 3600)

    def describe(self) -> str:
        """A sentence a user can act on, rather than a path."""
        name = self.project or "an unsaved project"
        return (f"{self.results} calculated result(s) for {name}, from a session that started "
                f"{self.age_hours:.1f} hours ago and did not close normally")

    def discard(self) -> None:
        """Delete it, once the user has decided they do not want it."""
        if not _is_a_scratch_directory(self.path, self.path.parent):
            logger.error("Refusing to delete '%s': it is not a scratch directory", self.path)
            return
        shutil.rmtree(self.path, ignore_errors=True)
        logger.info("Discarded abandoned session at '%s'", self.path)

    def __repr__(self) -> str:
        return f"AbandonedSession(path={str(self.path)!r}, results={self.results})"


class ScratchSpace:
    """A directory this session may write results into, and nobody else may touch.

    Args:
        root (Optional[Path]): Where sessions live. Defaults to the per-user data directory,
            and is overridable so tests need not write to it.
        session (Optional[str]): The session's name. Defaults to the process id and a token,
            which is what keeps two windows apart.

    Notes:
        - Nothing is created until a result is actually written, so starting the application
          and closing it leaves nothing behind.
    """

    DIRECTORY = "scratch"
    RESULTS = "results"

    def __init__(self, root: Optional[Path] = None, session: Optional[str] = None):
        self._root = Path(root) if root else data_home() / self.DIRECTORY
        self._session = session or f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._path: Optional[Path] = None
        self._project: Optional[str] = None

    @property
    def session(self) -> str:
        """The name that keeps this session's results apart from another's."""
        return self._session

    @property
    def path(self) -> Optional[Path]:
        """The directory, or None while nothing has been written."""
        return self._path

    @property
    def store(self) -> ResultStore:
        """A store writing into this session's scratch, created on first use."""
        if self._path is None:
            self._path = self._root / self._session
            (self._path / self.RESULTS).mkdir(parents=True, exist_ok=True)
            self._write_marker()
            logger.info("Results of this session are kept in '%s' until the project is saved",
                        self._path)
        return ResultStore(self._path / self.RESULTS)

    def note_project(self, name: Optional[str]) -> None:
        """Record which project is being worked on, so a recovery offer can name it."""
        self._project = name
        if self._path is not None:
            self._write_marker()

    def _write_marker(self) -> None:
        if self._path is None:
            return
        (self._path / MARKER).write_text(json.dumps({
            "pid": os.getpid(), "started": time.time(), "project": self._project,
            "session": self._session}, indent=2), encoding="utf-8")

    def discard(self) -> None:
        """Remove this session's scratch. For a clean exit, and only for a clean exit."""
        if self._path is None or not self._path.exists():
            self._path = None
            return
        if not _is_a_scratch_directory(self._path, self._root):
            logger.error("Refusing to delete '%s': it is not a scratch directory", self._path)
            self._path = None
            return
        shutil.rmtree(self._path, ignore_errors=True)
        logger.info("Removed this session's scratch directory")
        self._path = None

    @classmethod
    def abandoned(cls, root: Optional[Path] = None) -> List[AbandonedSession]:
        """Return scratch directories left by sessions that are no longer running.

        Args:
            root (Optional[Path]): Where to look. Defaults to the per-user data directory.

        Returns:
            List[AbandonedSession]: Newest first, and only those holding something. A session
                that crashed before computing anything has nothing to offer back.

        Notes:
            - A directory whose process is still alive is another window's, and is skipped.
              This is the whole reason a session gets a directory of its own.
        """
        base = Path(root) if root else data_home() / cls.DIRECTORY
        if not base.is_dir():
            return []

        found = []
        for candidate in base.iterdir():
            marker = candidate / MARKER
            if not candidate.is_dir() or not marker.is_file():
                continue
            try:
                data = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.debug("Ignoring '%s': its session marker cannot be read", candidate)
                continue
            if _process_is_alive(data.get("pid", 0)):
                continue
            session = AbandonedSession(candidate, data)
            if session.results:
                found.append(session)
        return sorted(found, key=lambda item: item.started, reverse=True)

    def __repr__(self) -> str:
        return f"ScratchSpace(session={self._session!r}, path={str(self._path)!r})"
