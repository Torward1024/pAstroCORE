"""Conventions that are easier to keep than to restore.

Each of these was fixed once across the whole codebase. Without a test, the next hundred lines
written would reintroduce it a few at a time, and nobody would notice until it had to be done
again.
"""
import ast
import pathlib
import re

import pytest

from pastrocore.super.schedule_calculator import ScheduleCalculator

ROOT = pathlib.Path(__file__).parent.parent
LOG_METHODS = {"debug", "info", "warning", "error", "critical", "exception"}


def source_files():
    """Hand-written modules. Generated Qt output is not ours to hold to a style."""
    files = [p for p in (ROOT / "pastrocore").rglob("*.py")
             if "__pycache__" not in p.parts and not p.name.startswith(("ui_", "rc_"))]
    files.append(ROOT / "run.py")
    return sorted(p for p in files if p.exists())


def eager_log_calls(path):
    """Find `logger.x(f"...")`, which formats its message whether or not anything reads it."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in LOG_METHODS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "logger"
                and node.args
                and isinstance(node.args[0], ast.JoinedStr)):
            found.append(node.lineno)
    return found


# Fifteen calls carry a format spec or a conversion -- `{x:.2f}`, `{x!r}` -- where `%s` would
# render something different. They are left alone deliberately. The number may only go down,
# and it went down by one when the calculator's per-call timing line became lazy.
ALLOWED_EAGER = 15


def test_logging_is_lazy():
    """`logger.debug("got %s", n)` costs 225 ns with debug disabled; the f-string form 1 277.

    The saving is small in absolute terms and this is mostly a convention, kept because it is
    the one MSB documents and because the cost is unbounded in a loop.
    """
    offenders = {path.relative_to(ROOT).as_posix(): lines
                 for path in source_files() if (lines := eager_log_calls(path))}
    total = sum(len(lines) for lines in offenders.values())
    assert total <= ALLOWED_EAGER, (
        f"{total} eager f-string log calls, {ALLOWED_EAGER} allowed:\n  "
        + "\n  ".join(f"{name}: {lines}" for name, lines in offenders.items()))


def test_the_allowance_is_not_larger_than_it_needs_to_be():
    """Lower the number when one is repaired, so the debt cannot quietly be kept."""
    total = sum(len(eager_log_calls(path)) for path in source_files())
    assert total == ALLOWED_EAGER, (
        f"only {total} eager calls remain; lower ALLOWED_EAGER to match")


@pytest.mark.parametrize("path", source_files(), ids=lambda p: p.name)
def test_a_module_parses(path):
    """Cheap, and it caught a rewrite that produced unparseable output."""
    ast.parse(path.read_text(encoding="utf-8"))


def redefined_methods(path):
    """Find a class defining the same method twice, where the second silently wins."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.ClassDef):
            continue
        seen = {}
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = {d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", None)
                          for d in item.decorator_list}
            if decorators & {"setter", "getter", "deleter", "overload"}:
                continue        # a property's second half, or a typing stub -- both deliberate
            if item.name in seen:
                found.append(f"{node.name}.{item.name} at line {item.lineno}, "
                             f"first defined at {seen[item.name]}")
            seen[item.name] = item.lineno
    return found


def test_no_class_defines_a_method_twice():
    """The second definition wins and the first becomes unreachable, with nothing said.

    It found a real one: `CalculationDialog` defined `calculation_finished` twice, and the
    winner took one argument where the signal carries `(results, errors)`. PySide drops the
    arguments a slot does not accept, so a run with failed steps was reported to the user as
    "All calculations completed successfully" -- the same shape of silence as the image export
    that reported "0 files".
    """
    offenders = {path.relative_to(ROOT).as_posix(): duplicates
                 for path in source_files() if (duplicates := redefined_methods(path))}
    assert not offenders, (
        "a method is defined twice, and the first is dead code:\n  "
        + "\n  ".join(f"{name}: {'; '.join(duplicates)}" for name, duplicates in offenders.items()))


