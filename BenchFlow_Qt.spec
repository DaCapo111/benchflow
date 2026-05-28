# -*- mode: python ; coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# BenchFlow Qt (PySide6) — PyInstaller spec
#
# Build:
#   python -m PyInstaller --noconfirm BenchFlow_Qt.spec
#
# Or via the helper scripts:
#   macOS:   ./build_qt_mac.sh
#   Windows: build_qt_windows.bat
# ─────────────────────────────────────────────────────────────────────────────
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = []
binaries = []
hiddenimports = []

# ── PySide6 ───────────────────────────────────────────────────────────────────
tmp = collect_all("PySide6")
datas    += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

# ── Optional export dependencies ─────────────────────────────────────────────
for pkg in ("reportlab", "docx", "PIL"):
    try:
        tmp = collect_all(pkg)
        datas    += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass  # optional — app works without them

# ── Bundle built-in protocol templates ───────────────────────────────────────
datas += [("templates", "templates")]

# ── VERSION file ─────────────────────────────────────────────────────────────
datas += [("VERSION", ".")]

a = Analysis(
    ["qt_app/main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "qt_app",
        "qt_app.app",
        "qt_app.theme",
        "qt_app.services.data",
        "qt_app.services.export_service",
        "qt_app.views.settings",
        "qt_app.views.import_page",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch", "tensorflow", "scipy", "pandas", "numpy", "pyarrow",
        "matplotlib", "customtkinter",
        "IPython", "jupyter", "notebook",
        "dask", "distributed", "botocore", "boto3", "openpyxl",
        "h5py", "zarr", "xarray", "statsmodels", "numba", "llvmlite",
        "sympy", "sklearn",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BenchFlow_Qt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: add icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BenchFlow_Qt",
)

app = BUNDLE(
    coll,
    name="BenchFlow.app",
    icon=None,  # TODO: add .icns icon
    bundle_identifier="com.benchflow.app",
    info_plist={
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # allow dark mode
    },
)
