# super/schedule_data.py
"""Getting data out of a project, as an operation rather than as a dialog.

The export the interface offers -- results as tab-separated text, plots as pictures -- lived
inside a `QDialog` and a `QThread`. Of the 312 lines there, only 60 touched Qt: **252 were logic
a command-line version would have had to write again and a server could not reach at all**.
They are here now, where a request reaches them like any other operation.

The interface keeps what is genuinely interface: the file chooser, the lists of what to export
and the progress bar. What it passes in is a pair of callables -- one to report progress, one to
ask whether to stop -- and that is the whole seam. Nothing here knows about signals, threads or
windows.

Deliberately not the place for VEX, SKED or CFX. Those share nothing with this but the word
export: this writes what a person wants to look at, they write a contract with software at a
correlator. Mixing them would give this module their vocabulary and give them this module's
tolerance for "close enough".
"""
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import polars as pl
from astropy.time import Time
from msb_arch import Loader, Persistence
from msb_arch.utils.logging_setup import logger

from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.result_store import json_safe
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject

#: Results that can be drawn. Anything else is exported as text only.

#: What `inspect(method="history")` adds to a journal row for showing it, and a session
#: file does not hold: a saved session is the requests as they were recorded.
SHOWN_ONLY = ("where", "reads", "call")

#: Filenames that do not follow from the calculation's name.
FILE_PREFIXES = {"Beam Pattern": "Beam_Pattern", "Mollweide Tracks": "Mollweide"}


