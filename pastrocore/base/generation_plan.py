# pastrocore/base/generation_plan.py
"""What a generation is, as one object: what to observe with what, when, and in what pattern (O1).

Notes:
    - **The arithmetic of a pattern lives here and nowhere else.** The generator worked out how long
      a pattern takes in order to place its scans, and the dialog worked the same thing out again to
      show an end time -- two implementations of one formula, and the dialog's inverse (the scan
      duration that fits a given end) was a third. They are one now, and the window asks.
    - **A plan is data, so it is a file.** What a preset used to save was the timing and not what it
      was for: the sources, stations and bands were dropped, so loading one left the dialog with a
      pattern and nothing to point it at. A plan carries the collections themselves.
    - The built-in presets are here rather than in the dialog, for the same reason every other list
      the interface shows is asked for rather than written down.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from msb_arch.utils.logging_setup import logger

from pastrocore.base.frequencies import Frequencies
from pastrocore.base.sources import Sources
from pastrocore.base.telescopes import Telescopes

#: How a time is written in a plan file: ISO 8601, to the second.
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class GenerationPlan:
    """One generation: the collections it runs on, when it starts, and the pattern it repeats.

    Args:
        observation_type (str): `VLBI` or `SINGLE_DISH`.
        start (Optional[datetime]): When the first scan starts.
        scan_duration (float): Seconds on source, per scan.
        num_scans (int): Scans per observation.
        interval_sec (float): Seconds between one scan block and the next.
        add_off_source (bool): Follow each scan with an off-source scan of the same length.
        parallel (bool): Every observation starts at the same moment; otherwise they follow one
            another, and the plan is as long as all of them together.
        naming_mask (str): How each observation is named.
        sources (Sources): One observation is generated per source.
        telescopes (Telescopes): The array. `SINGLE_DISH` uses the first of them.
        frequencies (Frequencies): The bands each scan records.
    """

    observation_type: str = "VLBI"
    start: Optional[datetime] = None
    scan_duration: float = 300.0
    num_scans: int = 5
    interval_sec: float = 0.0
    add_off_source: bool = False
    parallel: bool = True
    naming_mask: str = "Observation_{i}_{s}_{dt}"
    sources: Sources = field(default_factory=Sources)
    telescopes: Telescopes = field(default_factory=Telescopes)
    frequencies: Frequencies = field(default_factory=Frequencies)

    # --- how long a pattern takes ---------------------------------------------------------------

    @property
    def scan_block(self) -> float:
        """One scan, and the off-source scan after it when the pattern has one, in seconds."""
        return float(self.scan_duration) * (2 if self.add_off_source else 1)

    @property
    def observations(self) -> int:
        """How many observations the plan makes: one per source, and at least one to reason about."""
        return max(len(self.sources.get_items()), 1)

    def span_per_observation(self) -> float:
        """Seconds from the first scan of an observation to the end of its last.

        Notes:
            - The interval falls *between* blocks, so `n` scans carry `n - 1` of them. An interval
              after the last scan would be time the observation does not use.
        """
        if self.num_scans <= 0:
            return 0.0
        return self.scan_block + (self.num_scans - 1) * (self.scan_block + float(self.interval_sec))

    def span(self) -> float:
        """Seconds the whole plan takes: one observation's, or all of them end to end."""
        per = self.span_per_observation()
        return per if self.parallel else per * self.observations

    def end(self) -> Optional[datetime]:
        """When the plan finishes, or None when it does not say where it starts."""
        if self.start is None:
            return None
        return self.start + timedelta(seconds=self.span())

    def scan_duration_for(self, seconds: float) -> float:
        """The scan duration that makes the plan take `seconds` -- the inverse of `span`.

        Args:
            seconds (float): How long the whole plan should take.

        Returns:
            float: Seconds per scan, or 0 when the intervals alone are already longer than that --
                which is a pattern that does not fit, not a duration of zero.
        """
        repeats = 1 if self.parallel else self.observations
        gaps = (max(self.num_scans - 1, 0) * float(self.interval_sec)) * repeats
        scans = self.num_scans * repeats * (2 if self.add_off_source else 1)
        if scans <= 0 or seconds - gaps <= 0:
            return 0.0
        return (seconds - gaps) / scans

    # --- what the generator is asked ---------------------------------------------------------------

    def attributes(self) -> Dict[str, Any]:
        """The plan as the attributes `generate_observations` takes."""
        return {
            "sources": self.sources,
            "telescopes": self.telescopes,
            "frequencies": self.frequencies,
            "observation_type": self.observation_type,
            "time_range": {"start": self.start, "end": self.end()},
            "scan_duration": float(self.scan_duration),
            "num_scans": int(self.num_scans),
            "parallel": bool(self.parallel),
            "pattern": {"add_off_source": bool(self.add_off_source),
                        "interval_sec": float(self.interval_sec),
                        "naming_mask": self.naming_mask},
        }

    # --- a plan as a file ----------------------------------------------------------------------

    @staticmethod
    def _collection(held: Any) -> Dict[str, Any]:
        """A collection as data, without the name its container happens to carry.

        Notes:
            - A plan is about *which* sources, stations and bands, not about the container holding
              them, and those names are generated: `srcs_<uuid>`. Kept, two plans over the same
              selection would never compare equal and a file would change on every save.
        """
        return {key: value for key, value in held.to_dict().items() if key != "name"}

    def to_dict(self) -> Dict[str, Any]:
        """The whole plan as plain data, collections included."""
        return {
            "observation_type": self.observation_type,
            "start": self.start.strftime(TIME_FORMAT) if self.start else None,
            "scan_duration": float(self.scan_duration),
            "num_scans": int(self.num_scans),
            "interval_sec": float(self.interval_sec),
            "add_off_source": bool(self.add_off_source),
            "parallel": bool(self.parallel),
            "naming_mask": self.naming_mask,
            "sources": self._collection(self.sources),
            "telescopes": self._collection(self.telescopes),
            "frequencies": self._collection(self.frequencies),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationPlan":
        """Read a plan back, with whatever it carries; what is missing takes the default.

        Args:
            data (Dict[str, Any]): What `to_dict` wrote, or a subset of it -- a plan written by an
                older version has fewer keys, and is worth reading rather than refusing.

        Returns:
            GenerationPlan: The plan.
        """
        plan = cls()
        start = data.get("start")
        if start:
            try:
                plan.start = datetime.strptime(start, TIME_FORMAT)
            except ValueError:
                logger.warning("A plan's start time is not %s: '%s'", TIME_FORMAT, start)
        for name, convert in (("observation_type", str), ("scan_duration", float), ("num_scans", int),
                              ("interval_sec", float), ("add_off_source", bool), ("parallel", bool),
                              ("naming_mask", str)):
            if data.get(name) is not None:
                setattr(plan, name, convert(data[name]))
        for name, kind in (("sources", Sources), ("telescopes", Telescopes), ("frequencies", Frequencies)):
            held = data.get(name)
            if held:
                setattr(plan, name, kind.from_dict(held))
        return plan

    @classmethod
    def of(cls, data: Any) -> "GenerationPlan":
        """A plan from whatever shape it arrives in.

        Args:
            data (Any): A plan; or a mapping of its fields whose collections are either the
                objects themselves -- which is what a window holds and hands to a request -- or
                their data, which is what a file holds.

        Returns:
            GenerationPlan: The plan.

        Notes:
            - **So that nothing outside has to convert.** The window sends what it is showing and
              the backend reads it; a file is read the same way. The interface reaches the model
              through requests, and `to_dict` on the way out of a dialog was exactly that rule
              being broken.
        """
        if isinstance(data, cls):
            return data
        data = dict(data or {})
        for name, kind in (("sources", Sources), ("telescopes", Telescopes),
                           ("frequencies", Frequencies)):
            held = data.get(name)
            if isinstance(held, kind):
                data[name] = held.to_dict()
        start = data.get("start")
        if isinstance(start, datetime):
            data["start"] = start.strftime(TIME_FORMAT)
        return cls.from_dict(data)

    def as_mapping(self) -> Dict[str, Any]:
        """The plan as its fields, holding the collections themselves rather than their data.

        Notes:
            - What a window is given back when it reads a plan: it shows the collections and sets
              the fields, and converts nothing.
        """
        mapping = self.to_dict()
        mapping["start"] = self.start
        mapping["sources"] = self.sources
        mapping["telescopes"] = self.telescopes
        mapping["frequencies"] = self.frequencies
        return mapping

    def with_collections(self, sources: Sources = None, telescopes: Telescopes = None,
                         frequencies: Frequencies = None) -> "GenerationPlan":
        """A copy of this plan pointed at other collections -- what a preset is, given a selection."""
        return replace(self,
                       sources=sources if sources is not None else self.sources,
                       telescopes=telescopes if telescopes is not None else self.telescopes,
                       frequencies=frequencies if frequencies is not None else self.frequencies)


#: The patterns worth starting from, as plans rather than as a table in a dialog. A preset says
#: nothing about what to observe: that is the selection the user has already made.
PRESETS: Dict[str, Dict[str, Any]] = {
    "Standard VLBI": {"observation_type": "VLBI", "scan_duration": 300.0, "num_scans": 10,
                      "interval_sec": 300.0, "add_off_source": False, "parallel": True},
    "Quick Single Dish": {"observation_type": "SINGLE_DISH", "scan_duration": 60.0, "num_scans": 5,
                          "interval_sec": 60.0, "add_off_source": True, "parallel": False},
}


def presets() -> List[Dict[str, Any]]:
    """Every built-in pattern, in the order they are offered.

    Returns:
        List[Dict[str, Any]]: `{"name": str, "plan": dict}` for each, the plan being what
            `GenerationPlan.from_dict` reads.
    """
    # Without the collections: a preset is a pattern, and it is applied to whatever is selected.
    # Empty ones would also carry a fresh random container name on every call, which would make two
    # identical presets compare unequal.
    pattern_only = []
    for name, settings in PRESETS.items():
        plan = GenerationPlan(**settings).to_dict()
        for collection in ("sources", "telescopes", "frequencies"):
            plan.pop(collection, None)
        pattern_only.append({"name": name, "plan": plan})
    return pattern_only
