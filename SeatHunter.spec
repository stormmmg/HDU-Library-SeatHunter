# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

project_root = os.path.dirname(os.path.abspath(SPECPATH))

# 收集Playwright的子模块和数据文件（含driver）
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

pw_datas = collect_data_files('playwright')
pw_imports = collect_submodules('playwright')

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=pw_datas,
    hiddenimports=[
        'config',
        'config.config',
        'utils',
        'utils.killer',
        'utils.window',
        'greenlet',
        'pyee',
        'requests',
        'urllib3',
        'yaml',
        'prettytable',
        'pwinput',
        'win32gui',
        'win32con',
        'win32api',
    ] + pw_imports,
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
    [],
    exclude_binaries=True,
    name='SeatHunter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SeatHunter',
)
