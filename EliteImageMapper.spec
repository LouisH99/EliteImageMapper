# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')


a = Analysis(
    ['EliteImageMapper_App.py'],
    pathex=[],
    binaries=pil_binaries,
    datas=pil_datas,
    hiddenimports=pil_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EliteImageMapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
