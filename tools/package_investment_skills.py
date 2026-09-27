#!/usr/bin/env python3
"""Compatibility wrapper: build or verify the three investment-report skill ZIPs.

All seven skills are packaged by tools/package_skills.py; this keeps the old
command working for the investment-report group only.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_skills  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(package_skills.main(sys.argv[1:] + ['--group', 'investment-report-skills']))