def silent_handlers(path):
    """Find `except ...: pass` -- a failure that leaves no trace at all."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.ExceptHandler)
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)):
            kind = node.type
            broad = kind is None or (isinstance(kind, ast.Name) and kind.id == "Exception")
            if broad:
                found.append(node.lineno)
    return found


def test_no_failure_is_swallowed_without_a_trace():
    """`except Exception: pass` is the one shape that cannot be diagnosed after the fact.

    A narrow catch of something Qt genuinely raises -- `except RuntimeError` around a
    `disconnect` -- is fine and is not what this looks for.
    """
    offenders = {path.relative_to(ROOT).as_posix(): lines
                 for path in source_files() if (lines := silent_handlers(path))}
    assert not offenders, (
        "a broad handler swallows silently:\n  "
        + "\n  ".join(f"{name}: {lines}" for name, lines in offenders.items()))


def test_a_swallowed_calculation_failure_keeps_its_traceback():
    """The calculation layer catches broadly and returns an empty frame, so a failure is
    indistinguishable from no data. The traceback is then the only way to tell them apart."""
    offenders = []
    for path in source_files():
        if "super" not in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.ExceptHandler)
                    and isinstance(node.type, ast.Name) and node.type.id == "Exception"):
                continue
            if any(isinstance(n, ast.Raise) for n in ast.walk(node)):
                continue
            logs = [call for call in ast.walk(node)
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr in ("error", "warning", "exception")
                    and isinstance(call.func.value, ast.Name) and call.func.value.id == "logger"]
            if logs and not any(k.arg == "exc_info" for call in logs for k in call.keywords):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    assert not offenders, (
        "a calculation failure is logged without its traceback:\n  " + "\n  ".join(offenders))


# --- constraints on annotations (M2) ------------------------------------------------------

def test_a_constraint_holds_at_every_entry_point():
    """A hand-written check in `__init__` guards construction and nothing else.

    The ones replaced here ran *after* `super().__init__()`, so the object was already built
    with the bad value, and `set` bypassed them entirely. On the annotation, the rule is
    enforced before the value is stored and at every way in.
    """
    from msb_arch import errors
    from pastrocore.base.frequencies import IF

    valid = IF(name="IF1", frequency=8400.0, bandwidth=16.0)

    with pytest.raises(errors.ConstraintError):
        IF(name="bad", frequency=-1.0)
    with pytest.raises(errors.ConstraintError):
        valid.set({"frequency": -5.0})
    with pytest.raises(errors.ConstraintError):
        IF.from_dict({**valid.to_dict(), "bandwidth": -3.0})

    assert valid.frequency == 8400.0, "a rejected assignment must leave the object alone"


def test_a_telescope_diameter_is_constrained():
    from msb_arch import errors
    from pastrocore.base.telescope import Telescope

    with pytest.raises(errors.ConstraintError):
        Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0, diameter=-10.0)


# --- the forms and their generated modules --------------------------------------------------

def test_every_generated_form_matches_its_ui_source():
    """An interface change made in the generated `.py` alone is lost the next time anyone
    opens the form in Designer. This fails the build instead of waiting for that.

    It found a real one when it was written: `ui_dialog_edit_if.py` carried styling for two
    spin boxes that `dialog_editor_if.ui` did not, and the `.ui` carried styling for the dialog
    that the `.py` did not. Both had been edited, neither knew about the other.
    """
    import subprocess
    import sys

    tool = pathlib.Path(__file__).resolve().parent.parent / "tools" / "regenerate_ui.py"
    result = subprocess.run([sys.executable, str(tool), "--check"],
                            capture_output=True, text=True, encoding="utf-8")

    if result.returncode != 0 and "cannot find pyside6-uic" in (result.stdout + result.stderr):
        pytest.skip("pyside6-uic is not available here")

    assert result.returncode == 0, (
        "a generated form no longer matches its .ui source:\n\n"
        f"{result.stdout}\n{result.stderr}\n"
        "Make the change in the .ui with Designer, then run: python tools/regenerate_ui.py")


def test_the_generated_forms_import_the_resource_by_package():
    """`uic` emits a bare `import icons_rc`, which resolves only if `pastrocore/gui` is on
    `sys.path` -- it is not. Regenerating looks like it worked and fails on the first icon."""
    generated = pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
    offenders = [module.name for module in generated.glob("ui_*.py")
                 if re.search(r"^import icons_rc\s*$", module.read_text(encoding="utf-8"),
                              re.MULTILINE)]
    assert not offenders, (
        f"{offenders} import the resource by a bare name. "
        f"Regenerate with tools/regenerate_ui.py, which rewrites it.")


def test_the_preferences_control_lives_in_the_form():
    """The memory-share control was built by hand in 0.5.0 because editing generated code
    would have lost it. The form carries it now, which is what the rule is for."""
    root = pathlib.Path(__file__).resolve().parent.parent
    form = (root / "pastrocore" / "gui_pyside" / "dialog_preferences.ui").read_text(encoding="utf-8")
    dialog = (root / "pastrocore" / "gui" / "p_dialog_preferences.py").read_text(encoding="utf-8")

    assert 'name="resultsMemorySpin"' in form, "the control belongs in the .ui"
    assert "QSpinBox(" not in dialog, "the dialog must not build widgets the form already has"
    assert "self.ui.resultsMemorySpin" in dialog, "and it must reach it through the form"


# --- the interface holds interface code -----------------------------------------------------

#: Hand-written GUI modules that import a model library. The list may shrink and must never
#: grow, and every entry carries the reason it is there. Twelve began on it; the two that
#: remain are decided rather than owed -- see the comment on each.
#:
#: Removing an entry means moving its logic, not moving its import.
MODULES_STILL_REACHING_FOR_THE_MODEL = {
    # Both turn what a user typed in a Qt widget into the model's own type -- a date from a
    # QDateTimeEdit into an astropy Time. That is the dialog's job and not a Super's: an
    # operation taking a Qt datetime would be worse than the import. Decided, not owed.
    "p_dialog_edit_scan.py",
    "p_dialog_edit_space_telescope.py",
}

HEAVY = re.compile(r"^\s*(?:import|from)\s+(polars|astropy|numpy|scipy)\b", re.M)


def _gui_modules():
    """Hand-written interface modules, excluding what Qt Designer generates."""
    gui = pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
    return [module for module in sorted(gui.glob("*.py"))
            if not module.name.startswith("ui_") and module.name != "rc_icons.py"]


def test_no_new_interface_module_reaches_for_the_model():
    """A rule nothing checks is a preference, which is what the regenerate-from-`.ui` rule was
    until a test enforced it -- and it had drifted in exactly one file meanwhile.

    A module importing polars or astropy is doing work a command-line version would have to
    write again and a server could not reach at all.
    """
    offenders = {module.name for module in _gui_modules()
                 if HEAVY.search(module.read_text(encoding="utf-8"))}

    new = offenders - MODULES_STILL_REACHING_FOR_THE_MODEL
    assert not new, (
        f"{sorted(new)} now import a model library. That logic belongs in a Super, where a CLI "
        f"and a server can reach it -- see stage 9 in docs/ROADMAP.md.")


def test_the_debt_list_shrinks_and_is_not_padded():
    """A stale entry would make the list look like progress that has not happened, and would
    quietly permit a module to reach for the model again."""
    offenders = {module.name for module in _gui_modules()
                 if HEAVY.search(module.read_text(encoding="utf-8"))}

    settled = MODULES_STILL_REACHING_FOR_THE_MODEL - offenders
    assert not settled, (
        f"{sorted(settled)} no longer import a model library -- remove them from "
        f"MODULES_STILL_REACHING_FOR_THE_MODEL so the list keeps meaning something.")


def test_the_exporter_dialog_is_off_the_list():
    """The first one moved, and the proof that the list can shrink at all."""
    source = (pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
              / "p_dialog_export_calculated_data.py").read_text(encoding="utf-8")
    assert not HEAVY.search(source), (
        "the export dialog reaches for the model again; its logic is in ScheduleData")


# --- one catalogue -------------------------------------------------------------------------

#: Spellings of calculations that must not appear in a dialog. A dialog asks the manipulator
#: what exists; a dialog that spells a calculation is a dialog that has to be edited when one
#: is added, which is the whole thing A5 removed.
CALCULATION_SPELLINGS = re.compile(
    r'"(?:UV Coverage|Mollweide Tracks|Baseline Projections|Time on Source|Sun Angles|'
    r'Azimuth/Elevation|Beam Pattern|Parallactic Angle|uv_coverage|mollweide_tracks|'
    r'baseline_projections|time_on_source|sun_angles|az_el|beam_pattern|parallactic_angle)"')

#: Where a spelling is legitimate, with why.
SPELLING_IS_ALLOWED = {
    # Each visualization tab is written for one result and says which, once, when it asks for
    # its own data. That is the tab naming itself, not a catalogue kept by hand.
    "p_tab_vis_uv_coverage.py", "p_tab_vis_az_el.py", "p_tab_vis_sun_angles.py",
    "p_tab_vis_time_on_source.py", "p_tab_vis_baseline_projections.py",
    "p_tab_vis_parallactic.py", "p_tab_vis_beam_pattern.py", "p_tab_vis_mollweide.py",
    # Maps a result to the widget that draws it. That is a fact about this interface and the
    # one thing the model cannot answer -- and it is keyed by the result rather than by a
    # label, so rewording a label cannot silently unbind a tab.
    "p_dialog_visualize.py",
}


def test_no_dialog_keeps_its_own_list_of_calculations():
    """Adding a calculation should touch the calculator and the schema, and nothing else.

    It used to touch three dialogs, which held the same knowledge nine times in four shapes --
    including a table of which calculation needs which, that being knowledge about the model
    living in a widget.
    """
    gui = pathlib.Path(__file__).resolve().parent.parent / "pastrocore" / "gui"
    offenders = {}
    for module in sorted(gui.glob("p_dialog_*.py")):
        if module.name in SPELLING_IS_ALLOWED:
            continue
        found = CALCULATION_SPELLINGS.findall(module.read_text(encoding="utf-8"))
        if found:
            offenders[module.name] = sorted(set(found))

    assert not offenders, (
        f"{offenders} spell calculations by hand. Ask the manipulator instead: "
        f"export(method='catalogue') -- see A5 in docs/ROADMAP.md.")


class CalculatorWithOneMore(ScheduleCalculator):
    """A calculator with a calculation the interface has never heard of.

    Defined in a file rather than attached at runtime, because the derivation reads source: a
    method glued onto a class after import is invisible to it, which is a real limit of the
    approach and not a thing to work around in a test.
    """

    def _calculate_invented_thing(self, obj, attributes):
        return self._calculate_time_arrays(obj, attributes)


def test_adding_a_calculation_needs_no_change_to_any_interface(project):
    """The claim A5 makes, tested rather than asserted.

    A calculation registered on the calculator appears in the catalogue -- which is what every
    dialog now reads -- with its label, its prerequisites and its place in the order, and
    without a line changing anywhere in `pastrocore/gui`.
    """
    from pastrocore.super.schedule_manipulator import ScheduleManipulator

    manipulator = ScheduleManipulator(project)
    # Replacing the registered calculator, which is what an application does when it extends
    # one; registering a second under the same name is refused, and rightly.
    manipulator._operations["calculate"] = CalculatorWithOneMore(manipulator)

    response = manipulator.compute(obj=project, method="catalogue", raise_on_error=False)
    catalogue = (response["result"] if isinstance(response, dict) else response) or []

    entry = next((e for e in catalogue if e["key"] == "invented_thing"), None)
    assert entry is not None, "a new handler must appear in the catalogue on its own"
    assert entry["label"] == "Invented Thing", "and be labelled without anybody naming it"
    assert entry["offer"] is True, "and be offered, since nothing said it was a step"
    assert entry["requires"] == ["time_arrays"], "and bring the edge it wrote in its own body"

    ordered = manipulator.compute(obj=project, method="order",
                                 keys=["invented_thing", "time_arrays"], raise_on_error=False)
    ordered = ordered["result"] if isinstance(ordered, dict) else ordered
    assert ordered == ["time_arrays", "invented_thing"], "and take its place in the order"


def test_a_handler_added_after_import_is_invisible():
    """A limit of reading source rather than the live class, asserted so it is known rather
    than discovered. Handlers are written in files; this only bites a caller who was expecting
    otherwise."""
    from pastrocore.super.schedule_calculator import ScheduleCalculator as Calculator

    Calculator._calculate_glued_on = lambda self, obj, attributes: None
    try:
        from msb_arch.catalogue import derive

        assert "glued_on" not in derive(Calculator(None), "calculate")
    finally:
        del Calculator._calculate_glued_on


# --- one way in ------------------------------------------------------------------------------

#: Methods that belong to the model. A window calling one of these is reaching past the
#: orchestrator, which is the thing a command line and a server cannot do -- so every one of
#: them is a line those two would have to write again.
MODEL_METHODS = re.compile(
    r"\.(get_telescopes|get_sources|get_scans|get_frequencies|get_observation|"
    r"get_observation_by_code|observations|create_telescope|create_source|create_scan|"
    r"create_if|create_item|add_item|set_item|clear_calculated_data|"
    r"set_calculated_data_by_key|stale_results|unsaved_results|discard_scratch_if_empty|"
    r"release|to_dict|from_dict)\(")

#: Where reaching the model is decided rather than owed, with the reason.
REACHING_IS_ALLOWED = {
    # Reads one result to draw it. Going through the orchestrator for the frame it is about to
    # filter would mean reading it whole first, which is the cost the lazy view exists to avoid.
    "p_dialog_visualize.py",
}


def test_the_interface_reaches_the_model_only_through_the_orchestrator():
    """One entry point, checked rather than believed.

    Six were found when this was written: the calculation dialog walked the telescopes to find
    a spacecraft and cleared results itself, two visualization tabs read the frequencies, and
    the window asked an observation what was stale, saved the project by calling it, and wrote
    an observation to a file with `json.dump(observation.to_dict())` -- which MSB's own `save`
    does atomically.
    """
    modules = [module for module in sorted((ROOT / "pastrocore" / "gui").glob("*.py"))
               if not module.name.startswith(("ui_", "rc_"))]
    modules.append(ROOT / "pastrocore" / "app.py")

    offenders = {}
    for module in modules:
        if module.name in REACHING_IS_ALLOWED:
            continue
        found = []
        for number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "manipulator." in stripped:
                continue
            for match in MODEL_METHODS.finditer(line):
                found.append(f"{match.group(1)} at line {number}")
        if found:
            offenders[module.name] = found

    assert not offenders, (
        "the interface reaches the model directly:\n  "
        + "\n  ".join(f"{name}: {'; '.join(calls)}" for name, calls in offenders.items())
        + "\nSend a request instead -- that is what a command line and a server will send.")


def test_a_coordinate_cannot_be_set_out_of_range():
    """`Source._validate_coordinates` ran in `__init__` and nowhere else, so the constructor
    refused ninety-nine hours of right ascension and `set` accepted it -- and so did
    `from_dict`, which is how a saved project carries one back.

    The same shape as the checks replaced when constraints first arrived here: a hand-written
    check guards construction, and an annotation guards every way in.
    """
    from msb_arch import errors
    from pastrocore.base.sources import Source

    source = Source(name="X", ra_h=1.0, de_d=10.0)

    with pytest.raises(errors.ConstraintError):
        Source(name="Y", ra_h=99.0)
    with pytest.raises(errors.ConstraintError):
        source.set({"ra_h": 99.0})
    with pytest.raises(errors.ConstraintError):
        source.set({"de_d": -91.0})
    with pytest.raises(errors.ConstraintError):
        Source.from_dict({**source.to_dict(), "de_s": 60.5})

    assert source.ra_h == 1.0, "a rejected assignment must leave the object alone"


def test_an_observation_type_is_one_of_two():
    """The other hand-written check of the same shape."""
    from msb_arch import errors
    from pastrocore.base.observation import Observation

    observation = Observation(name="obs", code="OBS")
    with pytest.raises(errors.ConstraintError):
        observation.set({"observation_type": "SOMETHING_ELSE"})


def test_a_scan_cannot_be_given_a_negative_duration():
    """`set_duration` checked it; `set` went straight past. A scan of minus five seconds makes
    every calculation that samples it produce nothing, and says nothing about why."""
    from astropy.time import Time
    from msb_arch import errors
    from pastrocore.base.scans import Scan

    scan = Scan(name="s", start=Time("2026-01-01T00:00:00"), duration=60.0)
    with pytest.raises(errors.ConstraintError):
        scan.set({"duration": -5.0})
    assert scan.duration == 60.0


def test_a_pointing_range_cannot_be_set_backwards():
    """Checked in `__init__` and nowhere else, so a range whose minimum is above its maximum
    could be set later -- and a station that can point nowhere is not visible as an error, only
    as a result with nothing in it."""
    from msb_arch import errors
    from pastrocore.base.telescope import Telescope

    telescope = Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0, diameter=100.0)

    with pytest.raises(errors.ConstraintError):
        telescope.set({"elevation_range": (90.0, 10.0)})
    with pytest.raises(errors.ConstraintError):
        telescope.set({"azimuth_range": (360.0, 0.0)})

    assert telescope.elevation_range == (15.0, 90.0)


def test_no_response_is_unwrapped_by_hand():
    """MSB 1.8.0 gave a request's answer one type, with `.value` doing the unwrapping. Before
    that, every caller wanting the whole response wrote this:

        response["result"] if isinstance(response, dict) and "status" in response else response

    Fifty-three of those were here, and the line is **wrong** for a request naming one method:
    the answer holds `{"get_code": {"status": True, "result": "OBS1"}}` under `result`, the
    facade unwraps it and the hand-written version does not. Twenty-six of the fifty-three were
    dead as well -- the call did not ask for the whole response, so the conditional never fired.
    """
    offenders = {}
    everywhere = (source_files() + sorted((ROOT / "tests").glob("*.py"))
                  + sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"])
    for path in everywhere:
        if path.name == "test_conventions.py":
            continue        # this file quotes the line it forbids, in the docstring above
        found = [number for number, line in
                 enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if '"status" in' in line and "isinstance" in line]
        if found:
            offenders[path.relative_to(ROOT).as_posix()] = found

    assert not offenders, (
        "a response is unwrapped by hand:\n  "
        + "\n  ".join(f"{name}: {lines}" for name, lines in offenders.items())
        + "\nUse `response.value` with `raise_on_error=False`, or nothing at all without it.")


#: The facade methods a request goes through. Each returns a `Response` only when the call
#: passes `raise_on_error=False`, and the bare answer otherwise.
REQUEST_METHODS = {"export", "inspect", "configure", "calculate", "compute", "visualize",
                   "save", "load", "pipeline", "replay"}


def _responses_read_without_asking_for_one(tree):
    """Return every `.value` / `.ok` / `.error` read off a request that returns no `Response`.

    Notes:
        - Scoped per function, because the same variable name is reused across a module and a
          match found in another function is not a match at all.
        - A variable reassigned *with* `raise_on_error` stops being an offender, which is the
          usual shape: ask plainly, then ask again tolerantly.
    """
    found = []
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        bare = {}
        for node in ast.walk(scope):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr in REQUEST_METHODS):
                continue
            asked = {keyword.arg for keyword in node.value.keywords if keyword.arg}
            name = node.targets[0].id
            if "raise_on_error" in asked:
                bare.pop(name, None)
            else:
                bare[name] = (node.lineno, node.value.func.attr)

        for node in ast.walk(scope):
            if (isinstance(node, ast.Attribute) and node.attr in ("value", "ok", "error")
                    and isinstance(node.value, ast.Name) and node.value.id in bare):
                line, operation = bare[node.value.id]
                found.append(f"line {node.lineno}: .{node.attr} on the answer of "
                             f"{operation}() at line {line}")
    return found


def test_styling_lives_in_the_stylesheet_and_nowhere_else():
    """G1's exit criterion: no `setStyleSheet` in the codebase.

    224 `styleSheet` properties were spread across 24 `.ui` forms and 131 lines were written
    inline in `app.main`, so "what does this application look like" had no answer and copying a
    form was how a second variant of a rule came to exist -- 38 spin boxes were styled two
    different ways for no reason anybody chose.

    One call survives, and it is the one that applies the file.
    """
    from pastrocore.gui.styling import SHIPPED

    offenders = {}
    for path in sorted((ROOT / "pastrocore").rglob("*.py")):
        if path.name.startswith(("ui_", "rc_")):
            continue
        found = [number for number, line in
                 enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if "setStyleSheet(" in line and not line.strip().startswith("#")]
        if found:
            offenders[path.relative_to(ROOT).as_posix()] = found

    assert offenders == {"pastrocore/app.py": [1543]} or list(offenders) == ["pastrocore/app.py"], (
        "styling has escaped the stylesheet:\n  "
        + "\n  ".join(f"{name}: lines {lines}" for name, lines in offenders.items())
        + f"\nPut the rule in {SHIPPED.name} instead.")

    assert SHIPPED.is_file(), "the stylesheet the application loads is not there"


def test_no_form_styles_itself():
    """The forms are authored in Designer, and a `styleSheet` property there is a rule nobody
    outside that form can see. They are regenerated from the `.ui` sources, so this checks the
    sources rather than what came out of them."""
    forms = ROOT / "pastrocore" / "gui_pyside"
    offenders = [path.name for path in sorted(forms.glob("*.ui"))
                 if "styleSheet" in path.read_text(encoding="utf-8")]

    assert not offenders, (
        f"these forms style themselves: {offenders}\n"
        f"Run: python tools/extract_stylesheets.py && python tools/regenerate_ui.py")


#: Reading a catalogue's contents. The catalogues hold `Sources` and `Telescopes`, which are
#: model types the orchestrator knows, so the interface reaches them the same way it reaches
#: everything else. Policed separately from `MODEL_METHODS` because `get_items` is far too
#: common a name to forbid outright.
CATALOGUE_READ = re.compile(r"catalog_manager\.(source_catalog|telescope_catalog)\.get_\w+\(")


def test_the_interface_reads_a_catalogue_through_the_orchestrator_too():
    """The catalogue layer was the one place left reaching past the orchestrator.

    `CatalogManager` is backend -- the parsing lives there, not in a dialog -- so this was never
    logic in the interface. It was the interface holding a model object and calling it, which is
    the half of the rule that makes a command line and a server possible: they have no
    `catalog_manager` attribute to reach through.
    """
    offenders = {}
    modules = [module for module in sorted((ROOT / "pastrocore" / "gui").glob("*.py"))
               if not module.name.startswith(("ui_", "rc_"))]
    modules.append(ROOT / "pastrocore" / "app.py")

    for module in modules:
        found = []
        for number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "manipulator.inspect(" in stripped:
                continue
            if CATALOGUE_READ.search(line):
                found.append(number)
        if found:
            offenders[module.relative_to(ROOT).as_posix()] = found

    assert not offenders, (
        "a catalogue is read directly:\n  "
        + "\n  ".join(f"{name}: lines {lines}" for name, lines in offenders.items())
        + "\nAsk the orchestrator: inspect(catalog, get_items=None).")


def test_a_response_is_only_read_where_one_was_asked_for():
    """`.value` exists on a `Response`, and a request returns one only when it is told not to
    raise. Without `raise_on_error=False` the answer is the value itself.

    The export dialog read `.value` off a plain dict. Every file had already been written, the
    operation had already succeeded, and the user was shown "'dict' object has no attribute
    'value'" -- a failure reported for work that was done. Nothing caught it because the thread
    logs and emits rather than raising, so the suite saw a signal it was not watching.

    Twenty-six calls of exactly this shape were fixed when 1.8.0 was adopted; this is what stops
    the twenty-seventh.
    """
    offenders = {}
    for path in source_files() + sorted((ROOT / "tests").glob("*.py")):
        if path.name == "test_conventions.py":
            continue
        found = _responses_read_without_asking_for_one(
            ast.parse(path.read_text(encoding="utf-8")))
        if found:
            offenders[path.relative_to(ROOT).as_posix()] = found

    # The documentation too. Teaching the line is worse than containing it, and a page that
    # showed `.value` on a plain answer was found by the suite running the page rather than by
    # this check -- which only looked at Python files.
    blocks = re.compile(r"```python\n(.*?)```", re.DOTALL)
    for page in sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]:
        for number, block in enumerate(blocks.findall(page.read_text(encoding="utf-8")), 1):
            try:
                found = _responses_read_without_asking_for_one(ast.parse(block))
            except SyntaxError:
                continue
            if found:
                offenders[f"{page.relative_to(ROOT).as_posix()} block {number}"] = found

    assert not offenders, (
        "a response is read where the request returns no response:\n  "
        + "\n  ".join(f"{name}: {'; '.join(lines)}" for name, lines in offenders.items())
        + "\nPass `raise_on_error=False` to get a Response, or read the answer directly.")


def test_a_to_dict_override_copies_before_it_writes():
    """`to_dict` on an object that caches returns the cache itself, and MSB 1.9.0 made writing
    to it raise rather than corrupt what every later call reports.

    Three overrides here wrote into what `super().to_dict()` handed back. Nothing constructs
    with `use_cache=True` today, so it was a rake with a label on it -- turning caching on for a
    telescope would have raised `SerializationError` on the second serialisation.
    """
    from msb_arch import errors
    from pastrocore.base.scans import Scan
    from pastrocore.base.spacetelescope import SpaceTelescope
    from pastrocore.base.telescope import Telescope

    from astropy.time import Time

    for entity in (Telescope(code="EF", name="Effelsberg", x=1.0, y=2.0, z=3.0, diameter=100.0),
                   SpaceTelescope(code="RADIO", name="RadioAstron"),
                   Scan(name="s", start=Time("2026-01-01T00:00:00"), duration=60.0)):
        entity._use_cache = True
        entity.to_dict()
        entity.to_dict()        # the second call is the one that meets the frozen mapping
