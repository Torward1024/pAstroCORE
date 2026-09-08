# super/schedule_vex.py
"""VEX as an operation.

`manipulator.vex(obj=observation, method="export", path=...)`. The operation is the format and
the method is what is being done to it, which is why it is a noun where the others are verbs:
writing a VEX file, reading one back and checking one against a parser are three things done to
the same contract, and they belong together rather than scattered across `export`, `load` and
`compute`.

**One `Super` per format.** VEX and CFX share the sentence "a file for a correlator" and nothing
else -- one is fifteen blocks of nested definitions, the other is flat sections -- so there is
nothing for them to inherit from each other, and a single class holding both would only be a
place for the two vocabularies to get mixed up.

The writing itself is in `pastrocore.formats.vex`, which knows the format and nothing about
requests. This is the door: it takes a request, finds what it names, writes the file where it
says, and hands back what the file does not state.
"""
from pathlib import Path
from typing import Any, Dict, List

from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.observation import Observation
from pastrocore.formats.vex import write_vex
from pastrocore.super.schedule_project import ScheduleProject


class ScheduleVEX(Super):
    """Writing a schedule as VEX, and saying what a station still has to add.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "vex"

    #: What a written file is called when the request does not say.
    SUFFIX = ".vex"

    def __init__(self, manipulator):
        super().__init__(manipulator)
        logger.debug("Initialized ScheduleVEX")

    def _observations(self, obj: Any) -> List[Observation]:
        """Return the observations a request names, whether it named one or a whole project.

        Raises:
            TypeError: If the request names something that is neither.

        Notes:
            - A project writes one file per observation, because a VEX file *is* an experiment:
              `$EXPER` names one and `$SCHED` holds its scans. Putting two in a file would be
              writing something no reader expects.
        """
        if isinstance(obj, Observation):
            return [obj]
        if isinstance(obj, ScheduleProject):
            return [item for item in obj.get_items() if item.isactive]
        raise TypeError(f"A VEX file is written for an observation or a project, not "
                        f"{type(obj).__name__}")

    def _vex_export(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write a schedule as VEX 1.5.

        Args:
            obj: The `Observation` to write, or a `ScheduleProject` whose active observations
                are each written to their own file.
            attributes: `path`, the file to write -- or, for a project, the directory to write
                into. `overwrite` (default True) permits replacing a file that is there.

        Returns:
            Dict[str, Any]: The report -- the stations, modes, sources and channels written,
                what was excluded and why, and every block left for a station to complete, with
                `path` saying where it went. A project's report is the same shape, added up,
                and carries `files` as well: one report per observation.

        Raises:
            ValueError: If no `path` was given, or the observation has nothing to write.
            FileExistsError: If the file is there and `overwrite` is off.
            TypeError: If `obj` is neither an observation nor a project.

        Notes:
            - **The report is the point, not a courtesy.** A VEX file this writes is complete in
              shape and partial in content by design, and the caller is told exactly which
              blocks are waiting: the interface shows the list, and a command line prints it.
            - Space telescopes appear under `excluded` rather than being dropped in silence.
              VEX 1.5 has no orbiting station.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is nowhere to write the VEX file")

        overwrite = attributes.get("overwrite", True)
        observations = self._observations(obj)
        target = Path(path)

        if len(observations) == 1 and not target.is_dir():
            return self._write_one(observations[0], target, overwrite)

        target.mkdir(parents=True, exist_ok=True)
        written = []
        for observation in observations:
            code = observation.get_observation_code() or observation.name
            written.append(self._write_one(
                observation, target / f"{code}{self.SUFFIX}", overwrite))
        return self._combined(written, target)

    @staticmethod
    def _combined(written: List[Dict[str, Any]], target: Path) -> Dict[str, Any]:
        """Return one report over several files, in the shape a single file's report has.

        Notes:
            - Adding up several reports is arithmetic about this operation's own output, so it
              belongs here: a caller showing the answer -- a dialog, a command line, anything
              later -- would otherwise each work it out, and differently.
            - `to_complete` is the same list for every file, because it comes from what the
              format needs rather than from what any one observation contains.
        """
        excluded: List[Dict[str, str]] = []
        stations, modes, sources = [], [], []
        for report in written:
            excluded.extend(report["excluded"])
            for name, into in (("stations", stations), ("modes", modes), ("sources", sources)):
                into.extend(one for one in report[name] if one not in into)
        return {"path": str(target), "files": written,
                "experiment": f"{len(written)} experiment(s)",
                "scans": sum(report["scans"] for report in written),
                "channels": sum(report["channels"] for report in written),
                "stations": sorted(stations), "modes": sorted(modes),
                "sources": sorted(sources), "excluded": excluded,
                "to_complete": written[0]["to_complete"] if written else []}

    def _write_one(self, observation: Observation, target: Path,
                   overwrite: bool) -> Dict[str, Any]:
        """Write one observation to one file, and return its report with the path in it."""
        if target.exists() and not overwrite:
            raise FileExistsError(f"'{target}' is already there")

        text, report = write_vex(observation)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

        report["path"] = str(target)
        logger.info("Wrote '%s' for observation '%s'", target, observation.name)
        return report
