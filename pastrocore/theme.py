# pastrocore/theme.py
"""One palette, from which the window and the plots are both drawn (U1).

Before this, "what does this application look like" had two answers that did not know about
each other: `gui/pastrocore.qss`, assembled out of the 224 inline `styleSheet` properties it
replaced -- with `QMenuBar`, `QMenu`, `QTableView` and `QLineEdit` each written twice, saying
different things -- and a `_style_config` inside the visualizer holding its own colours. A
colour was changed in two places, or in one and a half.

**Everything here is a token.** A palette per theme, one type scale, one set of spacings and
radii; the stylesheet and the matplotlib style are both generated from them, so a colour is
changed once. Nothing in this module imports Qt or matplotlib: it produces a string and a
mapping, which is what makes it readable from the backend as well as from the interface.

**Two themes, and the system's choice honoured.** `resolve` turns what the settings say --
`system`, `light` or `dark` -- into one of the two, so every caller works in terms of a theme
that exists.
"""
from typing import Any, Dict

#: What a theme is called in the settings, and what each means.
CHOICES = ("system", "light", "dark")

#: The themes themselves.
THEMES = ("light", "dark")

#: Type, spacing and radii: the same in both themes, because a palette is what changes when the
#: lights go out, not how far apart things stand.
SHAPE = {
    # One family, one scale. The sizes are point-free: a stylesheet in points and a form in
    # pixels disagree about what "12" means as soon as the display scales.
    "font": '"Segoe UI", "Inter", "Noto Sans", sans-serif',
    "font_mono": '"Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace',
    "size_small": "11px",
    "size": "13px",
    "size_large": "15px",
    "size_title": "17px",
    "radius": "6px",
    "radius_small": "4px",
    "radius_large": "8px",
    "pad_x": "8px",
    "pad_y": "4px",
    "gap": "6px",
    # **The content's height, not the control's.** Qt adds the padding and the border to this,
    # so a token of 28 made every text box 40 pixels tall and a telescope editor grew past the
    # screen. With the padding this comes to 32, which is what a spin box asks for as its
    # minimum -- below it `test_form_layout` reports a control clipped by its own frame.
    "control": "22px",
    "scrollbar": "12px",
    "border": "1px",
}

#: The colours, by theme. A token is named for what it is *for*, not for what it looks like:
#: `chrome` stays the bars and headers whether it is near-white or near-black.
PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#ffffff",
        "surface": "#ffffff",
        "chrome": "#f3f5f7",
        "raised": "#fbfcfd",
        "line": "#d6dbe1",
        "line_soft": "#e8ecf0",
        "input": "#ffffff",
        "input_disabled": "#f1f3f5",
        "text": "#2b3440",
        "text_strong": "#16202b",
        "text_dim": "#5c6875",
        "text_disabled": "#9aa5b1",
        "accent": "#1f6feb",
        "accent_hover": "#1a60cd",
        "accent_pressed": "#154faa",
        "accent_soft": "#e5efff",
        "accent_line": "#a9c9ff",
        "accent_text": "#ffffff",
        "ok": "#1a7f37",
        "warn": "#8a5a00",
        "error": "#c0392b",
        "handle": "#c2cad3",
        "handle_hover": "#a7b2bf",
        "tooltip_bg": "#16202b",
        "tooltip_text": "#f4f7fa",
        "shadow": "rgba(16, 24, 32, 0.10)",
        # The plots stand on the same palette. `plot_bg` is the figure, `plot_panel` the axes.
        "plot_bg": "#ffffff",
        "plot_panel": "#ffffff",
        "plot_grid": "#e3e8ee",
        "plot_text": "#2b3440",
        "plot_frame": "#c2cad3",
    },
    "dark": {
        "bg": "#171c22",
        "surface": "#1b2129",
        "chrome": "#1f262e",
        "raised": "#232b34",
        "line": "#2f3945",
        "line_soft": "#262f38",
        "input": "#131920",
        "input_disabled": "#1b2028",
        "text": "#c6d0da",
        "text_strong": "#eef3f8",
        "text_dim": "#8b98a6",
        "text_disabled": "#5b6672",
        "accent": "#4b93ff",
        "accent_hover": "#63a2ff",
        "accent_pressed": "#3b7fe0",
        "accent_soft": "#1b2b44",
        "accent_line": "#2f4e7d",
        "accent_text": "#0b1016",
        "ok": "#46c06a",
        "warn": "#d9a441",
        "error": "#f0715f",
        "handle": "#3a4652",
        "handle_hover": "#4b5a69",
        "tooltip_bg": "#eef3f8",
        "tooltip_text": "#16202b",
        "shadow": "rgba(0, 0, 0, 0.45)",
        "plot_bg": "#171c22",
        "plot_panel": "#1b2129",
        "plot_grid": "#2f3945",
        "plot_text": "#c6d0da",
        "plot_frame": "#3a4652",
    },
}

