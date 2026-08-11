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
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl
from astropy.time import Time
from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.result_store import json_safe
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject

#: Results that can be drawn. Anything else is exported as text only.
VISUALIZABLE = ("uv_coverage", "baseline_projections", "time_on_source", "sun_angles",
                "az_el", "mollweide_tracks", "beam_pattern", "parallactic_angle")

#: Filenames that do not follow from the calculation's name.
FILE_PREFIXES = {"Beam Pattern": "Beam_Pattern", "Mollweide Tracks": "Mollweide"}


class ScheduleData(Super):
    """Reading results out of a project and writing them somewhere else.

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

                key = calc_type.lower().replace(" ", "_").replace("/", "_")
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
                    if key not in VISUALIZABLE:
                        logger.debug("Skipping visualization for %s as it is not visualizable", calc_type)
                        continue
                    for source_name in sources:
                        png_path = os.path.join(
                            export_path, f"{obs_code}_{file_prefix}_{source_name}.png")
                        try:
                            self.manipulator.visualize(
                                obj=target, plot_type=key, output_file=png_path, dpi=76,
                                source_name=source_name,
                                baselines=baselines if key in ("uv_coverage", "baseline_projections") else [],
                                telescopes=telescopes if key in ("sun_angles", "az_el", "time_on_source",
                                                                 "beam_pattern", "parallactic_angle") else [],
                                scans=scans,
                                frequencies=frequencies if key in ("uv_coverage", "baseline_projections",
                                                                   "beam_pattern") else [],
                                units=units if key in ("uv_coverage", "baseline_projections") else None)
                        except Exception as e:
                            raise ValueError(
                                f"Visualization export failed for {calc_type} in {obs_code}: {str(e)}")
                        written.append(png_path)
                    current_step += 1
                    report(int(current_step / total_steps * 100),
                           f"Exported vis for {calc_type} in {obs_code}")

            # Every result read here stays in memory, and an export walks all of them for every
            # observation. Without this the exporter ends holding the entire project -- which
            # for a year of observing is the whole reason the results moved out of the model
            # file. Only results already on disk are released; anything not yet written has
            # nowhere to be read back from and is left alone.
            if hasattr(target.calculated_data, "release"):
                target.calculated_data.release()

        logger.info("Exported %s file(s) to '%s'", len(written), export_path)
        return {"written": written, "cancelled": False}

    def _save(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write any serialisable object to a file.

        Args:
            obj (Serializable): Anything the model can turn into a dictionary -- a telescope, a
                source, a container of scans.
            attributes: `path`, the file to write.

        Returns:
            Dict[str, Any]: `{"path": str}`.

        Raises:
            TypeError: If the object cannot serialise itself.
            ValueError: If no path was given.

        Notes:
            - The general case. A project is not one, because a project is a directory rather
              than a file, and it gets `_save_scheduleproject` -- which MSB reaches on its own,
              since a handler named for the object's type wins over this one. Nothing here has
              to know that branch exists.
        """
        path = self._destination(attributes)
        if not hasattr(obj, "to_dict"):
            raise TypeError(f"{type(obj).__name__} cannot be written to a file: it has no to_dict")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(json_safe(obj.to_dict()), indent=4, allow_nan=False),
                              encoding="utf-8")
        logger.info("Wrote %s to '%s'", type(obj).__name__, path)
        return {"path": path}

    def _save_scheduleproject(self, obj: 'ScheduleProject', attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Save a project, which is a directory rather than a file.

        Args:
            obj (ScheduleProject): The project.
            attributes: `path`, the project directory to write.

        Returns:
            Dict[str, Any]: `{"path": str}`.

        Notes:
            - A facade, not a second implementation: the model still serialises itself and this
              only puts an operation in front of it. What that buys is uniformity -- a caller
              mapping commands to requests needs no special case for save, the journal records
              the save that ended a session as well as the calculations in it, and a server
              needs no endpoint outside the request model.
            - Which is why it matters more than it looks: a journal that replays every
              calculation and then saves nothing is a rehearsal, not a pipeline.
        """
        path = self._destination(attributes)
        obj.save(path)
        return {"path": path}

    def _load(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file back into an object of the same kind as the one asked.

        Args:
            obj (Serializable): An object of the type to reconstruct. A request operates on
                something, and here that something says what to build.
            attributes: `path`, the file to read, and optionally `kind` -- the class to build,
                for importing something that does not exist yet.

        Returns:
            Dict[str, Any]: `{"object": ...}`.

        Raises:
            TypeError: If the type cannot reconstruct itself from a dictionary.
            ValueError: If no path was given.
        """
        path = self._destination(attributes, verb="load")
        # The object says what to build, unless the caller says otherwise -- which it must
        # when importing something that does not exist yet and so cannot be operated on.
        kind = attributes.get("kind") or type(obj)
        if not hasattr(kind, "from_dict"):
            raise TypeError(f"{kind.__name__} cannot be read from a file: it has no from_dict")

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        restored = kind.from_dict(data)
        logger.info("Read %s from '%s'", kind.__name__, path)
        return {"object": restored}

    def _load_scheduleproject(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Load a project from its directory.

        Args:
            obj: The project the request was made on. Its contents are not read -- a load has
                nothing to operate on yet, which is the one place this surface fits the request
                model awkwardly rather than naturally.
            attributes: `path`, the project directory to read.

        Returns:
            Dict[str, Any]: `{"object": ScheduleProject, "project": ScheduleProject}`. Both
                names, because "object" is what the general case returns and "project" is what
                a caller working with projects will look for.
        """
        path = self._destination(attributes, verb="load")
        project = ScheduleProject.open(path)
        return {"object": project, "project": project}

    def _load_telescopes(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Read a telescope, choosing its kind from the file rather than from the caller.

        Args:
            obj (Telescopes): The container it is being imported into.
            attributes: `path`, the file to read.

        Returns:
            Dict[str, Any]: `{"object": Telescope | SpaceTelescope}`.

        Notes:
            - A ground station and a spacecraft are written to the same kind of file and are
              told apart by what is in it. The general `_load` builds whatever type it was
              given, which cannot answer this -- so the answer lives here, where MSB finds it
              by the type of the container being imported into.
        """
        from pastrocore.base.spacetelescope import SpaceTelescope
        from pastrocore.base.telescope import Telescope

        path = self._destination(attributes, verb="load")
        data = json.loads(Path(path).read_text(encoding="utf-8"))

        # The same handler is reached whether a telescope is being imported *into* a container
        # or the container itself is being read back, because MSB resolves on the type of the
        # object the request runs on and both are `Telescopes`. The file says which it is.
        if "items" in data:
            restored = type(obj).from_dict(data)
            logger.info("Read %s from '%s'", type(restored).__name__, path)
            return {"object": restored}

        kind = SpaceTelescope if data.get("type") == "SpaceTelescope" else Telescope
        restored = kind.from_dict(data)
        logger.info("Read %s '%s' from '%s'", kind.__name__, restored.get_code(), path)
        return {"object": restored}

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

    def _export_scan_times(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List the scans a result covers for one source, with the time each starts.

        Args:
            obj (Observation): The observation to read.
            attributes: `key`, the result to look in, and `source_name`, the source to filter
                by.

        Returns:
            List[Dict[str, Any]]: `[{"scan_name": str, "start": str}]`, sorted by time, with
                the start as an ISOT string. Empty when there is no such data, which is an
                answer rather than an error -- a source may simply not be observed.

        Notes:
            - This existed ten times over, once in each visualization tab, and each copy needed
              polars to filter and group and astropy to turn an MJD into something readable.
              That is ten screens holding a query, and a command-line version would have had to
              write an eleventh.
            - Reached through the `export` operation because it is the same concern: getting
              data out of a project in a form something else can use. The interface uses it to
              fill a list; a script would use it to decide what to plot.
        """
        key = attributes.get("key")
        source_name = attributes.get("source_name")
        if not key or not source_name:
            raise ValueError("Both 'key' and 'source_name' are needed to list scan times")

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

        if "source_name" not in frame.columns or "time" not in frame.columns:
            logger.debug("Result '%s' is not keyed by source and time", key)
            return []

        filtered = frame.filter(pl.col("source_name") == source_name)
        if filtered.is_empty():
            logger.debug("No '%s' data for source '%s'", key, source_name)
            return []

        starts = filtered.group_by("scan_name").agg(time=pl.col("time").first()).sort("time")
        return [{"scan_name": row["scan_name"], "start": Time(row["time"], format="mjd").isot}
                for row in starts.iter_rows(named=True)]

    @staticmethod
    def _targets(obj: Any) -> List[Observation]:
        """Return the observations an export covers.

        Args:
            obj: An `Observation`, a `ScheduleProject`, or a list of observations.

        Returns:
            List[Observation]: What to export.
        """
        if isinstance(obj, ScheduleProject):
            items = obj.get_items()
            return list(items.values()) if isinstance(items, dict) else list(items)
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
            - Times are written in ISOT rather than as MJD floats, because the file is meant to
              be read by a person. NaN is preserved as it stands: a gap is a gap, and writing
              an empty field instead would let it read as zero.
            - `mollweide_tracks` appends the source coordinates from its metadata as extra rows
              with the time set to `-----`, which is how that file has always been written.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            key = calc_type.lower().replace(" ", "_").replace("/", "_")

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
