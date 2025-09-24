# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['aster_trading_gui_bootstrap.py'],
    pathex=['D:\\kt\\python\\asterdex-auto-tool'],
    binaries=[],
    datas=[
        ('faviconV2.png', '.'),
        ('faviconV2.ico', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'ttkbootstrap',
        'tkinter',
        'requests',
        'json',
        'threading',
        'queue',
        'datetime',
        'time',
        'os',
        'warnings',
        'webbrowser',
        'traceback'
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
    name='onehopeA9的对冲工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='faviconV2.ico',  # 使用图标
    version='version_info.txt'  # 添加版本信息
)