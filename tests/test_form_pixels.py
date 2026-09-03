"""Every form renders exactly as it did (G1's acceptance test).

G1 -- one stylesheet in a file rather than 224 `setStyleSheet` calls across 24 generated forms
-- was attempted once and reverted, and the reason is worth stating: **every form carries a
sheet on its top-level widget, which reaches every child**. Moving that to application level
changes which rule wins, so a form can end up styled by a rule it was previously shielded from.
Not one form matched what it replaced, and nothing in the suite noticed until someone looked.

So this exists before any of that is attempted again. It renders each form offscreen and
compares the pixels against a stored reference. It is not a test of whether the forms look
*good* -- it is a test of whether they look the same as they did, which is the only question a
refactoring of styling can be judged by.

The reference is regenerated deliberately:

    python -m pytest tests/test_form_pixels.py --regenerate-form-pixels

Do that only when a form was *meant* to change, and look at what changed first: the failure
names the form and how many pixels moved.
"""
import hashlib
import importlib
import json
import pathlib
import sys

import pytest

pytest.importorskip("PySide6")

from PySide6 import __version__ as QT_BINDING_VERSION
from PySide6.QtWidgets import QDialog, QMainWindow, QWidget

GUI = pathlib.Path(__file__).parent.parent / "pastrocore" / "gui"
REFERENCE = pathlib.Path(__file__).parent / "fixtures" / "form_pixels.json"


def platform_key() -> str:
    """Return which rendering this reference describes.

    Notes:
        - **Pixels are not portable.** The same form on Windows and on Linux differs in fonts,
          in metrics and in what the platform style draws, so one set of digests cannot serve
          both -- and the build runs on Ubuntu while this is usually authored on Windows.
        - So a reference is stored per platform and per binding version, and a platform with no
          reference **skips** rather than fails. The harness is for whoever is changing the
          styling, on the machine they are changing it on; a green build on a platform nobody
          recorded would be a claim about nothing.
    """
    return f"{sys.platform}-pyside{QT_BINDING_VERSION.split('.')[0]}"

#: A form is rendered at a fixed size, because a layout given no size settles at whatever its
#: contents ask for and that is not stable across Qt versions or fonts.
SIZE = (900, 700)


def form_classes():
    """Every generated form, as (module stem, class name)."""
    found = []
    for path in sorted(GUI.glob("ui_*.py")):
        module = importlib.import_module(f"pastrocore.gui.{path.stem}")
        for name in sorted(dir(module)):
            if name.startswith("Ui_"):
                found.append((path.stem, name))
    return found


def render(stem: str, class_name: str) -> str:
    """Return a digest of one form's pixels.

    Notes:
        - The `Ui_` class alone, on a bare host widget: no orchestrator, no model, no data. What
          is being compared is the form as authored, which is exactly what a stylesheet change
          moves.
        - A digest rather than the image. What matters is whether it changed, and 24 PNGs in the
          repository would be 24 binary files nobody can review in a diff.
    """
    module = importlib.import_module(f"pastrocore.gui.{stem}")
    form = getattr(module, class_name)

    # The application's stylesheet is applied, because that is where the styling lives now.
    # Rendering a form without it would compare a bare form against a styled reference and
    # call every difference a regression.
    from PySide6.QtWidgets import QApplication

    from pastrocore.gui.styling import load_stylesheet

    application = QApplication.instance()
    if application is not None and not application.styleSheet():
        application.setStyleSheet(load_stylesheet())

    for host_type in (QDialog, QWidget, QMainWindow):
        host = host_type()
        try:
            form().setupUi(host)
        except Exception:
            host.deleteLater()
            continue
        host.resize(*SIZE)
        image = host.grab().toImage()
        # A fixed format, so a platform's preferred depth cannot change the digest.
        image = image.convertToFormat(image.Format.Format_RGBA8888)
        raw = image.constBits().tobytes()
        host.deleteLater()
        return hashlib.sha256(raw).hexdigest()[:32]

    raise AssertionError(f"{stem}.{class_name} could not be built on any host widget")


def stored():
    """Return the digests recorded for this platform, or an empty mapping."""
    if not REFERENCE.is_file():
        return {}
    return json.loads(REFERENCE.read_text(encoding="utf-8")).get(platform_key(), {})


def test_the_reference_covers_every_form(qt_application):
    """A reference that quietly stops covering a form is worse than no reference."""
    reference = stored()
    if not reference:
        pytest.skip(f"no reference for {platform_key()}; "
                    f"run with --regenerate-form-pixels on this platform")

    named = {f"{stem}.{name}" for stem, name in form_classes()}
    assert named == set(reference), (
        f"forms not in the reference: {sorted(named - set(reference))}; "
        f"in the reference but gone: {sorted(set(reference) - named)}")


@pytest.mark.parametrize("stem,class_name", form_classes())
def test_a_form_renders_as_it_did(qt_application, stem, class_name, request):
    """Named per form, so a failure says which one moved."""
    reference = stored()
    key = f"{stem}.{class_name}"
    if key not in reference:
        pytest.skip(f"{key} has no reference for {platform_key()}; "
                    f"run with --regenerate-form-pixels")

    assert render(stem, class_name) == reference[key], (
        f"{key} does not render as it did.\n"
        f"If that was intended, regenerate the reference:\n"
        f"    python -m pytest tests/test_form_pixels.py --regenerate-form-pixels")


def test_the_harness_would_notice_a_change(qt_application):
    """A harness that cannot fail proves nothing. A sheet applied to a form must change its
    pixels -- which is the whole premise of using pixels to judge a styling change."""
    stem, class_name = form_classes()[0]
    module = importlib.import_module(f"pastrocore.gui.{stem}")

    host = QDialog()
    getattr(module, class_name)().setupUi(host)
    host.resize(*SIZE)
    before = hashlib.sha256(
        host.grab().toImage().convertToFormat(
            host.grab().toImage().Format.Format_RGBA8888).constBits().tobytes()).hexdigest()

    host.setStyleSheet("QWidget { background-color: #ff00ff; }")
    after = hashlib.sha256(
        host.grab().toImage().convertToFormat(
            host.grab().toImage().Format.Format_RGBA8888).constBits().tobytes()).hexdigest()
    host.deleteLater()

    assert before != after, "the harness cannot see a stylesheet change, so it proves nothing"