#: What a plot draws its series in, by theme. Eight, distinguishable in order, and the first
#: four are distinguishable in greyscale as well -- a plot is printed as often as it is read.
SERIES = {
    "light": ["#1f6feb", "#1a7f37", "#c0392b", "#8250df", "#0e8a9e", "#b8860b", "#d1417c",
              "#4b5a69"],
    "dark": ["#4b93ff", "#46c06a", "#f0715f", "#b083f0", "#3fc2d6", "#d9a441", "#f57bb0",
             "#96a3b1"],
}

#: What a sequential colour map runs through, poor to good, in each theme. Red is the poor end
#: throughout: a baseline that hears nothing is what a reader looks for.
RAMP = {
    "light": ["#a01b0b", "#e4572e", "#f2b705", "#7cb518", "#1a7f37", "#0e7c86", "#1f6feb"],
    "dark": ["#c0392b", "#f0715f", "#d9a441", "#8fd14f", "#46c06a", "#3fc2d6", "#4b93ff"],
}


#: The glyphs Qt draws itself unless it is given a picture: the arrows of a spin box, the tick
#: in a checkbox, the month arrows of a calendar, the branches of a tree. Qt's own are the
#: platform's -- a green arrow on the calendar, a grey square where a spin box's arrow should be
#: -- so they are the one part of a themed window that stays unthemed. Drawn here from the same
#: tokens, so they follow the palette like everything else.
GLYPHS = {
    "arrow-down": '<path d="M2.5 4l2.5 2.5L7.5 4"/>',
    "arrow-up": '<path d="M2.5 6L5 3.5 7.5 6"/>',
    "chevron-left": '<path d="M6.25 2.5L3.5 5l2.75 2.5"/>',
    "chevron-right": '<path d="M3.75 2.5L6.5 5l-2.75 2.5"/>',
    "branch-closed": '<path d="M3.75 2.5L6.5 5l-2.75 2.5"/>',
    "branch-open": '<path d="M2.5 3.75L5 6.5l2.5-2.75"/>',
    "check": '<path d="M2 5.2l2.1 2.1L8 3.2"/>',
    "close": '<path d="M3 3l4 4M7 3l-4 4"/>',
}

#: What each glyph is drawn in, by the token it takes its colour from.
GLYPH_COLOURS = {"": "text_dim", "-accent": "accent", "-on": "accent_text",
                 "-dim": "text_disabled"}

_GLYPH = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" width="10" height="10">'
          '<g fill="none" stroke="{colour}" stroke-width="1.5" stroke-linecap="round" '
          'stroke-linejoin="round">{path}</g></svg>')


def glyphs(theme: str) -> Dict[str, str]:
    """Return the small glyphs a themed window needs, as SVG text.

    Args:
        theme (str): `light` or `dark`.

    Returns:
        Dict[str, str]: File name (without a suffix) mapped to the SVG that draws it -- one per
            glyph and colour, because a style sheet cannot recolour a picture on hover.
    """
    palette = PALETTES[theme]
    drawn = {}
    for name, path in GLYPHS.items():
        for suffix, token in GLYPH_COLOURS.items():
            drawn[f"{name}{suffix}"] = _GLYPH.format(colour=palette[token], path=path)
    return drawn


def tokens(theme: str, assets: str = "") -> Dict[str, str]:
    """Return everything a stylesheet is written in, for one theme.

    Args:
        theme (str): `light` or `dark`.
        assets (str): Where the glyphs of `glyphs()` have been written, as a path a style sheet
            can read -- forward slashes, no trailing one. Empty when they have not been written,
            which leaves Qt to draw its own.

    Returns:
        Dict[str, str]: The palette, the shape tokens and where the glyphs are.

    Raises:
        KeyError: For a theme that does not exist, which is a typo rather than a case to handle.
    """
    return {**SHAPE, **PALETTES[theme], "assets": assets.replace("\\", "/").rstrip("/")}


