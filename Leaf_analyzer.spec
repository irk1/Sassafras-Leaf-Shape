# -*- mode: python ; coding: utf-8 -*-
import os

# Target folder where the final .exe will be saved
target_dir = r'C:\Users\izzyk\OneDrive\Documents\GitHub\Sassafras Leaf Shape'

a = Analysis(
    ['Leaf_analyzer.py'],
    pathex=[target_dir],
    binaries=[],
    datas=[],
    hiddenimports=['matplotlib.backends.backend_tkagg'], # Guarantees Matplotlib interactive windows work
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy unused frameworks while keeping Tkinter for Matplotlib ginput/show
    excludes=[
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 
        'scipy', 'pandas', 'IPython', 'jupyter', 'notebook',
        'pydoc', 'unittest'
    ],
    noarchive=False,
    optimize=0, # Strip docstrings to compress bytecode
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=os.path.join(target_dir, 'Leaf_analyzer'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Compresses executable using upx.exe if present
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Untitled-1.png', # Requires a valid .ico file
)