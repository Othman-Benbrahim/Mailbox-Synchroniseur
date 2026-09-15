# PyInstaller spec — dossier (onedir), jamais fichier unique.
#
# Le mode onedir est un choix de conformité, pas de confort : PySide6/Qt est
# distribué sous LGPLv3, qui exige que l'utilisateur puisse remplacer la
# bibliothèque par une autre version. Des DLL Qt visibles et remplaçables à côté
# de l'exécutable satisfont cette exigence ; un exécutable unique la rend
# discutable. Voir THIRD_PARTY.md.
from pathlib import Path

project = Path(SPECPATH).resolve().parent

analysis = Analysis(
    [str(project / "packaging" / "entry.py")],
    pathex=[str(project / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["mailbox_sync"],
    hookspath=[],
    runtime_hooks=[],
    # Qt modules the application never uses; excluded to keep the build honest
    # about what it ships, and smaller.
    excludes=["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtWebEngineCore",
              "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtMultimedia",
              "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf",
              "tkinter", "numpy", "matplotlib", "pytest"],
    noarchive=False,
)
archive = PYZ(analysis.pure)

executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Mailbox-Synchroniseur",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # no console window on Windows
    disable_windowed_traceback=False,
    icon=None,
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Mailbox-Synchroniseur",
)
