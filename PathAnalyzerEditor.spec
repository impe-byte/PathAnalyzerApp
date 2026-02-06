# -*- mode: python ; coding: utf-8 -*-
import os, customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)
block_cipher = None

a = Analysis(
    ['path_analyzer_editor.py'],
    datas=[(ctk_path, 'customtkinter')],
    hiddenimports=['customtkinter','tkinter','tkinter.filedialog','tkinter.messagebox'],
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='PathAnalyzerEditor', debug=False, strip=False, upx=True,
    console=False,  # Solo GUI, nessuna console
)
