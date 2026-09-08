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


from pastrocore.formats.cfx import read_cfx, write_cfx
from pastrocore.super.schedule_format import ScheduleFormat


class ScheduleCFX(ScheduleFormat):
    """Writing a schedule as CFX, and saying what correlation still has to add.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "cfx"

    SUFFIX = ".cfx"
    LABEL = "CFX"

    #: Added to what every format's report carries.
    COMBINED_NAMES = ScheduleFormat.COMBINED_NAMES + ("spacecraft",)

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

    def _cfx_import(self, obj, attributes):
        """Read a CFX file into the project (V5)."""
        return self._read_one(obj, attributes, read_cfx, "CFX")

