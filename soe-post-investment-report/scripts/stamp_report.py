#!/usr/bin/env python3
"""Stamp a safely edited base DOCX with the canonical report-spec fingerprint.

This helper rewrites only ``docProps/core.xml`` inside a passive DOCX package.
It exists for complex uploaded templates that must be edited in place rather
than rebuilt by ``build_report.py``. Always write to a separate output path,
then run ``validate_report.py --spec ... --docx ...`` on the stamped result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from render_docx import RenderError, inspect_docx


DC_NS = "http://purl.org/dc/elements/1.1/"
IDENTIFIER_PREFIX = "soe-post-investment-report:sha256:"


class StampError(RuntimeError):
    """A user-actionable stamping failure."""


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def spec_fingerprint(spec: dict[str, object]) -> str:
    canonical = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def stamp(input_path: Path, spec_path: Path, output_path: Path, *, force: bool) -> dict[str, object]:
    input_path = input_path.expanduser().resolve()
    spec_path = spec_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not input_path.is_file():
        raise StampError(f"Input DOCX not found: {input_path}")
    if not spec_path.is_file():
        raise StampError(f"Specification not found: {spec_path}")
    if input_path.suffix.casefold() != ".docx" or output_path.suffix.casefold() != ".docx":
        raise StampError("Input and output must use the .docx extension")
    if input_path == output_path:
        raise StampError("Refusing in-place stamping; use a separate output path")
    if output_path.exists() and not force:
        raise StampError(f"Output already exists (use --force to replace it): {output_path}")

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise StampError(f"Specification could not be read: {exc}") from exc
    if not isinstance(spec, dict):
        raise StampError("Specification root must be a JSON object")
    fingerprint = spec_fingerprint(spec)

    try:
        package_summary = inspect_docx(input_path)
    except RenderError as exc:
        raise StampError(f"Unsafe DOCX refused before stamping: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    staged = output_path.parent / f".{output_path.name}.tmp-{uuid.uuid4().hex}"
    try:
        with ZipFile(input_path) as source:
            names = source.namelist()
            if any(name.casefold().startswith("_xmlsignatures/") for name in names):
                raise StampError("Digitally signed DOCX packages cannot be stamped without invalidating the signature")
            if "docProps/core.xml" not in names:
                raise StampError("DOCX is missing docProps/core.xml")
            core_root = ET.fromstring(source.read("docProps/core.xml"))
            identifier = core_root.find(f"{{{DC_NS}}}identifier")
            if identifier is None:
                identifier = ET.SubElement(core_root, f"{{{DC_NS}}}identifier")
            identifier.text = IDENTIFIER_PREFIX + fingerprint
            core_payload = ET.tostring(core_root, encoding="utf-8", xml_declaration=True)

            with ZipFile(staged, "w", compression=ZIP_DEFLATED, compresslevel=9) as destination:
                destination.comment = source.comment
                for info in source.infolist():
                    payload = core_payload if info.filename == "docProps/core.xml" else source.read(info.filename)
                    destination.writestr(info, payload)

        with ZipFile(staged) as verification:
            bad_member = verification.testzip()
            if bad_member is not None:
                raise StampError(f"Stamped DOCX verification failed at member: {bad_member}")
            stamped_core = ET.fromstring(verification.read("docProps/core.xml"))
            stamped_identifier = stamped_core.find(f"{{{DC_NS}}}identifier")
            if stamped_identifier is None or stamped_identifier.text != IDENTIFIER_PREFIX + fingerprint:
                raise StampError("Stamped DOCX fingerprint verification failed")
        os.replace(staged, output_path)
    except (BadZipFile, ET.ParseError, OSError) as exc:
        raise StampError(f"DOCX could not be stamped safely: {exc}") from exc
    finally:
        staged.unlink(missing_ok=True)

    return {
        "ok": True,
        "input": str(input_path),
        "output": str(output_path),
        "spec": str(spec_path),
        "spec_sha256": fingerprint,
        **package_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="edited passive base DOCX")
    parser.add_argument("--spec", type=Path, required=True, help="final report specification JSON")
    parser.add_argument("--output", type=Path, required=True, help="separate stamped DOCX output")
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    try:
        result = stamp(args.input, args.spec, args.output, force=args.force)
    except StampError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
