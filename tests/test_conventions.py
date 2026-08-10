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
    files.append(ROOT / "pastrocore.py")
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
