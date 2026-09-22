from msb_arch import InvariantError
from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base.sources import Source
from pastrocore.base.telescopes import Telescope, SpaceTelescope
from pastrocore.base.scans import Scan
from pastrocore.base.observation import Observation
from pastrocore.base import freshness
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.super.schedule_project import ScheduleProject

from typing import Dict, Any, Optional, Tuple, List, Callable
from scipy.special import j1
from functools import wraps

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import ITRS, GCRS, CartesianRepresentation, SkyCoord, AltAz, get_sun, HADec

import numpy as np
import polars as pl

import hashlib
import threading
import time
from collections import OrderedDict
import re
import os

from scipy.interpolate import CubicSpline
from numpy.polynomial import chebyshev

from erfa import ErfaWarning
import warnings
warnings.filterwarnings("ignore", category=ErfaWarning)
warnings.filterwarnings("ignore", category=Warning, module="astropy")

def time_execution(func):
    """Decorator to measure and log the execution time of calculation methods.

    Args:
        func: The function to decorate.

    Returns:
        Callable: Wrapped function that logs execution duration.
    """
    @wraps(func)
    def wrapper(self, obj, attributes):
        start_time = time.perf_counter()
        result = func(self, obj, attributes)
        duration = time.perf_counter() - start_time
        calc_type = func.__name__.replace('_calculate_', '')
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        # Debug, not info. This fires on every *call*, and a calculation that reads its
        # prerequisite calls it too -- so a run of ten calculations wrote "Calculation
        # 'time_arrays' completed" six times over, each of them a cache hit of four
        # milliseconds, and it read exactly like six recomputations. What a run actually did is
        # in the report `compute(method="run")` returns, timed on the interceptor; what was
        # genuinely recomputed still says so at info, once, as "Calculating '...'".
        logger.debug("Calculation '%s' for '%s' returned in %.3f s", calc_type, obj_name, duration)
        return result
    return wrapper



class _InTurn:
    """Runs each piece of work where it stands, with an executor's vocabulary.

    Notes:
        - **One place decides how work is spread, and it is the pipeline.** Every calculation
          used to open a `ThreadPoolExecutor` of its own over the scans, and `_process_object`
          another over the observations -- underneath a pipeline that is already running the
          calculations in threads when asked to. Four workers under six concurrent steps is
          twenty-four threads contending for the GIL and for cores.
        - **It is not faster, and that is not the reason.** Measured on a 69-scan schedule,
          interleaved six times each: 9.62 s at the median with the inner pools and 9.71 s
          without, which is a wash. An earlier measurement said 6% faster and was a quiet
          window on the machine rather than a fact. The reasons are that eleven copies of one
          block are eleven places to change, and that a second policy for spreading work,
          hidden under the one the pipeline applies, is how a whole project came to draw
          nothing when the visualizer had the same shape.
        - It keeps `submit` and `result` so the call sites read as they did. The name says what
          it does, so nobody reads concurrency into it.
    """

    class _Done:
        """A result that is already there."""

        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

    def __enter__(self):
        return self

    def __exit__(self, *_details):
        return False

    def submit(self, work, *args, **kwargs):
        return self._Done(work(*args, **kwargs))


