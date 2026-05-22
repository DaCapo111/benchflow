# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'tensorflow', 'scipy', 'pandas', 'numpy', 'pyarrow',
        'matplotlib', 'PyQt5', 'IPython', 'jupyter', 'notebook',
        'dask', 'distributed', 'botocore', 'boto3', 'openpyxl',
        'h5py', 'zarr', 'xarray', 'statsmodels', 'numba', 'llvmlite',
        'sympy', 'sklearn',
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
    name='BenchFlow',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BenchFlow',
)
app = BUNDLE(
    coll,
    name='BenchFlow.app',
    icon='AppIcon.icns',
    bundle_identifier='com.benchflow.app',
    info_plist={
        'CFBundleDisplayName': 'BenchFlow',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'CFBundleName': 'BenchFlow',
        'CFBundleIconFile': 'AppIcon',
    },
)
