# -*- mode: python ; coding: utf-8 -*-
"""What a download holds: the application, its data, and the Qt it actually uses.

Run from the repository root:

    pyinstaller packaging/pastrocore.spec --noconfirm

Notes:
    - One folder rather than one file. A single executable unpacks itself on every start,
      and this one would unpack a few hundred megabytes before the window appeared.
    - Qt ships about forty modules and this imports three. Whatever is not excluded is
      shipped, so the list below is what keeps a download from being most of a gigabyte.
"""
import pathlib
import sys

from PyInstaller.utils.hooks import collect_data_files

ROOT = pathlib.Path(SPECPATH).resolve().parent

#: The catalogues and the icons, which live inside the package and are not Python.
DATA = collect_data_files("pastrocore", includes=["catalogs/*.json", "gui/icons/*"])

#: The leap seconds and Earth orientation tables astropy reads. Without them a build
#: reaches for them over the network on its first calculation, or refuses.
DATA += collect_data_files("astropy", includes=["**/*.dat", "**/*.csv", "**/*.ecsv"])
DATA += collect_data_files("astropy_iers_data")

#: **The source of both packages, as data.** MSB derives what an application offers by reading
#: the source of its handlers, and a frozen build holds bytecode alone: 1.18.0 started, opened
#: a project, and offered no calculations at all. A few hundred kilobytes of text.
for package in ("pastrocore", "msb_arch"):
    held = pathlib.Path(__import__(package).__file__).resolve().parent
    DATA += [(str(found), str(pathlib.Path(package) / found.relative_to(held).parent))
             for found in held.rglob("*.py") if "__pycache__" not in found.parts]

#: Imported through a string rather than a statement, so nothing walking the code finds them.
HIDDEN = ["matplotlib.backends.backend_qtagg", "matplotlib.backends.backend_agg",
          "pyarrow.parquet", "scipy.special", "scipy.interpolate"]

#: Qt modules this never imports, the test machinery, and the toolkits of other interfaces.
#: Each line is tens of megabytes a user would otherwise download.
WITHOUT = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtSerialPort",
    "PySide6.QtSensors", "PySide6.QtTextToSpeech", "PySide6.QtWebSockets",
    "PySide6.QtWebChannel", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
    "PySide6.QtNetworkAuth", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtOpenGL",
    "tkinter", "pytest", "IPython", "notebook", "sphinx", "PyQt5", "PyQt6",
]

#: What the window is called, and the file that starts it.
NAME = "pAstroCORE"
ICON = {"win32": ROOT / "packaging" / "pastrocore.ico",
        "darwin": ROOT / "packaging" / "pastrocore.icns"}.get(sys.platform)

analysis = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    datas=DATA,
    hiddenimports=HIDDEN,
    excludes=WITHOUT,
    noarchive=False,
)

archive = PYZ(analysis.pure)

executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=str(ICON) if ICON and ICON.is_file() else None,
)

collected = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name=NAME,
)

# A macOS download is an application bundle rather than a folder of files, and that is
# what a user drags into Applications.
if sys.platform == "darwin":
    app = BUNDLE(
        collected,
        name=f"{NAME}.app",
        icon=str(ICON) if ICON and ICON.is_file() else None,
        bundle_identifier="io.github.torward1024.pastrocore",
        info_plist={"NSHighResolutionCapable": True,
                    "CFBundleShortVersionString": __import__("pastrocore").__version__},
    )
