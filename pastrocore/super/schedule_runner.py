# super/schedule_runner.py
"""Running a set of calculations: what can be run, in what order, and what it did.

Split out of `ScheduleData` deliberately. Exporting means getting data *out* of a project --
files, pictures, a save; orchestrating calculations is a different concern that had ended up
there because that is where the plumbing already was.

It cannot live on the calculator either: a `Super`'s handlers are its operation's methods,
and the methods of `calculate` are the calculations, so a `_calculate_run` would appear in the
catalogue as a calculation called "Run". So this is a third operation: `calculate` does one,
`compute` orchestrates many, `export` writes the results somewhere.

The questions are not here. What can be calculated, in what order, what a session asked,
what is stale and what an edit would reach change nothing, so they are `RunQuestions` below and
`inspect` answers them. `ScheduleInspector` inherits them, and so does this class, which asks
them of itself while it runs.

Nothing here knows about signals, threads or windows. What a caller passes in is at most two
callables -- one to report progress, one to ask whether to stop -- which is the whole seam a
window, a command line and a server share.
"""
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from msb_arch.base.basecontainer import BaseContainer
from msb_arch.super.super import Super
from msb_arch.utils.logging_setup import logger

from pastrocore.base import freshness
from pastrocore.base.data_structure import CalculatedDataStructure
from pastrocore.base.observation import Observation
from pastrocore.super.schedule_project import ScheduleProject


