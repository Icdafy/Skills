#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公文常用字体检测与安装脚本。

用途：在生成 .docx 公文前，检测本机是否已安装立项报告所需的公文字体
（仿宋 simfang / 方正小标宋简体 / 楷体_GB2312）。若缺失，则从本技能自带的
assets/fonts 目录复制到用户字体目录，供 Word / LibreOffice 排版调用。

说明：assets/fonts 中的字体为受版权保护的商用/系统字体，随本私有技能仅供
本人使用，请勿再分发。

用法：
    python ensure_fonts.py            # 检测并按需安装
    python ensure_fonts.py --check    # 仅检测，返回缺失清单，不安装
"""
import os
import sys
import shutil
import platform

# 需要的字体：文件名 -> 可能的字体族名（用于检测是否已装）
REQUIRED_FONTS = {
    "simfang.ttf": ["FangSong", "仿宋", "STFangsong", "仿宋_GB2312"],
    "方正小标宋简体.ttf": ["FZXiaoBiaoSong-B05S", "方正小标宋简体", "FZXiaoBiaoSong"],
    "楷体_GB2312.ttf": ["KaiTi", "KaiTi_GB2312", "楷体", "楷体_GB2312", "STKaiti"],
}

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_SRC_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "fonts"))


def user_font_dir():
    """返回当前平台的用户级字体安装目录（无需管理员权限）。"""
    system = platform.system()
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(local, "Microsoft", "Windows", "Fonts")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    else:  # Linux
        return os.path.expanduser("~/.local/share/fonts")


def installed_font_files():
    """收集本机已安装字体的文件名集合（小写），用于快速判断是否已装。"""
    dirs = []
    system = platform.system()
    if system == "Windows":
        win = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(os.path.join(win, "Fonts"))
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
    elif system == "Darwin":
        dirs += ["/System/Library/Fonts", "/Library/Fonts",
                 os.path.expanduser("~/Library/Fonts")]
    else:
        dirs += ["/usr/share/fonts", "/usr/local/share/fonts",
                 os.path.expanduser("~/.local/share/fonts")]

    found = set()
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                found.add(f.lower())
    return found


def check():
    """返回缺失的字体文件名列表。"""
    installed = installed_font_files()
    missing = []
    for fname in REQUIRED_FONTS:
        if fname.lower() not in installed:
            missing.append(fname)
    return missing


def install(missing):
    """把缺失字体从技能自带目录复制到用户字体目录。返回成功安装的文件名。"""
    dest_dir = user_font_dir()
    os.makedirs(dest_dir, exist_ok=True)
    done = []
    for fname in missing:
        src = os.path.join(FONT_SRC_DIR, fname)
        if not os.path.isfile(src):
            print(f"  [跳过] 技能内未找到字体文件：{src}", file=sys.stderr)
            continue
        dst = os.path.join(dest_dir, fname)
        try:
            shutil.copy2(src, dst)
            done.append(fname)
            print(f"  [已安装] {fname} -> {dst}")
        except Exception as e:
            print(f"  [失败] {fname}: {e}", file=sys.stderr)
    return done


def main():
    check_only = "--check" in sys.argv
    missing = check()

    if not missing:
        print("[OK] 所需公文字体已全部安装：" +
              "、".join(REQUIRED_FONTS.keys()))
        return 0

    print("缺失字体：" + "、".join(missing))
    if check_only:
        return 1

    print(f"从技能自带目录安装（{FONT_SRC_DIR}）……")
    done = install(missing)
    if done:
        print("\n[OK] 安装完成。若 Word 已打开，请重启后生效。")
        if platform.system() == "Windows":
            print("  提示：用户级字体对当前用户所有程序可见，无需管理员权限。")
        return 0
    else:
        print("\n[X] 未能安装任何字体，请检查 assets/fonts 目录。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
