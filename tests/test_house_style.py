"""What the prose in this repository is held to, counted rather than judged (W1).

Every docstring, comment and `.md` is being cut down to one style: a one-line summary, Google
sections and nothing else; `Notes` only for what a caller must know; a comment of two lines
saying why. 889 places did not meet it when this was written, so the rule is a ledger rather
than a gate -- each module owes a number, the number may only go down, and a module that owes
nothing comes off the list.
"""
import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "pastrocore"

#: How long a summary line may be, which is the 95th percentile of the lines already here.
SUMMARY = 95

#: How many lines one point under `Notes` may take, and how many points there may be.
NOTE_LINES = 2
NOTES = 3

#: How many lines of comment may stand together before it is a docstring or nothing.
COMMENT_LINES = 2

#: How many lines a paragraph of markdown may take.
PARAGRAPH = 4

DATE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")

#: The Google sections, whose length a signature decides rather than a writer.
SECTION = re.compile(r"^\s*(Args|Arguments|Returns|Yields|Raises|Attributes|Examples?):\s*$")


def prose_of(text: str) -> int:
    """Return how many lines of a docstring are written rather than owed to the signature.

    Notes:
        - The summary and `Notes` are written; `Args` and `Returns` follow from the
          signature, and counting them held a ten-line function to a docstring of nine.
    """
    kept, inside = [], False
    for line in text.splitlines():
        if SECTION.match(line):
            inside = True
            continue
        if inside:
            if line.strip() and not line.startswith(" " * 8):
                inside = False
            else:
                continue
        kept.append(line)
    return sum(1 for line in kept if line.strip())


def modules():
    """Every hand-written module. Generated Qt output is not prose anybody chose."""
    return [path for path in sorted(PACKAGE.rglob("*.py"))
            if "__pycache__" not in path.parts and not path.name.startswith(("ui_", "rc_"))]


