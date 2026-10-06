# Download pAstroCORE

**Version 1.18.1.** One file for your machine, holding its own Python and everything else.
Nothing has to be installed first.

| | | |
| --- | --- | --- |
| **Windows** | [pAstroCORE-1.18.1-windows-x64.exe](https://github.com/Torward1024/pAstroCORE/releases/download/v1.18.1/pAstroCORE-1.18.1-windows-x64.exe) | Run it. It installs for you alone, so Windows never asks for an administrator, and puts pAstroCORE in the Start menu. |
| **macOS** | [pAstroCORE-1.18.1-macos-arm64.dmg](https://github.com/Torward1024/pAstroCORE/releases/download/v1.18.1/pAstroCORE-1.18.1-macos-arm64.dmg) | Open it and drag pAstroCORE into Applications. |
| **Linux** | [pAstroCORE-1.18.1-linux-x86_64.AppImage](https://github.com/Torward1024/pAstroCORE/releases/download/v1.18.1/pAstroCORE-1.18.1-linux-x86_64.AppImage) | `chmod +x` it and run it. An AppImage installs nothing. |

Every release is on [the releases page](https://github.com/Torward1024/pAstroCORE/releases), and
[the latest one](https://github.com/Torward1024/pAstroCORE/releases/latest) is always this one or newer.

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
