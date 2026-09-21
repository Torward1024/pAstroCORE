"""Every action has an icon, and every icon a form uses is drawn in one style (G10).

An icon set that grows by hand drifts: seven actions had no icon at all, four shared one that meant
something else -- Analyze, both catalogue browsers and the calculation report all showed the
catalogue -- and the ones that existed were drawn in two styles, half of them Illustrator exports
carrying a generator comment, a CSS block and a Cyrillic layer id.

So the style is written down here rather than in a note nobody reads:

- the canvas is 24x24, and the drawing is strokes, not fills;
- one colour, the palette's `icon` token, stated on the root and nowhere else -- which is what
  lets a theme draw the whole set in another ink rather than ship it twice (U1);
- stroke width 2, round caps and joins;
- nothing an editor left behind: no generator comment, no `<style>`, no class attributes.

What must obey it is derived, not listed: every SVG a `.ui` file names. The icons a stylesheet uses
for check marks, arrows and status dots are decoration with their own colours, and are not in it.
"""
import pathlib
import re

import pytest

FORMS = pathlib.Path(__file__).parent.parent / "pastrocore" / "gui_pyside"
ICONS = pathlib.Path(__file__).parent.parent / "pastrocore" / "gui" / "icons"
RESOURCE = ICONS / "icons.qrc"

from pastrocore import theme

#: The set is drawn in the light theme's ink; the dark one is painted from it at runtime.
STROKE = theme.PALETTES["light"]["icon"]


def forms():
    return sorted(FORMS.glob("*.ui"))


def icons_used_by_forms():
    """Every icon file the forms name, and which forms name it."""
    used = {}
    for form in forms():
        for name in re.findall(r":/icons/([\w.\-]+)", form.read_text(encoding="utf-8")):
            used.setdefault(name, []).append(form.name)
    return used


def actions_of(form):
    """Every action a form defines, as (name, text, icon or None)."""
    found = []
    for name, body in re.findall(r'<action name="(\w+)">(.*?)</action>',
                                 form.read_text(encoding="utf-8"), re.S):
        icon = re.search(r"normaloff>:/icons/([\w.\-]+)<", body)
        text = re.search(r'<property name="text">\s*<string>(.*?)</string>', body, re.S)
        found.append((name, text.group(1) if text else name, icon.group(1) if icon else None))
    return found


@pytest.mark.parametrize("form", forms(), ids=lambda form: form.stem)
def test_every_action_has_an_icon(form):
    """A menu of words with gaps where icons should be, and a toolbar cannot be built from it."""
    without = [f"{name} ('{text}')" for name, text, icon in actions_of(form) if not icon]
    assert not without, f"{form.name}: no icon on " + ", ".join(without)


def test_no_two_actions_of_the_main_window_share_an_icon():
    """An icon that means two things means neither. Analyze, the source catalogue, the telescope
    catalogue and the calculation report were one picture between them."""
    window = FORMS / "main_window.ui"
    seen = {}
    for name, text, icon in actions_of(window):
        seen.setdefault(icon, []).append(text)
    shared = {icon: texts for icon, texts in seen.items() if len(texts) > 1}
    assert not shared, "one icon for several actions: " + "; ".join(
        f"{icon}: {', '.join(texts)}" for icon, texts in shared.items())


@pytest.mark.parametrize("icon", sorted(icons_used_by_forms()))
def test_an_icon_a_form_uses_is_drawn_in_the_style(icon):
    """Same size, same colour, same weight -- and nothing an editor left behind."""
    if icon.endswith(".png"):
        pytest.skip(f"{icon} is a picture, not an icon drawn in strokes")
    path = ICONS / icon
    assert path.is_file(), f"{icon} is named by a form and is not here"
    text = path.read_text(encoding="utf-8")

    root = re.search(r"<svg\b[^>]*>", text)
    assert root, f"{icon} has no <svg>"
    root = root.group(0)
    for attribute, value in (("width", "24"), ("height", "24"), ("viewBox", "0 0 24 24"),
                             ("fill", "none"), ("stroke", STROKE), ("stroke-width", "2"),
                             ("stroke-linecap", "round"), ("stroke-linejoin", "round")):
        assert f'{attribute}="{value}"' in root, f"{icon}: the root needs {attribute}=\"{value}\""

    assert "Illustrator" not in text and "<style" not in text, f"{icon} carries an editor's leftovers"
    assert 'class="' not in text, f"{icon} styles itself through classes rather than the root"
    colours = {found.lower() for found in re.findall(r"#[0-9a-fA-F]{3,6}", text)}
    ink = STROKE.lower()
    assert colours <= {ink}, f"{icon} draws in {sorted(colours - {ink})}, not one colour"
    assert not re.search(r'\bstroke="(?!none)', text[text.index(">"):]), (
        f"{icon} states a stroke on a shape; the root states it once, so U1 can recolour the set")


def test_every_icon_here_is_in_the_resource_and_every_one_in_it_is_here():
    """An icon missing from `icons.qrc` is missing at run time, whatever the form says."""
    listed = set(re.findall(r"<file>([\w.\-]+)</file>", RESOURCE.read_text(encoding="utf-8")))
    present = {path.name for path in ICONS.iterdir() if path.suffix in (".svg", ".png")}

    assert listed - present == set(), f"in the resource and not here: {sorted(listed - present)}"
    assert present - listed == set(), f"here and not in the resource: {sorted(present - listed)}"


def test_every_icon_a_form_uses_is_in_the_resource():
    listed = set(re.findall(r"<file>([\w.\-]+)</file>", RESOURCE.read_text(encoding="utf-8")))
    used = icons_used_by_forms()
    missing = {icon: forms for icon, forms in used.items() if icon not in listed}
    assert not missing, f"used by a form and not in the resource: {sorted(missing)}"


@pytest.mark.parametrize("icon", sorted(icons_used_by_forms()))
def test_an_icon_draws_something(qt_application, icon):
    """A file Qt cannot render, or renders empty, is a blank space in the menu -- which is what an
    icon with a broken path looks like, and it looks like nothing else."""
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import QSize

    image = QIcon(str(ICONS / icon)).pixmap(QSize(24, 24)).toImage()
    assert not image.isNull(), f"{icon} did not render"
    painted = sum(1 for y in range(image.height()) for x in range(image.width())
                  if image.pixelColor(x, y).alpha() > 0)
    assert painted > 20, f"{icon} rendered {painted} painted pixels: it is blank"
