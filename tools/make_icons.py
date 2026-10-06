"""Make the platform icons a build needs, from the one icon the application ships.

Usage:
    python tools/make_icons.py            write whichever this platform needs

Notes:
    - Generated rather than committed, so the icon on a download and the icon in the window
      cannot be two different pictures.
    - Windows wants `.ico` and macOS wants `.icns`; Linux takes the PNG as it is. Each is
      made with what that platform has: Pillow for the one, `iconutil` for the other.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "pastrocore" / "gui" / "icons" / "pAstroCORE_icon.png"
INTO = ROOT / "packaging"

#: What a Windows icon holds. Every size Explorer asks for, from the taskbar to a large tile.
SIZES = [16, 24, 32, 48, 64, 128, 256]


def as_ico(into):
    """Write a Windows icon holding every size, and return where."""
    from PIL import Image

    path = into / "pastrocore.ico"
    Image.open(SOURCE).save(path, sizes=[(size, size) for size in SIZES])
    return path


def as_icns(into):
    """Write a macOS icon with `iconutil`, which is what macOS has for the purpose."""
    from PIL import Image

    path = into / "pastrocore.icns"
    folder = into / "pastrocore.iconset"
    folder.mkdir(parents=True, exist_ok=True)
    original = Image.open(SOURCE)
    for size in (16, 32, 128, 256, 512):
        original.resize((size, size)).save(folder / f"icon_{size}x{size}.png")
        original.resize((size * 2, size * 2)).save(folder / f"icon_{size}x{size}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(folder), "-o", str(path)], check=True)
    return path


def main():
    INTO.mkdir(parents=True, exist_ok=True)
    if not SOURCE.is_file():
        sys.exit(f"{SOURCE} is not here, and it is what every icon is made from")
    written = [as_ico(INTO)]
    if sys.platform == "darwin":
        written.append(as_icns(INTO))
    for path in written:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
