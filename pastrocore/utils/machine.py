# pastrocore/utils/machine.py
"""What this machine and this process have, asked in one place.

Two callers want it and for different reasons -- the residency budget decides how many results may
stay in hand from what the machine has free, and the window's status bar says what the process is
using -- and both would otherwise carry their own `import psutil` and their own fallback.

Notes:
    - **A guess rather than a refusal.** psutil is a declared dependency; if a stripped environment
      lacks it, reporting a conservative number is better than an import error, because neither
      caller is doing anything that depends on the number being right.
"""
from msb_arch.utils.logging_setup import logger

#: What to assume a machine has free when it cannot be asked: enough not to evict everything.
ASSUMED_AVAILABLE = 2 * 1024 ** 3


def available_memory() -> int:
    """Bytes of memory the machine has free just now, or `ASSUMED_AVAILABLE` if it cannot be asked."""
    try:
        import psutil

        return int(psutil.virtual_memory().available)
    except Exception:                                   # noqa: BLE001 - a number, not a failure
        logger.debug("Cannot read available memory; assuming %s GB", ASSUMED_AVAILABLE / 1024 ** 3)
        return ASSUMED_AVAILABLE


def process_memory() -> int:
    """Bytes this process holds in resident memory, or 0 if it cannot be asked.

    Notes:
        - The resident set rather than what has been allocated: it is what the machine is actually
          giving this process, and it is the number a user comparing with their task manager sees.
    """
    try:
        import psutil

        return int(psutil.Process().memory_info().rss)
    except Exception:                                   # noqa: BLE001 - a number, not a failure
        logger.debug("Cannot read this process's memory")
        return 0


def as_size(size: int) -> str:
    """Bytes as something to read: `212 MB`, `1.4 GB`.

    Args:
        size (int): A number of bytes.

    Returns:
        str: The size in the largest unit that leaves it above one, or an empty string for 0 --
            a status bar saying "0 B" is saying nothing, and should say nothing.
    """
    if size <= 0:
        return ""
    for unit, step in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if size >= step:
            scaled = size / step
            return f"{scaled:.1f} {unit}" if scaled < 10 and unit != "MB" else f"{scaled:.0f} {unit}"
    return f"{size} B"
