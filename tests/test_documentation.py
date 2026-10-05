"""Execute the Python examples in the documentation.

Documentation rots quietly: an example keeps looking right long after the code moved, and the
only person who finds out is a reader following it. This runs every fenced Python block, so
that cannot happen silently.

Conventions, so this is a rule rather than a curiosity:

- A ```python block must run. Blocks of one document execute in order, in one namespace,
  exactly as a reader following the page would.
- A block showing a *shape* rather than code -- a directory tree, a response layout -- is
  fenced ```text instead. It is documentation, not an example.
- A block that demonstrates a refusal declares it on its first line with `# raises: <Type>`,
  and the test insists it really does raise that.
- Where an example states what it produces, write it as an `assert` rather than a comment.
  `print(x)  # 8` passes whatever `x` is; an assert is checked along with the code.

Borrowed from MSB, which has run its own documentation this way since 1.1.0 and found an
example that printed a result and returned an error.
"""
import io
import contextlib
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

#: A page of decisions rather than instructions: its blocks are not programs.
EXCLUDED = {"ROADMAP.md"}

RAISES = re.compile(r"^\s*#\s*raises:\s*(\w+)", re.M)
BLOCKS = re.compile(r"```python\n(.*?)```", re.S)


def documents():
    """Every documentation page carrying Python examples, plus the README."""
    found = [path for path in sorted(DOCS.rglob("*.md")) if path.name not in EXCLUDED]
    found.append(ROOT / "README.md")
    return [path for path in found
            if path.exists() and "```python" in path.read_text(encoding="utf-8")]


@pytest.mark.parametrize("document", documents(), ids=lambda p: p.name)
def test_every_example_runs(document, tmp_path, monkeypatch):
    """One namespace per document, in order, as a reader would."""
    monkeypatch.chdir(tmp_path)
    blocks = BLOCKS.findall(document.read_text(encoding="utf-8"))
    assert blocks, f"{document.name} was collected as having examples and has none"

    namespace = {"__name__": "__doc_example__", "TMP": tmp_path,
                 "DOCUMENT": document.read_text(encoding="utf-8")}
    for number, block in enumerate(blocks, start=1):
        expected = RAISES.search(block)
        where = f"{document.relative_to(ROOT).as_posix()} block {number}"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(block, where, "exec"), namespace)
        except Exception as error:                      # noqa: BLE001 - reported as a failure
            if expected and type(error).__name__ == expected.group(1):
                continue
            if expected:
                raise AssertionError(
                    f"{where} declares `# raises: {expected.group(1)}` and raised "
                    f"{type(error).__name__}: {error}") from error
            raise AssertionError(f"{where} does not run: {type(error).__name__}: {error}") from error
        else:
            if expected:
                raise AssertionError(
                    f"{where} declares `# raises: {expected.group(1)}` and did not raise")


def test_a_page_shows_no_screenshot_that_is_not_made():
    """A screenshot in a manual goes stale the moment a form is edited, and nothing says so.

    Notes:
        - Every image a page shows must be one `tools/make_screenshots.py` writes, so a
          renamed tab fails the build rather than leaving the manual showing last month's.
        - The other way round is not checked: the harness makes a screen whether or not a
          page has got round to showing it.
    """
    import subprocess

    shown = set()
    for path in sorted(DOCS.rglob("*.md")):
        for name in re.findall(r"!\[[^\]]*\]\(images/([^)]+)\)",
                               path.read_text(encoding="utf-8")):
            shown.add((path.name, name))
    if not shown:
        pytest.skip("no page shows a screenshot yet")

    made = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "make_screenshots.py"), "--list"],
        capture_output=True, text=True, check=True, cwd=ROOT)
    known = {f"{name}.png" for name in made.stdout.split()}

    unknown = sorted(f"{page} shows {name}" for page, name in shown if name not in known)
    assert not unknown, f"these are not screenshots the harness makes: {unknown}"

    missing = sorted({name for _, name in shown} - {p.name for p in (DOCS / "images").glob("*")})
    assert not missing, f"these are named by a page and not written: {missing}"


def test_the_documentation_covers_what_r3_asks_for():
    """R3's exit criterion, as a list rather than as a feeling: installing, running, adding an
    observation, reading a result -- each with a runnable example."""
    pages = {path.name for path in DOCS.glob("*.md")}
    assert {"README.md", "installing.md", "guide.md", "calculations.md"} <= pages, (
        f"docs/ is missing a page R3 names: {sorted(pages)}")

    guide = (DOCS / "guide.md").read_text(encoding="utf-8")
    for subject in ("create_item", "create_telescope", "create_source", "create_scan",
                    'method="run"', "get_calculated_data_by_key"):
        assert subject in guide, f"the guide never shows {subject}"
