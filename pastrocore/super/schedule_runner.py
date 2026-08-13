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
import threading
import time
from typing import Any, Dict, List

from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

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
        result = response["result"] if isinstance(response, dict) and "status" in response else response
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
        wanted = list(attributes.get("calculations") or [])
        if not targets:
            raise ValueError("No 'targets' given; there is nothing to calculate for")
        if not wanted:
            raise ValueError("No 'calculations' given; there is nothing to run")

        # Everything asked for, plus everything those need, in an order that satisfies them.
        needed = list(wanted)
        for key in wanted:
            for prerequisite in self._manipulator.requirements_of("calculate", key):
                if prerequisite not in needed:
                    needed.append(prerequisite)
        ordered = self._manipulator.order_handlers("calculate", needed)

        passed = {name: value for name, value in attributes.items()
                  if name not in ("calculations", "targets", "method")}

        plan: Dict[str, Dict[str, Any]] = {}
        for target in targets:
            previous_by_key = {}
            for key in ordered:
                name = f"{target.code}/{key}"
                step = {"operation": "calculate", "obj": target, "method": key,
                        "store_key": key}
                step.update(passed)
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
            with guard:
                seen["done"] += 1
                done = seen["done"]
                measured[f"{code}/{key}"] = elapsed
            report(int(done / total * 100) if total else 100,
                   f"Calculated {labels.get(key, key) or key} in {elapsed:.2f} s")
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

        return {"ran": ran,
                "failed": list(outcome.failed),
                "cancelled": seen["stopped"],
                "timings": timings,
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
