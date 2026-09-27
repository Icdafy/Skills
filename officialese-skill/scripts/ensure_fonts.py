#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公文字体检测与安装脚本（三技能统一版，跨平台）。

在生成 .docx 公文前，检测本机是否已安装立项报告所需的三款公文字体：
仿宋_GB2312、楷体_GB2312、方正小标宋简体。若缺失，从本技能自带的
assets/fonts 目录做用户级安装（无需管理员权限）。

Windows 上除复制字体文件外，还会写入 HKCU 字体注册表——只复制不注册
Word 看不到字体。安装后已打开的 Word 需重启才生效。

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

# 需要的字体族：族名关键字（检测用）-> 候选文件名（不同技能打包的文件名不同，取先找到的）
REQUIRED_FONTS = [
    {
        "family": "仿宋_GB2312",
        "keywords": ["仿宋_GB2312", "FangSong_GB2312", "仿宋", "FangSong"],
        "files": ["simfang.ttf"],
    },
    {
        "family": "楷体_GB2312",
        "keywords": ["楷体_GB2312", "KaiTi_GB2312"],
        "files": ["楷体_GB2312.ttf", "KaiTi_GB2312.ttf"],
    },
    {
        "family": "方正小标宋简体",
        "keywords": ["方正小标宋简体", "FZXiaoBiaoSong"],
        "files": ["方正小标宋简体.ttf", "FZXiaoBiaoSongJT.ttf"],
    },
]

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_SRC_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "fonts"))
WIN_FONT_REG = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"


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


def _win_registered_families():
    """Windows：读 HKLM/HKCU 字体注册表的全部条目名（含族名）。"""
    import winreg
    names = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, WIN_FONT_REG) as key:
                i = 0
                while True:
                    try:
                        name, _, _ = winreg.EnumValue(key, i)
                        names.append(name)
                        i += 1
                    except OSError:
                        break
        except OSError:
            continue
    return names


def _installed_font_files():
    """非 Windows：收集本机已安装字体的文件名集合（小写）。"""
    dirs = []
    system = platform.system()
    if system == "Darwin":
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
    """返回缺失的字体条目列表（REQUIRED_FONTS 的元素）。"""
    missing = []
    if platform.system() == "Windows":
        registered = _win_registered_families()
        for item in REQUIRED_FONTS:
            hit = any(kw in name for name in registered for kw in item["keywords"])
            if not hit:
                missing.append(item)
    else:
        installed = _installed_font_files()
        for item in REQUIRED_FONTS:
            if not any(f.lower() in installed for f in item["files"]):
                missing.append(item)
    return missing


def _src_file(item):
    """在 assets/fonts 中找该字体的候选文件，返回第一个存在的路径。"""
    for fname in item["files"]:
        p = os.path.join(FONT_SRC_DIR, fname)
        if os.path.isfile(p):
            return p
    return None


def install(missing):
    """把缺失字体安装到用户字体目录；Windows 同时写 HKCU 注册表。"""
    dest_dir = user_font_dir()
    os.makedirs(dest_dir, exist_ok=True)
    is_win = platform.system() == "Windows"
    done = []
    for item in missing:
        src = _src_file(item)
        if src is None:
            print(f"  [跳过] 技能 assets/fonts 内未找到 {item['family']} 的字体文件"
                  f"（候选：{'、'.join(item['files'])}）", file=sys.stderr)
            continue
        dst = os.path.join(dest_dir, os.path.basename(src))
        try:
            shutil.copy2(src, dst)
            if is_win:
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_FONT_REG) as key:
                    winreg.SetValueEx(key, f"{item['family']} (TrueType)", 0,
                                      winreg.REG_SZ, dst)
            done.append(item["family"])
            print(f"  [已安装] {item['family']} -> {dst}")
        except Exception as e:
            print(f"  [失败] {item['family']}: {e}", file=sys.stderr)
    return done


def main():
    check_only = "--check" in sys.argv
    missing = check()

    if not missing:
        print("[OK] 所需公文字体已全部安装：" +
              "、".join(i["family"] for i in REQUIRED_FONTS))
        return 0

    print("缺失字体：" + "、".join(i["family"] for i in missing))
    if check_only:
        return 1

    print(f"从技能自带目录安装（{FONT_SRC_DIR}）……")
    done = install(missing)
    if done:
        print("\n[OK] 安装完成（用户级，无需管理员权限）。若 Word 已打开，请重启后生效。")
        return 0
    else:
        print("\n[X] 未能安装任何字体，请检查 assets/fonts 目录。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
