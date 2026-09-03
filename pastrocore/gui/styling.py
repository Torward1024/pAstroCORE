"""The one stylesheet, and where it comes from.

224 `styleSheet` properties across 24 forms and 131 lines written inline in `app.main` made
"what does this application look like" a question with no answer -- and copying a form was how
a second variant of a rule came to exist, which is why 38 spin boxes were styled two different
ways.

`pastrocore.qss` is the answer now. It ships beside this module, it is applied to the
`QApplication` so a dialog built later sees it too, and a user may put their own beside it.
"""
import pathlib

from msb_arch.utils.logging_setup import logger

#: The stylesheet shipped with the application.
SHIPPED = pathlib.Path(__file__).parent / "pastrocore.qss"

#: What a user's own stylesheet is called, if they keep one. Looked for beside the settings
#: rather than beside the installed package, which may be read-only and is replaced on upgrade.
USER_STYLESHEET = "pastrocore.qss"


def user_stylesheet_path() -> pathlib.Path:
    """Return where a user's own stylesheet would live -- beside their settings."""
    from pastrocore.base.scratch import data_home

    return pathlib.Path(data_home()) / USER_STYLESHEET


def load_stylesheet() -> str:
    """Return the stylesheet to apply to the application.

    Returns:
        str: The user's stylesheet if they keep one, and the shipped one otherwise. Empty when
            neither can be read, which leaves Qt's own appearance rather than a half-styled one.

    Notes:
        - A user's file **replaces** the shipped one rather than adding to it. Appending would
          mean a rule they removed still applies, which is the confusing half of both worlds.
        - Failures are logged and swallowed. An unreadable stylesheet is a cosmetic problem, and
          refusing to start over one would be worse than starting plain.
    """
    for path in (user_stylesheet_path(), SHIPPED):
        try:
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                logger.info("Styling from '%s' (%s lines)", path, len(text.splitlines()))
                return text
        except Exception as e:                          # noqa: BLE001 - appearance is not fatal
            logger.error("Could not read the stylesheet '%s': %s", path, str(e))

    logger.warning("No stylesheet found; the application will use Qt's own appearance")
    return ""
