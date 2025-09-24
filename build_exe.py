#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 自动将程序打包为exe文件，包含图标
"""

import os
import sys
import shutil
import subprocess

def build_exe():
    """打包为exe文件"""

    # 确保图标文件存在
    icon_file = "faviconV2.ico"
    if not os.path.exists(icon_file):
        print(f"❌ 错误：找不到图标文件 {icon_file}")
        print("请确保 faviconV2.ico 文件在当前目录中")
        return False

    # 准备打包命令
    # --onefile: 打包成单个文件
    # --windowed: 不显示控制台窗口（GUI程序）
    # --icon: 指定图标文件
    # --add-data: 添加数据文件（图标文件也要包含进去）
    # --name: 指定输出文件名

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        f"--icon={icon_file}",
        f"--add-data={icon_file};.",  # Windows分隔符是分号
        "--add-data=faviconV2.png;.",
        "--add-data=icon.ico;.",
        "--name=AsterDexTrading",
        "--clean",
        "--noconfirm",
        "aster_trading_gui_bootstrap.py"
    ]

    print("🔧 开始打包...")
    print(f"📦 打包命令: {' '.join(cmd)}")

    try:
        # 执行打包命令
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 打包成功！")
            print("📁 输出文件: dist/AsterDexTrading.exe")

            # 检查输出文件
            exe_path = "dist/AsterDexTrading.exe"
            if os.path.exists(exe_path):
                file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
                print(f"📊 文件大小: {file_size:.2f} MB")
                print("\n✨ 打包完成！可以将 dist/AsterDexTrading.exe 分发给其他用户")
                print("⚠️ 注意：首次运行可能会被杀毒软件拦截，需要添加信任")
            return True
        else:
            print("❌ 打包失败！")
            print("错误信息:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("❌ 错误：未找到 PyInstaller")
        print("请先安装 PyInstaller: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"❌ 打包出错: {e}")
        return False

def create_spec_file():
    """创建更详细的spec配置文件"""

    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['aster_trading_gui_bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('faviconV2.ico', '.'),
        ('faviconV2.png', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'ttkbootstrap',
        'requests',
        'hashlib',
        'hmac',
        'json',
        'threading',
        'queue'
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
    name='AsterDexTrading',
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
    icon='faviconV2.ico',
    version_file=None,
)
"""

    with open("AsterDexTrading.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)

    print("✅ 已创建 AsterDexTrading.spec 配置文件")

    # 使用spec文件打包
    cmd = ["pyinstaller", "--clean", "--noconfirm", "AsterDexTrading.spec"]

    try:
        print("📦 使用spec文件打包...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 打包成功！")
            return True
        else:
            print("❌ 打包失败！")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("onehopeA9的对冲工具 - 打包工具")
    print("=" * 50)

    # 检查依赖
    try:
        import pyinstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("\n选择打包方式:")
    print("1. 快速打包（使用默认配置）")
    print("2. 高级打包（使用spec文件）")

    choice = input("\n请输入选项 (1/2): ").strip()

    if choice == "2":
        create_spec_file()
    else:
        build_exe()

    input("\n按回车键退出...")