class DataQuestions:
    """What a project's stored results hold, asked rather than written anywhere.

    Handlers of `inspect`: `ScheduleInspector` inherits them and answers
    `inspect(method="available")`, `"distinct"`, `"scan_times"` and `"unsaved"`. They were `export`
    until 1.13.0, beside what writes files, so a session could not tell the two apart by name.
    """

    def _inspect_scan_times(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List the scans a result covers for one source, with the time each starts.

        Args:
            obj (Observation): The observation to read.
            attributes: `key`, the result to look in, and optionally any column the result has
                -- `source_name`, `target_code` -- to narrow
                it to one source. Without a source the answer covers every scan the result
                holds, which is what a plot showing all of them wants.

        Returns:
            List[Dict[str, Any]]: `[{"scan_name": str, "start": str}]`, sorted by time, with
                the start as an ISOT string. Empty when there is no such data, which is an
                answer rather than an error -- a source may simply not be observed.

        Notes:
            - Here rather than in each visualization tab, which otherwise each need polars
              to filter and astropy to make an MJD readable.
            - A question, so `inspect` answers it: the interface fills a list with it and a
              script decides what to plot.
        """
        key = attributes.get("key")
        if not key:
            raise ValueError("A 'key' is needed to list scan times")

        stored = obj.get_calculated_data_by_key(key) or {}
        frame = stored.get("data")
        if not isinstance(frame, pl.DataFrame) or frame.is_empty():
            logger.debug("No '%s' data to list scans from", key)
            return []

        expected = CalculatedDataStructure.get_columns(key)
        if expected:
            missing = [column for column in expected if column not in frame.columns]
            if missing:
                logger.error("Result '%s' is missing columns %s", key, missing)
                return []

        # Most results call the moment "time"; `time_on_source` records an interval and
        # calls its beginning "start". The column is found rather than assumed.
        moment = next((column for column in ("time", "start") if column in frame.columns), None)
        if moment is None:
            logger.debug("Result '%s' records no time", key)
            return []

        # Narrowed by whatever the caller named that the result has a column for, so a
        # new kind of result needs no case here.
        narrowing = {column: value for column, value in attributes.items()
                     if column in frame.columns and value is not None}
        filtered = frame
        for column, value in narrowing.items():
            filtered = filtered.filter(pl.col(column) == value)
        if filtered.is_empty():
            logger.debug("No '%s' data for %s", key, narrowing or "any")
            return []

        starts = (filtered.group_by("scan_name")
                  .agg(moment=pl.col(moment).first()).sort("moment"))
        return [{"scan_name": row["scan_name"], "start": Time(row["moment"], format="mjd").isot}
                for row in starts.iter_rows(named=True)]

    def _inspect_distinct(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, List[Any]]:
        """List the distinct values a result holds in the columns asked for.

        Args:
            obj (Observation): The observation to read.
            attributes: `key`, the result to look in, and `columns`, the column names.

        Returns:
            Dict[str, List[Any]]: `{column: sorted values}`. A column the result does not have
                comes back empty rather than missing, so a caller filling a list needs no
                second check.

        Notes:
            - The other question a visualization tab asks: which sources are in this result,
              which baselines, which telescopes.
        """
        key = attributes.get("key")
        columns = attributes.get("columns") or []
        if not key or not columns:
            raise ValueError("Both 'key' and 'columns' are needed to list distinct values")

        stored = obj.get_calculated_data_by_key(key) or {}
        frame = stored.get("data")
        if not isinstance(frame, pl.DataFrame) or frame.is_empty():
            logger.debug("No '%s' data to list values from", key)
            return {column: [] for column in columns}

        expected = CalculatedDataStructure.get_columns(key)
        if expected:
            missing = [column for column in expected if column not in frame.columns]
            if missing:
                logger.error("Result '%s' is missing columns %s", key, missing)
                return {column: [] for column in columns}

        found = {}
        for column in columns:
            if column not in frame.columns:
                logger.debug("Result '%s' has no column '%s'", key, column)
                found[column] = []
                continue
            found[column] = sorted(frame[column].unique().to_list())
        return found

    def _inspect_available(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """List the results this observation actually holds data for.

        Args:
            obj (Observation): The observation to ask.
            attributes: `keys`, to narrow the question; every result by default.

        Returns:
            List[str]: Sorted store keys whose result has at least one row.

        Notes:
            - What the visualize dialog asks to decide what it can offer.
            - Counted through a lazy scan, so a parquet answers from its footer and the rows
              are never read.
        """
        results = obj.calculated_data
        keys = attributes.get("keys") or (list(results.keys()) if hasattr(results, "keys") else [])

        available = []
        unreadable = []
        for key in keys:
            try:
                view = obj.scan_calculated_data(key)
                if view is None:
                    continue
                if view.select(pl.len()).collect().item() > 0:
                    available.append(key)
            except Exception as e:                      # noqa: BLE001 - reported below
                unreadable.append(f"{key}: {e}")

        # At warning, with the traceback: this answer is what the visualize dialog
        # offers, so a key that cannot be read is a plot that disappears.
        if unreadable:
            logger.warning("Cannot tell whether %s of %s result(s) hold anything: %s",
                           len(unreadable), len(keys), "; ".join(unreadable[:5]))
        return sorted(available)

    def _inspect_unsaved(self, obj: Any, attributes: Dict[str, Any]) -> int:
        """Return how many results this session holds that the project directory does not.

        Args:
            obj (ScheduleProject): The project to ask about.
            attributes: Ignored.

        Returns:
            int: The count. Zero for a project saved since its last calculation.

        Notes:
            - A request rather than a method call: a command line ending a session asks it
              the same way.
        """
        return obj.unsaved_results() if hasattr(obj, "unsaved_results") else 0


class ScheduleData(DataQuestions, Persistence, Loader):
    """Reading results out of a project and writing them somewhere else.

    Notes:
        - `save` and `load` are MSB's: the built-in writes atomically, refuses an existing
          file when told to, and raises the framework's own errors.
        - What stays here is about this model rather than about files -- a project is a
          directory, and a telescope is read back as the kind the file says.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "export"

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.debug("Initialized ScheduleData")

    def _export(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write a project's results out as text, pictures, or both.

        Args:
            obj: An `Observation`, or a `ScheduleProject` whose observations are all exported.
            attributes: `calc_types` names the calculations to write and `export_path` says
                where; `export_data` and `export_vis` choose text, pictures or both, and
                `units` applies to the plots that have any. Optionally `progress`, called with
                a percentage and a message, and `cancelled`, called to ask whether to stop --
                the two things a long operation owes its caller, expressed without knowing what
                kind of caller it is.

        Returns:
            Dict[str, Any]: `{"written": [...], "cancelled": bool}`, listing the files
                produced. A caller that wants to know what it got does not have to go looking
                on disk for it.

        Raises:
            ValueError: If no `export_path` was given, since there is then nowhere to write.
        """
        targets = self._targets(obj)
        calc_types = attributes.get("calc_types") or []
        export_data = attributes.get("export_data", True)
        export_vis = attributes.get("export_vis", False)
        export_path = attributes.get("export_path")
        units = attributes.get("units", "wavelengths")
        report = attributes.get("progress") or (lambda percent, message: None)
        cancelled = attributes.get("cancelled") or (lambda: False)

        if not export_path:
            raise ValueError("No 'export_path' given; there is nowhere to write")

        # What can be drawn and what each plot takes are both asked of the visualizer,
        # so a new plot is exported the moment it exists.
        drawable = self._manipulator.describe_operations("visualize").get("visualize", {}) \
            if export_vis else {}

        steps_per_target = len(calc_types) * ((1 if export_data else 0) + (1 if export_vis else 0))
        total_steps = len(targets) * steps_per_target if steps_per_target > 0 else 1
        current_step = 0
        written: List[str] = []

        for target in targets:
            if cancelled():
                logger.info("Export cancelled before '%s'", target.code)
                return {"written": written, "cancelled": True}

            obs_code = target.code
            report(int(current_step / total_steps * 100), f"Exporting for {obs_code}...")

            sources = list(target.get_sources()._items.keys())
            telescopes = [telescope.get_code() for telescope in target.get_telescopes()._items.values()]
            scans = [scan.name for scan in target.get_scans().get_items()]
            frequencies = [if_obj.frequency for if_obj in target.get_frequencies().get_items()]
            baselines = [f"{t1}-{t2}" for i, t1 in enumerate(telescopes) for t2 in telescopes[i + 1:]]

            for calc_type in calc_types:
                if cancelled():
                    logger.info("Export cancelled during '%s'", obs_code)
                    return {"written": written, "cancelled": True}

                # A calculation is named here by its label, and for one of them the
                # key that spells is the handler's name. The schema knows both.
                key = CalculatedDataStructure.store_key_for(
                    calc_type.lower().replace(" ", "_").replace("/", "_"))
                data = target.get_calculated_data_by_key(key).get("data", {})
                if not isinstance(data, pl.DataFrame):
                    logger.debug("No data for %s in %s, skipping", calc_type, obs_code)
                    continue

                file_prefix = FILE_PREFIXES.get(calc_type,
                                                calc_type.replace(" ", "_").replace("/", "_"))

                if export_data:
                    txt_path = os.path.join(export_path, f"{obs_code}_{file_prefix}.txt")
                    self._write_text(data, calc_type, txt_path, obs_code, target)
                    written.append(txt_path)
                    current_step += 1
                    report(int(current_step / total_steps * 100),
                           f"Exported data for {calc_type} in {obs_code}")

                if export_vis:
                    if key not in drawable:
                        logger.debug("Nothing draws '%s'; exporting its data only", calc_type)
                        continue
                    # Per source is a fact about the columns: one naming `source_name`
                    # is drawn once per source, one that does not is drawn once.
                    columns = set(CalculatedDataStructure.entry_for(key).get("columns") or [])
                    per_source = sources if "source_name" in columns else [None]
                    accepts = set(drawable[key].get("accepts") or ())
                    for source_name in per_source:
                        suffix = f"_{source_name}" if source_name else ""
                        png_path = os.path.join(
                            export_path, f"{obs_code}_{file_prefix}{suffix}.png")
                        # Offered, not assigned: everything the observation can say
                        # about itself, of which each plot takes what it reads.
                        offered = {"source_name": source_name, "sources": sources,
                                   "telescopes": telescopes, "scans": scans,
                                   "frequencies": frequencies, "baselines": baselines,
                                   "units": units}
                        try:
                            self._manipulator.visualize(
                                obj=target, plot_type=key, output_file=png_path, dpi=76,
                                **{name: value for name, value in offered.items()
                                   if name in accepts})
                        except Exception as e:
                            raise ValueError(
                                f"Visualization export failed for {calc_type} in {obs_code}: {str(e)}")
                        # Reported because it is there: a plot with nothing to draw
                        # writes no file, and naming one hands back a path to nothing.
                        if not os.path.isfile(png_path):
                            logger.warning("Nothing was drawn for %s in %s, so no file was "
                                           "written", calc_type, obs_code)
                            continue
                        written.append(png_path)
                    current_step += 1
                    report(int(current_step / total_steps * 100),
                           f"Exported vis for {calc_type} in {obs_code}")

            # An export walks every result of every observation, so without this it ends
            # holding the whole project. Only what is already on disk is released.
            if hasattr(target.calculated_data, "release"):
                target.calculated_data.release()

        logger.info("Exported %s file(s) to '%s'", len(written), export_path)
        return {"written": written, "cancelled": False}

    def _save_scheduleproject(self, obj: 'ScheduleProject', attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Save a project, which is a directory rather than a file.

        Args:
            obj (ScheduleProject): The project.
            attributes: `path`, the project directory to write; `progress`, optionally, called
                with a percentage and what is being written, as a calculation's is.

        Returns:
            Dict[str, Any]: `{"path": str}`.

        Notes:
            - A facade, not a second implementation: the model still serialises itself.
            - What it buys is that a save is a request like any other, so the journal records
              it and a replay performs it.
        """
        path = self._destination(attributes)
        obj.save(path, progress=attributes.get("progress"))
        return {"path": path}

    def _load_scheduleproject(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Load a project from its directory.

        Args:
            obj: The project the request was made on. Its contents are not read -- a load has
                nothing to operate on yet, which is the one place this surface fits the request
                model awkwardly rather than naturally.
            attributes: `path`, the project directory to read.

        Returns:
            ScheduleProject: The project. MSB's own `load` returns the object it read, and
                a specialisation that returned a wrapper instead would mean a caller had to know
                which of the two it had reached.
        """
        path = self._destination(attributes, verb="load")
        project = ScheduleProject.open(path)
        return project

    def _load_telescopes(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Read a telescope, choosing its kind from the file rather than from the caller.

        Args:
            obj (Telescopes): The container it is being imported into.
            attributes: `path`, the file to read.

        Returns:
            Dict[str, Any]: `{"object": Telescope | SpaceTelescope}`.

        Notes:
            - A ground station and a spacecraft share a file format and are told apart by
              what is in it, which the general `_load` cannot do.
        """
        from pastrocore.base.spacetelescope import SpaceTelescope
        from pastrocore.base.telescope import Telescope

        path = self._destination(attributes, verb="load")
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))

        # One handler for importing a telescope into a container and for reading the
        # container back: MSB resolves on the type, and both are `Telescopes`.
        if "items" in data:
            restored = type(obj).from_dict(data)
            logger.info("Read %s from '%s'", type(restored).__name__, path)
            return restored

        kind = SpaceTelescope if data.get("type") == "SpaceTelescope" else Telescope
        restored = kind.from_dict(data)
        logger.info("Read %s '%s' from '%s'", kind.__name__, restored.get_code(), path)
        return restored

    @staticmethod
    def _destination(attributes: Dict[str, Any], verb: str = "save") -> str:
        """Return the path a request names, refusing to guess one.

        Raises:
            ValueError: If none was given. There is no sensible default for where a user's
                files live.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError(f"No 'path' given; there is nowhere to {verb}")
        return path

    def _export_generation_plan(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write a generation plan to a file (O1).

        Args:
            obj: Whatever the request was made on; a plan belongs to nothing in the model.
            attributes: `path`, where to write; `plan`, what `GenerationPlan.to_dict` wrote.

        Returns:
            Dict[str, Any]: `{"path": str}`.

        Notes:
            - **The whole plan, collections included.** What the dialog used to save was the timing
              and not what it was for, so loading one left a pattern with nothing to point it at.
        """
        from pastrocore.base.generation_plan import GenerationPlan

        path = self._destination(attributes)
        # Whatever shape it arrives in: the window sends the collections it is showing, a caller
        # replaying a session sends their data.
        text = json.dumps(json_safe(GenerationPlan.of(attributes.get("plan")).to_dict()),
                          indent=4, allow_nan=False)
        target = Path(path)
        partial = target.with_name(target.name + ".partial")
        try:
            partial.write_text(text, encoding="utf-8")
            os.replace(partial, target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        logger.info("Wrote a generation plan to '%s'", path)
        return {"path": path}

    def _load_generation_plan(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Read a generation plan back.

        Args:
            obj: Whatever the request was made on.
            attributes: `path`, the file to read.

        Returns:
            Dict[str, Any]: The plan's fields, holding the sources, stations and bands themselves,
                so that whoever asked shows them rather than reading them out of data.
        """
        from pastrocore.base.generation_plan import GenerationPlan

        path = self._destination(attributes, verb="load")
        held = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(held, dict):
            raise ValueError(f"'{path}' does not hold a generation plan")
        logger.info("Read a generation plan from '%s'", path)
        return GenerationPlan.of(held).as_mapping()

    @staticmethod
    def _targets(obj: Any) -> List[Observation]:
        """Return the observations an export covers.

        Notes:
            - What a project holds is the project's answer; which shapes of request are
              accepted is this operation's.
        """
        if isinstance(obj, ScheduleProject):
            return obj.get_observations()
        if isinstance(obj, (list, tuple)):
            return list(obj)
        return [obj]

    def _write_text(self, data: pl.DataFrame, calc_type: str, path: str, obs_code: str,
                    target: Observation) -> None:
        """Write one calculated result to a tab-separated file.

        Args:
            data (pl.DataFrame): The result.
            calc_type (str): The calculation's display name, as the interface spells it.
            path (str): Where to write.
            obs_code (str): The observation's code, for messages.
            target (Observation): The observation, whose metadata some results need.

        Notes:
            - Times in ISOT, because a person reads the file. NaN is written as it stands:
              an empty field would read as zero.
            - `mollweide_tracks` appends its source coordinates as rows whose time is
              `-----`.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            key = CalculatedDataStructure.store_key_for(
                calc_type.lower().replace(" ", "_").replace("/", "_"))

            expected_columns = CalculatedDataStructure.get_columns(key)
            if expected_columns is None:
                logger.error("Unsupported calc_type for TXT export: %s", calc_type)
                raise ValueError(f"Unsupported calc_type for TXT export: {calc_type}")
            if not all(col in data.columns for col in expected_columns):
                missing_cols = [col for col in expected_columns if col not in data.columns]
                logger.error("Invalid DataFrame structure for key '%s' in observation '%s': missing columns %s", key, obs_code, missing_cols)
                raise ValueError(f"Invalid DataFrame structure for key '{key}': missing columns {missing_cols}")

            df_out = data.clone()
            converters = CalculatedDataStructure.get_converters(key) or {}

            for col in ["time", "start", "end"]:
                if col in df_out.columns:
                    try:
                        df_out = df_out.with_columns(
                            pl.col(col).map_elements(
                                lambda x: Time(x, format='mjd', scale='utc').isot if isinstance(x, (int, float)) and x is not None else x,
                                return_dtype=pl.String
                            )
                        )
                    except Exception as e:
                        logger.error("Failed to convert column '%s' to ISOT in key '%s' of observation '%s': %s", col, key, obs_code, str(e))
                        raise

            for col, converter in converters.items():
                if col in df_out.columns and col not in ["time", "start", "end"]:
                    try:
                        df_out = df_out.with_columns(pl.col(col).map_elements(converter, return_dtype=pl.Float64))
                    except Exception as e:
                        logger.error("Failed to apply converter for column '%s' in key '%s' of observation '%s': %s", col, key, obs_code, str(e))
                        raise

            if "scan_name" in df_out.columns:
                df_out = df_out.drop("scan_name")
            expected_columns = [col for col in expected_columns if col != "scan_name"]
            df_out = df_out.select(expected_columns)

            if key == "mollweide_tracks":
                sources = target.get_calculated_metadata(key).get("sources", {})
                logger.debug("Processing sources for %s in observation '%s': %s", calc_type, obs_code, sources)

                if not isinstance(sources, dict):
                    logger.error("Invalid sources format in metadata for %s in observation '%s': expected dict, got %s", calc_type, obs_code, type(sources))
                    sources = {}

                source_rows = []
                for src_name, coords in sources.items():
                    try:
                        lon, lat = float(coords[0]), float(coords[1])
                        # Ensure column order matches df_out
                        source_rows.append({"time": "-----", "telescope_code": src_name, "lon": lon, "lat": lat})
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse coordinates for source '%s' in %s, observation '%s': %s", src_name, calc_type, obs_code, str(e))
                        continue

                if source_rows:
                    # Define schema with correct column order to match df_out
                    source_df = pl.DataFrame(source_rows, schema={"time": pl.String, "telescope_code": pl.String, "lon": pl.Float64, "lat": pl.Float64})
                    df_out = pl.concat([df_out, source_df], how="vertical")
                else:
                    logger.warning("No valid sources to append for %s in observation '%s'", calc_type, obs_code)

            df_out.write_csv(path, separator="\t", include_bom=True, null_value="NaN")
            logger.info("Exported data to %s", path)
        except Exception as e:
            logger.error("Failed to export data to %s: %s", path, str(e))
            raise

    def _export_journal(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write this session's requests to a file.

        Args:
            obj: Ignored; the session belongs to the orchestrator.
            attributes: `path`, the file to write; `about`, an object name to narrow it to; or
                `steps`, the rows to write instead of the whole session -- a session cut down to
                what is worth repeating (S1).

        Returns:
            Dict[str, Any]: `{"path": str, "steps": int}`.

        Raises:
            ValueError: If no path was given.

        Notes:
            - A journal entry is plain data -- what was asked, of which object by name -- so
              it leaves the process and holds nothing alive.
            - What comes back replays against whatever project is open then.
            - Cutting a session down changes the file, never the journal.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is nowhere to write the session")

        given = attributes.get("steps")
        if given is not None and not isinstance(given, list):
            raise ValueError("'steps' must be a list of the rows to write")
        steps = (self._manipulator.history(attributes.get("about")) if given is None
                 else [{key: value for key, value in step.items() if key not in SHOWN_ONLY}
                       for step in given])
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Beside the old one and moved over it: a truncated session reads as a short one
        # rather than as a failure.
        partial = target.with_name(target.name + ".partial")
        try:
            partial.write_text(
                json.dumps({"steps": json_safe(steps)}, indent=4, allow_nan=False),
                encoding="utf-8")
            os.replace(partial, target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        logger.info("Wrote a session of %s request(s) to '%s'", len(steps), path)
        return {"path": str(path), "steps": len(steps)}

    def _export_tidy(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Remove this session's scratch directory when nothing in it would be lost.

        Args:
            obj (ScheduleProject): The project being replaced or closed.
            attributes: Ignored.

        Returns:
            Dict[str, Any]: `{"discarded": bool, "held": int}`.

        Notes:
            - A scratch holding results is left where it is, so the next start offers them
              back. Litter is worth clearing; a day of calculation is not.
        """
        held = self._inspect_unsaved(obj, attributes)
        if not hasattr(obj, "discard_scratch_if_empty"):
            return {"discarded": False, "held": held}
        return {"discarded": obj.discard_scratch_if_empty(), "held": held}

    def _export_analysis(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write the answer to an analysis question as a tab-separated file.

        Args:
            obj: The project or observation the question is about.
            attributes: `path`, where to write (required). Either `rows` -- an answer already
                in hand, which is what the tab passes so the file matches what is on screen --
                or `question` plus whatever that question needs (`key`, `columns`, `group_by`,
                `where`, `gaps`, `at_least`), which is what a command line passes.
                `overwrite` (default True).

        Returns:
            Dict[str, Any]: `{"path": str, "rows": int, "columns": [...]}`.

        Raises:
            ValueError: If no `path` was given, or neither `rows` nor `question`.
            FileExistsError: If the file is there and `overwrite` is off.

        Notes:
            - The columns are whatever the answer carries, so a handler that grows a field
              writes it here untold.
            - Tab-separated with a BOM and `NaN` for what is missing, as a result is.
            - The question is asked here, so a command line is one command and the file
              cannot disagree with the screen.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is nowhere to write the analysis")

        rows = attributes.get("rows")
        if rows is None:
            question = attributes.get("question")
            if not question:
                raise ValueError("No 'rows' and no 'question'; there is nothing to write")
            asked = {name: value for name, value in attributes.items()
                     if name not in ("path", "question", "rows", "overwrite")}
            rows = self._manipulator.analyze(obj=obj, method=question, **asked)

        if not rows:
            raise ValueError("The analysis produced nothing; there is nothing to write")

        target = Path(path)
        if target.exists() and not attributes.get("overwrite", True):
            raise FileExistsError(f"'{target}' is already there")
        target.parent.mkdir(parents=True, exist_ok=True)

        columns = list(rows[0])
        frame = pl.DataFrame(
            [{column: row.get(column) for column in columns} for row in rows],
            infer_schema_length=None)
        frame.write_csv(str(target), separator="\t", include_bom=True, null_value="NaN")

        logger.info("Exported %s analysis row(s) to '%s'", frame.height, target)
        return {"path": str(target), "rows": frame.height, "columns": columns}

    #: What a packed project is called, and the name of the model inside it.
    ARCHIVE_SUFFIX = ".pastroz"

    def _export_package(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Pack a project into one file, to send to a colleague or attach to a bug report.

        Args:
            obj (ScheduleProject): The project to pack.
            attributes: `path`, the file to write. `results` (default True) packs the calculated
                results as well as the model; `overwrite` (default False) permits replacing a
                file that is already there.

        Returns:
            Dict[str, Any]: `{"path": str, "files": int, "bytes": int, "results": bool}`.

        Raises:
            ValueError: If no `path` was given.
            FileExistsError: If the file exists and `overwrite` is off.

        Notes:
            - A project is a directory, which is right for working in and wrong for sending.
            - Zip as an exchange format, not as storage: on the working project it saves
              0.6% and makes opening 46x slower.
            - `results=False` writes the model alone, which is what a bug report wants.
              The project is saved first, so what is packed is the project as it is now.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is nowhere to write the package")

        target = Path(path)
        if target.suffix != self.ARCHIVE_SUFFIX:
            target = target.with_suffix(self.ARCHIVE_SUFFIX)
        if target.exists() and not attributes.get("overwrite", False):
            raise FileExistsError(f"'{target}' is already there; pass overwrite=True to replace it")

        with_results = attributes.get("results", True)
        source = Path(tempfile.mkdtemp(prefix="pastrocore_package_")) / "project.pastro"
        # A copy, not a move: this directory is deleted below. And without the results
        # when they are not wanted, rather than copying every parquet in to leave it out.
        obj.to_directory(str(source), as_copy=True, with_results=with_results)

        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
                for item in sorted(source.rglob("*")):
                    if not item.is_file():
                        continue
                    inside = item.relative_to(source)
                    if not with_results and inside.parts[0] == obj.RESULTS_DIRECTORY:
                        continue
                    package.write(item, str(inside))
                    written += 1
        finally:
            shutil.rmtree(source.parent, ignore_errors=True)

        size = target.stat().st_size
        logger.info("Packed project '%s' into '%s': %s file(s), %s bytes%s",
                    obj.name, target, written, size, "" if with_results else ", model only")
        return {"path": str(target), "files": written, "bytes": size, "results": bool(with_results)}

    def _load_package(self, obj: Any, attributes: Dict[str, Any]) -> Any:
        """Unpack a project written by `export(method="package")`.

        Args:
            obj: Ignored; a package carries its own project.
            attributes: `path`, the package to read. `into`, the directory to unpack it to --
                a temporary one when not given, which is enough to open it and look.

        Returns:
            ScheduleProject: The project, with its results where it left them.

        Raises:
            IOError: If the file is not a package -- which is said plainly, because the other
                way to find out is a project that opens with everything missing.

        Notes:
            - Refuses an entry that would land outside the directory being unpacked into: a
              zip is a file from somewhere else.
        """
        path = attributes.get("path")
        if not path:
            raise ValueError("No 'path' given; there is no package to read")

        source = Path(path)
        if not source.is_file():
            raise IOError(f"'{source}' is not a file")
        if not zipfile.is_zipfile(source):
            raise IOError(f"'{source}' is not a pAstroCORE package")

        into = Path(attributes["into"]) if attributes.get("into") else Path(
            tempfile.mkdtemp(prefix="pastrocore_opened_"))
        into.mkdir(parents=True, exist_ok=True)
        root = into.resolve()

        with zipfile.ZipFile(source) as package:
            names = package.namelist()
            if ScheduleProject.MODEL_FILE not in names:
                raise IOError(f"'{source}' holds no {ScheduleProject.MODEL_FILE}; "
                              f"it is a zip, but not a project")
            for name in names:
                landing = (root / name).resolve()
                if not landing.is_relative_to(root):
                    raise IOError(f"'{source}' holds an entry that would be written outside "
                                  f"the directory it is unpacked into: '{name}'")
            package.extractall(root)

        project = ScheduleProject.open(str(root))
        logger.info("Opened package '%s' as project '%s' in '%s'", source, project.name, root)
        return project
