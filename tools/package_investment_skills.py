#!/usr/bin/env python3
"""Compatibility wrapper: build or verify the three investment-report skill ZIPs.

All seven skills are packaged by tools/package_skills.py; this keeps the old
command limited to the investment-report group. Writes require --skill or
an explicit --all (which selects only the historical three skills).
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_skills  # noqa: E402

INVESTMENT = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    scope = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    scope.add_argument('--skill', choices=INVESTMENT, action='append')
    scope.add_argument('--group', choices=('investment-report-skills',), action='append')
    selected, _ = scope.parse_known_args(argv)
    if '--all' in argv:
        if selected.skill:
            scope.error('Use --skill or --all, not both')
        argv.remove('--all')
        for name in INVESTMENT:
            argv.extend(['--skill', name])
    return package_skills.main(argv + ['--group', 'investment-report-skills'])


if __name__ == '__main__':
    raise SystemExit(main())
