# super/schedule_runner.py
"""Running a set of calculations: what can be run, in what order, and what it did.

Split out of `ScheduleData` deliberately. Exporting means getting data *out* of a project --
files, pictures, a save; orchestrating calculations is a different concern that had ended up
there because that is where the plumbing already was.

It cannot live on the calculator either, and that is mechanical rather than a matter of taste:
a `Super`'s handlers *are* its operation's methods, and the methods of `calculate` are the
calculations themselves. A `_calculate_run` would appear in the catalogue as a calculation
called "Run", offered in the dialog beside UV Coverage -- checked, not assumed. So this is a
third operation, `compute`, and the split is one sentence: **`calculate` does one, `compute`
orchestrates many, `export` writes the results somewhere.**

Nothing here knows about signals, threads or windows. What a caller passes in is at most two
callables -- one to report progress, one to ask whether to stop -- which is the whole seam a
window, a command line and a server share.
"""
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base import freshness
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject


class ScheduleRunner(Super):
    """Planning and running calculations, and saying what there is to run.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "compute"

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.debug("Initialized ScheduleRunner")

    @staticmethod
    def _targets(obj: Any) -> List[Observation]:
        """Return the observations a run covers.

        Notes:
            - A project answers for itself what it holds. Reading `get_items()` and guessing
              whether it came back as a mapping is how eight calculations ended up iterating a
              project's keys.
        """
        if isinstance(obj, ScheduleProject):
            return obj.observations()
        if isinstance(obj, (list, tuple)):
            return list(obj)
        return [obj]

    def _held_by(self, observation: Any) -> List[str]:
        """Return the results an observation already holds.

        Notes:
            - Asked of the export operation rather than worked out here. Which results exist on
              disk is a fact about stored data, and that is what `export` is for.
        """
        response = self._manipulator.export(obj=observation, method="available",
                                            raise_on_error=False)
        result = response.value
        return result or []

    #: What this model calls its parts, keyed by the accessor that reaches each. MSB reports
    #: the names a handler calls, without claiming to know what any of them mean; this is
    #: where that is said, and it is the only application-shaped thing the catalogue needs.
    MODEL_PARTS = {"get_telescopes": "telescopes", "get_sources": "sources",
                   "get_scans": "scans", "get_frequencies": "frequencies"}

    #: Words that keep their capitals when a handler's name becomes a label.
    ACRONYMS = {"uv": "UV", "az": "Az", "el": "El", "if": "IF", "sefd": "SEFD"}


    def _compute_plan(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build the plan that runs a set of calculations over a set of observations.

        Args:
            obj: Ignored; the observations are named in `targets`.
            attributes: `calculations`, the result keys asked for; `targets`, the observations;
                and any other attribute -- `time_step`, `target_telescope`, `recalculate` --
                which is passed to every step that accepts it.

        Returns:
            Dict[str, Dict[str, Any]]: A pipeline plan, keyed `<observation code>/<result>`.

        Notes:
            - The edges come from `requirements_of`, which MSB derives from the handlers
              themselves, so a calculation that gains a prerequisite gains an edge here without
              anything being written down.
            - A prerequisite nobody asked for is added to the plan: `telescope_visibility`
              cannot run without `telescope_az_el`, and a caller naming only the first means
              both.
            - Building the plan is separate from running it so a caller can look at it -- a
              command line printing what it is about to do, a test asserting the order.
        """
        targets = attributes.get("targets") or self._targets(obj)
        # A target may be named rather than handed over. That is what a replayed session
        # carries, and what a command line or a server would send -- a request is data, and an
        # observation in a JSON body can only be a name.
        targets = [self._manipulator.find(target) if isinstance(target, str) else target
                   for target in targets]
        missing = [target for target in targets if target is None]
        if missing:
            raise ValueError(f"{len(missing)} named target(s) are not in this project")
        wanted = list(attributes.get("calculations") or [])
        if not targets:
            raise ValueError("No 'targets' given; there is nothing to calculate for")
        if not wanted:
            raise ValueError("No 'calculations' given; there is nothing to run")

        # Everything asked for, plus everything those need, in an order that satisfies them.
        # MSB 1.7.0 does the join: these were six lines here, and the same six in anything else
        # that orchestrates an operation.
        ordered = self._manipulator.plan_for("calculate", wanted)

        passed = {name: value for name, value in attributes.items()
                  if name not in ("calculations", "targets", "method", "force", "recalculate")}

        # What a run recomputes, by default, is what has gone stale -- freshness already knows,
        # and a run that reuses a result whose inputs have changed is the interface showing a
        # number computed from a configuration that no longer exists. Worse, the reused frame
        # was then re-stamped as current, so freshness stopped saying so.
        #
        # Forcing is a separate thing to ask for, because the only case it serves is a change
        # freshness cannot see by construction: the calculation's own code.
        force = bool(attributes.get("force") or attributes.get("recalculate"))

        plan: Dict[str, Dict[str, Any]] = {}
        for target in targets:
            previous_by_key = {}
            for key in ordered:
                name = f"{target.code}/{key}"
                # Named by handler, filed under the schema's key. They are the same string for
                # every calculation but one, and passing the handler's name for that one stored
                # the result where nothing reads it.
                store_key = CalculatedDataStructure.store_key_for(key)
                step = {"operation": "calculate", "obj": target, "method": key,
                        "store_key": store_key}
                step.update(passed)
                # None means "cannot be told" -- a result predating the mechanism -- and that
                # is left alone deliberately: calling it stale would make opening an old
                # project a recomputation of everything in it.
                step["recalculate"] = force or freshness.is_stale(target, store_key) is True
                waits = [previous_by_key[prerequisite]
                         for prerequisite in self._manipulator.requirements_of("calculate", key)
                         if prerequisite in previous_by_key]
                if waits:
                    step["after"] = waits
                plan[name] = step
                previous_by_key[key] = name
        return plan

    def _compute_run(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Run the plan `_export_plan` builds, and report what each step did.

        Args:
            obj: As for `_export_plan`.
            attributes: As for `_export_plan`, plus `concurrent` to let independent steps of a
                stage run together, `progress`, called with a percentage and a message, and
                `cancelled`, called to ask whether to stop.

        Returns:
            Dict[str, Any]: `{"ran": [...], "failed": [...], "cancelled": bool,
                "timings": {step: seconds}}` -- step names, in plan order.

        Notes:
            - The whole point of doing it here rather than in a dialog: an interface, a command
              line and a server all send one request, and the ordering, the prerequisites and
              the skipping of a branch below a failure are the framework's job.
            - Progress, cancellation and timing ride on an interceptor, which is what the hook
              is for. It sees each step as it goes past, so nothing has to be counted twice, and
              a cancellation is a refused request -- which skips the branch below it exactly as
              a failure does.
            - Timing belongs here rather than in the caller: with a stage running several steps
              at once, the wall clock between two progress callbacks is not any one
              calculation's duration.
            - Progress is reported when a step **finishes**. A bar advanced on starting sits at
              80% through the longest step of the run and then jumps, which is the shape of a
              bar that looks stuck.
        """
        plan = self._compute_plan(obj, attributes)
        report = attributes.get("progress") or (lambda percent, message: None)
        cancelled = attributes.get("cancelled") or (lambda: False)

        total = len(plan)
        seen = {"done": 0, "stopped": False}
        labels = {name: name.split("/", 1)[-1] for name in plan}
        # A step is named by its handler and files its result under the schema's key, and for
        # one calculation the two differ. The interceptor sees the request, which carries the
        # store key, so this maps back to the step the plan named.
        step_of = {f"{getattr(step.get('obj'), 'code', '')}/{step.get('store_key')}": name
                   for name, step in plan.items()}
        measured: Dict[str, float] = {}
        # Steps of one stage run in threads when asked to, so the counter and the table are
        # touched from several at once.
        guard = threading.Lock()

        def watch(request, call_next):
            if request.get("operation") != "calculate":
                return call_next(request)
            if cancelled():
                seen["stopped"] = True
                return {"status": False, "object": None, "method": None, "result": None,
                        "error": "Cancelled", "error_type": "RequestError"}

            started = time.perf_counter()
            response = call_next(request)
            elapsed = time.perf_counter() - started

            key = request.get("attributes", {}).get("store_key", "")
            code = getattr(request.get("obj"), "code", "")
            name = step_of.get(f"{code}/{key}", f"{code}/{key}")
            with guard:
                seen["done"] += 1
                done = seen["done"]
                measured[name] = elapsed
            report(int(done / total * 100) if total else 100,
                   f"Calculated {labels.get(name, key) or key} in {elapsed:.2f} s")
            return response

        self._manipulator.add_interceptor(watch)
        try:
            outcome = self._manipulator.pipeline(
                plan, raise_on_error=False, concurrent=bool(attributes.get("concurrent")))
        finally:
            self._manipulator.remove_interceptor(watch)

        # In plan order rather than in the order they finished, which with a concurrent stage
        # is neither stable nor meaningful.
        timings = {name: measured[name] for name in plan if name in measured}
        ran = [name for name in outcome if name not in outcome.failed]
        slowest = max(timings, key=timings.get) if timings else None

        # One row per step, in plan order, labelled the way a person reads it. Assembled here
        # rather than by whatever displays it: a window renders this, a command line prints it
        # and a server serialises it, and none of the three should be joining three lists to
        # find out what happened.
        spelled = {entry["key"]: entry["label"]
                   for entry in self._compute_catalogue(obj, {})}
        rows = []
        for name in plan:
            if name not in measured and name not in outcome.failed:
                continue            # never reached: the run stopped above it
            key = name.split("/", 1)[-1]
            rows.append({"step": name,
                         "observation": name.split("/", 1)[0],
                         "label": spelled.get(key, labels.get(name, key)),
                         "seconds": measured.get(name, 0.0),
                         "outcome": "failed" if name in outcome.failed else "ok"})

        return {"ran": ran,
                "failed": list(outcome.failed),
                "cancelled": seen["stopped"],
                "timings": timings,
                "report": rows,
                # Summarised here rather than by whoever displays it. A window, a command line
                # and a server all want the same three numbers, and the first of them worked
                # them out for itself until this line existed.
                "summary": {"steps": len(ran), "failed": len(outcome.failed),
                            "seconds": sum(timings.values()),
                            "slowest": slowest.split("/", 1)[-1] if slowest else None,
                            "slowest_seconds": timings[slowest] if slowest else 0.0}}

    def _compute_catalogue(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Report what this application can calculate and draw.

        Args:
            obj: Ignored by the catalogue itself.
            attributes: `available_for` -- an observation, to mark which entries it already
                holds a result for.

        Returns:
            List[Dict[str, Any]]: One entry per calculation, each with its `key`, `label`, the
                other calculations it `requires`, whether it `can_plot`, whether it
                `needs_target`, and `available` when an observation was given.

        Notes:
            - Discovered, not listed. The manipulator works out its own registry -- handlers
              name themselves and call each other by name -- so adding a calculation means
              writing `_calculate_x` and a schema entry, and nothing in any interface has to be
              told about it.
            - All this adds is what the framework cannot know: what this model calls its parts,
              and how a few words are spelled.
        """
        described = self._manipulator.describe_operations(
            interpret=self.MODEL_PARTS.get, acronyms=self.ACRONYMS)

        calculations = described.get("calculate", {})
        plots = set(described.get("visualize", {}))

        observation = attributes.get("available_for")
        held = set(self._held_by(observation)) if observation is not None else set()

        entries = []
        for key in sorted(calculations):
            schema = CalculatedDataStructure.entry_for(key)
            entry = {
                "key": key,
                "label": schema.get("label") or calculations[key]["label"],
                "requires": calculations[key]["requires"],
                "can_plot": key in plots,
                "offer": not CalculatedDataStructure.is_intermediate(key),
                # A result recording a `target_code` is about something being tracked, so the
                # request has to say what. Read from the columns rather than listed, so a new
                # calculation of the same shape needs nothing added here.
                "needs_target": "target_code" in (schema.get("columns") or []),
            }
            if observation is not None:
                entry["available"] = key in held
            entries.append(entry)
        return entries

    def _compute_order(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """Return calculations in an order that satisfies their prerequisites.

        Args:
            obj: Ignored.
            attributes: `keys`, the calculations asked for in any order.

        Returns:
            List[str]: The same keys, each after everything it needs.

        Notes:
            - The calculations dialog used to carry this as a hardcoded table of which
              calculation needs which. That is knowledge about the model, and the model's own
              code states it already.
        """
        return self._manipulator.order_handlers("calculate", attributes.get("keys") or [])

    def _compute_history(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return what has been asked of this orchestrator in this session.

        Args:
            obj: Ignored.
            attributes: `about`, an object name to narrow it to.

        Returns:
            List[Dict[str, Any]]: One row per request -- `operation`, the `object` it named,
                the `method`, its `attributes`, whether it worked, and how long it took.

        Notes:
            - Plain data, all of it. MSB's journal records what was asked rather than the
              request as it ran, so a session can be written to a file and read anywhere --
              and, more to the point, so recording a session does not keep alive everything it
              touched.
        """
        return self._manipulator.history(attributes.get("about"))

    def _compute_replay(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Run a recorded session against the project in hand.

        Args:
            obj: Ignored; the project is whatever this orchestrator manages.
            attributes: `path`, a session written by `export(method="journal")`, or `steps`,
                the same rows in memory. `skip_failures` leaves out what failed the first time.

        Returns:
            Dict[str, Any]: `{"ran": [...], "failed": [...], "unresolved": [...]}` -- the last
                naming the steps whose object does not exist in this project.

        Raises:
            ValueError: If neither `path` nor `steps` was given.

        Notes:
            - A step names its object, so replaying resolves the name here. A session recorded
              against one project therefore runs against another, which is what makes it a
              reproduction rather than a souvenir.
            - Unresolved steps are reported rather than skipped in silence: a session that half
              ran is worse than one that refused.
        """
        steps = attributes.get("steps")
        path = attributes.get("path")
        if steps is None and not path:
            raise ValueError("No 'path' or 'steps' given; there is no session to replay")
        if steps is None:
            steps = json.loads(Path(path).read_text(encoding="utf-8")).get("steps") or []

        plan: Dict[str, Dict[str, Any]] = {}
        unresolved: List[str] = []
        previous = None
        for position, step in enumerate(steps, start=1):
            if attributes.get("skip_failures", True) and step.get("status") is False:
                continue
            named = step.get("object")
            found = self._manipulator.find(named) if isinstance(named, str) else None
            name = f"{step.get('operation')}_{position}"
            if named and found is None:
                unresolved.append(f"{name}: nothing here is called '{named}'")
                continue
            entry = {"operation": step.get("operation"), "obj": found,
                     "attributes": dict(step.get("attributes") or {})}
            if step.get("method"):
                entry["method"] = step["method"]
            if previous:
                entry["after"] = [previous]
            plan[name] = entry
            previous = name

        if not plan:
            logger.warning("Nothing in this session could be replayed here")
            return {"ran": [], "failed": [], "unresolved": unresolved}

        outcome = self._manipulator.pipeline(plan, raise_on_error=False)
        return {"ran": [name for name in outcome if name not in outcome.failed],
                "failed": list(outcome.failed),
                "unresolved": unresolved}

    def _compute_targets(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """Return what could be pointed at in a set of observations.

        Args:
            obj: An observation, a project, or a list of them; `targets` overrides it.
            attributes: `targets`, the observations to look in.

        Returns:
            List[str]: The codes of the space telescopes there, sorted, without repeats.

        Notes:
            - Asked by the calculation dialog before running anything that needs a target. It
              used to walk the model itself -- which is the model reaching into a window, and
              the reason a command line asking the same question would have to write it again.
        """
        from pastrocore.base.telescopes import SpaceTelescope

        codes = []
        for observation in (attributes.get("targets") or self._targets(obj)):
            for telescope in observation.get_telescopes().get_items():
                if isinstance(telescope, SpaceTelescope) and telescope.get_code() not in codes:
                    codes.append(telescope.get_code())
        return sorted(codes)

    def _compute_clear(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Discard the calculated results of a set of observations.

        Args:
            obj: An observation, a project, or a list of them; `targets` overrides it.
            attributes: `targets`, the observations to clear.

        Returns:
            Dict[str, Any]: `{"cleared": [codes]}`.

        Notes:
            - A request, because a window is not the only thing that wants it: a command line
              rebuilding a project from scratch asks for exactly this.
        """
        cleared = []
        for observation in (attributes.get("targets") or self._targets(obj)):
            observation.clear_calculated_data()
            cleared.append(observation.code)
        logger.info("Cleared the results of %s observation(s)", len(cleared))
        return {"cleared": cleared}

    def _compute_stale(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """Return the results of one observation whose inputs have changed since they were made.

        Args:
            obj (Observation): The observation to ask about.
            attributes: Ignored.

        Returns:
            List[str]: Store keys, sorted. Empty when nothing is known to be stale, which
                includes a result that predates the mechanism.

        Notes:
            - Reads no result: the answer comes from the metadata beside them and from the
              model, so asking costs a directory listing rather than the project.
        """
        return sorted(obj.stale_results()) if hasattr(obj, "stale_results") else []
