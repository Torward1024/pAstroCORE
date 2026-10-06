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

    name = written.group(1).replace("{#Name}", "pAstroCORE").replace("{#Version}", "*")
    looked_for = WORKFLOW.read_text(encoding="utf-8")
    assert "pAstroCORE-*-windows-x64.exe" in looked_for, "the workflow looks for another name"
    assert name.startswith("pAstroCORE-") and name.endswith("-windows-x64"), name


def test_every_platform_is_built_and_started():
    """I1 asks for three downloads, each started by the machine that made it."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for runner in ("windows-latest", "macos-latest", "ubuntu-22.04"):
        assert runner in workflow, f"{runner} builds nothing"
    assert workflow.count("--selftest") == 3, "a platform builds a download it never starts"
