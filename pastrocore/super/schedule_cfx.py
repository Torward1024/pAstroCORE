# super/schedule_cfx.py
"""CFX as an operation.

`manipulator.cfx(obj=observation, method="export", path=...)`, alongside `vex`. One `Super` per
format, named after the format, for the reason the VEX one states: writing a file, reading one
back and checking one are three things done to the same contract.

The difference from VEX is worth stating, because it is why this format exists here at all:
**a space telescope is an ordinary station with an orbit file**, so nothing has to be excluded.
The other difference is that a CFX file is one frequency setup rather than one experiment, so
an observation using two bands writes two files.
"""
from pathlib import Path
from typing import Any, Dict, List

from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.observation import Observation
from pastrocore.formats.cfx import read_cfx, write_cfx
from pastrocore.super.schedule_project import ScheduleProject


class ScheduleCFX(Super):
    """Writing a schedule as CFX, and saying what correlation still has to add.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "cfx"

    #: What a written file is called when the request does not say.
    SUFFIX = ".cfx"

    def __init__(self, manipulator):
        super().__init__(manipulator)
        logger.debug("Initialized ScheduleCFX")

    def _observations(self, obj: Any) -> List[Observation]:
        """Return the observations a request names, whether it named one or a whole project."""
        if isinstance(obj, Observation):
            return [obj]
        if isinstance(obj, ScheduleProject):
            return [item for item in obj.get_items() if item.isactive]
        raise TypeError(f"A CFX file is written for an observation or a project, not "
                        f"{type(obj).__name__}")

    def _cfx_export(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write a schedule as CFX, one file per frequency setup.

        Args:
            obj: The `Observation` to write, or a `ScheduleProject` whose active observations
                are all written.
            attributes: `path`, the file to write -- or the directory to write into, which is
                what a project, or an observation using more than one band, needs.
                `overwrite` (default True) permits replacing a file that is there.

        Returns:
            Dict[str, Any]: The report -- stations, spacecraft, sources and channels written,
                what was excluded and why, and everything left to be completed during
                correlation, with `path` saying where it went. More than one file adds `files`,
                one report each.

        Raises:
            ValueError: If no `path` was given, or the observation has nothing to write.
            FileExistsError: If a file is there and `overwrite` is off.
            TypeError: If `obj` is neither an observation nor a project.

        Notes:
            - **A file is named for its band when there is more than one**, because a CFX file
              is a frequency setup: the examples this was written against are one experiment in
              C band and in K band, as two files.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is nowhere to write the CFX file")

        overwrite = attributes.get("overwrite", True)
        observations = self._observations(obj)
        target = Path(path)

        written: List[Dict[str, Any]] = []
        for observation in observations:
            code = observation.get_observation_code() or observation.name
            files = write_cfx(observation)
            for mode, text, report in files:
                if len(observations) == 1 and len(files) == 1 and not target.is_dir():
                    where = target
                else:
                    target.mkdir(parents=True, exist_ok=True)
                    stem = code if len(files) == 1 else f"{code}_{mode.name}"
                    where = target / f"{stem}{self.SUFFIX}"
                written.append(self._put(text, report, where, overwrite))

        if len(written) == 1:
            return written[0]
        return self._combined(written, target)

    @staticmethod
    def _put(text: str, report: Dict[str, Any], target: Path,
             overwrite: bool) -> Dict[str, Any]:
        """Write one file and return its report with the path in it."""
        if target.exists() and not overwrite:
            raise FileExistsError(f"'{target}' is already there")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

        report["path"] = str(target)
        logger.info("Wrote '%s'", target)
        return report

    @staticmethod
    def _combined(written: List[Dict[str, Any]], target: Path) -> Dict[str, Any]:
        """Return one report over several files, in the shape a single file's report has.

        Notes:
            - Adding up several reports is arithmetic about this operation's own output, so a
              dialog and a command line do not each work it out, and differently.
        """
        excluded: List[Dict[str, str]] = []
        stations, spacecraft, sources = [], [], []
        for report in written:
            excluded.extend(report["excluded"])
            for name, into in (("stations", stations), ("spacecraft", spacecraft),
                               ("sources", sources)):
                into.extend(one for one in report[name] if one not in into)
        return {"path": str(target), "files": written,
                "experiment": f"{len(written)} file(s)",
                "mode": ", ".join(report["mode"] for report in written),
                "scans": sum(report["scans"] for report in written),
                "channels": sum(report["channels"] for report in written),
                "stations": sorted(stations), "spacecraft": sorted(spacecraft),
                "sources": sorted(sources), "excluded": excluded,
                "to_complete": written[0]["to_complete"] if written else []}

    def _cfx_import(self, obj, attributes):
        """Read a CFX file into the project (V5)."""
        return self._read_one(obj, attributes, read_cfx, "CFX")

    def _read_one(self, obj, attributes, reader, label):
        """Read a schedule file into the project, and say what was left behind.

        Args:
            obj (ScheduleProject): The project the observation is added to.
            attributes: `path`, the file to read. `code` names the observation, the file's own
                experiment code by default.
            reader: The format's reader.
            label (str): The format, for the messages.

        Returns:
            Dict[str, Any]: What came in -- `code`, `stations`, `sources`, `scans`, `channels`
                -- and what did not: `passed_over` names the blocks this model has no way to
                hold, `refused` the scans it would not accept.

        Raises:
            ValueError: If no `path` was given, or nothing usable was in the file.
            TypeError: If `obj` is not a project.

        Notes:
            - **What this model does not hold is read past, not carried** (V6). The hardware
              and the session are the station's and the correlator's; an export leaves those
              blocks empty for them to fill, so importing them would be keeping something
              nothing here can use or check.
            - A scan the model refuses is named rather than forced in. Two sub-arrays observing
              at once in different bands is an ordinary thing to do and something the rule
              about overlapping active scans cannot say, so `re03fr.vex` loses half its scans
              and says so.
        """
        from pastrocore.formats import build_observation

        path = attributes.get("path")
        if not path:
            raise ValueError(f"No 'path' given; there is no {label} file to read")
        if not isinstance(obj, ScheduleProject):
            raise TypeError(f"A {label} file is read into a project, not into "
                            f"{type(obj).__name__}")

        source = Path(path)
        read = reader(source.read_text(encoding="utf-8", errors="replace"), source=str(source))
        observation, refused = build_observation(read, code=attributes.get("code"))
        obj.add_item(observation)

        report = {
            "path": str(source), "format": label.lower(), "code": observation.code,
            "stations": [t.get_code() for t in observation.get_telescopes().get_items()],
            "sources": [s.name for s in observation.get_sources().get_items()],
            "scans": len(observation.get_scans().get_items()),
            "channels": sum(band.get_channel_count()
                            for band in observation.get_frequencies().get_items()),
            "passed_over": read.get("passed_over", []),
            "refused": refused,
        }
        logger.info("Read '%s' into observation '%s': %s scan(s), %s refused, %s passed over",
                    source, observation.code, report["scans"], len(refused),
                    len(report["passed_over"]))
        return report
