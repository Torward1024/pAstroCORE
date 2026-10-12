# selftest.py
"""What a build checks about itself, beyond having started.

1.18.0 started on three machines and could do nothing: MSB derives what an application offers
by reading the source of its handlers, and a frozen build holds bytecode. Every test passed,
because every test ran from a checkout.

So a build is asked to do the work rather than to describe it -- run the calculations an
observation allows, and draw each plot that has a result. What only breaks in a build breaks
here, on the machine that made it.
"""
from typing import Any, Dict, List, Tuple

from msb_arch.utils.logging_setup import logger


def offered_by(manipulator) -> Tuple[List[str], List[str]]:
    """Return the calculations a build offers, and the ones it can draw."""
    catalogue = manipulator.inspect(obj=None, method="catalogue") or []
    return ([entry["key"] for entry in catalogue if entry["offer"]],
            [entry["key"] for entry in catalogue if entry["can_plot"]])


def calculated(manipulator, project, keys: List[str]) -> int:
    """Run every calculation over the project, and return how many steps worked."""
    observations = project.get_observations()
    if not observations or not keys:
        return 0
    answer = manipulator.compute(obj=None, method="run", calculations=keys,
                                 targets=observations, raise_on_error=False)
    outcome = getattr(answer, "value", None) or {}
    return len(outcome.get("ran", []))


def drawn(manipulator, observation, keys: List[str]) -> int:
    """Draw each plot the observation has a result for, and return how many came out.

    Notes:
        - Into a figure of this process's own, with no window: what is being checked is that
          the drawing machinery is in the build, which is where a missing backend shows up.
    """
    from matplotlib.figure import Figure

    held = manipulator.inspect(obj=observation, method="available", keys=keys) or []
    made = 0
    for key in held:
        answer = manipulator.visualize(obj=observation, plot_type=key, show=False,
                                       return_figure=True, figure=Figure(),
                                       raise_on_error=False)
        if getattr(answer, "ok", False) or isinstance(answer, dict):
            made += 1
        else:
            logger.error("Could not draw '%s' in this build: %s", key,
                         getattr(answer, "error", "no reason given"))
    return made


def check(manipulator, project) -> Tuple[str, int]:
    """Do the work this build is for, and say what came of it.

    Args:
        manipulator (ScheduleManipulator): The orchestrator every request goes through.
        project (ScheduleProject): What was opened, which may hold no observations.

    Returns:
        Tuple[str, int]: A line to print, and what the process should exit with.
    """
    asked, drawable = offered_by(manipulator)
    said: Dict[str, Any] = {"calculation(s)": len(asked)}
    if not asked:
        return "0 calculation(s): this build offers none at all", 1

    observations = project.get_observations()
    if not observations:
        return f"{len(asked)} calculation(s), nothing opened to run them on", 0

    said["calculated"] = calculated(manipulator, project, asked)
    said["drawn"] = drawn(manipulator, observations[0], drawable)
    line = ", ".join(f"{count} {name}" for name, count in said.items())
    wrong = [name for name in ("calculated", "drawn") if not said[name]]
    return (line if not wrong else f"{line}: nothing {' or '.join(wrong)}",
            1 if wrong else 0)
