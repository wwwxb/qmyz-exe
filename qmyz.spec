# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec：绿色便携版（onedir）
# 用法： pyinstaller qmyz.spec --noconfirm
import os

APP_NAME = "QMYZ"

a = Analysis(
    ["app/gui.py"],
    pathex=["app"],
    binaries=[],
    # 题库整目录随包分发；运行时先在 exe 同级 qmyz/ 找，找不到再用内置的
    datas=[("app/qmyz", "qmyz")],
    hiddenimports=[
        "Crypto.Cipher.AES",
        "Crypto.Util.Padding",
        "qm_utils",
        "qm_utils.qm",
        "qm_utils.qm_tools",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy", "PIL", "IPython",
        "pytest", "setuptools", "pip", "pydoc_data", "test",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # 关掉 UPX：能显著减少杀软误报
    console=False,      # 无控制台窗口（GUI 程序）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="app/icon.ico",   # 有图标时取消注释
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
