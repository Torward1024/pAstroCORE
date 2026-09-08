# super/schedule_format.py
"""What writing a schedule out and reading one back have in common, written once.

`ScheduleVEX` and `ScheduleCFX` are one `Super` per format, and they should be: one format is
fifteen blocks of nested definitions and the other is flat sections, and neither has anything
to teach the other about its own syntax. What they *do* share is the request they answer -- what
a `path` means, what a project is against one observation, what a report of several files adds
up to, and what it means to read a file into a project.

That part sat in both classes, identically, and this is where it lives instead. The formats
keep their vocabulary; the door keeps its shape.
"""
from pathlib import Path
from typing import Any, Dict, List

from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject


class ScheduleFormat(Super):
    """The request-shaped half of a format: paths, projects, and reports.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.

    Notes:
        - No handler lives here. MSB resolves `_<operation>_<method>` on the instance, and the
          operations are the formats' own -- so a subclass declares `_vex_export` or
          `_cfx_import` and inherits everything underneath it.
    """

    #: What a written file is called when the request does not say. Subclasses set it.
    SUFFIX = ""

    #: The format's name, for messages. Subclasses set it.
    LABEL = ""

    #: The fields of a report that are lists of names, added up across several files by taking
    #: each name once. A subclass with one of its own adds it here rather than to `_combined`.
    COMBINED_NAMES = ("stations", "sources")

    def __init__(self, manipulator):
        super().__init__(manipulator)
        logger.debug("Initialized %s", type(self).__name__)

    def _observations(self, obj: Any) -> List[Observation]:
        """Return the observations a request names, whether it named one or a whole project.

        Raises:
            TypeError: If the request names something that is neither.

        Notes:
            - A project writes one file per observation, because a file in either format is one
              experiment: putting two in a file would be writing something no reader expects.
        """
        if isinstance(obj, Observation):
            return [obj]
        if isinstance(obj, ScheduleProject):
            return [item for item in obj.get_items() if item.isactive]
        raise TypeError(f"A {self.LABEL} file is written for an observation or a project, not "
                        f"{type(obj).__name__}")

    @staticmethod
    def _put(text: str, report: Dict[str, Any], target: Path,
             overwrite: bool) -> Dict[str, Any]:
        """Write one file and return its report with the path in it.

        Raises:
            FileExistsError: If the file is there and `overwrite` is off.
        """
        if target.exists() and not overwrite:
            raise FileExistsError(f"'{target}' is already there")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

        report["path"] = str(target)
        logger.info("Wrote '%s'", target)
        return report

    def _combined(self, written: List[Dict[str, Any]], target: Path) -> Dict[str, Any]:
        """Return one report over several files, in the shape a single file's report has.

        Notes:
            - Adding up several reports is arithmetic about this operation's own output, so it
              belongs here: a dialog and a command line would otherwise each work it out, and
              differently.
            - `to_complete` is the same list for every file, because it comes from what the
              format needs rather than from what any one observation contains.
        """
        combined: Dict[str, Any] = {"path": str(target), "files": written,
                                    "experiment": f"{len(written)} file(s)",
                                    "scans": sum(one["scans"] for one in written),
                                    "channels": sum(one["channels"] for one in written),
                                    "excluded": [entry for one in written
                                                 for entry in one["excluded"]],
                                    "to_complete": written[0]["to_complete"] if written else []}
        for field in self.COMBINED_NAMES:
            names: List[str] = []
            for one in written:
                names.extend(name for name in one.get(field, []) if name not in names)
            combined[field] = sorted(names)
        return combined

    def _read_one(self, obj: Any, attributes: Dict[str, Any], reader,
                  label: str) -> Dict[str, Any]:
        """Read a schedule file into the project, and say what was left behind.

        Args:
            obj (ScheduleProject): The project the observation is added to.
            attributes: `path`, the file to read. `code` names the observation, the file's own
                experiment code by default.
            reader: The format's reader.
            label (str): The format, for the messages.

        Returns:
            Dict[str, Any]: What came in -- `code`, `stations`, `sources`, `scans`, `channels`
                -- and what did not: `passed_over` names what this model has no way to hold,
                `refused` the scans it would not accept.

        Raises:
            ValueError: If no `path` was given, or nothing usable was in the file.
            TypeError: If `obj` is not a project.

        Notes:
            - **What this model does not hold is read past, not carried** (V6). The hardware and
              the session are the station's and the correlator's; an export leaves those blocks
              empty for them to fill, so importing them would be keeping something nothing here
              can use or check.
            - A scan the model refuses is named rather than forced in.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError(f"No 'path' given; there is no {label} file to read")
        if not isinstance(obj, ScheduleProject):
            raise TypeError(f"A {label} file is read into a project, not into "
                            f"{type(obj).__name__}")

        from pastrocore.formats import build_observation

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
