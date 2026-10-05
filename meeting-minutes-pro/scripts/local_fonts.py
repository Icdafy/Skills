"""Find user-supplied or installed fonts without shipping or installing fonts.

ICDAFY_FONT_DIR is exclusive when set, so missing resources are explicit.
This helper has no skill-specific format rules. Copies are physically bundled.
"""
import os
from pathlib import Path
import sys


def font_directories():
    configured = os.environ.get('ICDAFY_FONT_DIR')
    if configured is not None:
        return [Path(configured).expanduser()]
    if os.name == 'nt':
        return [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts']
    if sys.platform == 'darwin':
        return [Path.home() / 'Library/Fonts', Path('/Library/Fonts'), Path('/System/Library/Fonts')]
    return [Path.home() / '.local/share/fonts', Path('/usr/share/fonts'), Path('/usr/local/share/fonts')]


def resolve_fonts(targets):
    """Resolve {family: candidate filenames}; explicit directory never falls back."""
    directories = font_directories()
    result = {}
    for family, filenames in targets.items():
        for directory in directories:
            for filename in filenames:
                path = directory / filename
                if path.is_file():
                    result[family] = path.resolve()
                    break
            if family in result:
                break
    if os.environ.get('ICDAFY_FONT_DIR') is not None:
        return result
    # Registered fonts can have different file names and can live outside Fonts/.
    if os.name == 'nt':
        import winreg
        key_name = r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    i = 0
                    while True:
                        try:
                            label, value, _ = winreg.EnumValue(key, i)
                            i += 1
                        except OSError:
                            break
                        if not isinstance(value, str):
                            continue
                        path = Path(os.path.expandvars(value))
                        if not path.is_absolute():
                            path = directories[0] / path
                        if not path.is_file():
                            continue
                        for family, filenames in targets.items():
                            aliases = (family,) + tuple(Path(f).stem for f in filenames)
                            if family not in result and any(a.casefold() in label.casefold() for a in aliases):
                                result[family] = path.resolve()
            except OSError:
                continue
    else:
        wanted = {f.casefold(): family for family, files in targets.items() for f in files}
        for directory in directories:
            if directory.is_dir():
                for path in directory.rglob('*'):
                    family = wanted.get(path.name.casefold())
                    if family and family not in result and path.is_file():
                        result[family] = path.resolve()
    return result