class ScheduleCalculator(Super):
    """Scheduler implementation of Calculator for performing astronomical scheduling calculations.

    Provides methods to calculate telescope positions, source visibility, UV coverage, sun angles, and more for Observations and Projects.
    Supports caching of results and multi-threaded execution for efficiency.

    Attributes:
        manipulator: The Manipulator instance used to manage object interactions.
        _lock (threading.Lock): Thread lock for safe data caching.
    """
    OPERATION = "calculate"
    
    def __init__(self, manipulator: 'Manipulator'):
        """Initialize the ScheduleCalculator.

        Args:
            manipulator: The Manipulator instance providing method validation and execution capabilities.
        """
        super().__init__(manipulator)
        self._lock = threading.Lock()
        # An orbit file parsed once, keyed by path and what the file looked like when it was
        # read. `_orbit_cache` was here before and nothing ever wrote to or read from it, while
        # the lock named after it was held across the whole interpolation -- so the cache did
        # nothing and the lock serialised work the pipeline runs in parallel. One scan of ten
        # against one spacecraft re-read and re-parsed the same file ten times.
        self._orbit_cache: Dict[tuple, Dict[str, np.ndarray]] = {}
        self._orbit_cache_lock = threading.Lock()
        self._topocentric_cache: "OrderedDict[tuple, Tuple[np.ndarray, np.ndarray, np.ndarray]]" = OrderedDict()
        self._topocentric_bytes = 0
        self._topocentric_lock = threading.Lock()
        logger.debug("Initialized Scheduling Calculator")

    #: What the shared topocentric directions may occupy. A day at a one-second step for one
    #: station is 6 MB, so this holds a busy run's worth and never a project's.
    TOPOCENTRIC_CACHE_BYTES = 64 * 1024 ** 2

    def _topocentric(self, source: Source, positions: np.ndarray, times_mjd: np.ndarray,
                     frame: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return where a source stands, seen from a station, at every sample of a scan.

        Args:
            source (Source): What is looked at.
            positions (np.ndarray): The station's GCRS positions in metres, (n, 3).
            times_mjd (np.ndarray): The samples, MJD UTC, (n,).
            frame (str): "altaz" or "hadec".

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: In degrees and read-only -- azimuth and
                altitude for "altaz", hour angle and declination for "hadec" -- and the station's
                geodetic latitude at each sample.

        Notes:
            - **Computed once, read by three steps.** Visibility, az/el and the parallactic
              angle each rebuilt the station's location from its GCRS positions and transformed
              the source into the same frame over the same samples: the same two erfa pipelines,
              three times, and together more than half of a run's work.
            - Keyed by what the answer is made of -- the frame, the source's position, the bytes
              of the positions and the times -- so it has nothing to go stale against. A source
              moved or a station moved is a different key.
            - Bounded in bytes rather than entries, oldest first, because one entry of a day at
              a one-second step weighs as much as a hundred of a short scan.
        """
        key, positions, times_mjd = self._topocentric_key(source, positions, times_mjd, frame)
        with self._topocentric_lock:
            held = self._topocentric_cache.get(key)
            if held is not None:
                self._topocentric_cache.move_to_end(key)
                return held
        ra = np.full(len(times_mjd), float(source.ra_degrees))
        dec = np.full(len(times_mjd), float(source.dec_degrees))
        held = self._transform_topocentric(ra, dec, positions, times_mjd, frame)
        self._hold_topocentric(key, held)
        return held

    @staticmethod
    def _topocentric_key(source: Source, positions: np.ndarray, times_mjd: np.ndarray,
                         frame: str) -> Tuple[tuple, np.ndarray, np.ndarray]:
        """The cache key for one station's view of one source over one scan's samples."""
        times_mjd = np.ascontiguousarray(times_mjd, dtype=float)
        positions = np.ascontiguousarray(positions, dtype=float)
        fingerprint = hashlib.blake2b(positions.tobytes() + times_mjd.tobytes(), digest_size=16).digest()
        return (frame, float(source.ra_degrees), float(source.dec_degrees), fingerprint), positions, times_mjd

    @staticmethod
    def _transform_topocentric(ra: np.ndarray, dec: np.ndarray, positions: np.ndarray,
                               times_mjd: np.ndarray, frame: str) -> Tuple[np.ndarray, ...]:
        """One astropy transform over any number of samples, each with its own source and station."""
        obstime = Time(times_mjd, format="mjd", scale="utc")
        stations = GCRS(CartesianRepresentation(x=positions[:, 0] * u.m, y=positions[:, 1] * u.m,
                                                z=positions[:, 2] * u.m),
                        obstime=obstime).transform_to(ITRS(obstime=obstime)).earth_location
        looked_at = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
        if frame == "altaz":
            seen = looked_at.transform_to(AltAz(obstime=obstime, location=stations))
            held = (seen.az.deg, seen.alt.deg, stations.lat.deg)
        elif frame == "hadec":
            seen = looked_at.transform_to(HADec(obstime=obstime, location=stations))
            held = (seen.ha.deg, seen.dec.deg, stations.lat.deg)
        else:
            raise ValueError(f"No topocentric frame called '{frame}'")
        return tuple(np.array(values, dtype=float) for values in held)

    def _hold_topocentric(self, key: tuple, held: Tuple[np.ndarray, ...]) -> None:
        for values in held:
            values.setflags(write=False)
        size = sum(values.nbytes for values in held)
        with self._topocentric_lock:
            if key not in self._topocentric_cache:
                self._topocentric_cache[key] = held
                self._topocentric_bytes += size
                while self._topocentric_bytes > self.TOPOCENTRIC_CACHE_BYTES and len(self._topocentric_cache) > 1:
                    _, dropped = self._topocentric_cache.popitem(last=False)
                    self._topocentric_bytes -= sum(values.nbytes for values in dropped)

    @staticmethod
    def _ground_key(telescope: Telescope, times_mjd: np.ndarray) -> Tuple[tuple, np.ndarray]:
        """The cache key for one ground station's GCRS positions over one scan's samples."""
        times_mjd = np.ascontiguousarray(times_mjd, dtype=float)
        fingerprint = hashlib.blake2b(times_mjd.tobytes(), digest_size=16).digest()
        return (("gcrs",) + tuple(float(value) for value in telescope.get_coordinates())
                + tuple(float(value) for value in telescope.get_velocities()) + (fingerprint,)), times_mjd

    def _warm_ground_positions(self, observation: Observation, scans: List[Scan],
                               times_df: pl.DataFrame) -> int:
        """Rotate every ground station to GCRS for every scan at once, before they are asked.

        Returns:
            int: How many station-scan position sets were computed.

        Notes:
            - Going from ITRS to GCRS is a rotation that depends on the moment and not on the
              station, so every station over every scan is one transform. It was one per scan per
              station, each paying astropy's fixed cost: about three seconds for ten stations over
              fifty scans. Filed under the keys `_compute_telescope_position` asks for.
        """
        if not hasattr(self, "_j2000_mjd"):
            self._j2000_mjd = Time("2000-01-01T12:00:00").mjd
        entries = []
        for scan in scans:
            times_mjd = times_df.filter(pl.col("scan_name") == scan.name)["time"].to_numpy()
            if len(times_mjd) == 0:
                continue
            for tel in scan.get_telescopes(observation).get_items():
                if not tel.isactive or isinstance(tel, SpaceTelescope):
                    continue
                key, times = self._ground_key(tel, times_mjd)
                with self._topocentric_lock:
                    if key in self._topocentric_cache:
                        continue
                moved = (np.asarray(tel.get_coordinates(), dtype=float)[np.newaxis, :]
                         + np.asarray(tel.get_velocities(), dtype=float)[np.newaxis, :]
                         * ((times - self._j2000_mjd) / 365.25)[:, np.newaxis])
                entries.append((key, moved, times))
        if not entries:
            return 0

        moved = np.concatenate([values for _, values, _ in entries])
        times = np.concatenate([values for _, _, values in entries])
        obstime = Time(times, format="mjd", scale="utc")
        gcrs = ITRS(CartesianRepresentation(moved[:, 0], moved[:, 1], moved[:, 2], unit=u.m),
                    obstime=obstime).transform_to(GCRS(obstime=obstime)).cartesian
        everything = np.stack([gcrs.x.value, gcrs.y.value, gcrs.z.value], axis=-1)
        offset = 0
        for key, values, _ in entries:
            n = len(values)
            self._hold_topocentric(key, (np.array(everything[offset:offset + n], dtype=float),))
            offset += n
        return len(entries)

    def _warm_topocentric(self, observation: Observation, scans: List[Scan], times_df: pl.DataFrame,
                          position_df: pl.DataFrame, frame: Optional[str] = None) -> int:
        """Transform every scan's samples for every ground station at once, before they are asked.

        Args:
            observation (Observation): Whose scans these are.
            scans (List[Scan]): The scans a step is about to process one at a time.
            times_df (pl.DataFrame): The time grid, as the step reads it.
            position_df (pl.DataFrame): The stations' GCRS positions, as the step reads them.
            frame (Optional[str]): The one frame every station is wanted in -- the elevation
                of an equatorial mount is asked too -- or None for each mount's own.

        Returns:
            int: How many station-scan views were transformed.

        Notes:
            - **One transform for the whole observation instead of one per scan per station.**
              Each astropy transform costs about twelve milliseconds before it touches a sample,
              so ten stations over fifty scans spent six seconds on five hundred calls that do
              the same thing to ten samples each. Array-valued coordinates carry each sample's own
              source and station, so one call per frame covers them all.
            - The results are filed under exactly the keys the per-scan code will ask for, built
              from the same arrays read the same way, and the per-scan code is unchanged: this
              only decides when the work is done.
        """
        chunks = {"altaz": [], "hadec": []}
        by_scan = position_df.partition_by("scan_name", as_dict=True)
        for scan in scans:
            source = scan.get_source(observation)
            if source is None or not source.isactive:
                continue
            times_mjd = times_df.filter(pl.col("scan_name") == scan.name)["time"].to_numpy()
            scan_positions = by_scan.get((scan.name,))
            if len(times_mjd) == 0 or scan_positions is None:
                continue
            for tel in scan.get_telescopes(observation).get_items():
                if not tel.isactive or isinstance(tel, SpaceTelescope):
                    continue
                mount = tel.get("mount_type").value
                wanted = frame or ("altaz" if mount == "AZIM" else "hadec" if mount == "EQUA" else None)
                positions = scan_positions.filter(pl.col("telescope_code") == tel.get_code()).select(["x", "y", "z"]).to_numpy()
                if wanted is None or len(positions) != len(times_mjd):
                    continue
                key, positions, times = self._topocentric_key(source, positions, times_mjd, wanted)
                with self._topocentric_lock:
                    if key in self._topocentric_cache:
                        continue
                chunks[wanted].append((key, source, positions, times))

        warmed = 0
        for chunk_frame, entries in chunks.items():
            if not entries:
                continue
            lengths = [len(times) for _, _, _, times in entries]
            ra = np.concatenate([np.full(n, float(source.ra_degrees)) for (_, source, _, _), n in zip(entries, lengths)])
            dec = np.concatenate([np.full(n, float(source.dec_degrees)) for (_, source, _, _), n in zip(entries, lengths)])
            positions = np.concatenate([positions for _, _, positions, _ in entries])
            times = np.concatenate([times for _, _, _, times in entries])
            everything = self._transform_topocentric(ra, dec, positions, times, chunk_frame)
            offset = 0
            for (key, _, _, _), n in zip(entries, lengths):
                self._hold_topocentric(key, tuple(np.array(values[offset:offset + n]) for values in everything))
                offset += n
            warmed += len(entries)
        return warmed
    
    @staticmethod
    def _active_scan_count(obj: Observation | ScheduleProject) -> int:
        """Return how many active scans an observation or a whole project holds.

        Args:
            obj: An Observation, or a ScheduleProject of them.

        Returns:
            int: The count, summed across observations for a project.

        Notes:
            - Written out eleven times, identically, in the metadata of eleven calculations.
              It is one line each time and it is the same line, which is how the *other* count
              in this file came to be spelled differently from all of them.
        """
        if isinstance(obj, Observation):
            return len(obj.get_scans().get_active_items())
        return sum(len(o.get_scans().get_active_items()) for o in obj.get_observations())

    @staticmethod
    def _active_telescope_count(obj: Observation | ScheduleProject) -> int:
        """Return how many active telescopes an observation or a whole project holds."""
        if isinstance(obj, Observation):
            return len(obj.get_telescopes().get_active_items())
        return sum(len(o.get_telescopes().get_active_items()) for o in obj.get_observations())

    def _get_active_components(
        self,
        obj: Observation,
        require_scans: bool = True,
        require_telescopes: bool = False,
        min_telescopes: int = 1
    ) -> Tuple[List[Scan], List[Telescope | SpaceTelescope], List[Source]]:
        """Retrieve active scans, telescopes, and sources from an Observation.

        Args:
            obj: The Observation to check.
            require_scans: If True, requires at least one active scan.
            require_telescopes: If True, requires at least min_telescopes active telescopes.
            min_telescopes: Minimum number of active telescopes required.

        Returns:
            Tuple[List[Scan], List[Telescope | SpaceTelescope], List[Source]]: Active components.

        Notes:
            Logs warnings if required components are missing.
        """
        scans = obj.get_scans().get_active_items() if require_scans else []
        telescopes = obj.get_telescopes().get_active_items()
        sources = obj.get_sources().get_active_items()
        
        obj_code = obj.get_observation_code()
        if require_scans and not scans:
            logger.warning("No active scans in observation '%s'", obj_code)
            return [], [], []
        if require_telescopes and len(telescopes) < min_telescopes:
            logger.warning("Insufficient active telescopes (%s < %s) in '%s'", len(telescopes), min_telescopes, obj_code)
            return [], [], []
        if not sources:
            logger.warning("No active sources in observation '%s'", obj_code)
            return [], [], []
        
        return scans, telescopes, sources

    @staticmethod
    def _parameters_asked_for(store_key: str, attributes: Dict[str, Any],
                              metadata: Dict[str, Any],
                              stored: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """Return the parameters this call would work with that a stored result did not.

        Args:
            store_key (str): What the result is filed under.
            attributes (Dict[str, Any]): What the caller asked with.
            metadata (Dict[str, Any]): What this call would record -- the parameters as the
                handler resolved them, which is what the stored ones are comparable with.
            stored (Dict[str, Any]): The metadata of the result already held.

        Returns:
            List[Tuple[str, Any]]: `(name, wanted)` for each parameter that differs, empty when
                the stored result answers the question being asked.

        Notes:
            - **The one place the rule lives.** It was written three times -- the cache compared
              `time_step` by name, and two calculations compared the weather, the threshold and
              the recording themselves -- so the next calculation to take a parameter would have
              had none of it and would have handed back the previous numbers.
            - Resolved values rather than what was passed: a caller that omits a parameter gets
              the handler's default, and a default that matches what the result was worked out
              with is the same question. `attributes` is the fallback for a parameter a handler
              does not record.
            - Compared with `same_metadata`, so a list read back from JSON compares equal to the
              tuples it was written from rather than looking like a change on every open.
        """
        differing = []
        for name in CalculatedDataStructure.recorded_parameters(store_key):
            wanted = metadata.get(name, attributes.get(name))
            if not freshness.same_metadata(wanted, stored.get(name)):
                differing.append((name, wanted))
        return differing

    def _get_cached_or_calculate(self, obj: Observation | ScheduleProject, store_key: str, calc_func, attributes: Dict[str, Any], metadata: Dict[str, Any]) -> pl.DataFrame:
        """Retrieve cached data or perform calculation and cache the result.

        Args:
            obj (Observation | ScheduleProject): The object to calculate for.
            store_key (str): Unique key for storing/retrieving calculated data.
            calc_func: The calculation function to execute if no valid cache exists.
            attributes (Dict[str, Any]): Calculation parameters (e.g., "recalculate", "time_step").
            metadata (Dict[str, Any]): Metadata to store with the result (e.g., time step, scan count).

        Returns:
            pl.DataFrame: Calculated or cached data as Polars DataFrame.

        Notes:
            - Returns cached result if "recalculate" is False and valid cache exists.
            - Uses thread-safe caching with a lock.
            - Logs warnings for empty or invalid results.
            - **A stored result worked out with other parameters is another answer**, and is
              recomputed rather than handed back. Which parameters those are comes from the
              schema, so a calculation that takes a new one is covered by writing it down where
              it is recorded anyway.
        """
        if not store_key:
            logger.error("Empty store_key provided for caching")
            return pl.DataFrame()

        recalculate = attributes.get("recalculate", False)
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()

        existing_data = obj.get_calculated_data_by_key(store_key)
        another_question = []
        if existing_data and not recalculate:
            another_question = self._parameters_asked_for(store_key, attributes, metadata,
                                                          existing_data["metadata"])
            if another_question:
                # A different parameter is a different calculation, not a stale cache, so
                # recomputing is right. Said out loud because the alternative is a caller who
                # omitted one wondering why the call took 300 ms instead of one.
                logger.info("Stored '%s' for '%s' was worked out with %s; recalculating",
                            store_key, obj_name,
                            ", ".join(f"{name}={existing_data['metadata'].get(name)!r}, not "
                                      f"{wanted!r}" for name, wanted in another_question))
        if existing_data and not recalculate and not another_question:
            df = existing_data.get("data")
            if df is not None and not df.is_empty():
                logger.debug("Retrieved cached data for '%s' in '%s'", store_key, obj_name)
                return df
            logger.warning("Cached data for '%s' in '%s' is empty; recalculating", store_key, obj_name)

        logger.info("Calculating '%s' for '%s' (recalculate=%s)", store_key, obj_name, recalculate)
        result_df = calc_func(obj, attributes)
        if result_df.is_empty():
            logger.warning("Calculation for '%s' in '%s' returned empty result", store_key, obj_name)
        with self._lock:
            obj.set_calculated_data_by_key(store_key, result_df, metadata)
        return result_df

    def _process_object(
        self,
        obj: Observation | ScheduleProject,
        attributes: Dict[str, Any],
        calc_func: Callable[[Observation, Dict[str, Any]], pl.DataFrame],
        store_key: str,
        metadata: Dict[str, Any]
    ) -> pl.DataFrame:
        """Process an object (Observation or ScheduleProject) with parallel execution for projects.

        Args:
            obj: The object to process (Observation or ScheduleProject).
            attributes: Calculation parameters.
            calc_func: Function to perform calculation for a single Observation.
            store_key: Key for caching results.
            metadata: Metadata for cache validation.

        Returns:
            pl.DataFrame: Calculated results as Polars DataFrame.
        """
        obj_name = obj.name if isinstance(obj, ScheduleProject) else obj.get_observation_code()
        
        if isinstance(obj, ScheduleProject):
            # The project answers with its observations. `get_items()` hands back a mapping,
            # and iterating that yields the *names* -- which is how a whole-project calculation
            # called `get_observation_code()` on a string and came back empty.
            observations = obj.get_observations()
            if not observations:
                logger.warning("No observations in project '%s'", obj.name)
                return pl.DataFrame()
            dfs = []
            with _InTurn() as executor:
                futures = {
                    executor.submit(self._process_object, obs, attributes, calc_func, store_key, metadata): obs.get_observation_code()
                    for obs in observations
                }
                for future in futures:
                    df = future.result()
                    if not df.is_empty():
                        dfs.append(df)
            if dfs:
                combined_df = pl.concat(dfs)
                logger.info("Processed %s observations for '%s', combined into DF with %s rows", len(observations), obj_name, combined_df.height)
                return combined_df
            else:
                logger.warning("No data from observations in project '%s'", obj_name)
                return pl.DataFrame()
        
        result_df = self._get_cached_or_calculate(obj, store_key, calc_func, attributes, metadata)
        if result_df.is_empty():
            logger.warning("No data computed for '%s' with store_key '%s'", obj_name, store_key)
        return result_df
    
    def _store_result(self, obj, store_key: str, df: "pl.DataFrame", metadata: Dict[str, Any]) -> None:
        """Store a result together with metadata that describes *this* frame.

        Args:
            obj: The observation or project the result belongs to.
            store_key (str): Where to file it.
            df (pl.DataFrame): The frame just computed or read from cache.
            metadata (Dict[str, Any]): What is known about how it was produced.

        Notes:
            - This replaces a guard that read "store it if recalculating, or if nothing is
              stored yet", which could never correct anything: `_process_object` has already
              stored the frame with the placeholder metadata by the time the guard is reached,
              so the second condition is false exactly when the correction is needed. A real
              project was found holding `times.parquet` with 288 rows over one scan beside
              metadata saying `scan_count: 0` and `start_time: NaN`.
            - Written only when the metadata actually differs, because a write now reaches the
              disk and re-writing an unchanged result on every call would be a real cost.
        """
        # A result belongs to an observation. Asked for a whole project, `_process_object` has
        # already stored one per observation and what it returns is the combination -- which
        # has nowhere to live, since a project holds observations rather than results. Storing
        # it was attempted and raised, and the broad handler above turned a whole-project
        # calculation into an empty frame with a line in the log.
        if not hasattr(obj, "get_calculated_metadata"):
            logger.debug("%s holds no results of its own; the observations hold theirs",
                         type(obj).__name__)
            return

        # Stamped with a fingerprint of the inputs this calculation actually reads, so a later
        # session can tell whether the configuration has moved underneath it. Taken over the
        # subset in `freshness.DEPENDENCIES` rather than the whole observation: editing a scan
        # must not make a beam pattern stale, or every edit would stale everything and
        # "everything" would be all there is to recompute.
        stamped = freshness.stamp(obj, store_key, metadata)
        # Compared all the way down rather than with `==`: a metadata mapping may hold numpy
        # arrays -- Mollweide records the source coordinates it draws against -- and comparing
        # two of those gives an array rather than an answer.
        if freshness.same_metadata(stamped, obj.get_calculated_metadata(store_key)):
            return

        # The frame is already where it belongs -- `_get_cached_or_calculate` put it there,
        # with the metadata it had at the time. Only the stamp is missing, so only the stamp is
        # written. Storing the frame again to carry a corrected sidecar wrote every result's
        # parquet twice, and since 0.7.0 a store reaches the disk.
        if freshness.record_metadata(obj, store_key, stamped):
            return
        obj.set_calculated_data_by_key(store_key, df, stamped)

    @time_execution
    def _calculate_time_arrays(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate time arrays for active scans grouped by active sources with a configurable time threshold.

        Args:
            obj: The object to calculate time arrays for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "time_threshold", "store_key".

        Returns:
            pl.DataFrame: DataFrame with columns ["source_name", "scan_name", "time"] (time as float MJD).
        """
        try:
            time_step = attributes.get("time_step")
            time_threshold = attributes.get("time_threshold", 1.0)
            store_key = attributes.get("store_key", "times")
            
            if time_step is not None and time_step <= 0:
                logger.error("Invalid time_step: %s. Must be positive.", time_step)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
            if time_threshold <= 0:
                logger.error("Invalid time_threshold: %s. Must be positive.", time_threshold)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))

            def calculate_times(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, sources = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
                
                source_names = []
                scan_names = []
                times_array = []
                start_times = []
                end_times = []
                processed_scans = 0
                
                for scan in scans:
                    source = scan.get_source(obs)
                    if source is None or not source.isactive:
                        logger.debug("Skipping scan '%s' in '%s': no active source", scan.name, obs.get_observation_code())
                        continue
                    source_name = source.name
                    start_time = scan.get_start()
                    duration = scan.get_duration()
                    
                    start_mjd_rounded = round(start_time.mjd * 86400.0 / time_threshold) * time_threshold / 86400.0
                    duration_rounded = round(duration / time_threshold) * time_threshold
                    
                    if time_step is None:
                        mjd_values = np.array([start_mjd_rounded + (duration_rounded / 2) / 86400.0])
                    else:
                        n_points = int(np.ceil(duration_rounded / time_step))
                        time_offsets = np.linspace(0, duration_rounded, n_points, endpoint=False) / 86400.0
                        mjd_values = start_mjd_rounded + time_offsets
                    
                    if len(mjd_values) == 0:
                        logger.warning("Empty time array for scan '%s' in '%s'", scan.name, obs.get_observation_code())
                        continue
                    
                    source_names.append(np.full_like(mjd_values, source_name, dtype=object))
                    scan_names.append(np.full_like(mjd_values, scan.name, dtype=object))
                    times_array.append(mjd_values)
                    start_times.append(start_mjd_rounded)
                    end_times.append(start_mjd_rounded + duration_rounded / 86400.0)
                    processed_scans += 1
                
                if processed_scans == 0:
                    logger.warning("No valid scans processed in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))
                
                source_names = np.concatenate(source_names) if source_names else np.array([])
                scan_names = np.concatenate(scan_names) if scan_names else np.array([])
                times_array = np.concatenate(times_array) if times_array else np.array([])
                
                df = pl.DataFrame({
                    "source_name": source_names,
                    "scan_name": scan_names,
                    "time": times_array
                }, schema=CalculatedDataStructure.get_dtypes("times"))
                
                logger.info("Calculated time arrays for %s scans across %s sources in '%s', DF rows: %s", processed_scans, df['source_name'].unique().len(), obs.get_observation_code(), df.height)
                return df

            # No placeholders for anything the frame itself will answer. They were NaN and 0
            # here, and a frame stored beside them kept them -- so a result with 288 rows over
            # one scan advertised itself as covering nothing.
            metadata = {
                "time_step": time_step,
                "time_threshold": time_threshold,
                "start_time": None,
                "end_time": None,
                "scan_count": 0
            }

            df = self._process_object(obj, attributes, calculate_times, store_key, metadata)

            if not df.is_empty():
                metadata["start_time"] = float(df["time"].min())
                metadata["end_time"] = float(df["time"].max())
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            
            return df
        except Exception as e:
            logger.error("Failed to calculate time arrays for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("times"))

    @time_execution
    def _calculate_interpolated_orbits(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate interpolated orbit data for active SpaceTelescopes in active scans.

        Args:
            obj: The object to calculate orbits for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "x", "y", "z"] (time as float MJD, positions in meters).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "interpolated_orbits")

            if time_step is not None and time_step <= 0:
                logger.error("Invalid time_step: %s. Must be positive.", time_step)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

            # Nothing to interpolate, so nothing is looked up, computed or stored -- each of which
            # the caching layer reported as a warning when it found the answer empty.
            observations = [obj] if isinstance(obj, Observation) else list(obj.get_observations())
            if not any(observation.has_orbit_file_telescopes() for observation in observations):
                logger.debug("No spacecraft placed from an orbit file in '%s'; no orbits to interpolate",
                             obj.get_observation_code() if isinstance(obj, Observation) else obj.name)
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

            def calculate_orbits(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_scans=True, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.warning("No time arrays available for observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                active_space_telescopes = [
                    tel for tel in telescopes
                    if isinstance(tel, SpaceTelescope) and tel.follows_orbit_file
                ]
                if not active_space_telescopes:
                    logger.debug("No active SpaceTelescopes with use_kep=False in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                times_list = []
                scan_names = []
                telescope_codes = []
                x_list = []
                y_list = []
                z_list = []
                excluded_telescopes = []

                # No lock around this. It held `_orbit_cache_lock` for the whole loop -- every
                # file read and every interpolation -- to guard a cache nothing used, which
                # serialised exactly the work the pipeline runs in parallel. The cache guards
                # itself now, around the dictionary access and nothing else.
                for scan in scans:
                    scan_name = scan.name
                    source = scan.get_source(obs)
                    if not source or not source.isactive:
                        logger.debug("Skipping scan '%s' due to inactive or missing source", scan_name)
                        continue

                    scan_times_df = times_df.filter(pl.col("scan_name") == scan_name)
                    if scan_times_df.is_empty():
                        logger.debug("No valid times for scan '%s' in source '%s'", scan_name, source.name)
                        continue

                    scan_times_mjd = scan_times_df["time"].to_numpy()
                    scan_telescopes = scan.get_telescopes(obs).get_active_items()
                    scan_space_telescopes = [
                        tel for tel in scan_telescopes
                        if isinstance(tel, SpaceTelescope) and tel.follows_orbit_file
                    ]
                    if not scan_space_telescopes:
                        logger.debug("No active SpaceTelescopes in scan '%s'", scan_name)
                        continue

                    start_time = scan.get_start().mjd
                    end_time = start_time + scan.get_duration() / 86400.0

                    for tel in scan_space_telescopes:
                        tel_code = tel.get_code()
                        orbit_file = tel.get_orbit()
                        if not orbit_file:
                            logger.warning("No orbit file for telescope '%s' in scan '%s'; excluding", tel_code, scan_name)
                            excluded_telescopes.append(tel_code)
                            continue

                        try:
                            positions = self._interpolate_orbit(tel, scan_times_mjd, start_time, end_time)
                            if positions.shape[0] != len(scan_times_mjd):
                                logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, positions.shape[0], len(scan_times_mjd))
                                # Keep what was computed and pad the rest. This read
                                # `positions[:k] = positions[:k]` *after* rebinding `positions`
                                # to all-NaN, so it copied NaN onto NaN and threw away every
                                # position the interpolation had produced.
                                computed = positions
                                positions = np.full((len(scan_times_mjd), 3), np.nan)
                                keep = min(computed.shape[0], len(scan_times_mjd))
                                positions[:keep] = computed[:keep]

                            if np.any(np.isnan(positions)):
                                logger.warning("Orbit data for '%s' in scan '%s' contains NaN values", tel_code, scan_name)

                            n_times = len(scan_times_mjd)
                            times_list.append(scan_times_mjd)
                            scan_names.append(np.full(n_times, scan_name, dtype=object))
                            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
                            x_list.append(positions[:, 0])
                            y_list.append(positions[:, 1])
                            z_list.append(positions[:, 2])
                        except ValueError as e:
                            logger.warning("Excluding telescope '%s' in scan '%s' due to interpolation error: %s", tel_code, scan_name, str(e))
                            excluded_telescopes.append(tel_code)

                if excluded_telescopes:
                    logger.info("Excluded %s telescopes: %s", len(set(excluded_telescopes)), ', '.join(set(excluded_telescopes)))

                if not times_list:
                    logger.warning("No valid orbit data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }, schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

                logger.info("Calculated interpolated orbits for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj)
            }
            df = self._process_object(obj, attributes, calculate_orbits, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate interpolated orbits for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("interpolated_orbits"))

    def _interpolate_orbit(self, telescope: SpaceTelescope, times_mjd: np.ndarray, start_time_mjd: float, end_time_mjd: float) -> np.ndarray:
        """Interpolate orbit data for a space telescope over a given array of times.

        Args:
            telescope (SpaceTelescope): The space telescope.
            times_mjd (np.ndarray): Array of times for interpolation (MJD as float).
            start_time_mjd (float): Start time of the required range (MJD).
            end_time_mjd (float): End time of the required range (MJD).

        Returns:
            np.ndarray: Interpolated positions as np.array([[x, y, z], ...]) in meters.
        """
        if telescope.get("use_kep"):
            logger.info("Skipping interpolation for '%s' as use_kep=True", telescope.get_code())
            return np.array([])

        orbit_file = telescope.get_orbit()
        if not orbit_file:
            logger.warning("No orbit file defined for telescope '%s'", telescope.get_code())
            return np.array([])

        try:
            if np.any(np.isnan(times_mjd)) or np.any(np.isinf(times_mjd)):
                logger.error("Invalid MJD values in times for '%s': %s", telescope.get_code(), times_mjd)
                return np.array([])

            orbit_data = self._load_orbit_data(orbit_file, start_time_mjd, end_time_mjd)
            if not orbit_data:
                logger.warning("No valid orbit data for '%s' in time range %s to %s", telescope.get_code(), start_time_mjd, end_time_mjd)
                return np.full((len(times_mjd), 3), np.nan)

            data_times_mjd = orbit_data["times"]
            positions = orbit_data["positions"]

            j2000_mjd = Time("2000-01-01T12:00:00", scale='utc').mjd
            interp_times = (times_mjd - j2000_mjd) * 86400.0
            data_times = (data_times_mjd - j2000_mjd) * 86400.0

            t_start = max((start_time_mjd - j2000_mjd) * 86400.0, data_times[0])
            t_end = min((end_time_mjd - j2000_mjd) * 86400.0, data_times[-1])
            valid_mask = (interp_times >= t_start) & (interp_times <= t_end)
            valid_interp_times = interp_times[valid_mask]

            # What the orbit file does not cover comes back NaN, and NaN reaches a plot as a
            # blank rather than as a complaint -- the same silent-empty failure as the
            # baseline projections defect. Say it once, plainly, naming both spans.
            uncovered = int(np.sum(~valid_mask))
            if uncovered:
                covered_from = j2000_mjd + data_times[0] / 86400.0
                covered_to = j2000_mjd + data_times[-1] / 86400.0
                logger.warning(
                    "The orbit of '%s' covers MJD %.5f to %.5f, which leaves %s of %s requested "
                    "times outside it (MJD %.5f to %.5f). Those positions are unknown, not zero",
                    telescope.get_code(), covered_from, covered_to, uncovered, len(times_mjd),
                    float(np.min(times_mjd)), float(np.max(times_mjd)))

            if not valid_interp_times.size:
                logger.warning("The orbit of '%s' does not cover any of the requested times; "
                               "its position over this scan is unknown", telescope.get_code())
                return np.full((len(times_mjd), 3), np.nan)

            unique_indices = np.unique(data_times, return_index=True)[1]
            filtered_times = data_times[unique_indices]
            filtered_positions = positions[unique_indices]

            if len(filtered_times) < 2:
                logger.warning("Too few points (%s) for interpolation for '%s'", len(filtered_times), telescope.get_code())
                return np.full((len(times_mjd), 3), np.nan)

            method = telescope.get("interpolation_method") or "linear"
            full_positions = np.full((len(times_mjd), 3), np.nan, dtype=float)

            if method == "chebyshev":
                full_positions[valid_mask] = self._chebyshev_positions(
                    filtered_times, filtered_positions, valid_interp_times)
            elif method == "cubic_spline":
                full_positions[valid_mask] = np.array([CubicSpline(filtered_times, pos)(valid_interp_times) for pos in filtered_positions.T]).T
            else:
                full_positions[valid_mask] = np.array([
                    np.interp(valid_interp_times, filtered_times, pos, left=np.nan, right=np.nan)
                    for pos in filtered_positions.T
                ]).T

            if np.any(np.isnan(full_positions)):
                logger.warning("Interpolated positions for '%s' contain NaN values", telescope.get_code())

            logger.info("Interpolated orbit for '%s' using %s with %s points", telescope.get_code(), method, len(valid_interp_times))
            return full_positions

        except Exception as e:
            logger.error("Failed to interpolate orbit for '%s': %s", telescope.get_code(), str(e), exc_info=True)
            return np.full((len(times_mjd), 3), np.nan)

    #: How many orbit samples to keep either side of a scan when a file is read for one. Every
    #: method interpolates between samples, so the ends of a scan need samples beyond them.
    ORBIT_SAMPLE_MARGIN = 8

    #: Degree of each Chebyshev arc, and how many samples one arc spans. Twelve is what
    #: ephemeris systems use per segment; the orbit is smooth over a short arc, and raising the
    #: degree buys nothing while costing conditioning.
    CHEBYSHEV_DEGREE = 12
    CHEBYSHEV_SAMPLES_PER_ARC = 2 * (CHEBYSHEV_DEGREE + 1)

    def _chebyshev_positions(self, sample_times: np.ndarray, sample_positions: np.ndarray,
                             wanted: np.ndarray) -> np.ndarray:
        """Interpolate an orbit with a Chebyshev polynomial per short arc.

        Args:
            sample_times (np.ndarray): The orbit file's times, ascending and unique.
            sample_positions (np.ndarray): The positions at those times, shape (n, 3).
            wanted (np.ndarray): The times to evaluate, within the samples' span.

        Returns:
            np.ndarray: Positions at `wanted`, shape (len(wanted), 3).

        Notes:
            - **One polynomial over the whole file is what this replaces, and it was wrong by
              kilometres.** The degree was capped at 30 and the fit spanned everything the file
              covered, so a Molniya-type orbit -- fast through perigee, slow at apogee -- was
              asked of a single polynomial that cannot describe both. Measured against a Kepler
              orbit of eccentricity 0.94 sampled every 600 s: 846 km at worst and 44.7 km on
              average, where linear interpolation of the same samples was 171 km and 1.0 km.
              A space telescope 40 km from where it is said to be puts the same error into every
              baseline, which is why `linear` agreed with an independent tool and this did not.
            - Arcs are cut along the **samples**, a fixed number of them each, rather than along
              the requested span. An arc is then the same number of samples wherever it sits --
              short in time through perigee, where the orbit turns fastest, and long at apogee.
              Cutting the requested span into equal pieces of time instead left 43 km at perigee.
            - Each arc is fitted on its own samples plus half a degree either side, so the joins
              are informed from both directions rather than extrapolated to.
            - Now 19.5 km at worst and 0.063 km on average on that same orbit, which is a cubic
              spline's accuracy (14.9 km, 0.016 km) and 700 times better on average than what it
              replaces. What remains is at perigee and belongs to the sampling: no method
              recovers a turn the file did not record.
        """
        degree = self.CHEBYSHEV_DEGREE
        positions = np.full((len(wanted), 3), np.nan, dtype=float)
        if not len(wanted):
            return positions

        first = max(int(np.searchsorted(sample_times, wanted.min())) - 1, 0)
        last = min(int(np.searchsorted(sample_times, wanted.max())) + 1, len(sample_times) - 1)
        if last <= first:
            first, last = 0, len(sample_times) - 1

        cuts = list(range(first, last + 1, self.CHEBYSHEV_SAMPLES_PER_ARC))
        if cuts[-1] != last:
            cuts.append(last)

        for arc in range(len(cuts) - 1):
            start_index, end_index = cuts[arc], cuts[arc + 1]
            start, end = sample_times[start_index], sample_times[end_index]
            # The closing arc owns its right-hand edge; the others stop short of it, so no
            # requested time is evaluated twice or missed at a join.
            final = arc == len(cuts) - 2
            here = ((wanted >= start) & (wanted <= end) if final
                    else (wanted >= start) & (wanted < end))
            if not here.any():
                continue

            low = max(start_index - degree // 2, 0)
            high = min(end_index + degree // 2 + 1, len(sample_times))
            arc_times, arc_positions = sample_times[low:high], sample_positions[low:high]
            span = end - start
            if span <= 0:
                positions[here] = sample_positions[start_index]
                continue

            scaled = 2 * (arc_times - start) / span - 1
            asked = 2 * (wanted[here] - start) / span - 1
            fitted = min(degree, len(arc_times) - 1)
            positions[here] = np.array(
                [chebyshev.Chebyshev.fit(scaled, axis, fitted)(asked)
                 for axis in arc_positions.T]).T

        return positions

    def _orbit_within(self, orbit_data: Dict[str, np.ndarray], orbit_file: str,
                      start_time_mjd: Optional[float],
                      end_time_mjd: Optional[float]) -> Dict[str, np.ndarray]:
        """Return the part of a parsed orbit that covers a span, with samples either side.

        Args:
            orbit_data (Dict[str, np.ndarray]): The whole file, parsed.
            orbit_file (str): Its path, for the message when nothing covers the span.
            start_time_mjd (Optional[float]): Start of the span, or None for everything.
            end_time_mjd (Optional[float]): End of the span.

        Returns:
            Dict[str, np.ndarray]: `times`, `positions` and `velocities`, cut to the span plus
                `ORBIT_SAMPLE_MARGIN` samples on each side. Empty when the file covers none of it.

        Notes:
            - **The margin is the point.** Every method here interpolates *between* samples, and
              this used to cut the file to the scan exactly -- so the first and last moments of
              a scan had nothing beyond them to lean on and every method extrapolated there.
              That is the worst place to extrapolate and the hardest to notice, because the
              numbers still come out.
            - Separate from parsing so the parse can be cached: the file does not change between
              one scan and the next, only the span asked of it does.
        """
        times_mjd = orbit_data["times"]
        if start_time_mjd is None or end_time_mjd is None:
            return orbit_data

        mask = (times_mjd >= start_time_mjd) & (times_mjd <= end_time_mjd)
        if not np.any(mask):
            logger.warning("No orbit data within time range %s to %s for file '%s'",
                           start_time_mjd, end_time_mjd, orbit_file)
            return {}

        inside = np.flatnonzero(mask)
        first = max(int(inside[0]) - self.ORBIT_SAMPLE_MARGIN, 0)
        last = min(int(inside[-1]) + self.ORBIT_SAMPLE_MARGIN + 1, len(times_mjd))
        return {"times": orbit_data["times"][first:last],
                "positions": orbit_data["positions"][first:last],
                "velocities": orbit_data["velocities"][first:last]}

    def _load_orbit_data(self, orbit_file: str, start_time_mjd: Optional[float] = None, end_time_mjd: Optional[float] = None) -> Dict[str, np.ndarray]:
        """Load orbit data from a CCSDS OEM 2.0 styled file, optionally filtering by time range.

        Args:
            orbit_file (str): Path to the orbit file.
            start_time_mjd (Optional[float]): Start time for filtering data (MJD).
            end_time_mjd (Optional[float]): End time for filtering data (MJD).

        Returns:
            Dict[str, np.ndarray]: Dictionary containing times (MJD), positions (meters), and velocities (m/s).
        """
        if not os.path.isfile(orbit_file):
            raise FileNotFoundError(f"Orbit file '{orbit_file}' not found")

        # Keyed by what the file looked like, so an orbit edited on disk is re-read rather than
        # answered from a stale parse.
        stamp = os.stat(orbit_file)
        key = (os.path.abspath(orbit_file), stamp.st_mtime_ns, stamp.st_size)
        with self._orbit_cache_lock:
            cached = self._orbit_cache.get(key)
        if cached is not None:
            return self._orbit_within(cached, orbit_file, start_time_mjd, end_time_mjd)

        try:
            with open(orbit_file, 'r') as f:
                lines = f.readlines()

            data_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            data_section = False
            valid_lines = []

            for line in data_lines:
                if "META_STOP" in line:
                    data_section = True
                    continue
                if not data_section:
                    continue
                if "COVARIANCE_START" in line:
                    break
                parts = re.split(r'\s+', line.strip())
                if len(parts) == 7:
                    valid_lines.append(line)

            if len(valid_lines) < 2:
                raise ValueError(f"Orbit file must contain at least 2 data points, got {len(valid_lines)}")

            time_strs = [re.split(r'\s+', line)[0] for line in valid_lines]
            times = Time(time_strs, format='isot', scale='utc')
            times_mjd = times.mjd

            positions = np.zeros((len(valid_lines), 3))
            velocities = np.zeros((len(valid_lines), 3))
            for i, line in enumerate(valid_lines):
                parts = re.split(r'\s+', line)
                x, y, z = map(float, parts[1:4])  # km -> m
                vx, vy, vz = map(float, parts[4:7])  # km/s -> m/s
                positions[i] = [x * 1000, y * 1000, z * 1000]
                velocities[i] = [vx * 1000, vy * 1000, vz * 1000]

            if np.any(np.isnan(positions)) or np.any(np.isnan(velocities)):
                logger.warning("Orbit file '%s' contains NaN values", orbit_file)
                return {}

            orbit_data = {
                "times": times_mjd,
                "positions": positions,
                "velocities": velocities
            }

            with self._orbit_cache_lock:
                self._orbit_cache[key] = orbit_data
            logger.info("Loaded orbit data from '%s' with %s points", orbit_file, len(orbit_data['times']))
            return self._orbit_within(orbit_data, orbit_file, start_time_mjd, end_time_mjd)

        except FileNotFoundError:
            logger.error("Orbit file '%s' not found", orbit_file)
            raise
        except ValueError as e:
            logger.error("Error parsing orbit file: %s", str(e))
            raise
        except Exception as e:
            logger.warning("Unexpected error loading orbit file '%s': %s", orbit_file, str(e), exc_info=True)
            return {}

    @time_execution
    def _calculate_telescope_positions(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate telescope positions in GCRS (J2000) for all active scans using times from time_arrays and interpolated orbits.

        Args:
            obj: The object to calculate positions for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "x", "y", "z"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_positions")

            def calculate_positions(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                if times_df.is_empty():
                    logger.error("No time data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                has_orbit_telescopes = any(isinstance(tel, SpaceTelescope) and tel.follows_orbit_file for tel in telescopes)
                orbit_df = pl.DataFrame()
                if has_orbit_telescopes:
                    orbit_attrs = {"time_step": time_step, "store_key": "interpolated_orbits", "recalculate": False}
                    orbit_df = self._calculate_interpolated_orbits(obs, orbit_attrs)
                    logger.debug("Orbit data for '%s': %s", obs.get_observation_code(), not orbit_df.is_empty())

                times_list = []
                scan_names = []
                telescope_codes = []
                x_list = []
                y_list = []
                z_list = []
                excluded_telescopes = []

                self._warm_ground_positions(obs, scans, times_df)

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obs).get_active_items()])
                            continue
                        scan_orbits = orbit_df.filter(pl.col("scan_name") == scan_name) if not orbit_df.is_empty() else pl.DataFrame()
                        futures[executor.submit(
                            self._process_scan_positions, scan, obs, scan_times, scan_orbits
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, x, y, z = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            x_list.append(x)
                            y_list.append(y)
                            z_list.append(z)
                        else:
                            scan = next(s for s in scans if s.name == scan_name)
                            excluded_telescopes.extend([tel.get_code() for tel in scan.get_telescopes(obs).get_active_items()])

                if excluded_telescopes:
                    logger.info("Excluded %s telescopes: %s", len(set(excluded_telescopes)), ', '.join(set(excluded_telescopes)))

                if not times_list:
                    logger.warning("No valid positions computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "x": np.concatenate(x_list),
                    "y": np.concatenate(y_list),
                    "z": np.concatenate(z_list)
                }, schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

                logger.info("Calculated positions for %s scans in '%s', DF rows: %s", df['scan_name'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj)
            }
            df = self._process_object(obj, attributes, calculate_positions, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate telescope positions for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_positions"))

    def _process_scan_positions(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, orbit_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process telescope positions for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            orbit_df (pl.DataFrame): Precomputed orbit data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, x, y, z) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source.name)
            return None
        
        obstime=Time(times_mjd, format="mjd", scale="utc")

        times_list = []
        scan_names = []
        telescope_codes = []
        x_list = []
        y_list = []
        z_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            if isinstance(tel, SpaceTelescope) and tel.follows_orbit_file:
                tel_orbit = orbit_df.filter(pl.col("telescope_code") == tel_code)
                if tel_orbit.is_empty():
                    logger.warning("No orbit data for telescope '%s' in scan '%s'", tel_code, scan_name)
                    continue
                positions = tel_orbit.select(["x", "y", "z"]).to_numpy()
                if len(positions) != n_times:
                    logger.warning("Orbit data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(positions), n_times)
                    positions = np.full((n_times, 3), np.nan)
                    positions[:min(len(positions), n_times)] = tel_orbit.select(["x", "y", "z"]).to_numpy()[:n_times]
            else:
                positions = self._compute_telescope_position(tel, times_mjd, obstime=obstime)
                if positions.shape[0] != n_times:
                    logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, positions.shape[0], n_times)
                    # As above: rebinding first meant this copied NaN onto NaN and lost
                    # every position that had been computed.
                    computed = positions
                    positions = np.full((n_times, 3), np.nan)
                    keep = min(computed.shape[0], n_times)
                    positions[:keep] = computed[:keep]

            if np.all(np.isnan(positions)):
                logger.warning("All positions are NaN for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            x_list.append(positions[:, 0])
            y_list.append(positions[:, 1])
            z_list.append(positions[:, 2])

        if not times_list:
            logger.warning("No valid positions computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed %s telescope positions for scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(x_list),
            np.concatenate(y_list),
            np.concatenate(z_list)
        )

    def _compute_telescope_position(self, telescope: Telescope | SpaceTelescope, times_mjd: np.ndarray, obstime: Optional[Time] = None) -> np.ndarray:
        """Compute a telescope's GCRS position at specified times.

        Optimized version:
        - Fully vectorized Kepler solver (no np.vectorize).
        - Single matrix multiplication for orbital rotation.
        - Lazy J2000 MJD caching on the calculator instance.
        - Single Time object for obstime.

        Args:
            telescope (Telescope | SpaceTelescope): The telescope to compute position for.
            times_mjd (np.ndarray): Array of times for calculation (MJD as float).

        Returns:
            np.ndarray: GCRS coordinates (x, y, z) in meters, shape (n_times, 3).
        """
        n_times = len(times_mjd)
        nan_result = np.full((n_times, 3), np.nan, dtype=float)

        if not hasattr(self, "_j2000_mjd"):
            self._j2000_mjd = Time("2000-01-01T12:00:00").mjd

        try:
            if isinstance(telescope, Telescope) and not isinstance(telescope, SpaceTelescope):
                key, times_mjd = self._ground_key(telescope, times_mjd)
                with self._topocentric_lock:
                    held = self._topocentric_cache.get(key)
                if held is not None:
                    return held[0]
                x, y, z = telescope.get_coordinates()
                res = telescope.get(["vx", "vy", "vz"])
                vx, vy, vz = res["vx"], res["vy"], res["vz"]

                # **Years, because a station's velocity is metres per year.** That is what VEX
                # writes as `site_velocity ... m/yr`, what CFX's `TLSC_PAR` carries, and what the
                # editor holds. This multiplied it by *seconds* since J2000: a station moving
                # 23 mm a year was placed 9 500 km from where it is -- Westerbork, Svetloe and
                # Badary read from a RadioAstron schedule all sat inside the Earth, and every
                # visibility, uv point and elevation computed for them was for nowhere. The
                # fixture's stations do not move, so nothing had ever noticed.
                #
                # J2000 is taken as the epoch the coordinates hold at. A file states its own
                # (VEX `site_position_epoch`, CFX's eighth field) and the model does not carry it;
                # at these speeds the difference is centimetres.
                dt = (times_mjd - self._j2000_mjd) / 365.25

                itrs_coords = CartesianRepresentation(
                    x + vx * dt,
                    y + vy * dt,
                    z + vz * dt,
                    unit=u.m
                )

                if obstime is None:
                    obstime=Time(times_mjd, format="mjd", scale="utc")

                itrs = ITRS(itrs_coords, obstime=obstime)
                gcrs = itrs.transform_to(GCRS(obstime=obstime))

                pos = np.stack([gcrs.cartesian.x.value,
                                gcrs.cartesian.y.value,
                                gcrs.cartesian.z.value], axis=-1)

                if np.any(np.isnan(pos)):
                    logger.warning("Computed NaN position for ground telescope '%s'", telescope.get_code())
                pos = np.array(pos, dtype=float)
                self._hold_topocentric(key, (pos,))
                return pos

            elif isinstance(telescope, SpaceTelescope) and telescope.get("use_kep"):
                kepler = telescope.get("kepler_elements")
                if kepler is None:
                    logger.warning("No Keplerian elements defined for telescope '%s'", telescope.get_code())
                    return nan_result

                a = kepler["a"]          # m
                e = kepler["e"]
                i = np.radians(kepler["i"])
                raan = np.radians(kepler["raan"])
                argp = np.radians(kepler["argp"])
                nu0 = np.radians(kepler["nu"])
                epoch = kepler["epoch"].mjd
                mu = kepler["mu"]
                n = np.sqrt(mu / a**3)

                dt = (times_mjd - epoch) * 86400.0
                M = nu0 + n * dt

                E = self._solve_kepler(M, e)

                # True anomaly
                cos_nu = (np.cos(E) - e) / (1 - e * np.cos(E))
                sin_nu = (np.sqrt(1 - e**2) * np.sin(E)) / (1 - e * np.cos(E))
                nu = np.arctan2(sin_nu, cos_nu)

                r = a * (1 - e**2) / (1 + e * np.cos(nu))

                # position in orbital plane (n_times, 3)
                p = np.column_stack((
                    r * np.cos(nu),
                    r * np.sin(nu),
                    np.zeros_like(r)
                ))

                # rotation matrix (constant per telescope)
                c_raan, s_raan = np.cos(raan), np.sin(raan)
                c_i, s_i = np.cos(i), np.sin(i)
                c_argp, s_argp = np.cos(argp), np.sin(argp)

                R1 = np.array([[c_raan, -s_raan, 0],
                               [s_raan,  c_raan, 0],
                               [0,       0,      1]], dtype=float)
                R2 = np.array([[1, 0,      0],
                               [0, c_i, -s_i],
                               [0, s_i,  c_i]], dtype=float)
                R3 = np.array([[c_argp, -s_argp, 0],
                               [s_argp,  c_argp, 0],
                               [0,       0,      1]], dtype=float)

                R = R1 @ R2 @ R3

                # vectorized rotation: p (n,3) row-vectors → pos = p @ R.T
                pos = p @ R.T

                if np.any(np.isnan(pos)):
                    logger.warning("Keplerian position for '%s' contains NaN", telescope.get_code())
                return pos

            else:
                logger.warning("Position for SpaceTelescope '%s' should be precomputed in interpolated_orbits", telescope.get_code())
                return nan_result

        except Exception as e:
            logger.warning("Unexpected error in computing position for '%s': %s", telescope.get_code(), str(e), exc_info=True)
            return nan_result

    def _solve_kepler(self, M: np.ndarray, e: float, tol: float = 1e-8, max_iter: int = 200) -> np.ndarray:
        """Solve Kepler's equation for an array of mean anomalies (fully vectorized Newton-Raphson).

        This replaces the original scalar + np.vectorize version and gives 10-100x speedup
        for typical VLBI time arrays (n_times > 1000).

        Args:
            M (np.ndarray): Mean anomaly array (radians).
            e (float): Eccentricity (< 1).
            tol (float): Convergence tolerance.
            max_iter (int): Maximum iterations per element.

        Returns:
            np.ndarray: Eccentric anomaly array (radians).
        """
        if e >= 1.0:
            raise ValueError("Eccentricity must be < 1 for elliptical orbit")

        M_arr = np.asarray(M, dtype=float)
        n = len(M_arr)

        # starter value
        if e < 0.9:
            x = M_arr.copy()
        else:
            x = np.full(n, np.pi, dtype=float)

        for _ in range(max_iter):
            f = x - e * np.sin(x) - M_arr
            df = 1.0 - e * np.cos(x)

            # safe division
            dx = np.zeros_like(x)
            valid = np.abs(df) > 1e-12
            dx[valid] = -f[valid] / df[valid]

            x += dx

            if np.all(np.abs(dx) < tol):
                break
        else:
            n_unconv = np.sum(np.abs(dx) >= tol)
            logger.warning(
                f"Kepler's equation did not converge for {n_unconv}/{n} points "
                f"(e={e:.4f}, max|dx|={np.max(np.abs(dx)):.2e})"
            )

        return x

    @time_execution
    def _calculate_source_visibility(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate source visibility for all active scans in the observation or project.

        Args:
            obj: The object to calculate visibility for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "visibility"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "source_visibility")
            position_store_key = attributes.get("position_store_key", "telescope_positions")

            def calculate_visibility(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or position data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                is_visible_list = []

                self._warm_topocentric(obs, scans, times_df, position_df)

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_source_visibility, scan, obs, scan_times, scan_positions
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, is_visible = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            is_visible_list.append(is_visible)

                if not times_list:
                    logger.warning("No valid visibility data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "visibility": np.concatenate(is_visible_list)
                }, schema=CalculatedDataStructure.get_dtypes("source_visibility"))

                logger.info("Calculated visibility for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "position_store_key": position_store_key
            }
            df = self._process_object(obj, attributes, calculate_visibility, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate source visibility for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("source_visibility"))

    def _process_source_visibility(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process source visibility for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, is_visible) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None


        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        is_visible_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty():
                logger.warning("No position data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            if len(positions) != n_times:
                logger.warning("Position data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(positions), n_times)
                # `positions` is all-NaN of length n_times by the time the slice is taken, so
                # the left-hand side was always the full length while the right-hand side was
                # however many rows there really were -- a shape mismatch whenever this branch
                # was reached with fewer.
                found = positions
                positions = np.full((n_times, 3), np.nan)
                keep = min(len(found), n_times)
                positions[:keep] = found[:keep]

            nan_positions = np.any(np.isnan(positions), axis=1)
            is_visible = np.full(n_times, False, dtype=bool)

            if isinstance(tel, SpaceTelescope):
                is_visible[~nan_positions] = True
            else:
                mount_type = tel.get("mount_type").value
                valid_positions = ~nan_positions
                if not np.any(valid_positions):
                    logger.warning("All positions are NaN for ground telescope '%s' in scan '%s'", tel_code, scan_name)
                    continue

                # **Only the frame the mount is limited in.** Both transforms were computed for
                # every station and one of them thrown away: an azimuthal dish is bounded in
                # elevation and azimuth and never looks at the hour angle, and an equatorial one
                # is the other way round. Each is an erfa transform over the whole time grid, so
                # this is half the cost of the step for an array of one kind -- which every
                # array in these examples is.
                if mount_type == "AZIM":
                    az, el, _ = self._topocentric(source, positions, times_mjd, "altaz")
                    el_range = tel.get_elevation_range()
                    az_range = tel.get_azimuth_range()
                    is_visible[valid_positions] = (
                        (float(el_range[0]) <= el[valid_positions]) &
                        (el[valid_positions] <= float(el_range[1])) &
                        (float(az_range[0]) <= az[valid_positions]) &
                        (az[valid_positions] <= float(az_range[1]))
                    )
                elif mount_type == "EQUA":
                    ha, dec, _ = self._topocentric(source, positions, times_mjd, "hadec")
                    ha_range = tel.get_azimuth_range()
                    dec_range = tel.get_elevation_range()
                    is_visible[valid_positions] = (
                        (float(dec_range[0]) <= dec[valid_positions]) &
                        (dec[valid_positions] <= float(dec_range[1])) &
                        (float(ha_range[0]) <= ha[valid_positions]) &
                        (ha[valid_positions] <= float(ha_range[1]))
                    )
                else:
                    logger.warning("Unsupported mount type '%s' for telescope '%s' in scan '%s'", mount_type, tel_code, scan_name)
                    continue

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            is_visible_list.append(is_visible)

            logger.debug("Computed visibility for telescope '%s' in scan '%s': %s visible points", tel_code, scan_name, np.sum(is_visible))

        if not times_list:
            logger.warning("No visibility data computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(is_visible_list)
        )

    @time_execution
    def _calculate_uv_coverage(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate (u,v,w) coverage for all scans in the observation or project in geometric coordinates (meters).

        Args:
            obj: The object to calculate UV coverage for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "baseline", "source_name", "u", "v", "w"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "uv_coverage")
            if "freq_name" in attributes:
                logger.info("Ignoring 'freq_name' attribute for UV coverage calculation in geometric coordinates")

            def calculate_uv(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": "source_visibility", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                times_list = []
                scan_names = []
                baselines = []
                source_names = []
                u_list = []
                v_list = []
                w_list = []

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_uv_coverage, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, baseline_arr, source_name_arr, u, v, w = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            baselines.append(baseline_arr)
                            source_names.append(source_name_arr)
                            u_list.append(u)
                            v_list.append(v)
                            w_list.append(w)

                if not times_list:
                    logger.warning("No valid UV coverage data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "source_name": np.concatenate(source_names),
                    "scan_name": np.concatenate(scan_names),
                    "baseline": np.concatenate(baselines),
                    "u": np.concatenate(u_list),
                    "v": np.concatenate(v_list),
                    "w": np.concatenate(w_list)
                }, schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

                logger.info("Calculated UV coverage for %s scans across %s baselines in '%s', DF rows: %s", df['scan_name'].unique().len(), df['baseline'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj)
            }
            df = self._process_object(obj, attributes, calculate_uv, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                metadata["baseline_count"] = df["baseline"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate UV coverage for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("uv_coverage"))

    def _process_uv_coverage(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process UV coverage for a single scan using vectorized computations in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, baselines, source_names, u, v, w) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if len(active_telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) for UV coverage in scan '%s'", len(active_telescopes), scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        tel_codes = [tel.get_code() for tel in active_telescopes]
        n_tels = len(tel_codes)

        positions = np.full((n_tels, n_times, 3), np.nan, dtype=float)
        visibility = np.full((n_tels, n_times), False, dtype=bool)

        for i, tel_code in enumerate(tel_codes):
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if not tel_positions.is_empty() and len(tel_positions) == n_times:
                positions[i] = tel_positions.select(["x", "y", "z"]).to_numpy()
            else:
                logger.warning("Missing or mismatched position data for telescope '%s' in scan '%s'", tel_code, scan_name)
            if not tel_visibility.is_empty() and len(tel_visibility) == n_times:
                visibility[i] = tel_visibility["visibility"].to_numpy()
            else:
                logger.warning("Missing or mismatched visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)

        try:
            uv_points = self._compute_uv_at_time(active_telescopes, times_mjd, source, visibility, positions)
        except Exception as e:
            logger.error("Failed to calculate UV coverage for scan '%s': %s", scan_name, str(e), exc_info=True)
            return None

        if not uv_points:
            logger.warning("No valid UV points computed for scan '%s'", scan_name)
            return None

        times_list = []
        scan_names = []
        baselines = []
        source_names = []
        u_list = []
        v_list = []
        w_list = []

        for pair, uvw in uv_points.items():
            valid_indices = ~np.any(np.isnan(uvw), axis=1)
            n_valid = np.sum(valid_indices)
            if n_valid == 0:
                logger.debug("No valid UVW points for baseline '%s' in scan '%s'", pair, scan_name)
                continue
            times_list.append(times_mjd[valid_indices])
            scan_names.append(np.full(n_valid, scan_name, dtype=object))
            baselines.append(np.full(n_valid, pair, dtype=object))
            source_names.append(np.full(n_valid, source_name, dtype=object))
            u_list.append(uvw[valid_indices, 0])
            v_list.append(uvw[valid_indices, 1])
            w_list.append(uvw[valid_indices, 2])

        if not times_list:
            logger.warning("No valid UV coverage data computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed UV coverage for %s baselines in scan '%s'", len(uv_points), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(baselines),
            np.concatenate(source_names),
            np.concatenate(u_list),
            np.concatenate(v_list),
            np.concatenate(w_list)
        )

    def _compute_uv_at_time(self, telescopes: List[Telescope | SpaceTelescope], times_mjd: np.ndarray, source: Optional[Source] = None, visibility: Optional[np.ndarray] = None, gcrs_positions: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """Compute UVW coordinates for multiple times in geometric coordinates (meters) using vectorized operations.

        Args:
            telescopes (List[Telescope | SpaceTelescope]): List of telescopes.
            times_mjd (np.ndarray): Array of observation times (MJD as float).
            source (Optional[Source]): Source for UV calculation.
            visibility (Optional[np.ndarray]): Visibility array of shape (n_telescopes, n_times).
            gcrs_positions (Optional[np.ndarray]): GCRS positions of shape (n_telescopes, n_times, 3).

        Returns:
            Dict[str, np.ndarray]: UVW coordinates in meters per baseline, formatted as {baseline: np.array([[u,v,w], ...])},
            where the array has shape (n_times, 3) and contains NaN for non-visible times or invalid positions.
        """
        if not telescopes or len(telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) to compute (u,v,w)", len(telescopes))
            return {}
        if source is None:
            logger.warning("No source provided; cannot calculate (u,v,w)")
            return {}
        if visibility is None or gcrs_positions is None:
            logger.warning("Missing visibility or position data; cannot calculate (u,v,w)")
            return {}

        n_tels = len(telescopes)
        n_times = len(times_mjd)
        if visibility.shape != (n_tels, n_times):
            logger.error("Visibility shape %s does not match expected (%s, %s)", visibility.shape, n_tels, n_times)
            return {}
        if gcrs_positions.shape != (n_tels, n_times, 3):
            logger.error("Position shape %s does not match expected (%s, %s, 3)", gcrs_positions.shape, n_tels, n_times)
            return {}

        i, j = np.triu_indices(n_tels, k=1)
        pairs = [f"{telescopes[i].get_code()}-{telescopes[j].get_code()}" for i, j in zip(i, j)]

        baselines = gcrs_positions[i] - gcrs_positions[j]  # shape: (n_pairs, n_times, 3)

        vis_mask = visibility[i] & visibility[j]  # shape: (n_pairs, n_times)
        pos_nan = np.any(np.isnan(gcrs_positions), axis=2)  # shape: (n_tels, n_times)
        baseline_nan = pos_nan[i] | pos_nan[j]  # shape: (n_pairs, n_times)
        vis_mask = vis_mask & ~baseline_nan

        source_coord = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg, frame='icrs')
        ra = source_coord.ra.rad
        dec = source_coord.dec.rad
        cos_ra, sin_ra = np.cos(ra), np.sin(ra)
        cos_dec, sin_dec = np.cos(dec), np.sin(dec)
        rotation_matrix = np.array([
            [-sin_ra, cos_ra, 0],
            [-cos_ra * sin_dec, -sin_ra * sin_dec, cos_dec],
            [cos_ra * cos_dec, sin_ra * cos_dec, sin_dec]
        ])  # shape: (3, 3)

        uvw = np.einsum('ijk,lk->ijl', baselines, rotation_matrix)  # shape: (n_pairs, n_times, 3)
        uvw[~vis_mask] = np.nan

        uv_points = {}
        for pair_idx, pair in enumerate(pairs):
            uv_points[pair] = uvw[pair_idx]
            valid_count = np.sum(~np.any(np.isnan(uvw[pair_idx]), axis=1))
            logger.debug("Computed %s valid UVW points for baseline '%s' (total %s points)", valid_count, pair, n_times)

        if not uv_points:
            logger.warning("No valid UVW points computed for any baseline")
        return uv_points

    @time_execution
    def _calculate_sun_angles(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate angular separation between source and Sun for all active scans in geometric coordinates.

        Args:
            obj: The object to calculate sun angles for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "angle"] (angles in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sun_angles")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")

            def calculate_sun_angles(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                sun_angles_list = []

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_sun_angles, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, sun_angles = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            sun_angles_list.append(sun_angles)

                if not times_list:
                    logger.warning("No valid sun angles computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "angle": np.concatenate(sun_angles_list)
                }, schema=CalculatedDataStructure.get_dtypes("sun_angles"))

                logger.info("Calculated sun angles for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_sun_angles, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate sun angles for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sun_angles"))

    def _process_sun_angles(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process Sun angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, sun_angles) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [tel for tel in scan_telescopes.get_items() if tel.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        sun_angles_list = []

        # **Directions, subtracted and dotted -- once per scan, not three transforms per
        # station.** An angle between two directions does not depend on the frame they are
        # written in, so neither needs to reach AltAz. What being on a station does change is the
        # Sun's parallax, and that is exactly the difference of two vectors this step already
        # has: the Sun from the geocentre, and the station from the geocentre, both GCRS.
        #
        # Measured on the fixture at a 60 s step: 1.12 s to 0.18 s, and 0.21" from astropy's
        # topocentric `get_body` against 0.013" before -- the difference is diurnal aberration,
        # which a limit stated in degrees cannot see. For a spacecraft it is a correction: the
        # Sun was taken from the geocentre, which for an orbit reaching 350 000 km is off by up
        # to 0.13 degrees.
        obstime = Time(times_mjd, format="mjd", scale="utc")
        sun_from_geocentre = get_sun(obstime).cartesian.xyz.to_value(u.m).T  # (n_times, 3)
        towards_source = SkyCoord(ra=source.ra_degrees * u.deg, dec=source.dec_degrees * u.deg,
                                  frame="icrs").transform_to(GCRS(obstime=obstime)).cartesian
        towards_source = np.column_stack([towards_source.x.value, towards_source.y.value,
                                          towards_source.z.value])
        towards_source /= np.linalg.norm(towards_source, axis=1)[:, np.newaxis]

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("No position or visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy().astype(bool)
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s': positions=%s, visibility=%s, expected %s", tel_code, scan_name, len(positions), len(visibility), n_times)
                continue

            nan_positions = np.any(np.isnan(positions), axis=1)
            if np.mean(nan_positions) > 0.5:
                logger.warning("High NaN ratio (%.2f%%) in positions for telescope '%s' in scan '%s'", 100 * np.mean(nan_positions), tel_code, scan_name)
                continue

            sun_angles = np.full(n_times, np.nan, dtype=float)
            is_visible = visibility & ~nan_positions

            if np.any(is_visible):
                towards_sun = sun_from_geocentre[is_visible] - positions[is_visible]
                towards_sun /= np.linalg.norm(towards_sun, axis=1)[:, np.newaxis]
                cos_sep = np.clip(np.sum(towards_sun * towards_source[is_visible], axis=1), -1.0, 1.0)
                sun_angles[is_visible] = np.degrees(np.arccos(cos_sep))

                logger.debug("Computed %s sun angles for telescope '%s' in scan '%s'", np.sum(is_visible), tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            sun_angles_list.append(sun_angles)

        if not times_list:
            logger.warning("No sun angles computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed sun angles for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(sun_angles_list)
        )

    @time_execution
    def _calculate_az_el(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate azimuth/elevation or hour angle/declination angles for active ground telescopes in all active scans.

        Args:
            obj: The object to calculate az/el or ha/dec angles for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "position_store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "source_name", "az_ha", "el_dec"] (angles in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")

            def calculate_az_el(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug("No ground telescopes in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time, position, or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                az_ha_list = []
                el_dec_list = []

                self._warm_topocentric(obs, scans, times_df, position_df)

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_az_el, scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, az_ha, el_dec = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            az_ha_list.append(az_ha)
                            el_dec_list.append(el_dec)

                if not times_list:
                    logger.warning("No valid az/el or ha/dec angles computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "az": np.concatenate(az_ha_list),
                    "el": np.concatenate(el_dec_list)
                }, schema=CalculatedDataStructure.get_dtypes("az_el"))

                logger.info("Calculated az/el or ha/dec for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_az_el, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate az/el or ha/dec for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("az_el"))

    def _process_az_el(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process az/el or ha/dec angles for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, source_names, az_ha, el_dec) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive and not isinstance(t, SpaceTelescope)]
        if not active_telescopes:
            logger.warning("No active ground telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None


        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        az_ha_list = []
        el_dec_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            mount_type = tel.get("mount_type").value
            if mount_type not in ["AZIM", "EQUA"]:
                logger.warning("Unsupported mount type '%s' for telescope '%s' in scan '%s'", mount_type, tel_code, scan_name)
                continue

            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("No position or visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()
            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s': positions=%s, visibility=%s, expected %s", tel_code, scan_name, len(positions), len(visibility), n_times)
                positions = np.full((n_times, 3), np.nan)[:min(len(positions), n_times)] if len(positions) > 0 else np.full((n_times, 3), np.nan)
                visibility = np.full(n_times, False)[:min(len(visibility), n_times)] if len(visibility) > 0 else np.full(n_times, False)

            nan_positions = np.any(np.isnan(positions), axis=1)
            if np.mean(nan_positions) > 0.5:
                logger.warning(f"High NaN ratio ({np.mean(nan_positions):.2%}) in positions for telescope '{tel_code}' in scan '{scan_name}'")
                continue

            az_ha = np.full(n_times, np.nan, dtype=float)
            el_dec = np.full(n_times, np.nan, dtype=float)
            is_visible = visibility & ~nan_positions

            if np.any(is_visible):
                first, second, _ = self._topocentric(
                    source, positions, times_mjd, "altaz" if mount_type == "AZIM" else "hadec")
                az_ha[is_visible] = first[is_visible]
                el_dec[is_visible] = second[is_visible]

                logger.debug("Computed %s az/el or ha/dec angles for telescope '%s' in scan '%s'", np.sum(is_visible), tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            az_ha_list.append(az_ha)
            el_dec_list.append(el_dec)

        if not times_list:
            logger.warning("No valid az/el or ha/dec angles computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed az/el or ha/dec for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(az_ha_list),
            np.concatenate(el_dec_list)
        )

    @time_execution
    def _calculate_telescope_az_el(self, obj: "Observation | ScheduleProject", attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate where each ground station must point to see a space telescope.

        Args:
            obj: The observation, or a project of them.
            attributes: Parameters including "target_telescope" -- the code of the spacecraft to
                point at -- and "time_step", "store_key", "position_store_key",
                "orbit_store_key", "recalculate".

        Returns:
            pl.DataFrame: Columns ["time", "target_code", "scan_name", "telescope_code", "az",
                "el", "range"], with angles in degrees and range in metres.

        Notes:
            - A calculation of its own that the user asks for by name, never part of an
              ordinary observation. Pointing at a spacecraft is a different question from
              observing a source, and a project with no spacecraft in it must pay nothing.
            - The target is named by a parameter rather than by a new kind of observation or a
              time-dependent `Source`. An observation already holds its telescopes; asking when
              one of them is visible from the others needs no new entity, and the request is
              already data, so one more attribute is the shape the architecture has.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_az_el")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            orbit_store_key = attributes.get("orbit_store_key", "interpolated_orbits")
            target_code = attributes.get("target_telescope")

            if not target_code:
                logger.error("No 'target_telescope' given; there is nothing to point at")
                return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

            def calculate_telescope_az_el(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                empty = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return empty

                target = next((tel for tel in telescopes
                               if isinstance(tel, SpaceTelescope) and tel.get_code() == target_code), None)
                if target is None:
                    logger.warning("No active space telescope '%s' in observation '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                observers = [tel for tel in telescopes
                             if not isinstance(tel, SpaceTelescope) and tel.get_code() != target_code]
                if not observers:
                    logger.warning("No ground stations to see '%s' from in observation '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                orbit_attrs = {"time_step": time_step, "store_key": orbit_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                orbit_df = self._calculate_interpolated_orbits(obs, orbit_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or station position data for '%s'", obs.get_observation_code())
                    return empty

                collected = []
                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s'", scan_name)
                            continue
                        futures[executor.submit(
                            self._process_telescope_az_el, scan, obs, scan_times,
                            position_df.filter(pl.col("scan_name") == scan_name),
                            orbit_df.filter(pl.col("scan_name") == scan_name),
                            target, observers)] = scan_name

                    for future in futures:
                        result = future.result()
                        if result is not None:
                            collected.append(result)

                if not collected:
                    logger.warning("No pointing computed towards '%s' in '%s'",
                                   target_code, obs.get_observation_code())
                    return empty

                df = pl.DataFrame({
                    "time": np.concatenate([c[0] for c in collected]),
                    "target_code": np.concatenate([c[1] for c in collected]),
                    "scan_name": np.concatenate([c[2] for c in collected]),
                    "telescope_code": np.concatenate([c[3] for c in collected]),
                    "az": np.concatenate([c[4] for c in collected]),
                    "el": np.concatenate([c[5] for c in collected]),
                    "range": np.concatenate([c[6] for c in collected])
                }, schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

                logger.info("Computed pointing towards '%s' from %s station(s) over %s scan(s), %s rows",
                            target_code, df["telescope_code"].unique().len(),
                            df["scan_name"].unique().len(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "target_code": target_code,
                "position_store_key": position_store_key,
                "orbit_store_key": orbit_store_key
            }
            df = self._process_object(obj, attributes, calculate_telescope_az_el, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except Exception as e:
            logger.error("Failed to compute pointing towards a space telescope for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_az_el"))

    def _process_telescope_az_el(self, scan: Scan, observation: Observation, times_mjd: np.ndarray,
                                 position_df: pl.DataFrame, orbit_df: pl.DataFrame,
                                 target: SpaceTelescope, observers: List[Telescope]) -> Optional[Tuple]:
        """Point each ground station at the spacecraft, for one scan.

        Args:
            scan (Scan): The scan being processed.
            observation (Observation): Its parent.
            times_mjd (np.ndarray): The scan's time grid.
            position_df (pl.DataFrame): Ground station positions for this scan.
            orbit_df (pl.DataFrame): Spacecraft positions for this scan.
            target (SpaceTelescope): What is being pointed at.
            observers (List[Telescope]): The stations doing the pointing.

        Returns:
            Optional[Tuple]: Arrays of (times, target codes, scan names, station codes, az, el,
                range), or None if nothing could be computed.

        Notes:
            - The direction is the *vector from station to spacecraft*, not a fixed sky
              position. A source is far enough away that every station sees it in the same
              direction; a spacecraft in Earth orbit is not, and two stations a baseline apart
              point measurably differently at it. Using a source's geometry here would give
              answers that look plausible and are wrong by degrees.
            - Both positions are rotated into the Earth-fixed frame first, so the vector
              between them is taken between two things that are stationary with respect to
              each other's frame rather than between one that is and one that is not.
        """
        target_code = target.get_code()
        n_times = len(times_mjd)
        if n_times == 0:
            return None

        # The target need not take part in the scan. Asking when a station can see a spacecraft
        # is a question about the spacecraft, not about the observation it may or may not be
        # observing in -- so its position is computed here rather than read out of a result
        # that only covers scan participants.
        orbit_rows = orbit_df.filter(pl.col("telescope_code") == target_code)
        if orbit_rows.is_empty():
            spacecraft_xyz = self._compute_telescope_position(target, times_mjd)
        else:
            placed = self._on_time_grid(times_mjd, orbit_rows, ["x", "y", "z"], target_code, scan.name)
            spacecraft_xyz = np.column_stack([placed["x"], placed["y"], placed["z"]])

        if spacecraft_xyz is None or np.all(np.isnan(spacecraft_xyz)):
            logger.warning("The orbit of '%s' does not cover scan '%s'; nothing to point at",
                           target_code, scan.name)
            return None

        obstime = Time(times_mjd, format="mjd", scale="utc")
        target_itrs = self._to_earth_fixed(spacecraft_xyz, obstime)

        times_list, target_codes, scan_names, station_codes = [], [], [], []
        az_list, el_list, range_list = [], [], []

        for station in observers:
            code = station.get_code()
            station_rows = position_df.filter(pl.col("telescope_code") == code)
            if station_rows.is_empty():
                logger.debug("No position for station '%s' in scan '%s'", code, scan.name)
                continue

            placed = self._on_time_grid(times_mjd, station_rows, ["x", "y", "z"], code, scan.name)
            station_xyz = np.column_stack([placed["x"], placed["y"], placed["z"]])
            station_itrs = self._to_earth_fixed(station_xyz, obstime)

            az, el, distance = self._look_angles(station_itrs, target_itrs)

            times_list.append(times_mjd)
            target_codes.append(np.full(n_times, target_code, dtype=object))
            scan_names.append(np.full(n_times, scan.name, dtype=object))
            station_codes.append(np.full(n_times, code, dtype=object))
            az_list.append(az)
            el_list.append(el)
            range_list.append(distance)

        if not times_list:
            return None
        return (np.concatenate(times_list), np.concatenate(target_codes), np.concatenate(scan_names),
                np.concatenate(station_codes), np.concatenate(az_list), np.concatenate(el_list),
                np.concatenate(range_list))

    @staticmethod
    def _to_earth_fixed(positions: np.ndarray, obstime: Time) -> np.ndarray:
        """Rotate celestial-frame positions into the Earth-fixed frame.

        Args:
            positions (np.ndarray): An (n, 3) array of GCRS positions in metres.
            obstime (Time): The times they belong to.

        Returns:
            np.ndarray: The same positions in ITRS, in metres, NaN where the input was NaN.
        """
        finite = ~np.any(np.isnan(positions), axis=1)
        result = np.full_like(positions, np.nan, dtype=float)
        if not np.any(finite):
            return result

        gcrs = GCRS(CartesianRepresentation(x=positions[:, 0] * u.m, y=positions[:, 1] * u.m,
                                            z=positions[:, 2] * u.m), obstime=obstime)
        itrs = gcrs.transform_to(ITRS(obstime=obstime)).cartesian
        rotated = np.column_stack([itrs.x.to_value(u.m), itrs.y.to_value(u.m), itrs.z.to_value(u.m)])
        result[finite] = rotated[finite]
        return result

    @staticmethod
    def _look_angles(station: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return azimuth, elevation and range from a station to a target, both Earth-fixed.

        Args:
            station (np.ndarray): An (n, 3) array of station positions in metres, ITRS.
            target (np.ndarray): An (n, 3) array of target positions in metres, ITRS.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: Azimuth east of north in degrees,
                elevation above the horizon in degrees, and range in metres. NaN wherever
                either position is unknown.

        Notes:
            - The local east-north-up frame is built from the station's own geocentric
              direction, so this is geocentric rather than geodetic elevation. The difference
              reaches about 0.2 degrees at mid-latitudes, which matters for a horizon mask and
              is why it is written down here rather than left to be discovered.
        """
        count = station.shape[0]
        azimuth = np.full(count, np.nan)
        elevation = np.full(count, np.nan)
        distance = np.full(count, np.nan)

        usable = ~(np.any(np.isnan(station), axis=1) | np.any(np.isnan(target), axis=1))
        if not np.any(usable):
            return azimuth, elevation, distance

        s = station[usable]
        line = target[usable] - s

        radius = np.linalg.norm(s, axis=1)
        radius[radius == 0] = np.nan
        up = s / radius[:, None]

        # East is perpendicular to both the polar axis and the local vertical.
        east = np.column_stack([-s[:, 1], s[:, 0], np.zeros(len(s))])
        east_norm = np.linalg.norm(east, axis=1)
        east_norm[east_norm == 0] = np.nan          # directly over a pole: east is undefined
        east = east / east_norm[:, None]
        north = np.cross(up, east)

        length = np.linalg.norm(line, axis=1)
        length[length == 0] = np.nan

        azimuth[usable] = np.degrees(np.arctan2(np.sum(line * east, axis=1),
                                                np.sum(line * north, axis=1))) % 360.0
        elevation[usable] = np.degrees(np.arcsin(np.clip(np.sum(line * up, axis=1) / length, -1.0, 1.0)))
        distance[usable] = length
        return azimuth, elevation, distance

    @time_execution
    def _calculate_telescope_visibility(self, obj: "Observation | ScheduleProject", attributes: Dict[str, Any]) -> pl.DataFrame:
        """Report when each ground station can actually see the space telescope.

        Args:
            obj: The observation, or a project of them.
            attributes: Parameters including "target_telescope", and "time_step", "store_key",
                "az_el_store_key", "recalculate".

        Returns:
            pl.DataFrame: Columns ["time", "target_code", "scan_name", "telescope_code",
                "visibility"].

        Notes:
            - Above the horizon is not enough: a station has an elevation range it can drive
              to, and a spacecraft below that limit is as unreachable as one below the horizon.
              The same rule a source is checked against.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "telescope_visibility")
            az_el_store_key = attributes.get("az_el_store_key", "telescope_az_el")
            target_code = attributes.get("target_telescope")
            empty = pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

            if not target_code:
                logger.error("No 'target_telescope' given; there is nothing to be visible")
                return empty

            def calculate_telescope_visibility(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                angles = self._calculate_telescope_az_el(obs, {
                    "time_step": time_step, "store_key": az_el_store_key,
                    "target_telescope": target_code, "recalculate": False})
                if angles.is_empty():
                    return empty

                limits = {}
                for telescope in obs.get_telescopes().get_active_items():
                    if isinstance(telescope, SpaceTelescope):
                        continue
                    low, high = telescope.get("elevation_range")
                    limits[telescope.get_code()] = (float(low), float(high))

                elevation = angles["el"].to_numpy()
                codes = angles["telescope_code"].to_list()
                low = np.array([limits.get(code, (0.0, 90.0))[0] for code in codes])
                high = np.array([limits.get(code, (0.0, 90.0))[1] for code in codes])

                with np.errstate(invalid="ignore"):
                    visible = (elevation >= low) & (elevation <= high)
                visible &= ~np.isnan(elevation)

                df = pl.DataFrame({
                    "time": angles["time"].to_numpy(),
                    "target_code": angles["target_code"].to_list(),
                    "scan_name": angles["scan_name"].to_list(),
                    "telescope_code": codes,
                    "visibility": visible
                }, schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

                logger.info("'%s' is visible for %s of %s sampled moments across %s station(s)",
                            target_code, int(visible.sum()), len(visible),
                            df["telescope_code"].unique().len())
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "target_code": target_code,
                "az_el_store_key": az_el_store_key
            }
            df = self._process_object(obj, attributes, calculate_telescope_visibility, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except Exception as e:
            logger.error("Failed to compute visibility of a space telescope for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("telescope_visibility"))

    @time_execution
    def _calculate_time_on_source(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate time-on-source blocks for all active scans in the observation or project.

        Args:
            obj: The object to calculate time on source for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "visibility_store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["scan_name", "telescope_code", "source_name", "start_mjd", "end_mjd", "duration"].
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "time_on_source")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")

            def calculate_time_on_source(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing time or visibility data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                scan_names = []
                telescope_codes = []
                source_names = []
                start_mjd_list = []
                end_mjd_list = []
                durations_list = []

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_time_on_source, scan, obs, scan_times, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            scan_name_arr, tel_codes, source_name_arr, start_mjd, end_mjd, durations = scan_result
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            start_mjd_list.append(start_mjd)
                            end_mjd_list.append(end_mjd)
                            durations_list.append(durations)

                if not scan_names:
                    logger.warning("No valid time-on-source blocks computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                df = pl.DataFrame({
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "start": np.concatenate(start_mjd_list),
                    "end": np.concatenate(end_mjd_list),
                    "duration": np.concatenate(durations_list)
                }, schema=CalculatedDataStructure.get_dtypes("time_on_source"))

                logger.info("Calculated time-on-source for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_time_on_source, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate time on source for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("time_on_source"))

    def _process_time_on_source(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, visibility_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process time-on-source blocks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (scan_names, telescope_codes, source_names, start_mjd, end_mjd, durations) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        # One sample alone covers the whole scan and sits at its middle: that is how the grid
        # is built without a step. Otherwise each sample opens the spacing that follows it.
        if n_times > 1:
            # Across the whole grid rather than between two neighbours: an MJD near 61000 is
            # resolved to about a microsecond, and one neighbouring difference carries all of
            # that error into every sample a block holds.
            # To the microsecond, which is all an MJD this size resolves: what is left beyond
            # it is float noise, and it reached the exported file as 32400.000000105138.
            spacing_seconds = round((times_mjd[-1] - times_mjd[0]) * 86400.0 / (n_times - 1), 6)
            opens_at = 0.0
        else:
            spacing_seconds = float(scan.get_duration())
            opens_at = spacing_seconds / 2.0

        scan_names = []
        telescope_codes = []
        source_names = []
        start_mjd_list = []
        end_mjd_list = []
        durations_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)
            if tel_visibility.is_empty():
                logger.warning("No visibility data for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            visibility = tel_visibility["visibility"].to_numpy().astype(bool)
            if len(visibility) != n_times:
                logger.warning("Visibility data length mismatch for '%s' in scan '%s': got %s, expected %s", tel_code, scan_name, len(visibility), n_times)
                continue

            # Runs of visible samples: padded with False on both sides, a run starts where the
            # difference is +1 and ends -- exclusively -- where it is -1.
            edges = np.diff(np.concatenate(([0], visibility.astype(np.int8), [0])))
            start_indices = np.flatnonzero(edges == 1)
            end_indices = np.flatnonzero(edges == -1)
            if len(start_indices) == 0:
                logger.debug("No visibility blocks for telescope '%s' in scan '%s'", tel_code, scan_name)
                continue

            # **A sample stands for one spacing of the grid, so a run of k samples lasts k
            # spacings.** Measuring from the first visible sample to the last counted k - 1:
            # every block lost one step, a source seen in a single sample was on source for
            # zero seconds, and a scan visible throughout came out shorter than the scan. The
            # grid is `linspace(0, duration, n, endpoint=False)`, so the spacing is read off
            # the grid itself -- a scan whose length is not a multiple of the step is sampled
            # more finely than `time_step`.
            n_blocks = len(start_indices)
            blocks_start = times_mjd[start_indices] - opens_at / 86400.0
            blocks_duration = (end_indices - start_indices) * spacing_seconds
            blocks_end = blocks_start + blocks_duration / 86400.0

            scan_names.append(np.full(n_blocks, scan_name, dtype=object))
            telescope_codes.append(np.full(n_blocks, tel_code, dtype=object))
            source_names.append(np.full(n_blocks, source_name, dtype=object))
            start_mjd_list.append(blocks_start)
            end_mjd_list.append(blocks_end)
            durations_list.append(blocks_duration)

            logger.debug("Computed %s time-on-source blocks for telescope '%s' in scan '%s'", n_blocks, tel_code, scan_name)

        if not scan_names:
            logger.warning("No time-on-source blocks computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(start_mjd_list),
            np.concatenate(end_mjd_list),
            np.concatenate(durations_list)
        )
    
    #: What the recording keeps of the signal, by bits per sample: the correlation lost to quantising
    #: it. Two-level is 2/pi; four-level with the optimal threshold, 0.8825 (Thompson, Moran &
    #: Swenson, table 8.1).
    RECORDING_EFFICIENCY = {1: 2.0 / np.pi, 2: 0.8825}

    @time_execution
    def _calculate_sefd(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Work out each station's SEFD in each band of the observation, and say where it came from (E1).

        Args:
            obj: The observation or project.
            attributes: `fill` -- write an SEFD computed from a station's parameters into its SEFD
                table, as a row covering the band; `store_key`; `recalculate`.

        Returns:
            pl.DataFrame: One row per station and band: `sefd` in Jy, its `origin` -- `table`,
                `parameters` or `none` -- the parts it was computed from, the `basis`, the `reason`
                there is none, and whether it was `filled` into the table.

        Notes:
            - The physics is the telescope's own (`Telescope.get_sefd_estimate`): the table first,
              then `2 k Tsys / A_eff` from rows covering the band's frequency.
            - **Filling writes only what was computed, and only where nothing was measured.** The
              row covers the band -- from its frequency up by its bandwidth -- and a row that would
              overlap one already in the table is not written; the reason says so. What was
              measured is never replaced.
        """
        try:
            store_key = attributes.get("store_key", "sefd")
            fill = bool(attributes.get("fill", False))
            if fill:
                # Filling is something to do, not something to look up: a stored answer would
                # skip it.
                attributes = {**attributes, "recalculate": True}

            def calculate_sefd(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                telescopes = obs.get_telescopes().get_active_items()
                bands = obs.get_frequencies().get_active_items()
                rows = []
                for telescope in telescopes:
                    for band in bands:
                        estimate = telescope.get_sefd_estimate(float(band.frequency))
                        filled, reason = False, estimate["reason"]
                        if fill and estimate["origin"] == "parameters":
                            low = float(band.frequency)
                            high = low + float(band.bandwidth)
                            try:
                                telescope.add_sefd(low, high, estimate["sefd"])
                                filled = True
                            except (InvariantError, ValueError) as e:
                                reason = f"not written to the SEFD table: {e}"
                        rows.append({
                            "telescope_code": telescope.get_code(), "if_name": band.name,
                            "frequency": float(band.frequency), "bandwidth": float(band.bandwidth),
                            "sefd": estimate["sefd"], "origin": estimate["origin"],
                            "tsys": estimate["tsys"], "effective_area": estimate["effective_area"],
                            "efficiency": estimate["efficiency"], "basis": estimate["basis"],
                            "reason": reason, "filled": filled})
                if not rows:
                    logger.warning("No active stations or bands in '%s'", obs.get_observation_code())
                return pl.DataFrame(rows, schema=CalculatedDataStructure.get_dtypes("sefd"))

            metadata = {"filled": 0}
            df = self._process_object(obj, attributes, calculate_sefd, store_key, metadata)
            if not df.is_empty():
                metadata["filled"] = int(df["filled"].sum())
                self._store_result(obj, store_key, df, metadata)
            return df
        except Exception as e:
            logger.error("Failed to work out SEFDs for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sefd"))

    #: What a station's SEFD along a scan takes for granted, recorded with the result.
    TRACK_ASSUMPTION = ("the SEFD a station has is the one at zenith, through the atmosphere there; "
                        "the atmosphere is flat, airmass 1/sin(elevation)")

    @time_execution
    def _calculate_sefd_track(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Work out each station's SEFD at every sample of every scan, from where the source stands (E1).

        Args:
            obj: The observation or project.
            attributes: `opacity`, rows `[f_min, f_max, tau0]` of the zenith opacity assumed at
                every station, in MHz; `t_atm`, the temperature of the atmosphere in kelvin, which
                an opacity needs; `gain_curve`, by station code, rows
                `[f_min, f_max, [c0, c1, ...]]` of a polynomial in elevation, in degrees;
                `time_step`; `store_key`; `recalculate`.

        Returns:
            pl.DataFrame: One row per sample, station and band: the `elevation` and the `airmass`,
                the `opacity` and the `attenuation` over the zenith's it gives, the system
                temperature `tsys`, the `gain` over the zenith's, the `sefd_zenith` and the `sefd`
                there, the `basis` saying what was applied, and the `reason` where there is no SEFD.

        Notes:
            - **On the time grid** -- every sample `times` holds, whether the station sees the
              source then or not. What the SEFD would be is worth drawing; when the source is seen
              is `time_on_source`'s to say.
            - **The zenith SEFD is the one seen at zenith, through the atmosphere there**: the
              `sefd` result. Away from the zenith
              `SEFD = SEFD_zenith e^(tau0 (A - 1)) Tsys / Tsys_zenith g(90) / g(el)` -- the source
              dimmed through more air, the system warmed by what more air emits,
              `Tsys = Tsys_zenith + T_atm (e^-tau0 - e^(-tau0 A))`, and the dish's gain there. The
              airmass is a flat atmosphere's, `A = 1 / sin(el)`.
            - **Nothing of this is written to a station.** The weather is the day's rather than the
              dish's, so the opacity is a parameter and the same at every station; a gain curve is
              given by the station's code.
            - **A gain curve is taken as the ratio `g(90) / g(el)`**, so how it was normalised does
              not matter: one peaking at 1 at 50 degrees and the same curve doubled give one answer.
            - What is not given is not applied, and `basis` says so. With no system temperature at
              zenith the atmosphere's emission cannot be added, and `basis` says that too.
            - **No SEFD where the dish does not point** -- below the horizon, and outside its own
              elevation range. A flat atmosphere's airmass runs away towards the horizon, so a
              station observing above 15 degrees would otherwise carry SEFDs of tens of millions
              of janskys at elevations it never uses. In space there is no atmosphere and no
              elevation, and the SEFD is the zenith's.
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "sefd_track")
            opacity, t_atm, gain_curve = self._elevation_parameters(attributes)

            sefd_attrs = {"store_key": "sefd", "recalculate": False}
            time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
            position_attrs = {"time_step": time_step, "store_key": "telescope_positions",
                              "recalculate": False}
            dtypes = CalculatedDataStructure.get_dtypes("sefd_track")

            def calculate_sefd_track(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs)
                if not scans:
                    return pl.DataFrame(schema=dtypes)
                zenith = {(row["telescope_code"], row["if_name"]): row
                          for row in self._calculate_sefd(obs, sefd_attrs).iter_rows(named=True)}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                if times_df.is_empty():
                    logger.error("Missing times for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=dtypes)
                by_scan = {}
                if not position_df.is_empty():
                    by_scan = position_df.partition_by("scan_name", as_dict=True)
                    # An equatorial mount's elevation is asked too, which visibility never needs.
                    self._warm_topocentric(obs, scans, times_df, position_df, frame="altaz")

                columns: Dict[str, list] = {name: [] for name in dtypes}
                for scan in scans:
                    source = scan.get_source(obs)
                    if source is None or not source.isactive:
                        continue
                    times_mjd = times_df.filter(pl.col("scan_name") == scan.name)["time"].to_numpy()
                    n = len(times_mjd)
                    if n == 0:
                        continue
                    bands = [b for b in scan.get_frequencies(obs).get_items() if b.isactive]
                    for telescope in scan.get_telescopes(obs).get_items():
                        if not telescope.isactive:
                            continue
                        code = telescope.get_code()
                        elevation = self._elevation_along(telescope, source, by_scan.get((scan.name,)),
                                                          times_mjd)
                        for band in bands:
                            along = self._sefd_along(telescope, band, zenith.get((code, band.name)),
                                                     elevation, n, opacity, t_atm,
                                                     gain_curve.get(code, []))
                            along.update(time=times_mjd,
                                         scan_name=np.full(n, scan.name, dtype=object),
                                         source_name=np.full(n, source.name, dtype=object),
                                         telescope_code=np.full(n, code, dtype=object),
                                         if_name=np.full(n, band.name, dtype=object),
                                         frequency=np.full(n, float(band.frequency)))
                            for name in dtypes:
                                columns[name].append(along[name])

                if not columns["time"]:
                    logger.warning("No station and band to follow in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=dtypes)
                # **The text columns are handed over as lists.** A numpy array of objects that
                # happen to be strings is an `Object` column to polars, and one holding nothing
                # but None -- a scan where every sample worked out, so no row has a reason --
                # cannot be cast to a string at all: `cannot cast 'Object' type`, and the whole
                # calculation came back empty.
                joined = {name: np.concatenate(parts) for name, parts in columns.items()}
                return pl.DataFrame({name: values.tolist() if values.dtype == object else values
                                     for name, values in joined.items()},
                                    schema=dtypes).fill_nan(None)

            metadata = {"time_step": time_step, "scan_count": self._active_scan_count(obj),
                        "opacity": opacity, "t_atm": t_atm, "gain_curve": gain_curve,
                        "assumption": self.TRACK_ASSUMPTION}
            df = self._process_object(obj, attributes, calculate_sefd_track, store_key, metadata)
            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to follow SEFDs along the scans of '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("sefd_track"))

    @classmethod
    def _elevation_parameters(cls, attributes: Dict[str, Any]) -> Tuple[List[list], Optional[float], Dict[str, List[list]]]:
        """Return the weather and the gain curves a calculation was asked with, checked.

        Returns:
            Tuple: `opacity` rows `[f_min, f_max, tau0]`, `t_atm` in kelvin or None, and
                `gain_curve` rows `[f_min, f_max, [c0, c1, ...]]` by station code -- as plain lists,
                which is what they read back as from a saved result, so the two compare.

        Raises:
            ValueError: Saying what is wrong with them.
        """
        def an_opacity(value: Any) -> Optional[str]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not value >= 0:
                return f"an opacity of {value!r} is not one: it is a number, zero or more"
            return None

        def a_polynomial(value: Any) -> Optional[str]:
            if (not isinstance(value, (list, tuple)) or not value
                    or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in value)):
                return f"{value!r} is not a polynomial's coefficients, [c0, c1, ...]"
            return None

        opacity = [[low, high, float(tau)] for low, high, tau
                   in cls._frequency_rows(attributes.get("opacity"), "opacity", an_opacity)]
        t_atm = attributes.get("t_atm")
        if t_atm is not None:
            if isinstance(t_atm, bool) or not isinstance(t_atm, (int, float)) or not t_atm > 0:
                raise ValueError(f"t_atm of {t_atm!r} is not a temperature: it is in kelvin, above zero")
            t_atm = float(t_atm)
        if opacity and t_atm is None:
            raise ValueError("an opacity needs t_atm, the temperature of the atmosphere in kelvin, "
                             "for what more air emits")

        curves = attributes.get("gain_curve") or {}
        if not isinstance(curves, dict):
            raise ValueError("gain_curve is given by station code: "
                             "{code: [[f_min, f_max, [c0, c1, ...]]]}")
        gain_curve = {str(code): [[low, high, [float(c) for c in coefficients]] for low, high, coefficients
                                  in cls._frequency_rows(rows, f"gain_curve of {code}", a_polynomial)]
                      for code, rows in sorted(curves.items())}
        return opacity, t_atm, gain_curve

    @staticmethod
    def _frequency_rows(rows: Any, name: str, refuse: Callable[[Any], Optional[str]]) -> List[list]:
        """Return rows of `[f_min, f_max, value]` given as a parameter, checked as a telescope's tables are.

        Raises:
            ValueError: A row that is not one, a range the wrong way round, rows that overlap, or
                a value `refuse` gives a reason against.
        """
        if rows is None:
            return []
        if not isinstance(rows, (list, tuple)):
            raise ValueError(f"{name} is rows of [f_min, f_max, value], not {rows!r}")
        checked = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise ValueError(f"{name}: {row!r} is not a row of [f_min, f_max, value]")
            try:
                low, high = float(row[0]), float(row[1])
            except (TypeError, ValueError):
                raise ValueError(f"{name}: {row!r} does not start with two frequencies") from None
            if not 0 < low <= high:
                raise ValueError(f"{name}: a range {low:g}-{high:g} MHz runs from a positive "
                                 f"frequency up")
            problem = refuse(row[2])
            if problem:
                raise ValueError(f"{name} over {low:g}-{high:g} MHz: {problem}")
            checked.append([low, high, row[2]])
        checked.sort(key=lambda row: (row[0], row[1]))
        for (low, high, _), (next_low, next_high, _) in zip(checked, checked[1:]):
            if next_low < high:
                raise ValueError(f"{name}: rows {low:g}-{high:g} and {next_low:g}-{next_high:g} MHz "
                                 f"overlap, so a frequency between would have two values")
        return checked

    def _elevation_along(self, telescope: Telescope, source: Source, scan_positions: Optional[pl.DataFrame],
                         times_mjd: np.ndarray) -> Optional[np.ndarray]:
        """Return a ground station's elevation of a source at each sample, NaN where it has no position, and None in space."""
        if isinstance(telescope, SpaceTelescope):
            return None
        n = len(times_mjd)
        elevation = np.full(n, np.nan)
        if scan_positions is None:
            return elevation
        positions = (scan_positions.filter(pl.col("telescope_code") == telescope.get_code())
                     .select(["x", "y", "z"]).to_numpy())
        if len(positions) != n:
            return elevation
        known = ~np.any(np.isnan(positions), axis=1)
        if np.any(known):
            _, altitude, _ = self._topocentric(source, positions, times_mjd, "altaz")
            elevation[known] = altitude[known]
        return elevation

    @staticmethod
    def _sefd_along(telescope: Telescope, band: Any, zenith: Optional[dict], elevation: Optional[np.ndarray],
                    n: int, opacity: List[list], t_atm: Optional[float], curve: List[list]) -> Dict[str, np.ndarray]:
        """Return one station's SEFD in one band at each sample of a scan, and what went into it."""
        frequency = float(band.frequency)
        code = telescope.get_code()
        sefd_zenith = zenith["sefd"] if zenith else None
        tsys_zenith = (zenith or {}).get("tsys") or telescope.get_system_temperature(frequency)
        nothing = np.full(n, np.nan)
        answer = {"sefd_zenith": np.full(n, np.nan if sefd_zenith is None else float(sefd_zenith))}
        reason = np.full(n, None, dtype=object)
        no_zenith = zenith["reason"] if zenith else f"no SEFD worked out for {code} in {band.name}"

        if elevation is None:
            if sefd_zenith is None:
                reason[:] = no_zenith
            answer.update(elevation=nothing, airmass=nothing, opacity=nothing, attenuation=np.ones(n),
                          tsys=np.full(n, np.nan if tsys_zenith is None else float(tsys_zenith)),
                          gain=np.ones(n), sefd=answer["sefd_zenith"].copy(), reason=reason,
                          basis=np.full(n, "in space: no atmosphere and no elevation", dtype=object))
            return answer

        parts = []
        # **Where the dish can actually point**, not merely above the horizon. A flat atmosphere's
        # airmass runs away as the elevation goes to zero -- 1/sin(0.5 deg) is 115 -- so a station
        # whose limit is 15 degrees was given SEFDs of tens of millions of janskys at elevations it
        # never observes at, and every plot of the track was that spike.
        low, high = (float(value) for value in telescope.get_elevation_range())
        with np.errstate(divide="ignore", invalid="ignore"):
            above = (elevation >= max(low, 0.0)) & (elevation <= high) & (elevation > 0)
            airmass = np.where(above, 1.0 / np.sin(np.radians(elevation)), np.nan)

            row = Telescope._covering(opacity, frequency)
            tau = None if row is None else float(row[2])
            if tau is None:
                attenuation = np.where(above, 1.0, np.nan)
                parts.append(f"no opacity covers {frequency:g} MHz" if opacity else "no opacity given")
            else:
                attenuation = np.exp(tau * (airmass - 1.0))
                parts.append(f"opacity {tau:g} over {row[0]:g}-{row[1]:g} MHz")

            if tsys_zenith is None:
                tsys, warming = nothing, np.where(above, 1.0, np.nan)
                if tau is not None:
                    parts.append("its emission not added: no system temperature at zenith")
            else:
                added = t_atm * (np.exp(-tau) - np.exp(-tau * airmass)) if tau is not None else 0.0
                tsys = np.where(above, float(tsys_zenith) + added, np.nan)
                warming = tsys / float(tsys_zenith)

            row = Telescope._covering(curve, frequency)
            not_positive = np.zeros(n, dtype=bool)
            zenith_gain = None
            if row is None:
                gain = np.where(above, 1.0, np.nan)
                parts.append("no gain curve")
            else:
                coefficients = [float(c) for c in row[2]]
                zenith_gain = float(np.polynomial.polynomial.polyval(90.0, coefficients))
                gain = np.polynomial.polynomial.polyval(elevation, coefficients) / zenith_gain
                not_positive = (above & ~(gain > 0)) if zenith_gain > 0 else above
                gain = np.where(above & ~not_positive, gain, np.nan)
                parts.append(f"gain curve over {row[0]:g}-{row[1]:g} MHz")

            sefd = (np.nan if sefd_zenith is None else float(sefd_zenith)) * attenuation * warming / gain

        # Where there is no SEFD, the first thing that stood in its way.
        for index in np.flatnonzero(np.isnan(sefd)):
            if np.isnan(elevation[index]):
                reason[index] = f"no position for {code} at this sample"
            elif elevation[index] <= 0:
                reason[index] = "below the horizon"
            elif not above[index]:
                reason[index] = (f"{elevation[index]:.1f} deg is outside what {code} points at, "
                                 f"{low:g}-{high:g} deg")
            elif sefd_zenith is None:
                reason[index] = no_zenith
            elif not_positive[index]:
                where = "the zenith" if zenith_gain <= 0 else f"{elevation[index]:.1f} deg"
                reason[index] = f"the gain curve is not positive at {where}"

        answer.update(elevation=elevation, airmass=airmass,
                      opacity=np.where(above, np.nan if tau is None else tau, np.nan),
                      attenuation=attenuation, tsys=tsys, gain=gain, sefd=sefd, reason=reason,
                      basis=np.full(n, "; ".join(parts), dtype=object))
        return answer

    @time_execution
    def _calculate_baseline_sensitivity(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Work out each baseline's noise on each scan, the signal-to-noise it reaches, and the shortest scan that would detect the source (E1).

        Args:
            obj: The observation or project.
            attributes: `threshold`, the signal-to-noise a detection needs (5); `bits` per sample,
                1 or 2 (2); `recording_efficiency`, to state the system's efficiency outright rather
                than from the bits -- the VLBA quotes 0.8 for everything the recording loses;
                `opacity`, `t_atm` and `gain_curve`, for the SEFDs along the scan, as
                `sefd_track` takes them; `time_step`; `store_key`; `recalculate`.

        Returns:
            pl.DataFrame: A row per scan, baseline and band, and a row with `if_name` `all` per scan
                and baseline for the bands together: `duration` both stations see the source, the
                stations' SEFDs over it, `noise` in Jy, `flux`, `snr`, `detected`, `min_duration`
                in seconds, and the `reason` where something could not be worked out.

        Notes:
            - **The time is the time both stations see the source** -- the overlap of their
              `time_on_source` blocks, not the scan's length.
            - **Noise by the radiometer equation, summed over that time**: each piece of it adds
              `2 dnu P dt eta^2 / (SEFD1 SEFD2)` to `1 / sigma^2`, with the SEFDs of the sample it
              lies in (`sefd_track`), `eta` what the recording keeps, `dnu` the band's width and
              `P` its polarizations, whose parallel hands add. With the SEFDs constant this is
              `sqrt(SEFD1 SEFD2) / (eta sqrt(2 dnu tau P))`.
            - **Detection** is `snr >= threshold`, and the shortest scan reaching it is
              `(threshold sigma_1s / S)^2`, with `sigma_1s` the noise in one second at the SEFDs
              the scan had.
            - **All bands together** add as signal-to-noise does, `sqrt(sum snr_i^2)`, over the bands
              with a flux and both SEFDs -- which is what fringe fitting across a recording gets.
            - **The source is taken as unresolved**: the correlated flux is the total flux. On a
              baseline that resolves it the flux is lower, and the result says what it assumed.
            - A value that cannot be worked out -- no SEFD, no flux at that frequency, no time
              together -- is left empty with the reason, never guessed.
        """
        try:
            store_key = attributes.get("store_key", "baseline_sensitivity")
            time_step = attributes.get("time_step")
            threshold = float(attributes.get("threshold", 5.0))
            bits = int(attributes.get("bits", 2))
            if bits not in self.RECORDING_EFFICIENCY:
                raise ValueError(f"{bits} bits per sample: the recording efficiency is known for "
                                 f"{', '.join(str(b) for b in self.RECORDING_EFFICIENCY)}")
            if threshold <= 0:
                raise ValueError(f"a detection threshold of {threshold} sigma is not one")
            stated = attributes.get("recording_efficiency")
            efficiency = float(stated) if stated is not None else self.RECORDING_EFFICIENCY[bits]
            if not 0 < efficiency <= 1:
                raise ValueError(f"a recording efficiency of {efficiency} is not a fraction")
            opacity, t_atm, gain_curve = self._elevation_parameters(attributes)
            asked = {"threshold": threshold, "bits": bits, "recording_efficiency": efficiency,
                     "opacity": opacity, "t_atm": t_atm, "gain_curve": gain_curve}

            track_attrs = {"time_step": time_step, "store_key": "sefd_track", "recalculate": False,
                           "opacity": opacity, "t_atm": t_atm, "gain_curve": gain_curve}
            on_source_attrs = {"time_step": time_step, "store_key": "time_on_source",
                               "recalculate": False}

            def calculate_baseline_sensitivity(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                tracks = self._tracks_by_scan(self._calculate_sefd_track(obs, track_attrs))
                blocks = self._calculate_time_on_source(obs, on_source_attrs)
                scans, _, _ = self._get_active_components(obs)

                rows = []
                for scan in scans:
                    source = scan.get_source(obs)
                    if source is None or not source.isactive:
                        continue
                    stations = [t for t in scan.get_telescopes(obs).get_items() if t.isactive]
                    bands = [b for b in scan.get_frequencies(obs).get_items() if b.isactive]
                    seen = self._blocks_by_station(blocks, scan.name)
                    start = float(scan.get_MJD_starttime())
                    for i, first in enumerate(stations):
                        for second in stations[i + 1:]:
                            codes = (first.get_code(), second.get_code())
                            together = self._overlap_intervals(seen.get(codes[0], []),
                                                               seen.get(codes[1], []))
                            common = {"time": start, "scan_name": scan.name,
                                      "source_name": source.name, "baseline": "-".join(codes),
                                      "scan_duration": float(scan.get_duration()),
                                      "duration": sum(end - begin for begin, end in together) * 86400.0}
                            per_band = []
                            for band in bands:
                                sefds = self._sefd_together(
                                    together, tracks.get((scan.name, codes[0], band.name)),
                                    tracks.get((scan.name, codes[1], band.name)), codes)
                                per_band.append(self._band_sensitivity(common, band, source, sefds,
                                                                       efficiency, threshold))
                            rows.extend(per_band)
                            rows.append(self._all_bands(common, per_band, threshold))

                if not rows:
                    logger.warning("No baselines to work out sensitivity for in '%s'",
                                   obs.get_observation_code())
                return pl.DataFrame(rows, schema=CalculatedDataStructure.get_dtypes("baseline_sensitivity"))

            metadata = {**asked, "time_step": time_step, "scan_count": self._active_scan_count(obj),
                        "assumption": "unresolved source: the correlated flux is the total flux"}
            df = self._process_object(obj, attributes, calculate_baseline_sensitivity, store_key, metadata)
            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)
            return df
        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to work out baseline sensitivity for '%s': %s",
                         obj.get_observation_code() if isinstance(obj, Observation) else obj.name,
                         str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_sensitivity"))

    @staticmethod
    def _blocks_by_station(blocks: pl.DataFrame, scan_name: str) -> Dict[str, List[Tuple[float, float]]]:
        """Return each station's time-on-source intervals in one scan, as MJD pairs."""
        seen: Dict[str, List[Tuple[float, float]]] = {}
        if blocks.is_empty():
            return seen
        for row in blocks.filter(pl.col("scan_name") == scan_name).iter_rows(named=True):
            seen.setdefault(row["telescope_code"], []).append((row["start"], row["end"]))
        return seen

    @staticmethod
    def _overlap_intervals(first: List[Tuple[float, float]], second: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Return the intervals two stations see the source at the same time, as MJD pairs."""
        together = []
        for start_a, end_a in first:
            for start_b, end_b in second:
                start, end = max(start_a, start_b), min(end_a, end_b)
                if end > start:
                    together.append((start, end))
        return sorted(together)

    @staticmethod
    def _tracks_by_scan(track: pl.DataFrame) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
        """Return each station's SEFD along each scan in each band, in time order: NaN where there is none."""
        tracks: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        if track.is_empty():
            return tracks
        parts = track.sort("time").partition_by(["scan_name", "telescope_code", "if_name"],
                                                as_dict=True, maintain_order=True)
        for key, part in parts.items():
            tracks[key] = {"time": part["time"].to_numpy(),
                           "sefd": part["sefd"].cast(pl.Float64).fill_null(np.nan).to_numpy(),
                           "reason": part["reason"].to_list()}
        return tracks

    @staticmethod
    def _sefd_together(together: List[Tuple[float, float]], first: Optional[dict], second: Optional[dict],
                       codes: Tuple[str, str]) -> Dict[str, Any]:
        """Return a baseline's SEFDs over the time both stations see the source, weighted as its noise is.

        Returns:
            Dict[str, Any]: `sefd_1` and `sefd_2`, each station's SEFD averaged over the time
                together; `sefd`, the baseline's, `sqrt(tau / sum(dt / (SEFD1 SEFD2)))`; and the
                `reason` there is none.

        Notes:
            - **`1 / sigma^2` adds up over time**, each piece of the time together bringing
              `dt / (SEFD1 SEFD2)`. The one SEFD giving the same noise over all of it is the one
              above; with the SEFDs constant it is `sqrt(SEFD1 SEFD2)`, and the radiometer equation
              is the whole scan's.
            - Each piece takes the SEFDs of the sample it lies in: a sample stands for the time
              from it to the next, as `time_on_source` counts it, and a lone sample for the scan.
            - A piece shorter than a microsecond is not time but the float noise of an MJD, which
              resolves no finer -- and it would put a block's end into the next sample, whose SEFD
              may be one below the horizon.
        """
        answer = {"sefd_1": None, "sefd_2": None, "sefd": None, "reason": None}
        if not together:
            return answer
        missing = [code for code, track in zip(codes, (first, second)) if track is None]
        if missing:
            answer["reason"] = f"no SEFD along the scan for {', '.join(missing)}"
            return answer

        times = first["time"]
        lengths, samples = [], []
        for start, end in together:
            cuts = np.concatenate(([start], times[(times > start) & (times < end)], [end]))
            seconds = np.round(np.diff(cuts) * 86400.0, 6)
            index = np.clip(np.searchsorted(times, (cuts[:-1] + cuts[1:]) / 2.0, side="right") - 1, 0, None)
            lengths.append(seconds[seconds > 0])
            samples.append(index[seconds > 0])
        seconds, index = np.concatenate(lengths), np.concatenate(samples)
        if seconds.sum() <= 0:
            return answer

        sefd_1, sefd_2 = first["sefd"][index], second["sefd"][index]
        problems: List[str] = []
        for code, track, values in ((codes[0], first, sefd_1), (codes[1], second, sefd_2)):
            for k in index[np.isnan(values)]:
                problem = f"{code}: {track['reason'][k]}"
                if problem not in problems:
                    problems.append(problem)
        if problems:
            answer["reason"] = "; ".join(problems)
            return answer

        tau = seconds.sum()
        answer.update(sefd_1=float((seconds * sefd_1).sum() / tau),
                      sefd_2=float((seconds * sefd_2).sum() / tau),
                      sefd=float(np.sqrt(tau / (seconds / (sefd_1 * sefd_2)).sum())))
        return answer

    @staticmethod
    def _band_sensitivity(common: Dict[str, Any], band: Any, source: Source, sefds: Dict[str, Any],
                          efficiency: float, threshold: float) -> Dict[str, Any]:
        """Return one baseline's row for one band, from its SEFDs over the time together."""
        frequency = float(band.frequency)
        row = {**common, "if_name": band.name, "frequency": frequency,
               "bandwidth": float(band.bandwidth), "sefd_1": sefds["sefd_1"],
               "sefd_2": sefds["sefd_2"], "noise": None, "flux": None, "flux_basis": None,
               "snr": None, "detected": None, "min_duration": None, "reason": None, "noise_1s": None}
        reasons = []
        if common["duration"] <= 0:
            reasons.append("the two stations do not see the source together in this scan")
        elif sefds["reason"]:
            reasons.append(sefds["reason"])

        flux = source.get_flux_estimate(frequency)
        row["flux"], row["flux_basis"] = flux["flux"], flux["basis"]
        if flux["flux"] is None:
            reasons.append(f"{source.name}: {flux['reason']}")

        if sefds["sefd"] is not None and common["duration"] > 0:
            polarizations = max(1, len(band.polarizations or []))
            bandwidth_hz = float(band.bandwidth) * 1e6
            noise_1s = sefds["sefd"] / (efficiency * np.sqrt(2.0 * bandwidth_hz * polarizations))
            row["noise_1s"] = float(noise_1s)
            row["noise"] = float(noise_1s / np.sqrt(common["duration"]))
            if flux["flux"] is not None:
                row["min_duration"] = float((threshold * noise_1s / flux["flux"]) ** 2)
                row["snr"] = float(flux["flux"] / row["noise"])
                row["detected"] = row["snr"] >= threshold

        row["reason"] = "; ".join(reasons) or None
        return row

    @staticmethod
    def _all_bands(common: Dict[str, Any], per_band: List[Dict[str, Any]], threshold: float) -> Dict[str, Any]:
        """Return one baseline's row for all its bands together: signal-to-noise adds in quadrature."""
        row = {**common, "if_name": "all", "frequency": None,
               "bandwidth": float(sum(r["bandwidth"] for r in per_band)) if per_band else None,
               "sefd_1": None, "sefd_2": None, "noise": None, "flux": None, "flux_basis": None,
               "snr": None, "detected": None, "min_duration": None, "reason": None, "noise_1s": None}
        if common["duration"] <= 0:
            row["reason"] = "the two stations do not see the source together in this scan"
            return row
        usable = [r for r in per_band if r["noise_1s"] is not None and r["flux"] is not None]
        if not usable:
            row["reason"] = "no band with both SEFDs and a flux"
            return row
        per_second = sum((r["flux"] / r["noise_1s"]) ** 2 for r in usable)
        row["min_duration"] = float(threshold ** 2 / per_second)
        row["noise"] = float(1.0 / np.sqrt(sum(1.0 / r["noise"] ** 2 for r in usable)))
        row["snr"] = float(np.sqrt(per_second * common["duration"]))
        row["detected"] = row["snr"] >= threshold
        if len(usable) < len(per_band):
            row["reason"] = f"{len(per_band) - len(usable)} band(s) left out"
        return row

    @time_execution
    def _calculate_beam_pattern(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate each active telescope's beam, once, for every frequency at the same time.

        Args:
            obj: The object to calculate beam pattern for (Observation or ScheduleProject).
            attributes: Parameters including "store_key", "recalculate".

        Returns:
            pl.DataFrame: Columns ["telescope_code", "theta", "pattern"], pattern normalised.

        Notes:
            - **`theta` is not an angle.** It is `t` in `x = D sin(t)`, over -pi/2..pi/2, and
              the pattern is Airy's `(2 J1(x) / x)^2`. The Airy pattern has
              `x = pi D sin(theta) / lambda`, so at any wavelength the angle is
              `sin(theta) = lambda sin(t) / pi` -- which is what the visualizer applies. One
              curve per dish, and the frequency is chosen when it is drawn.
            - `x` reaches `D`, so a dish under 3.83 m does not reach its first null. The
              shipped catalogue starts at 6 m.
        """
        try:
            store_key = attributes.get("store_key", "beam_pattern")

            def calculate_beam_pattern(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                _, telescopes, _ = self._get_active_components(obs, require_scans=False, require_telescopes=True)
                if not telescopes:
                    logger.warning("No active telescopes in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                obs_type = obs.get_observation_type()
                if obs_type not in ["SINGLE_DISH", "VLBI"]:
                    logger.warning("Beam pattern calculation is only for SINGLE_DISH or VLBI, got %s", obs_type)
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                theta = np.linspace(-np.pi / 2, np.pi / 2, 5000)  # radians
                telescope_codes = []
                theta_list = []
                pattern_list = []
                valid_telescopes = []
                diameters = []

                for tel in telescopes:
                    diameter = tel.get("diameter")
                    if diameter is None or diameter <= 0:
                        logger.warning("Invalid diameter for telescope '%s' in '%s'; skipping", tel.get_code(), obs.get_observation_code())
                        continue
                    valid_telescopes.append(tel)
                    diameters.append(diameter)
                    telescope_codes.append(np.full(len(theta), tel.get_code(), dtype=object))
                    theta_list.append(theta)
                    x = diameter * np.sin(theta)
                    pattern = (2 * j1(x) / x) ** 2
                    pattern = np.where(np.isnan(pattern), 1.0, pattern)
                    pattern = pattern / np.max(pattern)
                    pattern_list.append(pattern)

                if not valid_telescopes:
                    logger.warning("No telescopes with valid diameters in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                df = pl.DataFrame({
                    "telescope_code": np.concatenate(telescope_codes),
                    "theta": np.concatenate(theta_list),
                    "pattern": np.concatenate(pattern_list)
                }, schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

                logger.info("Calculated beam pattern for %s telescopes in '%s', DF rows: %s", len(valid_telescopes), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "telescope_count": self._active_telescope_count(obj),
                "scale_instruction": "sin(theta) = wavelength * sin(t) / pi, t being the stored theta"
            }
            df = self._process_object(obj, attributes, calculate_beam_pattern, store_key, metadata)

            if not df.is_empty():
                metadata["telescope_count"] = df["telescope_code"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate beam pattern for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("beam_pattern"))

    @time_execution
    def _calculate_baseline_projections(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate baseline projections for VLBI observations in geometric coordinates (meters).

        Args:
            obj: The object to calculate projections for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate", "visibility_store_key".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "source_name", "baseline", "projection"] (projection in meters).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "baseline_projections")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")

            def calculate_baseline_projections(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                if obs.get_observation_type() != "VLBI":
                    logger.warning("Baseline projections are only for VLBI, got %s", obs.get_observation_type())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True, min_telescopes=2)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                uv_attrs = {"time_step": time_step, "store_key": "uv_coverage", "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                uv_coverage_df = self._calculate_uv_coverage(obs, uv_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or uv_coverage_df.is_empty():
                    logger.error("Missing time or UV coverage data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                times_list = []
                scan_names = []
                source_names = []
                baselines = []
                projections_list = []

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_uv = uv_coverage_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_baseline_projections, scan, obs, scan_times, scan_uv, scan_visibility, telescopes
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, source_name_arr, baseline_arr, projections = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            source_names.append(source_name_arr)
                            baselines.append(baseline_arr)
                            projections_list.append(projections)

                if not times_list:
                    logger.warning("No valid baseline projections computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "source_name": np.concatenate(source_names),
                    "baseline": np.concatenate(baselines),
                    "projection": np.concatenate(projections_list)
                }, schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

                logger.info("Calculated baseline projections for %s scans across %s baselines in '%s', DF rows: %s", df['scan_name'].unique().len(), df['baseline'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "visibility_store_key": visibility_store_key
            }
            df = self._process_object(obj, attributes, calculate_baseline_projections, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate baseline projections for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("baseline_projections"))

    @staticmethod
    def _on_time_grid(times_mjd: np.ndarray, frame: pl.DataFrame, columns: List[str], baseline: str, scan_name: str) -> Dict[str, np.ndarray]:
        """Place a frame's columns on the scan's time grid, matching on time rather than on position.

        Args:
            times_mjd (np.ndarray): The scan's time grid, as MJD.
            frame (pl.DataFrame): Rows to place, carrying a "time" column.
            columns (List[str]): The columns to return.
            baseline (str): Named only so a dropped row can be reported usefully.
            scan_name (str): Likewise.

        Returns:
            Dict[str, np.ndarray]: One array per requested column, each the length of the grid,
                holding NaN where the frame has no row for that time.

        Notes:
            - Matching on time is the whole point. A calculation that covers only part of the
              grid -- UV coverage covers only the times the source is up -- produces fewer rows
              than the grid has, and the two are not aligned from the start. Copying such rows
              into the first N positions puts every value at the wrong time. Where the source
              rose partway through a scan, as it usually does, the result was that no value
              survived the visibility mask at all and every projection came out NaN.
            - **Matched in numpy, not joined in polars.** The same rule -- the first row at each
              moment of the grid, NaN where there is none -- but a DataFrame built, deduplicated
              and joined per call cost a fraction of a millisecond, and this is called three times
              per baseline per scan: ten stations over fifty scans spent five seconds here.
        """
        grid = np.asarray(times_mjd, dtype=float)
        if frame.height == 0:
            return {column: np.full(len(grid), np.nan) for column in columns}
        moments, first = np.unique(frame["time"].to_numpy().astype(float), return_index=True)
        found = np.clip(np.searchsorted(moments, grid), 0, len(moments) - 1)
        hit = moments[found] == grid
        matched = int(np.count_nonzero(hit))
        if matched < frame.height:
            logger.debug("Only %s of %s rows for baseline '%s' in scan '%s' fall on the time grid",
                         matched, frame.height, baseline, scan_name)
        rows = first[found[hit]]
        placed = {}
        for column in columns:
            values = frame[column].cast(pl.Float64).fill_null(float("nan")).to_numpy()
            out = np.full(len(grid), np.nan)
            out[hit] = values[rows]
            placed[column] = out
        return placed

    def _process_baseline_projections(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, uv_coverage_df: pl.DataFrame, visibility_df: pl.DataFrame, telescopes: List[Telescope | SpaceTelescope]) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process baseline projections for a single scan in geometric coordinates (meters).

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            uv_coverage_df (pl.DataFrame): Precomputed UV coverage data filtered by scan_name.
            visibility_df (pl.DataFrame): Precomputed visibility data filtered by scan_name.
            telescopes (List[Telescope | SpaceTelescope]): List of active telescopes.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, source_names, baselines, projections) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        source_name = source.name
        active_telescopes = [t for t in telescopes if t.isactive]
        if len(active_telescopes) < 2:
            logger.warning("Insufficient telescopes (%s) for baseline projections in scan '%s'", len(active_telescopes), scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source_name)
            return None

        times_list = []
        scan_names = []
        source_names = []
        baselines = []
        projections_list = []

        pairs = [f"{active_telescopes[i].get_code()}-{active_telescopes[j].get_code()}" for i, j in zip(*np.triu_indices(len(active_telescopes), k=1))]

        # Split once rather than filtered per baseline, and each station's visibility placed on
        # the grid once rather than once per baseline it belongs to.
        uv_by_baseline = {key[0]: part for key, part in uv_coverage_df.partition_by("baseline", as_dict=True).items()}             if not uv_coverage_df.is_empty() else {}
        seen_by_station = {}
        for key, part in (visibility_df.partition_by("telescope_code", as_dict=True).items()
                          if not visibility_df.is_empty() else ()):
            seen_by_station[key[0]] = self._on_time_grid(times_mjd, part, ["visibility"], key[0], scan_name)["visibility"]

        for baseline in pairs:
            tel1_code, tel2_code = baseline.split('-')
            uv_data = uv_by_baseline.get(baseline, uv_coverage_df.clear())

            projections = np.full(n_times, np.nan, dtype=float)

            if uv_data.is_empty():
                logger.debug("No UV data for baseline '%s' in scan '%s'; filling with NaN", baseline, scan_name)
            else:
                aligned = self._on_time_grid(times_mjd, uv_data, ["u", "v"], baseline, scan_name)
                u, v = aligned["u"], aligned["v"]
                projections = np.sqrt(u**2 + v**2)

            for telescope_code in (tel1_code, tel2_code):
                visible = seen_by_station.get(telescope_code)
                if visible is None:
                    continue
                projections[~(visible > 0)] = np.nan

            valid_count = np.sum(~np.isnan(projections))
            logger.debug("Computed %s valid projections for baseline '%s' in scan '%s'", valid_count, baseline, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            baselines.append(np.full(n_times, baseline, dtype=object))
            projections_list.append(projections)

        if not times_list:
            logger.warning("No valid baseline projections computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed baseline projections for %s baselines in scan '%s'", len(baselines), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(source_names),
            np.concatenate(baselines),
            np.concatenate(projections_list)
        )

    @time_execution
    def _calculate_mollweide_tracks(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate Mollweide projection tracks for telescopes in active scans.

        Args:
            obj: The object to calculate tracks for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate".

        Returns:
            pl.DataFrame: DataFrame with columns ["time", "scan_name", "telescope_code", "lon", "lat"] (lon, lat in degrees).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "mollweide_tracks")

            def calculate_mollweide(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, _, _ = self._get_active_components(obs, require_scans=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": "telescope_positions", "recalculate": False}
                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)

                if times_df.is_empty() or position_df.is_empty():
                    logger.error("Missing time or position data for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                times_list = []
                scan_names = []
                telescope_codes = []
                lons_list = []
                lats_list = []

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s' in observation '%s'", scan_name, obs.get_observation_code())
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_mollweide_tracks, scan, obs, scan_times, scan_positions
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, lons, lats = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            lons_list.append(lons)
                            lats_list.append(lats)

                if not times_list:
                    logger.warning("No valid Mollweide tracks computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "lon": np.concatenate(lons_list),
                    "lat": np.concatenate(lats_list)
                }, schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

                logger.info("Calculated Mollweide tracks for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            sources_metadata = {}
            for source in obj.get_sources().get_active_items():
                ra = source.ra_degrees
                dec = source.dec_degrees
                lon = ra - 360.0 if ra > 180.0 else ra
                lat = np.clip(dec, -90.0, 90.0)
                sources_metadata[source.name] = np.array([lon, lat])

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "sources": sources_metadata
            }
            df = self._process_object(obj, attributes, calculate_mollweide, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df
        except Exception as e:
            logger.error("Failed to calculate Mollweide tracks for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("mollweide_tracks"))

    def _process_mollweide_tracks(self, scan: Scan, observation: Observation, times_mjd: np.ndarray, position_df: pl.DataFrame) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process Mollweide tracks for a single scan using vectorized computations.

        Args:
            scan (Scan): The scan to process.
            observation (Observation): Parent observation.
            times_mjd (np.ndarray): Precomputed times (MJD as float).
            position_df (pl.DataFrame): Precomputed telescope positions filtered by scan_name.

        Returns:
            Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]: 
                Tuple of (times, scan_names, telescope_codes, lons, lats) as Numpy arrays, or None if no valid data.
        """
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s' in observation '%s'", scan.name, observation.get_observation_code())
            return None

        scan_name = scan.name
        scan_telescopes = scan.get_telescopes(observation)
        active_telescopes = [t for t in scan_telescopes.get_items() if t.isactive]
        if not active_telescopes:
            logger.warning("No active telescopes for scan '%s' starting at %s", scan_name, scan.get_start().isot)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s' in source '%s'", scan_name, source.name)
            return None

        times_list = []
        scan_names = []
        telescope_codes = []
        lons_list = []
        lats_list = []

        for tel in active_telescopes:
            tel_code = tel.get_code()
            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            if tel_positions.is_empty():
                logger.debug("No position data for telescope '%s' in scan '%s'; filling with NaN", tel_code, scan_name)
                positions = np.full((n_times, 3), np.nan, dtype=float)
            else:
                positions = tel_positions.select(["x", "y", "z"]).to_numpy()
                if len(positions) != n_times:
                    logger.debug("Position data length mismatch for '%s' in scan '%s': got %s, expected %s; adjusting with NaN", tel_code, scan_name, len(positions), n_times)
                    temp = np.full((n_times, 3), np.nan, dtype=float)
                    temp[:min(len(positions), n_times)] = positions[:n_times]
                    positions = temp

            r = np.sqrt(np.sum(positions**2, axis=1))
            valid_mask = r > 0  # avoid division by zero
            ra_rad = np.full(n_times, np.nan, dtype=float)
            dec_rad = np.full(n_times, np.nan, dtype=float)
            ra_rad[valid_mask] = np.arctan2(positions[valid_mask, 1], positions[valid_mask, 0])
            dec_rad[valid_mask] = np.arcsin(positions[valid_mask, 2] / r[valid_mask])
            ra = np.degrees(ra_rad)
            dec = np.degrees(dec_rad)
            lon = np.where(ra > 180.0, ra - 360.0, ra)
            lat = np.clip(dec, -90.0, 90.0)

            valid_points = np.sum(~np.isnan(lon) & ~np.isnan(lat))
            if valid_points == 0:
                logger.debug("No valid Mollweide coordinates for telescope '%s' in scan '%s'", tel_code, scan_name)
            else:
                logger.debug("Computed %s valid Mollweide coordinates for telescope '%s' in scan '%s'", valid_points, tel_code, scan_name)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            lons_list.append(lon)
            lats_list.append(lat)

        if not times_list:
            logger.warning("No valid Mollweide tracks computed for scan '%s'", scan_name)
            return None

        logger.debug("Computed Mollweide tracks for %s telescopes in scan '%s'", len(telescope_codes), scan_name)
        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(lons_list),
            np.concatenate(lats_list)
        )

    @time_execution
    def _calculate_parallactic_angle(self, obj: Observation | ScheduleProject, attributes: Dict[str, Any]) -> pl.DataFrame:
        """Calculate parallactic angle for ground-based telescopes in all active scans.

        The parallactic angle is crucial for polarization observations as it describes
        the orientation of the feed relative to the sky.

        Args:
            obj: The object to calculate parallactic angle for (Observation or ScheduleProject).
            attributes: Parameters including "time_step", "store_key", "recalculate",
                       "position_store_key", "visibility_store_key".

        Returns:
            pl.DataFrame: DataFrame with columns 
                ["time", "scan_name", "telescope_code", "source_name", "parallactic_angle"] 
                (angle in degrees, range usually -180 to +180).
        """
        try:
            time_step = attributes.get("time_step")
            store_key = attributes.get("store_key", "parallactic_angle")
            position_store_key = attributes.get("position_store_key", "telescope_positions")
            visibility_store_key = attributes.get("visibility_store_key", "source_visibility")

            def calculate_parallactic(obs: Observation, attrs: Dict[str, Any]) -> pl.DataFrame:
                scans, telescopes, _ = self._get_active_components(obs, require_telescopes=True)
                if not scans:
                    logger.warning("No active scans in observation '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                # Only ground telescopes are relevant for parallactic angle
                ground_telescopes = [tel for tel in telescopes if not isinstance(tel, SpaceTelescope)]
                if not ground_telescopes:
                    logger.debug("No ground telescopes in '%s' for parallactic angle calculation", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                time_attrs = {"time_step": time_step, "store_key": "times", "recalculate": False}
                position_attrs = {"time_step": time_step, "store_key": position_store_key, "recalculate": False}
                visibility_attrs = {"time_step": time_step, "store_key": visibility_store_key, "recalculate": False}

                times_df = self._calculate_time_arrays(obs, time_attrs)
                position_df = self._calculate_telescope_positions(obs, position_attrs)
                visibility_df = self._calculate_source_visibility(obs, visibility_attrs)

                if times_df.is_empty() or position_df.is_empty() or visibility_df.is_empty():
                    logger.error("Missing required data for parallactic angle in '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                times_list = []
                scan_names = []
                telescope_codes = []
                source_names = []
                pa_list = []

                self._warm_topocentric(obs, scans, times_df, position_df)

                with _InTurn() as executor:
                    futures = {}
                    for scan in scans:
                        scan_name = scan.name
                        scan_times = times_df.filter(pl.col("scan_name") == scan_name)["time"].to_numpy()
                        if len(scan_times) == 0:
                            logger.warning("No valid times for scan '%s'", scan_name)
                            continue
                        scan_positions = position_df.filter(pl.col("scan_name") == scan_name)
                        scan_visibility = visibility_df.filter(pl.col("scan_name") == scan_name)
                        futures[executor.submit(
                            self._process_parallactic_angle,
                            scan, obs, scan_times, scan_positions, scan_visibility
                        )] = scan_name

                    for future in futures:
                        scan_name = futures[future]
                        scan_result = future.result()
                        if scan_result is not None:
                            times, scan_name_arr, tel_codes, source_name_arr, pa = scan_result
                            times_list.append(times)
                            scan_names.append(scan_name_arr)
                            telescope_codes.append(tel_codes)
                            source_names.append(source_name_arr)
                            pa_list.append(pa)

                if not times_list:
                    logger.warning("No valid parallactic angle data computed for '%s'", obs.get_observation_code())
                    return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                df = pl.DataFrame({
                    "time": np.concatenate(times_list),
                    "scan_name": np.concatenate(scan_names),
                    "telescope_code": np.concatenate(telescope_codes),
                    "source_name": np.concatenate(source_names),
                    "parallactic_angle": np.concatenate(pa_list)
                }, schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

                logger.info("Calculated parallactic angles for %s scans across %s telescopes in '%s', DF rows: %s", df['scan_name'].unique().len(), df['telescope_code'].unique().len(), obs.get_observation_code(), df.height)
                return df

            metadata = {
                "time_step": time_step,
                "scan_count": self._active_scan_count(obj),
                "position_store_key": position_store_key,
                "visibility_store_key": visibility_store_key
            }

            df = self._process_object(obj, attributes, calculate_parallactic, store_key, metadata)

            if not df.is_empty():
                metadata["scan_count"] = df["scan_name"].unique().len()
                self._store_result(obj, store_key, df, metadata)

            return df

        except Exception as e:
            logger.error("Failed to calculate parallactic angle for '%s': %s", obj.get_observation_code() if isinstance(obj, Observation) else obj.name, str(e), exc_info=True)
            return pl.DataFrame(schema=CalculatedDataStructure.get_dtypes("parallactic_angle"))

    def _process_parallactic_angle(
            self,
            scan: Scan,
            observation: Observation,
            times_mjd: np.ndarray,
            position_df: pl.DataFrame,
            visibility_df: pl.DataFrame
        ) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """Process parallactic angle for a single scan using robust vectorized calculation."""
        source = scan.get_source(observation)
        if not source or not source.isactive:
            logger.warning("No active source for scan '%s'", scan.name)
            return None

        scan_name = scan.name
        source_name = source.name
        scan_telescopes = scan.get_telescopes(observation)
        active_ground_telescopes = [
            t for t in scan_telescopes.get_items() 
            if t.isactive and not isinstance(t, SpaceTelescope)
        ]

        if not active_ground_telescopes:
            logger.debug("No active ground telescopes for parallactic angle in scan '%s'", scan_name)
            return None

        n_times = len(times_mjd)
        if n_times == 0:
            logger.warning("No valid times for scan '%s'", scan_name)
            return None


        times_list = []
        scan_names = []
        telescope_codes = []
        source_names = []
        pa_list = []

        for tel in active_ground_telescopes:
            tel_code = tel.get_code()

            tel_positions = position_df.filter(pl.col("telescope_code") == tel_code)
            tel_visibility = visibility_df.filter(pl.col("telescope_code") == tel_code)

            if tel_positions.is_empty() or tel_visibility.is_empty():
                logger.warning("Missing position or visibility data for '%s' in scan '%s'", tel_code, scan_name)
                continue

            positions = tel_positions.select(["x", "y", "z"]).to_numpy()
            visibility = tel_visibility["visibility"].to_numpy()

            if len(positions) != n_times or len(visibility) != n_times:
                logger.warning("Data length mismatch for '%s' in scan '%s'", tel_code, scan_name)
                positions = np.full((n_times, 3), np.nan, dtype=float)
                visibility = np.full(n_times, False, dtype=bool)

            nan_positions = np.any(np.isnan(positions), axis=1)
            is_visible = visibility & ~nan_positions

            parallactic = np.full(n_times, np.nan, dtype=float)

            if np.any(is_visible):
                try:
                    # From the direction the mount already needed, rather than a transform of
                    # its own. On the celestial sphere the angle at the source between the pole
                    # and the zenith is the same spherical triangle written either way:
                    #   q = atan2( sin H cos(phi), sin(phi) cos(dec) - cos(phi) sin(dec) cos H)
                    #     = atan2(-sin A cos(phi), sin(phi) cos(h)   - cos(phi) sin(h)   cos A)
                    # -- equal to 1e-13 degrees against astropy's own hour angle, measured.
                    if tel.get("mount_type").value == "EQUA":
                        hour, declination, latitude = self._topocentric(source, positions, times_mjd, "hadec")
                        hour, declination = np.radians(hour[is_visible]), np.radians(declination[is_visible])
                        lat = np.radians(latitude[is_visible])
                        sin_pa = np.sin(hour) * np.cos(lat)
                        cos_pa = (np.sin(lat) * np.cos(declination)
                                  - np.cos(lat) * np.sin(declination) * np.cos(hour))
                    else:
                        azimuth, altitude, latitude = self._topocentric(source, positions, times_mjd, "altaz")
                        azimuth, altitude = np.radians(azimuth[is_visible]), np.radians(altitude[is_visible])
                        lat = np.radians(latitude[is_visible])
                        sin_pa = -np.sin(azimuth) * np.cos(lat)
                        cos_pa = (np.sin(lat) * np.cos(altitude)
                                  - np.cos(lat) * np.sin(altitude) * np.cos(azimuth))
                    pa_rad = np.arctan2(sin_pa, cos_pa)

                    pa_deg = np.degrees(pa_rad)
                    pa_deg = (pa_deg + 180) % 360 - 180

                    parallactic[is_visible] = pa_deg

                except Exception as inner_e:
                    logger.warning("Failed to compute parallactic angle for '%s' in scan '%s': %s", tel_code, scan_name, inner_e, exc_info=True)

            times_list.append(times_mjd)
            scan_names.append(np.full(n_times, scan_name, dtype=object))
            telescope_codes.append(np.full(n_times, tel_code, dtype=object))
            source_names.append(np.full(n_times, source_name, dtype=object))
            pa_list.append(parallactic)

            valid_count = np.sum(~np.isnan(parallactic))
            logger.debug("Computed parallactic angles for '%s' in scan '%s': %s/%s valid points", tel_code, scan_name, valid_count, n_times)

        if not times_list:
            logger.warning("No parallactic angle data computed for scan '%s'", scan_name)
            return None

        return (
            np.concatenate(times_list),
            np.concatenate(scan_names),
            np.concatenate(telescope_codes),
            np.concatenate(source_names),
            np.concatenate(pa_list)
        )