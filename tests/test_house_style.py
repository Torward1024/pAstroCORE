"""What the prose in this repository is held to, counted rather than judged (W1).

Every docstring, comment and `.md` is held to one style: a one-line summary, Google sections and
nothing else; `Notes` only for what a caller must know; a comment of two lines saying why; a
paragraph of four. Both ledgers are empty, so the style is a gate. A file that cannot meet it
yet is written down with what it owes, and that number may only go down.
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

#: The shortest a docstring may be held to whatever the body is. A one-line function still
#: takes a summary and a note, and Google style has no shorter form than that.
PROSE_FLOOR = 3

DATE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")

#: The Google sections, whose length a signature decides rather than a writer.
SECTION = re.compile(r"^\s*(Args|Arguments|Returns|Yields|Raises|Attributes|Examples?):\s*$")

#: A bullet or a numbered step, which starts a paragraph of its own.
ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")


def prose_lines(text: str) -> list:
    """Return the lines of a docstring that are written rather than owed to the signature.

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
    return kept


def prose_of(text: str) -> int:
    """Return how many lines of a docstring are written rather than owed to the signature."""
    return sum(1 for line in prose_lines(text) if line.strip())


def paragraph_lines(text: str) -> list:
    """Return a docstring's prose, numbered, with what is not prose blanked out.

    Notes:
        - An example indented under a sentence is a code block, and a row of `|` is a table.
          Neither is a paragraph, and holding them to four lines would say to cut an example.
    """
    kept = prose_lines(text)
    body = [len(line) - len(line.lstrip()) for line in kept[1:] if line.strip()]
    margin = min(body) if body else 0
    return [(number, "" if line.lstrip().startswith("|")
             or len(line) - len(line.lstrip()) >= margin + 4 else line)
            for number, line in enumerate(kept, 1)]


def over_a_paragraph(lines) -> list:
    """Return the line of each paragraph that runs past `PARAGRAPH` lines.

    Args:
        lines (Iterable[Tuple[int, str]]): Numbered lines, already stripped of tables, code
            fences and anything else that is not prose.

    Returns:
        list: The number of the first line of each paragraph that is too long.
    """
    found, run, start = [], 0, 0
    for number, line in lines:
        if not line.strip():
            run = 0
            continue
        run = 1 if ITEM.match(line) else run + 1
        start = number if run == 1 else start
        if run == PARAGRAPH + 1:
            found.append(start)
    return found


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
    for _ in over_a_paragraph(paragraph_lines(text)):
        found.append(f"line {where}: a paragraph over {PARAGRAPH} lines")
    if not summary.rstrip().endswith((".", "?", ":")):
        found.append(f"line {where}: a summary with no full stop")
    if DATE.search(text):
        found.append(f"line {where}: a date in a docstring")

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        body = node.body[1:]
        written = (body[-1].end_lineno - body[0].lineno + 1) if body else 0
        held = prose_of(text)
        if held > max(written, PROSE_FLOOR):
            found.append(f"line {where}: {held} lines of prose over {written} of body")

    if "Notes:" not in text:
        return
    # Up to the next Google section: `Examples` after `Notes` is not a note.
    tail = text.split("Notes:", 1)[1]
    for number, line in enumerate(tail.splitlines()):
        if SECTION.match(line):
            tail = "\n".join(tail.splitlines()[:number])
            break
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
    """Return the markdown paragraphs that run past `PARAGRAPH` lines.

    Notes:
        - A table, a heading and a fenced block are not prose, and a list is not one
          paragraph: each item is held to the same four lines on its own.
    """
    prose, fenced = [], False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            prose.append((number, ""))
            continue
        prose.append((number, "" if fenced or line.lstrip().startswith(("|", "#")) else line))
    return [f"line {start}" for start in over_a_paragraph(prose)]


#: What each module still owes. A number may only go down, and a module that owes nothing comes
#: off the list -- a stale entry would make the ledger look like progress that has not happened.
OWED = {}

#: The same, for the markdown.
PARAGRAPHS_OWED = {}


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