def resolve(choice: str, system_is_dark: bool = False) -> str:
    """Return the theme to use, from what the settings say and what the system is set to.

    Args:
        choice (str): `system`, `light` or `dark`. Anything else is taken as `system`, because a
            settings file is a file a person may edit.
        system_is_dark (bool): What the desktop is set to, where that can be told.

    Returns:
        str: `light` or `dark`.
    """
    if choice in THEMES:
        return choice
    return "dark" if system_is_dark else "light"


def plot_style(theme: str) -> Dict[str, Any]:
    """Return the visualizer's style configuration, drawn from the same palette as the window.

    Args:
        theme (str): `light` or `dark`.

    Returns:
        Dict[str, Any]: What `ScheduleVisualizer.set_style_config` takes, so a plot on a dark
            window is a dark plot rather than a white rectangle in it.
    """
    palette = PALETTES[theme]
    size = int(SHAPE["size"].removesuffix("px"))
    return {
        "figure": {"facecolor": palette["plot_bg"]},
        "axes": {"facecolor": palette["plot_panel"], "edgecolor": palette["plot_frame"],
                 "labelcolor": palette["plot_text"], "grid": True},
        "grid": {"color": palette["plot_grid"], "linestyle": "--", "linewidth": 0.5},
        "text": {"color": palette["plot_text"]},
        "xtick": {"color": palette["plot_text"], "labelsize": size},
        "ytick": {"color": palette["plot_text"], "labelsize": size},
        "colors": list(SERIES[theme]),
        "intersection_color": palette["warn"],
    }


