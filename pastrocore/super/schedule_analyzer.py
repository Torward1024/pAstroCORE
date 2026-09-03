# super/schedule_analyzer.py
"""Asking questions of results that have already been calculated.

A calculation finished and that was the end of it. The numbers were on disk and the only thing
anyone could do with them was look at a plot: visibility is a boolean per station per moment,
and "when is it visible, for how long, where are the gaps" could not be asked at all -- nor
could "what is the longest baseline this project achieves", which is a `max` over one column.

This is a fifth operation, `analyze`, and it reads results rather than producing them.

**Nothing here names a column or a calculation.** Which results exist, which of their columns
are numbers, which are categories worth grouping or filtering by, and which are booleans with
runs in them are all read from the schemas the calculations already declare. A calculation
added tomorrow can be summarised, sliced and grouped by this without a line changing -- and the
interface offering those choices is filled from `describe`, so it cannot offer a column that is
not there or miss one that is.

**Scope.** An operation earns its place here when it answers a question asked *while
scheduling*: when can I observe, how long for, what does this baseline reach, which station is
carrying the array. Not by being a statistic that exists.
"""
from typing import Any, Dict, List, Optional

import polars as pl
from astropy.time import Time
from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject


class ScheduleAnalyzer(Super):
    """Summaries, slices and runs over results that already exist.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "analyze"

    #: Columns that are a moment in time rather than a plain number. Reported in ISO as well as
    #: in MJD, because "the array is busy from 61262.2 to 61262.3" is not an answer anyone reads.
    TIME_COLUMNS = ("time", "start", "end")

    #: What a summary reports for a numeric column. `range` is max - min, which is the question
    #: actually asked of a baseline or an elevation.
    STATISTICS = ("count", "min", "max", "mean", "median", "std", "range")

    def __init__(self, manipulator):
        super().__init__(manipulator)
        logger.debug("Initialized Schedule Analyzer")

    # --- what there is to ask about ------------------------------------------------------

    @staticmethod
    def _columns_of(key: str) -> Dict[str, List[str]]:
        """Return one calculation's columns, sorted into what can be done with them."""
        dtypes = CalculatedDataStructure.get_dtypes(key) or {}
        numeric, categorical, boolean = [], [], []
        for column, dtype in dtypes.items():
            name = str(dtype)
            if "Bool" in name:
                boolean.append(column)
            elif "Float" in name or "Int" in name:
                numeric.append(column)
            elif name == "String":
                categorical.append(column)
        return {"numeric": numeric, "categorical": categorical, "boolean": boolean}

    def _targets(self, obj: Any) -> List[Observation]:
        """Return the observations a request is about."""
        if isinstance(obj, Observation):
            return [obj]
        if isinstance(obj, ScheduleProject):
            return obj.observations()
        if isinstance(obj, (list, tuple)):
            return [item for item in obj if isinstance(item, Observation)]
        return []

    def _frame(self, observation: Observation, key: str,
               where: Optional[Dict[str, Any]]) -> Optional[pl.DataFrame]:
        """Return one result, filtered, or None when the observation has not calculated it.

        Notes:
            - Filtered **lazily**, so the slice reaches the read rather than the result being
              loaded whole and mostly discarded. That is what the parquet store exists for.
        """
        view = observation.scan_calculated_data(key)
        if view is None:
            return None

        for column, wanted in (where or {}).items():
            if wanted is None:
                continue
            if isinstance(wanted, (list, tuple, set)):
                view = view.filter(pl.col(column).is_in(list(wanted)))
            elif isinstance(wanted, dict):
                # A range: {"from": x, "to": y}, either end optional. NaN is dropped first,
                # because a calculation writes NaN for a moment it has no answer for -- the
                # source was below the horizon -- and comparing NaN against a bound answers
                # neither True nor False reliably. "Elevation above 20" means the moments
                # where there *is* an elevation and it is above 20.
                view = view.filter(pl.col(column).is_not_nan())
                if wanted.get("from") is not None:
                    view = view.filter(pl.col(column) >= wanted["from"])
                if wanted.get("to") is not None:
                    view = view.filter(pl.col(column) <= wanted["to"])
            else:
                view = view.filter(pl.col(column) == wanted)

        try:
            return view.collect()
        except Exception as e:                          # noqa: BLE001 - a bad filter is not fatal
            logger.error("Could not read '%s' of '%s': %s", key, observation.code, str(e),
                         exc_info=True)
            return None

    def _analyze_describe(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Return what can be asked of each result an observation holds.

        Args:
            obj: An observation, a project, or a list of them.
            attributes: `key`, to describe one calculation rather than all of them. `values`
                (default True) includes the distinct values of each categorical column, which
                is what a filter in an interface is filled from.

        Returns:
            Dict[str, Any]: Keyed by calculation, each with `numeric`, `categorical`, `boolean`
                and -- when asked for -- `values`, plus `rows` and which observations hold it.

        Notes:
            - **This is what makes the interface hold no list of its own.** The analysis tab
              offers the columns this reports, so a calculation added tomorrow appears there
              with its own columns and nobody edits a combo box.
            - Distinct values come from the results rather than from the model: a filter should
              offer the stations a result actually mentions, not every station in the project.
        """
        observations = self._targets(obj)
        wanted = [attributes["key"]] if attributes.get("key") else None
        with_values = attributes.get("values", True)

        described: Dict[str, Any] = {}
        for observation in observations:
            results = observation.calculated_data
            held = list(results.keys()) if hasattr(results, "keys") else []
            for key in held:
                if wanted and key not in wanted:
                    continue
                entry = described.setdefault(key, {
                    **self._columns_of(key), "rows": 0, "observations": [],
                    "label": CalculatedDataStructure.label_for(key)
                    if hasattr(CalculatedDataStructure, "label_for") else key})
                frame = self._frame(observation, key, None)
                if frame is None:
                    continue
                entry["rows"] += frame.height
                entry["observations"].append(observation.code)
                if with_values:
                    values = entry.setdefault("values", {})
                    for column in entry["categorical"]:
                        if column in frame.columns:
                            seen = values.setdefault(column, set())
                            seen.update(frame[column].unique().to_list())

        if with_values:
            for entry in described.values():
                entry["values"] = {column: sorted(v for v in seen if v is not None)
                                   for column, seen in entry.get("values", {}).items()}
        logger.info("Described %s result(s) over %s observation(s)",
                    len(described), len(observations))
        return described

    # --- N3: the numbers ------------------------------------------------------------------

    def _analyze_summary(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Summarise numeric columns of one result, optionally grouped and sliced.

        Args:
            obj: An observation, a project, or a list of them.
            attributes: `key`, the calculation to summarise (required). `columns`, which numeric
                columns -- every one by default. `group_by`, categorical columns to break the
                answer down by. `where`, a mapping of column to a value, a list of values, or
                `{"from": x, "to": y}`.

        Returns:
            List[Dict[str, Any]]: A row per group per column, with `count`, `min`, `max`,
                `mean`, `median`, `std` and `range`. Time columns carry `min_iso` and `max_iso`
                beside the numbers.

        Raises:
            ValueError: If no `key` was given, or it names no calculation.

        Notes:
            - `range` is there because it is the question: the longest baseline a project
              achieves is `max(projection) - min(projection)` away from the shortest, and
              nobody wants to subtract two numbers out of two separate answers.
            - Grouping is done by polars over the filtered frame, so "per station" costs one
              pass rather than one read per station.
        """
        key = attributes.get("key")
        if not key:
            raise ValueError("No 'key' given; there is no result to summarise")

        columns_of = self._columns_of(key)
        if not columns_of["numeric"] and not columns_of["categorical"]:
            raise ValueError(f"Nothing is calculated under '{key}'")

        wanted = attributes.get("columns") or columns_of["numeric"]
        unknown = [column for column in wanted if column not in columns_of["numeric"]]
        if unknown:
            raise ValueError(f"'{key}' has no numeric column called {', '.join(unknown)}; "
                             f"it has {', '.join(columns_of['numeric'])}")

        group_by = attributes.get("group_by") or []
        if isinstance(group_by, str):
            group_by = [group_by]
        unknown = [column for column in group_by if column not in columns_of["categorical"]]
        if unknown:
            raise ValueError(f"'{key}' has no column called {', '.join(unknown)} to group by; "
                             f"it has {', '.join(columns_of['categorical'])}")

        rows: List[Dict[str, Any]] = []
        for observation in self._targets(obj):
            frame = self._frame(observation, key, attributes.get("where"))
            if frame is None or frame.is_empty():
                continue
            for group, part in self._grouped(frame, group_by):
                for column in wanted:
                    if column not in part.columns:
                        continue
                    rows.append({"observation": observation.code, **group,
                                 "column": column, **self._statistics(part[column], column)})

        logger.info("Summarised '%s' into %s row(s)", key, len(rows))
        return rows

    @staticmethod
    def _grouped(frame: pl.DataFrame, group_by: List[str]):
        """Yield (labels, frame) per group, or the whole frame when nothing is grouped by."""
        if not group_by:
            yield {}, frame
            return
        for keys, part in frame.group_by(group_by, maintain_order=True):
            labels = dict(zip(group_by, keys if isinstance(keys, tuple) else (keys,)))
            yield labels, part

    def _statistics(self, series: pl.Series, column: str) -> Dict[str, Any]:
        """Return the statistics of one column, with ISO times where the column is a time.

        Notes:
            - **NaN is not a number and is not averaged.** A calculation writes NaN for a moment
              it has no answer for -- an elevation while the source is below the horizon, a
              position outside what the orbit file covers -- and including those would make the
              mean elevation of a source meaningless and the median come out NaN, which is what
              polars does with them. They are counted and reported as `missing`, because *how
              many moments have no answer* is itself worth knowing.
        """
        clean = series.drop_nulls().drop_nans() if series.dtype.is_float() else series.drop_nulls()
        missing = int(series.len() - clean.len())
        if clean.is_empty():
            return {**{statistic: None for statistic in self.STATISTICS}, "missing": missing}

        lowest, highest = float(clean.min()), float(clean.max())
        answer: Dict[str, Any] = {
            "count": int(clean.len()),
            "missing": missing,
            "min": lowest,
            "max": highest,
            "mean": float(clean.mean()),
            "median": float(clean.median()),
            "std": float(clean.std()) if clean.len() > 1 else 0.0,
            "range": highest - lowest,
        }
        if column in self.TIME_COLUMNS:
            answer["min_iso"] = self._iso(lowest)
            answer["max_iso"] = self._iso(highest)
        return answer

    @staticmethod
    def _iso(mjd: float) -> Optional[str]:
        """Return an MJD as an ISO string, or None if it is not one."""
        try:
            return Time(mjd, format="mjd", scale="utc").isot
        except Exception:                               # noqa: BLE001 - a label, not a result
            return None

    # --- N1: runs of a boolean -------------------------------------------------------------

    def _analyze_windows(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the runs of a boolean column as intervals: when, and for how long.

        Args:
            obj: An observation, a project, or a list of them.
            attributes: `key`, the calculation (required) -- one that has a boolean column.
                `column`, which boolean, when there is more than one. `by`, the categorical
                columns a run belongs to; every one of them by default, so a window is per
                station per source rather than a run across two stations that never overlapped.
                `gaps` (default False) returns the runs of False instead. `where`, as for
                `summary`.

        Returns:
            List[Dict[str, Any]]: A row per window with `start`, `end`, `start_iso`, `end_iso`,
                `duration` in seconds, and `samples`.

        Raises:
            ValueError: If no `key` was given, or the calculation has no boolean column.

        Notes:
            - **This is the primitive the rest of the analysis is made of.** A window of
              visibility, a gap in it, the longest run and the total are all runs of consecutive
              `True` in a boolean column grouped by station.
            - A run is bounded by the samples that make it, so its duration is the time between
              the first and last sample plus one sampling step -- a single sample is a window of
              one step, not of zero. The step is taken from the data rather than from the
              request, since a result may have been calculated with a different one.
        """
        key = attributes.get("key")
        if not key:
            raise ValueError("No 'key' given; there is nothing to find windows in")

        columns_of = self._columns_of(key)
        if not columns_of["boolean"]:
            raise ValueError(
                f"'{key}' has no true-or-false column to find runs in; "
                f"{', '.join(self._with_booleans()) or 'nothing'} has one")

        column = attributes.get("column") or columns_of["boolean"][0]
        if column not in columns_of["boolean"]:
            raise ValueError(f"'{key}' has no boolean column called '{column}'")

        wanted = attributes.get("gaps", False) is False
        by = attributes.get("by")
        if by is None:
            by = columns_of["categorical"]
        elif isinstance(by, str):
            by = [by]

        windows: List[Dict[str, Any]] = []
        for observation in self._targets(obj):
            frame = self._frame(observation, key, attributes.get("where"))
            if frame is None or frame.is_empty() or "time" not in frame.columns:
                continue
            frame = frame.sort("time")
            for labels, part in self._grouped(frame, [c for c in by if c in frame.columns]):
                part = part.sort("time")
                # The step is measured *within* the group. Taken across the whole frame it is
                # measured over two stations' samples interleaved -- the same instant twice --
                # so the spacing came out wrong and every window was short by a few steps.
                step = self._sampling_step(part["time"])
                windows.extend(
                    {"observation": observation.code, **labels, **run}
                    for run in self._runs(part, column, wanted, step))

        logger.info("Found %s %s in '%s'", len(windows), "gap(s)" if not wanted else "window(s)",
                    key)
        return windows

    def _with_booleans(self) -> List[str]:
        """Return every calculation that has a boolean column, for the message above."""
        return sorted(key for key in CalculatedDataStructure.SCHEMAS
                      if self._columns_of(key)["boolean"])

    @staticmethod
    def _sampling_step(times: pl.Series) -> float:
        """Return the spacing between samples, in days, as the data shows it."""
        if times.len() < 2:
            return 0.0
        gaps = times.diff().drop_nulls().drop_nans()
        if gaps.is_empty():
            return 0.0
        return float(gaps.median() or 0.0)

    def _runs(self, part: pl.DataFrame, column: str, wanted: bool,
              step: float) -> List[Dict[str, Any]]:
        """Return the runs of `wanted` in one group, as intervals."""
        states = part[column].to_list()
        times = part["time"].to_list()

        found: List[Dict[str, Any]] = []
        start_index = None
        for index, state in enumerate(states):
            if bool(state) == wanted and start_index is None:
                start_index = index
            elif bool(state) != wanted and start_index is not None:
                found.append(self._interval(times, start_index, index - 1, step))
                start_index = None
        if start_index is not None:
            found.append(self._interval(times, start_index, len(states) - 1, step))
        return found

    def _interval(self, times: List[float], first: int, last: int,
                  step: float) -> Dict[str, Any]:
        """Return one run as an interval, in MJD, ISO and seconds."""
        start, end = times[first], times[last] + step
        return {"start": start, "end": end,
                "start_iso": self._iso(start), "end_iso": self._iso(end),
                "duration": (end - start) * 86400.0,
                "samples": last - first + 1}

    # --- N2: across stations ---------------------------------------------------------------

    def _analyze_coverage(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return when a source is visible from at least so many stations at once.

        Args:
            obj: An observation, a project, or a list of them.
            attributes: `key`, the calculation (defaults to `source_visibility`). `at_least`,
                how many stations must see it at the same moment -- 1 for "from any", the
                number of stations for "from all", 2 for the least that makes a baseline.
                `column`, the boolean. `where`, as for `summary`.

        Returns:
            List[Dict[str, Any]]: A row per moment per source with `stations` (how many saw it)
                and whether it `meets` the threshold, collapsed into windows.

        Notes:
            - **Joining these frames by hand is what this replaces.** "Visible from at least
              two" is a real question -- it is the least that makes a baseline -- and answering
              it meant pivoting a frame per station and lining the moments up.
            - A moment counts a station once. Two scans sampling the same instant do not make
              an array of two.
        """
        key = attributes.get("key") or "source_visibility"
        columns_of = self._columns_of(key)
        if not columns_of["boolean"]:
            raise ValueError(f"'{key}' has no true-or-false column to count stations in")

        column = attributes.get("column") or columns_of["boolean"][0]
        at_least = int(attributes.get("at_least", 1))
        subject = "source_name" if "source_name" in columns_of["categorical"] else (
            columns_of["categorical"][0] if columns_of["categorical"] else None)

        rows: List[Dict[str, Any]] = []
        for observation in self._targets(obj):
            frame = self._frame(observation, key, attributes.get("where"))
            if frame is None or frame.is_empty():
                continue
            visible = frame.filter(pl.col(column))
            if visible.is_empty():
                continue
            grouping = [c for c in ([subject] if subject else []) + ["time"] if c in visible.columns]
            counted = (visible.group_by(grouping)
                       .agg(pl.col("telescope_code").n_unique().alias("stations"))
                       .sort(grouping))
            meeting = counted.filter(pl.col("stations") >= at_least)
            if meeting.is_empty():
                continue
            # From the distinct moments, not from the frame: the frame holds one row per
            # station per moment, so its spacing is measured over the same instant repeated.
            step = self._sampling_step(frame["time"].unique().sort())
            for labels, part in self._grouped(meeting, [subject] if subject else []):
                part = part.sort("time")
                times = part["time"].to_list()
                for run in self._consecutive(times, step):
                    rows.append({"observation": observation.code, **labels,
                                 "at_least": at_least,
                                 "stations": int(part["stations"].max()), **run})

        logger.info("Coverage by at least %s station(s): %s window(s)", at_least, len(rows))
        return rows

    def _consecutive(self, times: List[float], step: float) -> List[Dict[str, Any]]:
        """Return runs of consecutive moments as intervals, given the sampling step."""
        if not times:
            return []
        tolerance = step * 1.5 if step else 0.0
        found, first = [], 0
        for index in range(1, len(times)):
            if tolerance and (times[index] - times[index - 1]) > tolerance:
                found.append(self._interval(times, first, index - 1, step))
                first = index
        found.append(self._interval(times, first, len(times) - 1, step))
        return found