def documents():
    """Every markdown file in the repository."""
    return [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").glob("*.md"))]


def _docstring_faults(node, found):
    """Add what one docstring owes to `found`."""
    text = ast.get_docstring(node, clean=False)
    if not text or not text.strip():
        return
    # A module's docstring has no line of its own; it starts at the top of the file.
    where = getattr(node, "lineno", 1)
    summary = text.strip().splitlines()[0]
    if len(summary) > SUMMARY:
        found.append(f"line {where}: a summary of {len(summary)} characters")
    if not summary.rstrip().endswith((".", "?", ":")):
        found.append(f"line {where}: a summary with no full stop")
    if DATE.search(text):
        found.append(f"line {where}: a date in a docstring")

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        body = node.body[1:]
        written = (body[-1].end_lineno - body[0].lineno + 1) if body else 0
        held = prose_of(text)
        if held > max(written, 1):
            found.append(f"line {where}: {held} lines of prose over {written} of body")

    if "Notes:" not in text:
        return
    tail = text.split("Notes:", 1)[1]
    points = re.split(r"^\s*- ", tail, flags=re.M)[1:]
    if len(points) > NOTES:
        found.append(f"line {where}: {len(points)} notes")
    for point in points:
        taken = len(point.strip().splitlines())
        if taken > NOTE_LINES:
            found.append(f"line {where}: a note of {taken} lines")


def owed_by(path) -> list:
    """Return what one module owes the style, a line apiece.

    Args:
        path (Path): The module to read.

    Returns:
        list: One string per place that does not meet the style, naming the line.
    """
    text = path.read_text(encoding="utf-8")
    found = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            _docstring_faults(node, found)

    run = start = 0
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("#"):
            run += 1
            start = number if run == 1 else start
            if run == COMMENT_LINES + 1:
                found.append(f"line {start}: a comment over {COMMENT_LINES} lines")
            if DATE.search(line):
                found.append(f"line {number}: a date in a comment")
        else:
            run = 0
    return found


def long_paragraphs(path) -> list:
    """Return the markdown paragraphs that run past `PARAGRAPH` lines."""
    found = []
    run = start = 0
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            run = 0
            continue
        if fenced or line.startswith(("|", "#")) or not line.strip():
            run = 0
            continue
        run += 1
        start = number if run == 1 else start
        if run == PARAGRAPH + 1:
            found.append(f"line {start}")
    return found


#: What each module still owes, measured 30.09.2026 before the W1 pass. A number may only go
#: down, and a module that owes nothing comes off the list -- a stale entry would make the
#: ledger look like progress that has not happened.
OWED = {
    "app.py":                                 46,
    "base/data_structure.py":                 15,
    "base/frequencies.py":                    22,
    "base/freshness.py":                      13,
    "base/generation_plan.py":                7,
    "base/observation.py":                    11,
    "base/result_store.py":                   27,
    "base/scans.py":                          13,
    "base/scratch.py":                        7,
    "base/sources.py":                        18,
    "base/spacetelescope.py":                 8,
    "base/telescope.py":                      13,
    "base/telescopes.py":                     10,
    "cli.py":                                 6,
    "cli_request.py":                         5,
    "formats/__init__.py":                    15,
    "formats/cfx.py":                         8,
    "formats/vex.py":                         24,
    "gui/icon_theme.py":                      2,
    "gui/p_custom_model.py":                  9,
    "gui/p_dialog_about.py":                  1,
    "gui/p_dialog_add_observation.py":        1,
    "gui/p_dialog_calculations.py":           16,
    "gui/p_dialog_catalog.py":                2,
    "gui/p_dialog_edit_if.py":                6,
    "gui/p_dialog_edit_scan.py":              7,
    "gui/p_dialog_edit_source.py":            4,
    "gui/p_dialog_edit_space_telescope.py":   2,
    "gui/p_dialog_edit_telescope.py":         2,
    "gui/p_dialog_export_calculated_data.py": 4,
    "gui/p_dialog_generate_observations.py":  5,
    "gui/p_dialog_preferences.py":            2,
    "gui/p_dialog_progress.py":               6,
    "gui/p_dialog_run_report.py":             3,
    "gui/p_dialog_schedule_export.py":        2,
    "gui/p_dialog_session.py":                5,
    "gui/p_dialog_visualize.py":              7,
    "gui/p_status_bar.py":                    3,
    "gui/p_tab_analysis.py":                  6,
    "gui/p_tab_frequencies.py":               7,
    "gui/p_tab_observation.py":               4,
    "gui/p_tab_project.py":                   3,
    "gui/p_tab_scans.py":                     5,
    "gui/p_tab_sources.py":                   7,
    "gui/p_tab_telescopes.py":                6,
    "gui/p_tab_vis_base.py":                  15,
    "gui/p_tab_vis_beam_pattern.py":          3,
    "gui/p_tab_vis_mollweide.py":             3,
    "gui/p_tab_vis_sensitivity.py":           1,
    "gui/p_tab_vis_spacecraft.py":            4,
    "gui/p_tab_vis_uv_coverage.py":           2,
    "gui/p_table_models.py":                  3,
    "paths.py":                               5,
    "super/schedule_address.py":              2,
    "super/schedule_analyzer.py":             15,
    "super/schedule_calculator.py":           79,
    "super/schedule_cfx.py":                  1,
    "super/schedule_configurator.py":         7,
    "super/schedule_data.py":                 31,
    "super/schedule_format.py":               5,
    "super/schedule_inspector.py":            2,
    "super/schedule_manipulator.py":          11,
    "super/schedule_project.py":              25,
    "super/schedule_runner.py":               49,
    "super/schedule_vex.py":                  1,
    "super/schedule_visualizer.py":           40,
    "theme.py":                               4,
    "utils/catalogmanager.py":                11,
    "utils/machine.py":                       1,
}

#: The same, for the markdown.
PARAGRAPHS_OWED = {
    "CHANGELOG.md":         90,
    "README.md":            5,
    "docs/README.md":       1,
    "docs/ROADMAP.md":      2,
    "docs/analysis.md":     1,
    "docs/calculations.md": 5,
    "docs/command-line.md": 1,
    "docs/formats.md":      3,
}


@pytest.mark.parametrize("path", modules(), ids=lambda p: p.relative_to(PACKAGE).as_posix())
def test_a_module_owes_no_more_than_it_did(path):
    """The ledger is a ceiling. Prose added to a module has to meet the style."""
    name = path.relative_to(PACKAGE).as_posix()
    found = owed_by(path)
    allowed = OWED.get(name, 0)

    assert len(found) <= allowed, (
        f"{name} owes {len(found)} where {allowed} was allowed:\n  "
        + "\n  ".join(found[:12]))


@pytest.mark.parametrize("path", documents(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_a_document_owes_no_more_than_it_did(path):
    """The same ceiling for the markdown: a paragraph is four lines."""
    name = path.relative_to(ROOT).as_posix()
    found = long_paragraphs(path)
    allowed = PARAGRAPHS_OWED.get(name, 0)

    assert len(found) <= allowed, (
        f"{name} has {len(found)} paragraphs over {PARAGRAPH} lines where {allowed} "
        f"was allowed: {', '.join(found[:8])}")


def test_the_ledger_is_not_padded():
    """A module that owes nothing comes off the list, so the numbers keep meaning something."""
    settled = sorted(name for name, allowed in OWED.items()
                     if allowed and not owed_by(PACKAGE / name))
    settled += sorted(f"{name} (markdown)" for name, allowed in PARAGRAPHS_OWED.items()
                      if allowed and not long_paragraphs(ROOT / name))

    assert not settled, f"these owe nothing now -- take them out of the ledger: {settled}"


def test_the_ledger_names_only_what_is_there():
    """An entry for a module that has gone would hide the next one that needs it."""
    missing = [name for name in OWED if not (PACKAGE / name).is_file()]
    missing += [name for name in PARAGRAPHS_OWED if not (ROOT / name).is_file()]

    assert not missing, f"the ledger names files that are not here: {missing}"
