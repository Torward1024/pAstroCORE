"""One palette, and a window with nothing left unstyled (U1).

The failure this guards against is the one a user reported: *part* of an application is themed,
and the rest is the platform's default painted white. A half-styled window looks broken, where
an unstyled one merely looks plain -- so what is checked here is coverage as much as colour.
"""
import pathlib
import re

import pytest

from pastrocore import theme

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORMS = ROOT / "pastrocore" / "gui_pyside"
GUI = ROOT / "pastrocore" / "gui"

#: Widgets that carry no appearance of their own: they are layouts, or a window's frame.
NOT_DRAWN = {"QWidget", "QDialog", "QMainWindow", "QHBoxLayout", "QVBoxLayout", "QGridLayout",
             "QFormLayout", "QStackedLayout", "QSpacerItem", "QAction", "QButtonGroup",
             "QFrame", "QSplitter", "QScrollArea", "QTableWidget", "QTreeWidget", "QListView"}


def classes_used() -> set:
    """Every Qt widget class the forms build, found rather than listed."""
    used = set()
    for form in FORMS.glob("*.ui"):
        used |= set(re.findall(r'class="(Q[A-Za-z]+)"', form.read_text(encoding="utf-8")))
    # The ones no form mentions because the code builds them: menus, calendars, tooltips.
    for module in GUI.glob("p_*.py"):
        used |= set(re.findall(r"\b(Q(?:Menu|CalendarWidget|ToolTip|ProgressBar|ToolButton|"
                               r"TreeView|StatusBar|ScrollBar)[A-Za-z]*)\b",
                               module.read_text(encoding="utf-8")))
    return used


def selectors(sheet: str) -> str:
    """Return the sheet's selectors alone, so a colour is never mistaken for a rule."""
    without_comments = re.sub(r"/\*.*?\*/", " ", sheet, flags=re.S)
    return "\n".join(block.rsplit("}", 1)[-1] for block in without_comments.split("{"))


@pytest.mark.parametrize("name", theme.THEMES)
def test_every_widget_the_application_builds_is_styled(name):
    """What the user asked for: no element left in the platform's default, painted white."""
    sheet = theme.stylesheet(name, "/glyphs")
    rules = selectors(sheet)

    missing = sorted(widget for widget in classes_used() - NOT_DRAWN
                     if not re.search(rf"\b{widget}\b", rules))

    assert not missing, f"nothing in the '{name}' theme styles {missing}"


@pytest.mark.parametrize("name", theme.THEMES)
def test_the_parts_qt_draws_itself_are_given_a_picture(name):
    """A spin box's arrow, a checkbox's tick and a calendar's month arrows are drawn by the
    platform unless the sheet hands over a picture -- which is how a themed window keeps a green
    arrow on its calendar."""
    sheet = theme.stylesheet(name, "/glyphs")
    wanted = set(re.findall(r"url\(/glyphs/([a-z-]+)\.svg\)", sheet))
    drawn = set(theme.glyphs(name))

    assert wanted, "the sheet asks for no pictures at all"
    assert wanted <= drawn, f"the '{name}' sheet asks for {sorted(wanted - drawn)}, which nothing draws"
    for svg in theme.glyphs(name).values():
        assert svg.startswith("<svg") and "stroke=\"#" in svg


@pytest.mark.parametrize("name", theme.THEMES)
def test_a_theme_leaves_no_token_unfilled(name):
    """A `{token}` reaching Qt is a rule Qt drops on the floor, silently."""
    sheet = theme.stylesheet(name, "/glyphs")

    left = re.findall(r"\{[a-z_]+\}", sheet)
    assert not left, f"the '{name}' sheet still holds {sorted(set(left))}"
    assert sheet.count("{") == sheet.count("}"), "a rule was left open"


@pytest.mark.parametrize("name", theme.THEMES)
def test_both_themes_hold_the_same_tokens(name):
    """A token that exists in one theme and not the other is a rule that works in one theme."""
    assert set(theme.PALETTES[name]) == set(theme.PALETTES["light"])
    assert set(theme.plot_style(name)) == set(theme.plot_style("light"))
    assert len(theme.SERIES[name]) == len(theme.SERIES["light"]) >= 8


