"""Conventions that are easier to keep than to restore.

Each of these was fixed once across the whole codebase. Without a test, the next hundred lines
written would reintroduce it a few at a time, and nobody would notice until it had to be done
again.
"""
import ast
import pathlib
import re

import pytest

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


# Sixteen calls carry a format spec or a conversion -- `{x:.2f}`, `{x!r}` -- where `%s` would
# render something different. They are left alone deliberately. The number may only go down.
ALLOWED_EAGER = 16


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
