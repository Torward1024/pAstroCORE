"""What a download is built from, checked without building one.

A build takes minutes and three machines, so what can go wrong between them is worth catching
here: a Qt module the application started importing and the spec still excludes, a file the
spec names and nobody ships, a download whose name the workflow looks for and the installer
does not write.

The build itself is checked by CI starting what it made. These are the things that would make
that failure take a release to discover.
"""
import ast
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "pastrocore.spec"
INSTALLER = ROOT / "packaging" / "pastrocore.iss"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
PACKAGE = ROOT / "pastrocore"


def declared(name: str) -> list:
    """Return a list the spec assigns to `name`, read rather than imported.

    Notes:
        - A spec is Python with names PyInstaller injects, so it cannot be imported here.
    """
    for node in ast.parse(SPEC.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    pytest.fail(f"the spec declares no {name}")


def modules():
    """Every hand-written module, which is what a build has to be able to import."""
    return [path for path in PACKAGE.rglob("*.py") if "__pycache__" not in path.parts]


def test_no_excluded_module_is_one_the_application_imports():
    """The excludes are what keeps a download from being most of a gigabyte, and a module
    added to the interface would be excluded silently: the build succeeds and the window
    fails to open on a machine that has no Python to fall back on."""
    without = set(declared("WITHOUT"))
    imported = set()
    for path in modules():
        text = path.read_text(encoding="utf-8")
        imported.update(f"PySide6.{found}" for found in re.findall(r"from PySide6\.(\w+)", text))
        imported.update(re.findall(r"^\s*import\s+([\w.]+)", text, re.M))

    shipped_and_excluded = sorted(imported & without)
    assert not shipped_and_excluded, (
        f"the spec excludes what the application imports: {shipped_and_excluded}")


def test_the_spec_names_files_that_are_here():
    """A spec pointing at a renamed file fails on the build machine and nowhere else."""
    text = SPEC.read_text(encoding="utf-8")
    for named in re.findall(r'"([\w./]+\.(?:py|png|ico|icns))"', text):
        if named.endswith((".ico", ".icns")):
            continue                                # made by `tools/make_icons.py` at build time
        assert (ROOT / named).is_file() or (ROOT / "packaging" / named).is_file(), (
            f"the spec names {named}, which is not here")


def test_the_build_carries_the_source_both_packages_are_derived_from():
    """1.18.0 started on three machines and offered no calculations: MSB derives what an
    application can do by reading the source of its handlers, and a frozen build holds
    bytecode. Without the `.py` files the catalogue comes back empty and nothing works."""
    text = SPEC.read_text(encoding="utf-8")
    collected = re.search(r'for package in \(([^)]+)\)', text)
    assert collected, "the spec collects no source at all"

    named = set(re.findall(r'"(\w+)"', collected.group(1)))
    assert {"pastrocore", "msb_arch"} <= named, f"the spec carries the source of {named}"
    assert 'rglob("*.py")' in text, "the spec collects something other than source"


def test_what_the_spec_collects_from_the_package_is_there_to_collect():
    """A pattern matching nothing ships nothing, and the build says nothing about it: the
    download starts and its catalogues are empty."""
    text = SPEC.read_text(encoding="utf-8")
    package = re.search(r'collect_data_files\("pastrocore", includes=\[([^\]]+)\]', text)
    assert package, "the spec collects nothing from the package"

    for pattern in re.findall(r'"([^"]+)"', package.group(1)):
        assert list(PACKAGE.glob(pattern)), f"{pattern} matches nothing in the package"


def test_the_installer_writes_the_name_the_workflow_looks_for():
    """Two places spell one file name, and a download nobody collects is a release with
    nothing attached to it."""
    written = re.search(r"OutputBaseFilename=(\S+)", INSTALLER.read_text(encoding="utf-8"))
    assert written, "the installer script says nothing about what it writes"

    # The workflow matches on a pattern, the version being the one part of the name it
    # cannot know: `{#Version}` is what the compiler fills in and `*` is what finds it.
    name = written.group(1).replace("{#Name}", "pAstroCORE").replace("{#Version}", "*") + ".exe"
    assert name in WORKFLOW.read_text(encoding="utf-8"), (
        f"the installer writes {name} and the workflow looks for something else")


def test_the_download_page_links_at_the_files_that_are_built():
    """Two lists of three names -- what is built and what is linked -- and nothing says when
    they stop agreeing except a release with three dead links on its page."""
    sys.path.insert(0, str(ROOT / "tools"))
    from make_download import DOWNLOADS

    page = (ROOT / "docs" / "download.md").read_text(encoding="utf-8")
    for held in DOWNLOADS.values():
        assert held["suffix"] in page, f"the page links at no {held['suffix']}"


def test_every_download_says_which_version_it_is():
    """Two of them on a disk are told apart by their names and by nothing else."""
    sys.path.insert(0, str(ROOT / "tools"))
    from make_download import DOWNLOADS, download_name

    where = "linux" if sys.platform.startswith("linux") else sys.platform
    if where not in DOWNLOADS:
        pytest.skip(f"nothing is built for {where}")
    assert "9.9.9" in download_name("9.9.9", where)


def test_every_platform_is_built_and_started():
    """I1 asks for three downloads, each started by the machine that made it."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for runner in ("windows-latest", "macos-latest", "ubuntu-22.04"):
        assert runner in workflow, f"{runner} builds nothing"
    assert workflow.count("--selftest") == 3, "a platform builds a download it never starts"
