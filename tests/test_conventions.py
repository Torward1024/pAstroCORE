"""Conventions that are easier to keep than to restore.

Each of these was fixed once across the whole codebase. Without a test, the next hundred lines
written would reintroduce it a few at a time, and nobody would notice until it had to be done
again.
"""
import ast
import pathlib

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
