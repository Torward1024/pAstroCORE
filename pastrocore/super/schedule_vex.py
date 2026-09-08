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
from typing import Any, Dict


from pastrocore.formats.vex import read_vex, write_vex
from pastrocore.super.schedule_format import ScheduleFormat


class ScheduleVEX(ScheduleFormat):
    """Writing a schedule as VEX, and saying what a station still has to add.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "vex"

    SUFFIX = ".vex"
    LABEL = "VEX"

    #: Added to what every format's report carries.
    COMBINED_NAMES = ScheduleFormat.COMBINED_NAMES + ("modes",)

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

        alone = len(observations) == 1 and not target.is_dir()
        if not alone:
            target.mkdir(parents=True, exist_ok=True)

        written = []
        for observation in observations:
            code = observation.get_observation_code() or observation.name
            text, report = write_vex(observation)
            written.append(self._put(
                text, report, target if alone else target / f"{code}{self.SUFFIX}", overwrite))
        return written[0] if alone else self._combined(written, target)

    def _vex_import(self, obj, attributes):
        """Read a VEX file into the project (V5)."""
        return self._read_one(obj, attributes, read_vex, "VEX")
