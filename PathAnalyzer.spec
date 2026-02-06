# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file per Path Analyzer GUI.
Gestisce il bundling corretto di customtkinter.
"""

import os
import customtkinter

block_cipher = None

# Trova il percorso di customtkinter per includere i suoi assets
ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['path_analyzer_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # CRITICO: include gli assets di customtkinter (temi, immagini)
        (ctk_path, 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='PathAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # False = nessuna finestra console (solo GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Decommentare se hai un'icona
)
