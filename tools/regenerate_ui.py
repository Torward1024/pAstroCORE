"""Regenerate the Qt forms and the icon resource from their sources.

Interface changes are made in the `.ui` files with Qt Designer and regenerated from here. A
form edited only in its generated `.py` cannot be opened in Designer again without losing the
edit, so the rule protects the tool rather than the file.

    python tools/regenerate_ui.py            # rewrite the generated modules
    python tools/regenerate_ui.py --check    # report drift, change nothing

`--check` is what the test suite runs, so a form edited in its `.py` alone fails the build
rather than surviving until somebody opens Designer and loses it.

Two things this does that a bare `pyside6-uic` does not:

- **Finds where each form belongs.** The generated names are not `ui_` plus the source stem:
  `dialog_editor_if.ui` produces `ui_dialog_edit_if.py`, and one source is spelled
  `dialog_edtior_source.ui`. Matching on the form's *class* rather than its filename means the
  mapping needs no table to fall out of date.
- **Fixes the resource import.** `uic` emits `import icons_rc`, a bare module name that only
  resolves if `pastrocore/gui` is on `sys.path`, which it is not. It is rewritten to a package
  import. This is the trap that makes regenerating look like it works and then fail on the
  first icon.
"""
import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMS = ROOT / "pastrocore" / "gui_pyside"
GENERATED = ROOT / "pastrocore" / "gui"
RESOURCE = GENERATED / "icons" / "icons.qrc"
RESOURCE_MODULE = GENERATED / "rc_icons.py"

# What `uic` writes, and what it has to become. See the module docstring.
RESOURCE_IMPORT = re.compile(r"^import icons_rc\s*$", re.MULTILINE)
RESOURCE_REPLACEMENT = "from pastrocore.gui import rc_icons  # noqa: F401"


def find_tool(name: str) -> list:
    """Return a command that runs one of the PySide6 code generators.

    Args:
        name (str): Either "uic" or "rcc".

    Returns:
        list: The command, as a list ready for `subprocess`.

    Raises:
        FileNotFoundError: If the tool cannot be found, naming what was looked for.

    Notes:
        - Installed as `pyside6-uic` on the path, and also as a binary beside the PySide6
          package. The second is checked because a virtual environment that was not activated
          has the package importable and the console script missing.
    """
    on_path = shutil.which(f"pyside6-{name}")
    if on_path:
        return [on_path]

    import PySide6

    beside = Path(PySide6.__file__).parent / (f"{name}.exe" if os.name == "nt" else name)
    if beside.is_file():
        return [str(beside)]

    raise FileNotFoundError(
        f"cannot find pyside6-{name}: not on PATH, and not at {beside}")


def form_class(ui_file: Path) -> str:
    """Return the class name a form generates, read from the form itself."""
    match = re.search(r"<class>(.*?)</class>", ui_file.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{ui_file.name} declares no <class>")
    return match.group(1)


def generated_modules() -> dict:
    """Map each generated class to the module that currently defines it.

    Returns:
        dict: `{"MainWindow": Path(".../ui_main_window.py"), ...}`.
    """
    found = {}
    for module in GENERATED.glob("ui_*.py"):
        match = re.search(r"^class Ui_(\w+)", module.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            found[match.group(1)] = module
    return found


def target_for(ui_file: Path, existing: dict) -> Path:
    """Return where a form's generated module belongs.

    Args:
        ui_file (Path): The form.
        existing (dict): What `generated_modules` found.

    Returns:
        Path: The module to write. An existing one keeps its name; a form that has never been
            generated gets `ui_<stem>.py`.
    """
    return existing.get(form_class(ui_file), GENERATED / f"ui_{ui_file.stem}.py")


def generate(ui_file: Path, destination: Path, uic: list) -> str:
    """Generate one form and return the text, with the resource import corrected."""
    result = subprocess.run(uic + ["-g", "python", str(ui_file)],
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"uic failed on {ui_file.name}: {result.stderr.strip()}")

    text = RESOURCE_IMPORT.sub(RESOURCE_REPLACEMENT, result.stdout)
    # uic records the file it read, which is a Designer temp name when the form was saved from
    # Designer. Normalising it keeps a regeneration from showing as a change every time.
    return re.sub(r"^## Form generated from reading UI file '.*'$",
                  f"## Form generated from reading UI file '{ui_file.name}'",
                  text, flags=re.MULTILINE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="report what would change and exit non-zero, writing nothing")
    arguments = parser.parse_args()

    uic = find_tool("uic")
    existing = generated_modules()
    drifted, written = [], 0

    for ui_file in sorted(FORMS.glob("*.ui")):
        destination = target_for(ui_file, existing)
        fresh = generate(ui_file, destination, uic)
        current = destination.read_text(encoding="utf-8") if destination.is_file() else ""

        if fresh == current:
            continue
        if arguments.check:
            drifted.append((ui_file.name, destination.name, fresh, current))
            continue
        destination.write_text(fresh, encoding="utf-8")
        written += 1
        print(f"  {ui_file.name:44s} -> {destination.name}")

    if not arguments.check and RESOURCE.is_file():
        rcc = find_tool("rcc")
        result = subprocess.run(rcc + [str(RESOURCE), "-o", str(RESOURCE_MODULE)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(f"rcc failed: {result.stderr.strip()}", file=sys.stderr)
            return 1
        print(f"  {RESOURCE.name:44s} -> {RESOURCE_MODULE.name}")

    if arguments.check:
        if not drifted:
            print(f"all {len(list(FORMS.glob('*.ui')))} forms match their sources")
            return 0
        for source, module, fresh, current in drifted:
            print(f"\n{module} does not match {source}:")
            diff = difflib.unified_diff(current.splitlines(), fresh.splitlines(),
                                        fromfile=module, tofile=f"{source} regenerated",
                                        lineterm="", n=1)
            for line in list(diff)[:24]:
                print(f"  {line}")
        print(f"\n{len(drifted)} form(s) drifted. Run: python tools/regenerate_ui.py")
        return 1

    print(f"{written} module(s) rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
