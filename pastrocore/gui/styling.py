"""The look of the window: generated from the tokens, with a user's own file still winning.

224 `styleSheet` properties across 24 forms and 131 lines written inline in `app.main` made
"what does this application look like" a question with no answer -- and copying a form was how
a second variant of a rule came to exist, which is why 38 spin boxes were styled two different
ways. `pastrocore.qss` answered that, and then held the same rule twice itself: `QMenuBar`,
`QMenu`, `QTableView` and `QLineEdit` were each written out in two places, saying different
things.

**Nothing is written by hand now** (U1). `pastrocore.theme` holds the tokens; this module turns
them into the sheet Qt is given, and writes out the handful of pictures a style sheet cannot
draw for itself -- the arrows of a spin box, the tick of a checkbox, the month arrows of a
calendar. A user may still keep their own sheet beside their settings, and it replaces ours
whole.
"""
import pathlib

from msb_arch.utils.logging_setup import logger

from pastrocore import theme

#: What a user's own stylesheet is called, if they keep one. Looked for beside the settings
#: rather than beside the installed package, which may be read-only and is replaced on upgrade.
USER_STYLESHEET = "pastrocore.qss"


def user_stylesheet_path() -> pathlib.Path:
    """Return where a user's own stylesheet would live -- beside their settings."""
    from pastrocore.base.scratch import data_home

    return pathlib.Path(data_home()) / USER_STYLESHEET


def assets_directory(name: str) -> pathlib.Path:
    """Return where one theme's glyphs are kept."""
    from pastrocore.base.scratch import data_home

    return pathlib.Path(data_home()) / "theme" / name


def write_glyphs(name: str) -> str:
    """Write the small pictures a themed window needs, and say where they went.

    Args:
        name (str): `light` or `dark`.

    Returns:
        str: The directory, for a style sheet to read -- empty when it could not be written, in
            which case Qt draws its own and the window is styled everywhere else.

    Notes:
        - **Written rather than shipped**, because there is one of each per theme and per state,
          and a picture in the repository is a colour that does not follow the palette.
        - Rewritten every start: they are small, and a stale one after a token changes would be
          the kind of wrongness nobody thinks to look for.
    """
    directory = assets_directory(name)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for glyph, svg in theme.glyphs(name).items():
            (directory / f"{glyph}.svg").write_text(svg, encoding="utf-8")
    except Exception as e:                              # noqa: BLE001 - appearance is not fatal
        logger.error("Could not write the theme's glyphs to '%s': %s", directory, str(e))
        return ""
    return str(directory)


def load_stylesheet(choice: str = "system", system_is_dark: bool = False) -> str:
    """Return the stylesheet to apply to the application.

    Args:
        choice (str): What the settings say -- `system`, `light` or `dark`.
        system_is_dark (bool): What the desktop is set to, where that can be told.

    Returns:
        str: The user's stylesheet if they keep one, and the generated one otherwise.

    Notes:
        - A user's file **replaces** the generated one rather than adding to it. Appending would
          mean a rule they removed still applies, which is the confusing half of both worlds.
        - Failures are logged and swallowed. An unreadable stylesheet is a cosmetic problem, and
          refusing to start over one would be worse than starting plain.
    """
    name = theme.resolve(choice, system_is_dark)
    theirs = user_stylesheet_path()
    try:
        if theirs.is_file():
            text = theirs.read_text(encoding="utf-8")
            logger.info("Styling from '%s' (%s lines)", theirs, len(text.splitlines()))
            return text
    except Exception as e:                              # noqa: BLE001 - appearance is not fatal
        logger.error("Could not read the stylesheet '%s': %s", theirs, str(e))

    sheet = theme.stylesheet(name, write_glyphs(name))
    logger.info("Styling from the '%s' theme (%s lines)", name, len(sheet.splitlines()))
    return sheet