def contrast(one: str, other: str) -> float:
    """The WCAG contrast ratio between two `#rrggbb` colours."""
    def luminance(colour: str) -> float:
        channels = [int(colour[index:index + 2], 16) / 255.0 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                  for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = luminance(one), luminance(other)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("name", theme.THEMES)
def test_text_can_be_read_against_what_it_stands_on(name):
    """Measured rather than eyeballed. A dark theme is easy to draw and easy to make unreadable."""
    palette = theme.PALETTES[name]
    # Text, including the colours a status line says things in: 4.5:1 is what is readable.
    readable = [("text", "bg"), ("text", "surface"), ("text_strong", "bg"), ("text_dim", "bg"),
                ("text_dim", "chrome"), ("text_strong", "accent_soft"), ("accent_text", "accent"),
                ("tooltip_text", "tooltip_bg"), ("plot_text", "plot_panel"),
                ("ok", "chrome"), ("warn", "chrome"), ("error", "chrome")]
    for ink, under in readable:
        ratio = contrast(palette[ink], palette[under])
        assert ratio >= 4.5, f"'{name}': {ink} on {under} is {ratio:.1f}:1, and 4.5 is readable"

    # A control a person aims at -- a filled button, a focused border -- is 3:1.
    for ink, under in (("accent", "bg"), ("accent", "chrome"), ("accent", "input")):
        ratio = contrast(palette[ink], palette[under])
        assert ratio >= 3.0, f"'{name}': {ink} on {under} is {ratio:.1f}:1, and 3.0 is visible"

    # A separator and a scrollbar's handle are meant to be quiet, but they are not meant to
    # vanish: a table with invisible gridlines is a table nobody can read a row off.
    for ink, under in (("line", "bg"), ("line_soft", "bg"), ("handle", "bg"),
                       ("accent_soft", "bg"), ("accent_line", "accent_soft")):
        ratio = contrast(palette[ink], palette[under])
        assert ratio >= 1.15, f"'{name}': {ink} on {under} is {ratio:.2f}:1 -- it is not there"


@pytest.mark.parametrize("name", theme.THEMES)
def test_the_plots_stand_on_the_same_palette_as_the_window(name):
    """A white rectangle in a dark window is what happens when the two are set separately."""
    palette = theme.PALETTES[name]
    style = theme.plot_style(name)

    assert style["figure"]["facecolor"] == palette["plot_bg"]
    assert style["axes"]["facecolor"] == palette["plot_panel"]
    assert style["text"]["color"] == palette["plot_text"]
    assert style["colors"][0] == theme.SERIES[name][0]


def test_the_theme_asked_for_is_the_theme_used():
    assert theme.resolve("light", system_is_dark=True) == "light"
    assert theme.resolve("dark", system_is_dark=False) == "dark"
    assert theme.resolve("system", system_is_dark=True) == "dark"
    assert theme.resolve("system", system_is_dark=False) == "light"
    # A settings file is a file a person may edit.
    assert theme.resolve("chartreuse", system_is_dark=True) == "dark"


def test_the_glyphs_are_written_where_the_sheet_looks_for_them(tmp_path, monkeypatch):
    from pastrocore.gui import styling

    monkeypatch.setattr("pastrocore.base.scratch.data_home", lambda: tmp_path)
    where = styling.write_glyphs("dark")

    assert where and pathlib.Path(where).is_dir()
    written = {path.stem for path in pathlib.Path(where).glob("*.svg")}
    assert written == set(theme.glyphs("dark"))

    sheet = styling.load_stylesheet("dark")
    for name in re.findall(r"url\(([^)]+\.svg)\)", sheet):
        if name.startswith(":/"):
            continue                                    # a shipped icon, in the resource file
        assert pathlib.Path(name).is_file(), f"the sheet points at {name}, which is not there"


def test_a_user_s_own_stylesheet_still_wins(tmp_path, monkeypatch):
    from pastrocore.gui import styling

    monkeypatch.setattr("pastrocore.base.scratch.data_home", lambda: tmp_path)
    (tmp_path / styling.USER_STYLESHEET).write_text("QWidget { background: pink; }",
                                                    encoding="utf-8")

    assert styling.load_stylesheet("dark") == "QWidget { background: pink; }"
