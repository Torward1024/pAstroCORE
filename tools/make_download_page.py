"""Write the download page, so every link names the version that is being released.

Usage:
    python tools/make_download_page.py            write `docs/download.md`
    python tools/make_download_page.py --check    fail if the page has drifted

Notes:
    - A download carries its version in its name, which is what tells two of them apart on
      a disk -- and that means the link to it changes every release. Written rather than
      typed, so a version bump cannot leave the page pointing at the release before it.
    - `test_documentation` runs the check, so the page is held to the version in the code.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "download.md"
SITE = "https://github.com/Torward1024/pAstroCORE"

#: What a reader does with each download, in the order they will do it.
WHAT_TO_DO = {
    "win32": ("Windows", "Run it. It installs for you alone, so Windows never asks for an "
                         "administrator, and puts pAstroCORE in the Start menu."),
    "darwin": ("macOS", "Open it and drag pAstroCORE into Applications."),
    "linux": ("Linux", "`chmod +x` it and run it. An AppImage installs nothing."),
}

TEXT = """# Download pAstroCORE

**Version {version}.** One file for your machine, holding its own Python and everything else.
Nothing has to be installed first.

| | | |
| --- | --- | --- |
{rows}

Every release is on [the releases page]({site}/releases), and
[the latest one]({site}/releases/latest) is always this one or newer.

## The first start

**The downloads are not signed**, so each platform asks once whether you meant it.

| | What it says | What to do |
| --- | --- | --- |
| **Windows** | Windows protected your PC | **More info**, then **Run anyway** |
| **macOS** | pAstroCORE cannot be checked for malicious software | Right-click the application, choose **Open**, then **Open** again |
| **Linux** | Nothing | — |

Signing them costs a certificate a year per platform, and the roadmap says so rather than
leaving it looking like an oversight.

## What you get

The window, and `pastrocore-cli` beside it inside the same install.
[Your first schedule](first-schedule.md) walks from an empty window to a VEX file;
[installing and running](installing.md) says where the settings and catalogues live.

A release is built by CI, which then installs it and starts it against a project. A download
that does not start is a failed build rather than a release.
"""


def version() -> str:
    """The one version there is, read from the package."""
    sys.path.insert(0, str(ROOT))
    from pastrocore import __version__

    return __version__


def page() -> str:
    """Return what the download page should say."""
    from make_download import DOWNLOADS, download_name

    number = version()
    rows = []
    for where, held in DOWNLOADS.items():
        platform, doing = WHAT_TO_DO[where]
        name = f"pAstroCORE-{number}-{held['suffix']}"
        link = f"{SITE}/releases/download/v{number}/{name}"
        rows.append(f"| **{platform}** | [{name}]({link}) | {doing} |")
    assert download_name                            # the same rule, named for the reader
    return TEXT.format(version=number, site=SITE, rows="\n".join(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the page is not what this would write")
    asked = parser.parse_args()

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    written = page()
    if asked.check:
        found = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
        if found.replace("\r\n", "\n") != written:
            sys.exit(f"{PAGE.name} is not what the version says; "
                     "run tools/make_download_page.py")
        print(f"{PAGE.relative_to(ROOT).as_posix()} is current")
        return

    PAGE.write_text(written, encoding="utf-8")
    print(PAGE.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
