# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para Verificador DUSA - TuPlanilla Edition
============================================================
Genera ejecutable portable para Windows y Mac.

Uso:
  Windows: pyinstaller verificador_dusa.spec
  Mac:     pyinstaller verificador_dusa.spec

El ejecutable resultante estará en dist/
"""

import sys
import os

# Detectar plataforma
is_windows = sys.platform == 'win32'
is_mac = sys.platform == 'darwin'

# Nombre del ejecutable
name = 'VerificadorDUSA'
if is_windows:
    name += '.exe'

# Archivos adicionales a incluir
datas = []

# Opciones de análisis
a = Analysis(
    ['app_tuplanilla.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'flask',
        'werkzeug',
        'pandas',
        'openpyxl',
        'selenium',
        'webdriver_manager',
        'requests',
        'telemetria',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.random._examples',
        'tkinter',
        'PyQt5',
        'PyQt6',
    ],
    noarchive=False,
    optimize=1,
)

# Filtrar binarios innecesarios para reducir tamaño
a.binaries = [x for x in a.binaries if not x[0].startswith('libQt')]
a.binaries = [x for x in a.binaries if not x[0].startswith('PyQt')]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    upx=True,  # Comprimir ejecutable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=True if is_mac else False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if is_windows else 'icon.icns' if is_mac else None,
)

# Para Mac: crear .app bundle
if is_mac:
    app = BUNDLE(
        exe,
        name='Verificador DUSA.app',
        icon='icon.icns',
        bundle_identifier='net.tuplanilla.verificador-dusa',
        info_plist={
            'CFBundleName': 'Verificador DUSA',
            'CFBundleDisplayName': 'Verificador DUSA',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