#: The stylesheet, in tokens. **Every widget class the application uses has a rule here** --
#: including the ones nobody writes into a form and everybody sees: scrollbars, the buttons of a
#: spin box, the calendar a date editor drops down, a progress bar, a tooltip. Half a styled
#: application is worse than none, because the unstyled half looks broken rather than plain.
TEMPLATE = """
/* ---- the surface everything stands on ------------------------------------------------- */
QWidget {{
    background-color: {bg};
    color: {text};
    font-family: {font};
    font-size: {size};
}}
QDialog, QMainWindow {{ background-color: {bg}; }}
QWidget:disabled {{ color: {text_disabled}; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {line}; background-color: {line}; }}
QSplitter::handle {{ background-color: {line_soft}; }}
QSplitter::handle:hover {{ background-color: {accent_line}; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
QStackedWidget, QScrollArea {{ background-color: {bg}; border: none; }}
QScrollArea > QWidget > QWidget {{ background-color: {bg}; }}

/* ---- text ------------------------------------------------------------------------------ */
QLabel {{ background: transparent; color: {text}; padding: 1px; }}
QLabel[role="title"] {{ color: {text_strong}; font-size: {size_title}; font-weight: 600; }}
QLabel[role="heading"] {{ color: {text_strong}; font-size: {size_large}; font-weight: 600; }}
QLabel[role="dim"] {{ color: {text_dim}; font-size: {size_small}; }}
QLabel[role="ok"] {{ color: {ok}; }}
QLabel[role="warning"] {{ color: {warn}; }}
QLabel[role="error"] {{ color: {error}; }}
QLabel[role="mono"] {{ font-family: {font_mono}; }}
QLabel:disabled {{ color: {text_disabled}; }}

/* ---- what is typed into --------------------------------------------------------------- */
/* **No `min-height` on what Qt sizes itself.** A spin box asks for room for its two buttons on
   top of its text, and a style sheet that sets a minimum height sets the *content's*, so Qt
   asks for three pixels more than the layout then gives it -- which `test_form_layout` reports,
   correctly, as a control clipped by its own frame. The padding sets the height here. */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit,
QDateEdit, QTimeEdit {{
    background-color: {input};
    color: {text_strong};
    border: {border} solid {line};
    border-radius: {radius_small};
    padding: {pad_y} {pad_x};
    selection-background-color: {accent};
    selection-color: {accent_text};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QComboBox:hover, QDateTimeEdit:hover, QDateEdit:hover, QTimeEdit:hover {{
    border-color: {accent_line};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QDateTimeEdit:focus, QDateEdit:focus, QTimeEdit:focus {{
    border-color: {accent};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QComboBox:disabled, QDateTimeEdit:disabled, QDateEdit:disabled,
QTimeEdit:disabled {{
    background-color: {input_disabled};
    color: {text_disabled};
    border-color: {line_soft};
}}
QLineEdit[readOnly="true"] {{ background-color: {input_disabled}; color: {text_dim}; }}

/* The little buttons of a spin box and a date editor, which no form mentions and everybody
   clicks. Arrows are drawn as borders rather than as images, so they take the palette. */
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateTimeEdit::up-button, QDateEdit::up-button,
QTimeEdit::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button,
QDateTimeEdit::down-button, QDateEdit::down-button, QTimeEdit::down-button {{
    background-color: transparent;
    border: none;
    width: 16px;
    margin-right: 2px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateTimeEdit::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover,
QDateTimeEdit::down-button:hover {{ background-color: {accent_soft}; border-radius: 3px; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateTimeEdit::up-arrow, QDateEdit::up-arrow,
QTimeEdit::up-arrow {{ image: url({assets}/arrow-up.svg); width: 10px; height: 10px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateTimeEdit::down-arrow,
QDateEdit::down-arrow, QTimeEdit::down-arrow {{ image: url({assets}/arrow-down.svg);
                                                width: 10px; height: 10px; }}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover,
QDateTimeEdit::up-arrow:hover {{ image: url({assets}/arrow-up-accent.svg); }}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover,
QDateTimeEdit::down-arrow:hover {{ image: url({assets}/arrow-down-accent.svg); }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::up-arrow:off, QDoubleSpinBox::up-arrow:off {{ image: url({assets}/arrow-up-dim.svg); }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled,
QSpinBox::down-arrow:off, QDoubleSpinBox::down-arrow:off {{ image: url({assets}/arrow-down-dim.svg); }}

QComboBox::drop-down, QDateTimeEdit::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{ image: url({assets}/arrow-down.svg); width: 10px; height: 10px;
                         margin-right: 6px; }}
QComboBox::down-arrow:on, QComboBox::down-arrow:hover {{
    image: url({assets}/arrow-down-accent.svg); }}
QComboBox::down-arrow:disabled {{ image: url({assets}/arrow-down-dim.svg); }}
QComboBox QAbstractItemView {{
    background-color: {raised};
    color: {text};
    border: {border} solid {line};
    border-radius: {radius_small};
    padding: 2px;
    outline: none;
    selection-background-color: {accent_soft};
    selection-color: {text_strong};
}}

/* ---- buttons ---------------------------------------------------------------------------- */
QPushButton {{
    background-color: {chrome};
    color: {text_strong};
    border: {border} solid {line};
    border-radius: {radius};
    padding: {pad_y} 16px;
    min-height: {control};
}}
QPushButton:hover {{ background-color: {raised}; border-color: {accent_line}; }}
QPushButton:pressed {{ background-color: {accent_soft}; border-color: {accent}; }}
QPushButton:focus {{ border-color: {accent}; }}
QPushButton:disabled {{ background-color: {input_disabled}; color: {text_disabled};
                        border-color: {line_soft}; }}
QPushButton[role="primary"], QPushButton:default {{
    background-color: {accent};
    color: {accent_text};
    border-color: {accent};
    font-weight: 600;
}}
QPushButton[role="primary"]:hover, QPushButton:default:hover {{ background-color: {accent_hover};
                                                                border-color: {accent_hover}; }}
QPushButton[role="primary"]:pressed, QPushButton:default:pressed {{
    background-color: {accent_pressed}; border-color: {accent_pressed}; }}
QPushButton[role="primary"]:disabled {{ background-color: {line}; border-color: {line};
                                        color: {text_disabled}; }}
QPushButton[role="danger"] {{ color: {error}; border-color: {line}; }}
QPushButton[role="danger"]:hover {{ background-color: {error}; color: {accent_text};
                                    border-color: {error}; }}
QPushButton[role="quiet"] {{ background: transparent; border-color: transparent;
                             color: {accent}; }}
QPushButton[role="quiet"]:hover {{ background-color: {accent_soft}; }}
QDialogButtonBox QPushButton {{ min-width: 84px; }}

/* ---- ticks and radios -------------------------------------------------------------------- */
QCheckBox, QRadioButton {{ background: transparent; color: {text}; spacing: {gap};
                           padding: 2px; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {text_disabled}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px; height: 15px;
    background-color: {input};
    border: {border} solid {line};
}}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent};
                                image: url({assets}/check-on.svg); }}
QCheckBox::indicator:checked:disabled {{ background-color: {line}; border-color: {line}; }}
QRadioButton::indicator:checked {{ background-color: {accent}; border: 4px solid {input};
                                   outline: {border} solid {accent}; }}
QCheckBox::indicator:indeterminate {{ background-color: {accent_soft};
                                      border-color: {accent}; }}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: {input_disabled}; border-color: {line_soft}; }}

/* ---- lists, tables and trees -------------------------------------------------------------- */
QListWidget, QListView, QTableView, QTableWidget, QTreeView, QTreeWidget, QColumnView {{
    background-color: {surface};
    alternate-background-color: {chrome};
    color: {text};
    border: {border} solid {line};
    border-radius: {radius};
    gridline-color: {line_soft};
    outline: none;
    selection-background-color: {accent_soft};
    selection-color: {text_strong};
}}
QListWidget::item, QListView::item, QTreeView::item, QTableView::item {{
    padding: 4px 6px;
    border: none;
}}
QListWidget::item:hover, QListView::item:hover, QTreeView::item:hover,
QTableView::item:hover {{ background-color: {line_soft}; }}
QListWidget::item:selected, QListView::item:selected, QTreeView::item:selected,
QTableView::item:selected {{ background-color: {accent_soft}; color: {text_strong}; }}
QTreeView::branch {{ background: transparent; }}
QTreeView::branch:has-children:!has-siblings:closed, QTreeView::branch:closed:has-children:has-siblings {{
    image: url({assets}/branch-closed.svg); }}
QTreeView::branch:open:has-children:!has-siblings, QTreeView::branch:open:has-children:has-siblings {{
    image: url({assets}/branch-open.svg); }}
QHeaderView {{ background-color: {chrome}; border: none; }}
QHeaderView::section {{
    background-color: {chrome};
    color: {text_dim};
    padding: 6px 8px;
    border: none;
    border-bottom: {border} solid {line};
    border-right: {border} solid {line_soft};
    font-weight: 600;
}}
QHeaderView::section:hover {{ color: {text_strong}; background-color: {raised}; }}
QHeaderView::section:vertical {{ border-right: {border} solid {line}; }}
QHeaderView::down-arrow, QHeaderView::up-arrow {{ width: 8px; height: 8px; }}
QTableCornerButton::section {{ background-color: {chrome}; border: none;
                               border-bottom: {border} solid {line}; }}

/* ---- tabs ---------------------------------------------------------------------------------- */
QTabWidget::pane {{ background-color: {bg}; border: {border} solid {line};
                    border-radius: {radius}; top: -1px; }}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background-color: {chrome};
    color: {text_dim};
    border: {border} solid {line};
    border-bottom: none;
    border-top-left-radius: {radius};
    border-top-right-radius: {radius};
    padding: 6px 14px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {text_strong}; background-color: {raised}; }}
QTabBar::tab:selected {{ background-color: {bg}; color: {text_strong}; font-weight: 600;
                         border-bottom: 2px solid {accent}; }}
QTabBar::tab:disabled {{ color: {text_disabled}; }}
QTabBar::close-button {{ image: url(:/icons/remove_icon.svg); subcontrol-position: right;
                         margin: 2px; }}

/* ---- groups ---------------------------------------------------------------------------------- */
QGroupBox {{
    background-color: {bg};
    border: {border} solid {line};
    border-radius: {radius};
    margin-top: 12px;
    padding: 10px;
    font-weight: 600;
    color: {text_strong};
}}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px;
                    padding: 0 6px; color: {text_dim}; }}

/* ---- the menus and the toolbar ------------------------------------------------------------- */
QMenuBar {{ background-color: {chrome}; color: {text}; border-bottom: {border} solid {line}; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; border-radius: {radius_small}; }}
QMenuBar::item:selected {{ background-color: {accent_soft}; color: {text_strong}; }}
QMenu {{ background-color: {raised}; color: {text}; border: {border} solid {line};
         border-radius: {radius}; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 28px; border-radius: {radius_small}; }}
QMenu::item:selected {{ background-color: {accent_soft}; color: {text_strong}; }}
QMenu::item:disabled {{ color: {text_disabled}; }}
QMenu::separator {{ height: {border}; background-color: {line_soft}; margin: 4px 8px; }}
QMenu::icon {{ padding-left: 8px; }}
QToolBar {{ background-color: {chrome}; border-bottom: {border} solid {line};
            padding: 4px; spacing: 4px; }}
QToolBar::separator {{ width: {border}; background-color: {line}; margin: 4px 6px; }}
QToolButton {{ background: transparent; color: {text}; border: {border} solid transparent;
               border-radius: {radius_small}; padding: 5px 8px; }}
QToolButton:hover {{ background-color: {raised}; border-color: {line}; }}
QToolButton:pressed, QToolButton:checked {{ background-color: {accent_soft};
                                            border-color: {accent_line}; color: {text_strong}; }}
QToolButton:disabled {{ color: {text_disabled}; }}
QToolButton::menu-indicator {{ image: none; }}
QStatusBar {{ background-color: {chrome}; color: {text_dim};
              border-top: {border} solid {line}; }}
QStatusBar::item {{ border: none; }}
QDockWidget {{ background-color: {bg}; color: {text}; titlebar-close-icon: url(:/icons/remove_icon.svg); }}
QDockWidget::title {{ background-color: {chrome}; padding: 6px; border-bottom: {border} solid {line}; }}

/* ---- scrollbars ---------------------------------------------------------------------------- */
QScrollBar:vertical {{ background: transparent; width: {scrollbar}; margin: 0; border: none; }}
QScrollBar:horizontal {{ background: transparent; height: {scrollbar}; margin: 0; border: none; }}
QScrollBar::handle:vertical {{ background-color: {handle}; border-radius: 5px; min-height: 28px;
                               margin: 2px; }}
QScrollBar::handle:horizontal {{ background-color: {handle}; border-radius: 5px; min-width: 28px;
                                 margin: 2px; }}
QScrollBar::handle:hover {{ background-color: {handle_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; background: none;
                                              border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- progress, sliders and the rest ---------------------------------------------------------- */
QProgressBar {{
    background-color: {line_soft};
    color: {text_strong};
    border: none;
    border-radius: {radius_small};
    text-align: center;
    min-height: 18px;
}}
QProgressBar::chunk {{ background-color: {accent}; border-radius: {radius_small}; }}
QSlider::groove:horizontal {{ background-color: {line_soft}; height: 4px; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background-color: {accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background-color: {accent}; border: 2px solid {bg};
                              width: 14px; height: 14px; margin: -6px 0; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ background-color: {accent_hover}; }}
QToolTip {{ background-color: {tooltip_bg}; color: {tooltip_text}; border: none;
            border-radius: {radius_small}; padding: 5px 8px; }}

/* ---- the calendar a date editor drops down ---------------------------------------------------- */
QCalendarWidget QWidget {{ alternate-background-color: {chrome}; background-color: {surface};
                           color: {text}; }}
QCalendarWidget QToolButton {{ background-color: {chrome}; color: {text_strong};
                               border-radius: {radius_small}; padding: 4px 8px; }}
QCalendarWidget QToolButton:hover {{ background-color: {accent_soft}; }}
QCalendarWidget QMenu {{ background-color: {raised}; }}
QCalendarWidget QSpinBox {{ min-height: 22px; }}
QCalendarWidget QAbstractItemView {{
    background-color: {surface};
    color: {text};
    outline: none;
    selection-background-color: {accent};
    selection-color: {accent_text};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {text_disabled}; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color: {chrome};
                                                     border-bottom: {border} solid {line}; }}
/* Qt's own month arrows are the platform's -- bright green on every theme. */
QCalendarWidget QToolButton#qt_calendar_prevmonth {{ qproperty-icon: url({assets}/chevron-left.svg);
                                                     qproperty-iconSize: 14px 14px; }}
QCalendarWidget QToolButton#qt_calendar_nextmonth {{ qproperty-icon: url({assets}/chevron-right.svg);
                                                     qproperty-iconSize: 14px 14px; }}
QCalendarWidget QToolButton::menu-indicator {{ image: url({assets}/arrow-down.svg);
                                               subcontrol-position: right center; }}

/* ---- what the window itself names ------------------------------------------------------------- */
QLabel#statusMessage {{ color: {text_dim}; font-size: {size_small}; }}
QLabel#statusMessage[level="warning"] {{ color: {warn}; }}
QLabel#statusMessage[level="error"] {{ color: {error}; }}
QLabel#statusMemory {{ color: {text_dim}; font-family: {font_mono}; font-size: {size_small}; }}
"""


def stylesheet(theme: str, assets: str = "") -> str:
    """Return the whole stylesheet for one theme.

    Args:
        theme (str): `light` or `dark`.
        assets (str): Where `glyphs()` have been written, for the rules that need a picture.

    Returns:
        str: Qt style sheet text, with every token filled in.

    Notes:
        - Generated rather than kept as a file, so a colour is changed in one place and both
          themes follow. What a user puts beside their settings still replaces it whole.
    """
    return TEMPLATE.format(**tokens(theme, assets))