class RunQuestions:
    """What there is to run and what has happened, asked rather than done.

    Handlers of `inspect`, which is the operation that only reads: `ScheduleInspector` inherits
    them and answers `inspect(method="catalogue")`, `"plan"`, `"history"` and the rest. The runner
    inherits them too, to ask its own questions without a request of its own for each.

    Notes:
        - On `inspect` rather than `compute`, so a session can leave every question out
          without a list of which of them are not calculations.
    """

    @staticmethod
    def _targets(obj: Any) -> List[Observation]:
        """Return the observations a run covers.

        Notes:
            - A project answers for itself what it holds, rather than a caller guessing
              whether `get_items()` came back as a mapping.
        """
        if isinstance(obj, ScheduleProject):
            return obj.get_observations()
        if isinstance(obj, (list, tuple)):
            return list(obj)
        return [obj]

    def _held_by(self, observation: Any) -> List[str]:
        """Return the results an observation already holds.

        Notes:
            - Asked of the export operation rather than worked out here. Which results exist on
              disk is a fact about stored data, and that is what `export` is for.
        """
        response = self._manipulator.inspect(obj=observation, method="available",
                                            raise_on_error=False)
        result = response.value
        return result or []

    #: What this model calls its parts, keyed by the accessor that reaches each. MSB
    #: reports the names a handler calls without knowing what they mean.
    MODEL_PARTS = {"get_telescopes": "telescopes", "get_sources": "sources",
                   "get_scans": "scans", "get_frequencies": "frequencies"}

    #: Words that keep their capitals when a handler's name becomes a label.
    ACRONYMS = {"uv": "UV", "az": "Az", "el": "El", "if": "IF", "sefd": "SEFD"}


    def _inspect_plan(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build the plan that runs a set of calculations over a set of observations.

        Args:
            obj: Ignored; the observations are named in `targets`.
            attributes: `calculations`, the result keys asked for; `targets`, the observations;
                and any other attribute -- `time_step`, `target_telescope`, `recalculate` --
                which is passed to every step that accepts it.

        Returns:
            Dict[str, Dict[str, Any]]: A pipeline plan, keyed `<observation code>/<result>`.

        Notes:
            - The edges come from `requirements_of`, which MSB derives from the handlers, so
              a new prerequisite is an edge here untold.
            - A prerequisite nobody asked for is added: naming `telescope_visibility` means
              `telescope_az_el` as well.
            - Built separately from being run, so a caller can look at it first.
        """
        targets = attributes.get("targets") or self._targets(obj)
        # A target may be named rather than handed over: a request is data, and an
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

        # Everything asked for, plus what those need, in an order that satisfies them.
        # MSB does the join.
        ordered = self._manipulator.plan_for("calculate", wanted)

        passed = {name: value for name, value in attributes.items()
                  if name not in ("calculations", "targets", "method", "force", "recalculate")}

        # A run recomputes what has gone stale, which freshness already knows. Forcing
        # is asked for separately: the only change freshness cannot see is the code.
        force = bool(attributes.get("force") or attributes.get("recalculate"))

        plan: Dict[str, Dict[str, Any]] = {}
        for target in targets:
            previous_by_key = {}
            for key in ordered:
                # A step with nothing to do here is not planned. What it takes to have
                # something to do is declared beside its result and asked of the model.
                condition = CalculatedDataStructure.condition_for(key)
                if condition and not self._manipulator.inspect(target, **{condition: None}):
                    logger.debug("Not planning '%s' for '%s': %s is not so", key, target.code, condition)
                    continue
                name = f"{target.code}/{key}"
                # Named by handler, filed under the schema's key: the same string for
                # every calculation but one.
                store_key = CalculatedDataStructure.store_key_for(key)
                step = {"operation": "calculate", "obj": target, "method": key,
                        "store_key": store_key}
                step.update(passed)
                # None means "cannot be told", and is left alone: calling it stale makes
                # opening an old project a recomputation of everything in it.
                step["recalculate"] = force or freshness.is_stale(target, store_key) is True
                waits = [previous_by_key[prerequisite]
                         for prerequisite in self._manipulator.requirements_of("calculate", key)
                         if prerequisite in previous_by_key]
                if waits:
                    step["after"] = waits
                plan[name] = step
                previous_by_key[key] = name
        return plan

    def _inspect_catalogue(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            - Discovered, not listed: adding a calculation means writing `_calculate_x` and
              a schema entry, and no interface is told about it.
            - All this adds is what the framework cannot know -- how a few words are spelled.
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
                # A result recording a `target_code` is about something being tracked,
                # so the request says what. Read from the columns rather than listed.
                "needs_target": "target_code" in (schema.get("columns") or []),
                # What it takes beyond the model, read from what its result records, so
                # no dialog has to know which calculation takes a threshold.
                "parameters": list(CalculatedDataStructure.parameters_of(key)),
            }
            if observation is not None:
                # By the key the result is filed under, not by the handler's name: for
                # one calculation the two differ.
                entry["available"] = CalculatedDataStructure.store_key_for(key) in held
            entries.append(entry)
        return entries

    def _inspect_order(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """Return calculations in an order that satisfies their prerequisites.

        Args:
            obj: Ignored.
            attributes: `keys`, the calculations asked for in any order.

        Returns:
            List[str]: The same keys, each after everything it needs.

        Notes:
            - Which calculation needs which is the model's own code to state.
        """
        return self._manipulator.order_handlers("calculate", attributes.get("keys") or [])

    def _inspect_history(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return what has been asked of this orchestrator in this session.

        Args:
            obj: Ignored.
            attributes: `about`, an object name to narrow it to.

        Returns:
            List[Dict[str, Any]]: One row per request as it was recorded -- `operation`, the
                `object` it named, the `method`, its `attributes`, whether it worked, and how long
                it took -- with three things added for showing it: `where` the object lives,
                whether the request only `reads`, and what it `call`ed.

        Notes:
            - Plain data: the journal records what was asked, not the request as it ran, so
              recording a session keeps nothing it touched alive.
            - Reads are here too; `reads` is what lets a session be cut down afterwards.
        """
        rows = self._manipulator.history(attributes.get("about"))
        # `where` beside `object`: a name is unique inside a container, so two
        # observations holding `1228+126` need the path to tell their rows apart.
        for row in rows:
            path = row.get("path") or ([row["object"]] if row.get("object") else [])
            row["where"] = " / ".join(str(segment) for segment in path)
            row["reads"] = self._manipulator.reads(row.get("operation"))
            row["call"] = self._called(row)
        return rows

    def _called(self, row: Dict[str, Any]) -> str:
        """Return what a request called, as a person reads it.

        Notes:
            - `method` is the operation's handler, not the model's.
            - The handler where there is one, the model's methods where there are, and
              nothing for another operation's default.
        """
        handler = self._asked(row)
        if handler:
            return str(handler)
        if row.get("operation") not in self._manipulator.CALLING:
            return ""
        # `name` addresses one member of a collection, and is not a method.
        return ", ".join(key for key in (row.get("attributes") or {}) if key != "name")

    @staticmethod
    def _asked(step: Dict[str, Any]) -> Any:
        """Return the handler a step named: its own `method`, or one among its attributes."""
        return step.get("method") or (step.get("attributes") or {}).get("method")

    def _read_session(self, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the steps of a session, from a file or from memory.

        Raises:
            ValueError: If neither was given, or the file is not a session.
        """
        steps = attributes.get("steps")
        path = attributes.get("path")
        if steps is None and not path:
            raise ValueError("No 'path' or 'steps' given; there is no session to work on")
        if steps is None:
            document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            if not isinstance(document, dict) or "steps" not in document:
                raise ValueError(f"'{path}' is not a session: it has no 'steps'")
            steps = document["steps"]
        if not isinstance(steps, list):
            raise ValueError("A session's 'steps' must be a list")
        return self._as_asked_now(steps)

    def _as_asked_now(self, steps: List[Any]) -> List[Any]:
        """Return a session's steps with each question asked of the operation that answers it now.

        Notes:
            - A step naming a method its operation no longer has, and `inspect` does, is read
              as `inspect`. Derived from what the operations offer, so nothing lists it.
        """
        described = self._manipulator.describe_operations()
        questions = described.get("inspect", {})
        moved = []
        for step in steps:
            asked = self._asked(step) if isinstance(step, dict) else None
            if (asked in questions and step.get("operation") in described
                    and asked not in described[step["operation"]]):
                step = {**step, "operation": "inspect"}
            moved.append(step)
        return moved

    def _resolve(self, step: Dict[str, Any]) -> Any:
        """Return the object a step names, by path first and by name second.

        Notes:
            - The path, because a name is unique inside a container rather than across a
              model. The name is the fallback for a session written by hand.
        """
        found = self._manipulator.locate(step["path"]) if step.get("path") else None
        named = step.get("object")
        if found is None and isinstance(named, str):
            found = self._manipulator.find(named)
        return found

    def _inspect_check(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Read a session and report what is wrong with it, without running anything.

        Args:
            obj: Ignored; the project is whatever this orchestrator manages.
            attributes: `path` or `steps`, as for `replay`.

        Returns:
            Dict[str, Any]: `{"steps": int, "problems": [...], "warnings": [...]}`. A problem
                stops a replay; a warning does not.

        Notes:
            - Every step is checked before any runs: a session that half ran is worse than
              one that refused. A read is not checked, because it is not run.
            - What it checks against is asked of the orchestrator.
            - An attribute no handler reads is a warning: `accepts` is a lower bound.
        """
        steps = self._read_session(attributes)
        described = self._manipulator.describe_operations()
        problems: List[str] = []
        warnings: List[str] = []

        for position, step in enumerate(steps, start=1):
            where = f"step {position}"
            if not isinstance(step, dict):
                problems.append(f"{where}: not a request")
                continue

            operation = step.get("operation")
            if operation not in described:
                problems.append(
                    f"{where}: no operation called '{operation}' "
                    f"(there is {', '.join(sorted(described))})")
                continue
            if self._manipulator.reads(operation):
                continue

            handlers = described[operation]
            method = self._asked(step)
            if method and method not in handlers:
                problems.append(f"{where}: '{operation}' has no '{method}'")
                continue

            named = step.get("object")
            if named and self._resolve(step) is None:
                looked = " / ".join(step["path"]) if step.get("path") else named
                problems.append(f"{where}: nothing here at '{looked}'")

            if method:
                accepts = set(handlers[method].get("accepts") or ())
                unread = [name for name in (step.get("attributes") or {})
                          if name not in accepts and name != "method"]
                if unread and accepts:
                    warnings.append(
                        f"{where}: '{method}' does not read {', '.join(sorted(unread))}")

        return {"steps": len(steps), "problems": problems, "warnings": warnings}

    def _inspect_targets(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
        """Return what could be pointed at in a set of observations.

        Args:
            obj: An observation, a project, or a list of them; `targets` overrides it.
            attributes: `targets`, the observations to look in.

        Returns:
            List[str]: The codes of the space telescopes there, sorted, without repeats.

        Notes:
            - Asked by the calculation dialog before running anything that needs a target,
              so the dialog does not walk the model itself.
        """
        from pastrocore.base.telescopes import SpaceTelescope

        codes = []
        for observation in (attributes.get("targets") or self._targets(obj)):
            for telescope in observation.get_telescopes().get_items():
                if isinstance(telescope, SpaceTelescope) and telescope.get_code() not in codes:
                    codes.append(telescope.get_code())
        return sorted(codes)

    @staticmethod
    def _parts_by_type() -> Dict[str, str]:
        """Return which part of an observation each type is held in, read from the model.

        Returns:
            Dict[str, str]: Type name to part name -- `{"Telescopes": "telescopes", ...}`.

        Notes:
            - Derived from `Observation`'s annotations, which are the same names a result
              declares in `depends_on`.
        """
        # Containers only: `calculated_data` is annotated `Any`, which answers True to
        # `isinstance(hint, type)`.
        parts = {}
        for field, hint in Observation._fields.items():
            if (not field.startswith("_") and isinstance(hint, type)
                    and issubclass(hint, BaseContainer)):
                parts[hint.__name__] = field
        return parts

    def _inspect_affected(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Return the results that editing something of a given type would make wrong.

        Args:
            obj: An observation or a project, to say which of the affected results actually
                exist. Optional -- with none, the answer is about the calculations rather than
                about any stored result.
            attributes: `type`, the name of what is about to be edited (`"Telescope"`,
                `"Scan"`, ...), or `subject`, an object to take that name from.

        Returns:
            Dict[str, Any]: `{"type": str, "parts": [...], "calculations": [...],
                "stored": [...]}` -- the parts of an observation a change reaches, every
                calculation that reads one of them, and which of those have actually been
                calculated and would therefore go stale.

        Raises:
            ValueError: If neither `type` nor `subject` was given, or the type is not in the
                model.

        Notes:
            - `stale` answers afterwards; this answers before a change is made.
            - Both halves are derived: MSB's model graph says what reaching a type reaches --
              a `Telescope` is named by `Scan` too -- and each schema says what it reads.
        """
        subject = attributes.get("subject")
        name = attributes.get("type") or (type(subject).__name__ if subject is not None else None)
        if not name:
            raise ValueError("No 'type' or 'subject' given; there is nothing to ask about")

        parts_by_type = self._parts_by_type()
        known = set(parts_by_type) | {"Observation"}
        reached = set(self._manipulator.dependents_of(name)) | {name}
        if not reached & known and name not in known:
            raise ValueError(
                f"Nothing in the model is called '{name}'; there is "
                f"{', '.join(sorted(known))} and what they hold")

        # A change to a part itself, or to anything the part holds, reaches that part.
        parts = sorted({part for held, part in parts_by_type.items() if held in reached})

        affected = sorted(
            key for key in CalculatedDataStructure.SCHEMAS
            if set(CalculatedDataStructure.get_dependencies(key)) & set(parts))

        stored = []
        for observation in self._targets(obj) if obj is not None else []:
            results = observation.calculated_data
            held = set(results.keys()) if hasattr(results, "keys") else set()
            for key in affected:
                if key in held:
                    stored.append(f"{observation.code}/{key}")

        logger.info("A change to '%s' reaches %s part(s) and %s calculation(s)",
                    name, len(parts), len(affected))
        return {"type": name, "parts": parts, "calculations": affected,
                "stored": sorted(stored)}

    def _inspect_stale(self, obj: Any, attributes: Dict[str, Any]) -> List[str]:
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

    def _inspect_recording(self, obj: Any, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Report what a recording keeps of the signal, by bits per sample (E1).

        Args:
            obj: Ignored.
            attributes: Ignored.

        Returns:
            List[Dict[str, Any]]: `{"bits": int, "efficiency": float}`, fewest bits first.

        Notes:
            - Asked rather than listed: how much of the correlation quantising leaves is
              physics -- two-level keeps 2/pi of it -- and not a combo box's to know.
        """
        from pastrocore.super.schedule_calculator import ScheduleCalculator

        return [{"bits": bits, "efficiency": float(efficiency)}
                for bits, efficiency in sorted(ScheduleCalculator.RECORDING_EFFICIENCY.items())]


class ScheduleRunner(RunQuestions, Super):
    """Running calculations, and the other requests that change what a project holds.

    Args:
        manipulator (Manipulator): The orchestrator every operation is reached through.
    """

    OPERATION = "compute"

    def __init__(self, manipulator: 'Manipulator'):
        super().__init__(manipulator)
        logger.debug("Initialized ScheduleRunner")

    def _compute_run(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Run the plan `_export_plan` builds, and report what each step did.

        Args:
            obj: As for `_export_plan`.
            attributes: As for `_export_plan`, plus `concurrent` to let independent steps of a
                stage run together, `progress`, called with a percentage and a message, and
                `cancelled`, called to ask whether to stop.

        Returns:
            Dict[str, Any]: `{"ran": [...], "failed": [...], "cancelled": bool,
                "timings": {step: seconds}, "report": [...], "summary": {...}}` -- step names,
                in plan order. The summary's `seconds` is the clock and `work` is the sum of
                the steps; with a concurrent stage the second is larger.

        Notes:
            - Here rather than in a dialog, so every caller sends one request.
            - Progress, cancellation and timing ride on an interceptor: a cancellation is a
              refused request, which skips the branch below it.
            - Timing belongs here, and progress is reported when a step finishes.
        """
        plan = self._inspect_plan(obj, attributes)
        report = attributes.get("progress") or (lambda percent, message: None)
        cancelled = attributes.get("cancelled") or (lambda: False)

        total = len(plan)
        seen = {"done": 0, "stopped": False}
        labels = {name: name.split("/", 1)[-1] for name in plan}
        # A step is named by its handler and filed under the schema's key; the request
        # carries the key, so this maps back to the step the plan named.
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
        began = time.perf_counter()
        try:
            outcome = self._manipulator.pipeline(
                plan, raise_on_error=False, concurrent=bool(attributes.get("concurrent")))
        finally:
            elapsed = time.perf_counter() - began
            self._manipulator.remove_interceptor(watch)

        # In plan order rather than in the order they finished, which with a concurrent stage
        # is neither stable nor meaningful.
        timings = {name: measured[name] for name in plan if name in measured}
        ran = [name for name in outcome if name not in outcome.failed]
        slowest = max(timings, key=timings.get) if timings else None

        # One row per step, in plan order. Assembled here rather than by whatever
        # displays it, so no caller joins three lists to find out what happened.
        spelled = {entry["key"]: entry["label"]
                   for entry in self._inspect_catalogue(obj, {})}
        rows = []
        for name in plan:
            if name not in measured and name not in outcome.failed:
                continue            # never reached: the run stopped above it
            key = name.split("/", 1)[-1]
            failed = name in outcome.failed
            rows.append({"step": name,
                         "observation": name.split("/", 1)[0],
                         "label": spelled.get(key, labels.get(name, key)),
                         "seconds": measured.get(name, 0.0),
                         "outcome": "failed" if failed else "ok",
                         # Why, not only that: "failed" alone leaves the reason in the
                         # log, where nobody looks.
                         "error": self._why(outcome, name) if failed else ""})

        return {"ran": ran,
                "failed": list(outcome.failed),
                "cancelled": seen["stopped"],
                "timings": timings,
                "report": rows,
                # Summarised here: `seconds` is the clock and `work` the sum of the steps,
                # which with a concurrent stage counts the same seconds twice.
                "summary": {"steps": len(ran), "failed": len(outcome.failed),
                            "seconds": elapsed,
                            "work": sum(timings.values()),
                            "slowest": slowest.split("/", 1)[-1] if slowest else None,
                            "slowest_seconds": timings[slowest] if slowest else 0.0}}

    @staticmethod
    def _why(outcome: Any, name: str) -> str:
        """Return what a step said when it refused, or an empty string when it said nothing."""
        try:
            response = outcome[name]
        except Exception:                               # noqa: BLE001 - a report, not a request
            return ""
        if isinstance(response, dict):
            return str(response.get("error") or "")
        return str(getattr(response, "error", "") or "")

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
            - A step names its object, so a session recorded against one project runs
              against another.
            - Unresolved steps are reported rather than skipped in silence.
            - Reads are not run, and are counted in `reads`: a question reproduces nothing.
        """
        steps = self._read_session(attributes)

        # Checked whole before anything runs: one bad step among good ones must run none
        # of them, because a session that half ran looks like it worked.
        report = self._inspect_check(obj, {"steps": steps})
        if report["problems"]:
            logger.warning("Refusing a session with %s problem(s)", len(report["problems"]))
            return {"ran": [], "failed": [], "unresolved": [], "reads": 0,
                    "problems": report["problems"], "warnings": report["warnings"]}

        plan: Dict[str, Dict[str, Any]] = {}
        unresolved: List[str] = []
        reads = 0
        previous = None
        for position, step in enumerate(steps, start=1):
            if attributes.get("skip_failures", True) and step.get("status") is False:
                continue
            if self._manipulator.reads(step.get("operation")):
                reads += 1
                continue
            named = step.get("object")
            found = self._resolve(step)
            name = f"{step.get('operation')}_{position}"
            if named and found is None:
                where = " / ".join(step["path"]) if step.get("path") else named
                unresolved.append(f"{name}: nothing here at '{where}'")
                continue
            # A journal records a callable as `<function>`, so these are dropped rather
            # than handed back as strings: absent means report to nobody, stop for nobody.
            asked = {key: value
                     for key, value in (step.get("attributes") or {}).items()
                     if not (isinstance(value, str) and value.startswith("<")
                             and value.endswith(">"))}
            entry = {"operation": step.get("operation"), "obj": found,
                     "attributes": asked}
            if step.get("method"):
                entry["method"] = step["method"]
            if previous:
                entry["after"] = [previous]
            plan[name] = entry
            previous = name

        if not plan:
            logger.warning("Nothing in this session could be replayed here")
            return {"ran": [], "failed": [], "unresolved": unresolved, "reads": reads,
                    "problems": [], "warnings": report["warnings"]}

        outcome = self._manipulator.pipeline(plan, raise_on_error=False)
        return {"ran": [name for name in outcome if name not in outcome.failed],
                "failed": list(outcome.failed),
                "unresolved": unresolved, "reads": reads,
                "problems": [], "warnings": report["warnings"]}

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

    def _compute_release(self, obj: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Let go of a project, so whatever holds it can replace it.

        Args:
            obj (ScheduleProject): The project to release.
            attributes: Ignored.

        Returns:
            Dict[str, Any]: `{"released": int}` -- how many observations were let go.

        Notes:
            - A request, so a command line opening one project after another asks the same
              way without importing anything of the model.
        """
        released = obj.release()
        return {"released": released}
