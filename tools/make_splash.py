"""Draw the splash a build shows while the interpreter starts.

Usage:
    python tools/make_splash.py

Notes:
    - What it covers is the second or so before Qt exists, when nothing can be shown from
      inside the application. The warm-up it used to be suggested for runs in a thread with
      the window already up, and needs no cover.
    - Drawn from the palette in `pastrocore.theme` and the icon the application ships, so
      the first thing seen is the colours of the thing starting.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICON = ROOT / "pastrocore" / "gui" / "icons" / "pAstroCORE_icon.png"
INTO = ROOT / "packaging" / "splash.png"

#: Wide enough for the name beside the icon, small enough not to cover a desktop.
SIZE = (520, 220)
MARK = 132


def palette():
    """The dark palette, which is what a splash on any desktop sits well against."""
    sys.path.insert(0, str(ROOT))
    from pastrocore import theme

    return theme.PALETTES["dark"]


def draw(into: pathlib.Path) -> pathlib.Path:
    """Write the splash, and return where."""
    from PIL import Image, ImageDraw, ImageFont

    from pastrocore import __version__

    ink = palette()
    image = Image.new("RGB", SIZE, ink["bg"])
    drawing = ImageDraw.Draw(image)

    # A line of accent along the top, which is the window's own chrome colour.
    drawing.rectangle([0, 0, SIZE[0], 3], fill=ink["accent"])
    drawing.rectangle([0, SIZE[1] - 1, SIZE[0], SIZE[1]], fill=ink["line"])

    mark = Image.open(ICON).convert("RGBA").resize((MARK, MARK), Image.LANCZOS)
    image.paste(mark, (34, (SIZE[1] - MARK) // 2), mark)

    left = 34 + MARK + 28
    for text, size, colour, top in (
            ("pAstroCORE", 34, ink["text_strong"], 62),
            (f"version {__version__}", 15, ink["text_dim"], 106),
            ("starting", 13, ink["text_disabled"], 134)):
        try:
            face = ImageFont.truetype("segoeui.ttf", size)
        except OSError:
            face = ImageFont.load_default(size)
        drawing.text((left, top), text, font=face, fill=colour)

    into.parent.mkdir(parents=True, exist_ok=True)
    image.save(into)
    return into


def main():
    if not ICON.is_file():
        sys.exit(f"{ICON} is not here, and the splash is drawn from it")
    print(draw(INTO).relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
