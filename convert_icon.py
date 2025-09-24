#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将PNG图标转换为ICO格式，用于Windows exe文件
"""

from PIL import Image
import os

def convert_png_to_ico(png_path, ico_path=None):
    """
    将PNG图片转换为ICO格式
    支持多尺寸图标
    """
    if not os.path.exists(png_path):
        print(f"[ERROR] File not found: {png_path}")
        return False

    try:
        # 打开PNG图片
        img = Image.open(png_path)

        # 如果是RGBA模式，保持透明度
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 生成多个尺寸的图标
        sizes = [
            (16, 16),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256)
        ]

        # 如果没有指定输出路径，使用默认名称
        if ico_path is None:
            ico_path = os.path.splitext(png_path)[0] + '.ico'

        # 创建多尺寸图标列表
        icons = []
        for size in sizes:
            # 使用高质量的重采样方法
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icons.append(resized)

        # 保存为ICO文件，包含所有尺寸
        icons[0].save(
            ico_path,
            format='ICO',
            sizes=[(icon.width, icon.height) for icon in icons],
            append_images=icons[1:]
        )

        print(f"[SUCCESS] Converted: {png_path} -> {ico_path}")
        print(f"   Sizes: {', '.join([f'{s[0]}x{s[1]}' for s in sizes])}")
        return True

    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}")
        return False

if __name__ == "__main__":
    # 转换faviconV2.png为ico格式
    convert_png_to_ico("faviconV2.png", "faviconV2.ico")

    # 也可以直接生成icon.ico供备用
    convert_png_to_ico("faviconV2.png", "icon.ico")