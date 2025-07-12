# -*- mode: python ; coding: utf-8 -*-

import sys

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('icon.png', '.')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)
if sys.platform != 'darwin':
    splash = Splash(
        'logo.png',
        binaries=a.binaries,
        datas=a.datas,
        text_pos=None,
        text_size=12,
        minify_script=True,
        always_on_top=True,
    )
else:
    splash = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    # Only add splash if not on macOS
    *( [splash, splash.binaries] if splash else [] ),
    exclude_binaries=True,
    name='diynafluor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],
)

if sys.platform == 'darwin':
    # Additionally create an app bundle on Darwin
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='diynafluor',
    )
    app = BUNDLE(
        coll,
        name='diynafluor.app',
        icon='icon.png',
        bundle_identifier=None,
        info_plist={
            'NSHighResolutionCapable': 'True'
        },
    )
