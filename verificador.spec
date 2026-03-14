# -*- mode: python ; coding: utf-8 -*-
"""
Spec file para PyInstaller - Verificador DUSA
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Recolectar todas las dependencias
datas = []
binaries = []
hiddenimports = []

# Pandas y sus dependencias
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('numpy')

# Agregar imports explícitos que suelen faltar
hiddenimports += [
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.offsets',
    'pandas._libs.tslibs.parsing',
    'pandas._libs.join',
    'pandas._libs.reshape',
    'pandas._libs.reduction',
    'pandas._libs.lib',
    'pandas._libs.hashtable',
    'pandas._libs.sparse',
    'pandas._libs.properties',
    'pandas._libs.indexing',
    'pandas._libs.index',
    'pandas._libs.internals',
    'pandas._libs.window',
    'pandas._libs.writers',
    'openpyxl.cell._writer',
    'openpyxl.workbook._writer',
    'openpyxl.worksheet._writer',
    'openpyxl.worksheet._reader',
    'openpyxl.reader.excel',
    'openpyxl.writer.excel',
    'engineio.async_drivers.threading',
    'werkzeug',
    'flask',
    'selenium',
    'requests',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
]

a = Analysis(
    ['app_tuplanilla.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'scipy',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VerificadorDUSA',
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
    icon='icon.ico' if sys.platform == 'win32' else 'icon.icns',
)
