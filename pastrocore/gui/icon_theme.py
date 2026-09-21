# pastrocore/gui/icon_theme.py
"""The icon set drawn in the palette's colour, whichever theme is on (U1).

The set is monochrome by design: every icon states its stroke once, on the root element, so
"what colour are the icons" has one answer per file and `test_icons` keeps it that way. What it
does not have is a second colour for a dark window, where a stroke chosen against white is a
smudge.

**Drawn, not shipped twice.** An icon is rendered and filled with the theme's colour, which for
a monochrome drawing is the same picture in another ink. The forms keep referring to
`:/icons/...` -- the resource -- so they still show their icons in Designer, which is where they
are edited.

**Including the windows opened later.** A dialog built after the theme changed would otherwise
carry the colour that was current when its form was generated, so an application-wide filter
catches each window as it is shown and paints what it holds.
"""
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter
from PySide6.QtWidgets import QAbstractButton, QApplication, QWidget
from msb_arch.utils.logging_setup import logger

#: The sizes an icon is drawn at. An SVG has no sizes of its own, and Qt picks the nearest one
#: it was given -- so these are what a toolbar, a menu, a button and a high-resolution display
#: ask for.
SIZES = (16, 20, 24, 32, 48)

#: The property a widget is marked with once its icons are in a theme's colour, so showing a
#: dialog twice does not redraw them twice.
MARK = "_icon_theme"


def retint(icon: QIcon, colour: str) -> QIcon:
    """Return the same drawing in another ink.

    Args:
        icon (QIcon): A monochrome icon.
        colour (str): What to draw it in, as `#rrggbb`.

    Returns:
        QIcon: The icon, at every size in `SIZES`, filled with the colour. The original when it
            is empty -- there is nothing to recolour and nothing to lose.
    """
    if icon.isNull():
        return icon
    ink = QColor(colour)
    tinted = QIcon()
    for size in SIZES:
        pixmap = icon.pixmap(QSize(size, size))
        if pixmap.isNull():
            continue
        # `SourceIn` keeps the shape and replaces what it is drawn with, which is what a
        # monochrome icon is: an alpha channel.
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), ink)
        painter.end()
        tinted.addPixmap(pixmap)
    return tinted if tinted.availableSizes() else icon


def paint(widget: QWidget, colour: str) -> int:
    """Draw every icon a widget holds in one colour.

    Args:
        widget (QWidget): A window, a dialog or a tab.
        colour (str): What to draw them in.

    Returns:
        int: How many icons were redrawn.

    Notes:
        - Actions and buttons, which is what carries an icon here: a menu, a toolbar, a tab's
          close button, the buttons of a dialog.
        - Marked once done, so a dialog shown a second time is not repainted.
    """
    painted = 0
    for action in widget.findChildren(QAction):
        if not action.icon().isNull():
            action.setIcon(retint(action.icon(), colour))
            painted += 1
    for button in widget.findChildren(QAbstractButton):
        if not button.icon().isNull():
            button.setIcon(retint(button.icon(), colour))
            painted += 1
    if not widget.windowIcon().isNull():
        widget.setWindowIcon(retint(widget.windowIcon(), colour))
    widget.setProperty(MARK, colour)
    return painted


class IconTheme(QObject):
    """Paints each window's icons as it is shown, and repaints what is open when the theme changes.

    Args:
        colour (str): The colour to draw icons in.

    Notes:
        - One filter on the application rather than a call in every dialog: a dialog that
          forgets the call is a dialog with the other theme's icons, and there are twenty of
          them.
    """

    def __init__(self, colour: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.colour = colour

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget) and watched.isWindow():
            if watched.property(MARK) != self.colour:
                paint(watched, self.colour)
        return False

    def set_colour(self, colour: str) -> None:
        """Take a new colour, and repaint what is already on screen."""
        self.colour = colour
        application = QApplication.instance()
        for window in (application.topLevelWidgets() if application else []):
            if isinstance(window, QWidget) and window.property(MARK) != colour:
                paint(window, colour)


#: The one filter, installed on the application the first time a theme is applied.
_installed: Optional[IconTheme] = None


def apply(colour: str) -> Optional[IconTheme]:
    """Draw the icons in this colour, now and for every window opened afterwards.

    Args:
        colour (str): `#rrggbb` from the palette.

    Returns:
        Optional[IconTheme]: The filter doing it, or None when there is no application to
            install it on -- a headless caller has no icons to paint.
    """
    global _installed

    application = QApplication.instance()
    if application is None:
        return None
    if _installed is None:
        _installed = IconTheme(colour, application)
        application.installEventFilter(_installed)
        logger.debug("Icons will be drawn in %s from now on", colour)
    _installed.set_colour(colour)
    return _installed
