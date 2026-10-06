"""Build the download for this platform: the application, wrapped as it is installed.

Usage:
    python tools/make_download.py              build, then wrap for this platform
    python tools/make_download.py --bundle     build the folder and stop

Notes:
    - One command on every platform, so what CI runs is what can be run by hand when a
      download misbehaves. What differs between the three is the last step alone.
    - Built from the environment it is run in. PyInstaller ships whatever it can import, so
      a build from a working Python carries that Python's other projects: 4.9 GB, once.
"""
import argparse
import os
import pathlib
import platform
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
NAME = "pAstroCORE"

#: What each platform's download is called, and the machine CI builds it on. The name is
#: also the link on the download page, so it is written here and read by both.
DOWNLOADS = {
    "win32": {"suffix": "windows-x64.exe", "machine": ("AMD64", "x86_64")},
    "darwin": {"suffix": "macos-arm64.dmg", "machine": ("arm64",)},
    "linux": {"suffix": "linux-x86_64.AppImage", "machine": ("x86_64",)},
}


def download_name(number: str, where: str = None) -> str:
    """Return what this platform's download is called, version and all.

    Raises:
        SystemExit: On a machine the name does not describe. A file called `x86_64` that
            holds arm64 binaries is worse than a build that stopped.
    """
    where = where or ("linux" if sys.platform.startswith("linux") else sys.platform)
    held = DOWNLOADS.get(where)
    if held is None:
        sys.exit(f"nothing is built for {where}")
    if platform.machine() not in held["machine"]:
        sys.exit(f"this is a {platform.machine()} machine and the name says {held['suffix']}")
    return f"{NAME}-{number}-{held['suffix']}"

#: What a `.desktop` file has to say for a Linux menu to show the application at all.
DESKTOP = """[Desktop Entry]
Type=Application
Name=pAstroCORE
Comment=Planning and checking VLBI schedules, ground and space
Exec=pAstroCORE
Icon=pastrocore
Categories=Science;Astronomy;
Terminal=false
"""


def version() -> str:
    """The one version there is, read from the package rather than passed in."""
    sys.path.insert(0, str(ROOT))
    from pastrocore import __version__

    return __version__


def run(*command, **extra):
    """Run a command, saying what it was, and stop on a failure."""
    print("$", " ".join(str(part) for part in command), flush=True)
    subprocess.run([str(part) for part in command], check=True, cwd=ROOT, **extra)


def bundle():
    """Build the folder PyInstaller makes, and return it."""
    run(sys.executable, "tools/make_icons.py")
    shutil.rmtree(DIST / NAME, ignore_errors=True)
    run(sys.executable, "-m", "PyInstaller", "packaging/pastrocore.spec", "--noconfirm",
        "--distpath", "dist", "--workpath", "build")
    built = DIST / (f"{NAME}.app" if sys.platform == "darwin" else NAME)
    if not built.exists():
        sys.exit(f"PyInstaller wrote no {built}")
    return built


def for_windows(built, number):
    """Wrap it as an installer that puts a shortcut in the Start menu."""
    compiler = shutil.which("ISCC") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not pathlib.Path(compiler).is_file():
        sys.exit("Inno Setup is not here: ISCC builds the installer")
    run(compiler, f"/DVersion={number}", "packaging/pastrocore.iss")
    return DIST / download_name(number)


def for_macos(built, number):
    """Wrap the bundle as a disk image with Applications beside it, to drag it into."""
    staging = DIST / "dmg"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copytree(built, staging / built.name, symlinks=True)
    os.symlink("/Applications", staging / "Applications")

    written = DIST / download_name(number)
    written.unlink(missing_ok=True)
    run("hdiutil", "create", "-volname", NAME, "-srcfolder", staging, "-ov",
        "-format", "UDZO", written)
    return written


def for_linux(built, number):
    """Wrap it as an AppImage, which is one file a user marks executable and runs."""
    tool = shutil.which("appimagetool") or shutil.which("appimagetool-x86_64.AppImage")
    if not tool:
        sys.exit("appimagetool is not here: it is what makes an AppImage")

    folder = DIST / "AppDir"
    shutil.rmtree(folder, ignore_errors=True)
    (folder / "usr").mkdir(parents=True)
    shutil.copytree(built, folder / "usr" / "bin")
    (folder / "pastrocore.desktop").write_text(DESKTOP, encoding="utf-8")
    shutil.copy(ROOT / "pastrocore" / "gui" / "icons" / "pAstroCORE_icon.png",
                folder / "pastrocore.png")
    # `AppRun` is what the AppImage starts, and it has to reach the executable wherever
    # the image is mounted: the mount point is different every run.
    start = folder / "AppRun"
    start.write_text('#!/bin/sh\nexec "$(dirname "$(readlink -f "$0")")/usr/bin/pAstroCORE" "$@"\n',
                     encoding="utf-8")
    start.chmod(0o755)

    written = DIST / download_name(number)
    written.unlink(missing_ok=True)
    run(tool, folder, written, env={**os.environ, "ARCH": platform.machine()})
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="store_true",
                        help="build the folder and stop, without wrapping it")
    asked = parser.parse_args()

    number = version()
    built = bundle()
    if asked.bundle:
        print(built.relative_to(ROOT).as_posix())
        return

    wrap = {"win32": for_windows, "darwin": for_macos}.get(sys.platform, for_linux)
    written = wrap(built, number)
    if not written.is_file():
        sys.exit(f"nothing was written to {written}")
    print(f"{written.relative_to(ROOT).as_posix()}  {written.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
