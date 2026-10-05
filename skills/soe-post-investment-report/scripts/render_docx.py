#!/usr/bin/env python3
"""Render a passive, self-contained DOCX to PDF and optional page PNGs.

The renderer treats the document as untrusted data.  Macros, external
relationships, attached templates, embedded/active objects, altChunk content,
linked images and unsafe field instructions are rejected before an Office
process is started. Microsoft Word is opened read-only with automation security
forced to "disable", and LibreOffice runs with a fresh temporary user profile.
Existing output files are never replaced unless ``--force`` is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile


MACRO_PARTS = (
    "vbaproject.bin",
    "vbadata.xml",
    "wordbasic.bin",
)

# Preflight limits keep XML inspection bounded before an Office process sees the
# package.  They are deliberately generous for a normal report while preventing
# a tiny archive from forcing unbounded allocation during the security check.
MAX_PACKAGE_PARTS = 20_000
MAX_TOTAL_UNCOMPRESSED_BYTES = 1_073_741_824  # 1 GiB
MAX_XML_PART_BYTES = 67_108_864  # 64 MiB

UNSAFE_PART_PREFIXES = (
    "word/embeddings/",
    "word/activex/",
)

UNSAFE_RELATIONSHIP_TYPE_SUFFIXES = (
    "/attachedtemplate",
    "/oleobject",
    "/package",
    "/control",
    "/activexcontrolbinary",
    "/afchunk",
    "/vbaproject",
    "/vbaprojectsignature",
)

UNSAFE_CONTENT_TYPE_TOKENS = (
    "macroenabled",
    "vnd.ms-office.vbaproject",
    "activex",
    "oleobject",
)

EXTERNAL_TARGET_RE = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*:|//|\\\\)",
    flags=re.IGNORECASE,
)

DDE_FIELD_RE = re.compile(r"(?<![A-Z0-9_])DDE(?:AUTO)?(?![A-Z0-9_])", re.IGNORECASE)

EXTERNAL_CONTENT_FIELD_RE = re.compile(
    r"(?<![A-Z0-9_])(?:INCLUDEPICTURE|INCLUDETEXT|LINK|DATABASE)(?![A-Z0-9_])",
    re.IGNORECASE,
)


class RenderError(RuntimeError):
    """A user-actionable rendering failure."""


def configure_utf8_stdio() -> None:
    """Prefer readable Unicode CLI output without affecting module imports."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def _emit(payload: dict[str, object], *, stream: object = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_name(name: str) -> str:
    """Return the local component of an expanded XML name."""
    return name.rsplit("}", 1)[-1].casefold()


def _attribute(element: ET.Element, local_name: str) -> str:
    wanted = local_name.casefold()
    for name, value in element.attrib.items():
        if _local_name(name) == wanted:
            return value
    return ""


def _bounded_xml(archive: ZipFile, member: str) -> bytes:
    info = archive.getinfo(member)
    if info.file_size > MAX_XML_PART_BYTES:
        raise RenderError(
            f"DOCX XML part is too large for safe preflight ({info.file_size} bytes): {member}"
        )
    payload = archive.read(member)
    lowered = payload.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise RenderError(f"DTD/entity declarations are refused in DOCX XML: {member}")
    return payload


def _parse_xml(archive: ZipFile, member: str) -> ET.Element:
    try:
        return ET.fromstring(_bounded_xml(archive, member))
    except ET.ParseError as exc:
        raise RenderError(f"Malformed XML in DOCX package part {member}: {exc}") from exc


def _relationship_findings(archive: ZipFile, members: list[str]) -> list[str]:
    findings: list[str] = []
    for member in members:
        if not member.casefold().endswith(".rels"):
            continue
        root = _parse_xml(archive, member)
        for relationship in root.iter():
            if _local_name(relationship.tag) != "relationship":
                continue
            rel_id = _attribute(relationship, "Id") or "(no Id)"
            rel_type = _attribute(relationship, "Type").strip()
            target = _attribute(relationship, "Target").strip()
            target_mode = _attribute(relationship, "TargetMode").strip()
            rel_type_folded = rel_type.casefold().rstrip("/")

            if target_mode.casefold() == "external":
                findings.append(f"external relationship {member}#{rel_id}")
            elif target and EXTERNAL_TARGET_RE.match(target):
                # Reject URI/UNC targets even when a malformed relationship omits
                # TargetMode=External; Office must never be asked to resolve them.
                findings.append(f"external target {member}#{rel_id}")

            if any(
                rel_type_folded.endswith(suffix)
                for suffix in UNSAFE_RELATIONSHIP_TYPE_SUFFIXES
            ):
                kind = rel_type_folded.rsplit("/", 1)[-1] or "unsafe"
                findings.append(f"{kind} relationship {member}#{rel_id}")
    return findings


def _markup_findings(archive: ZipFile, members: list[str]) -> list[str]:
    findings: list[str] = []
    for member in members:
        folded_member = member.casefold()
        if not (folded_member.startswith("word/") and folded_member.endswith(".xml")):
            continue
        root = _parse_xml(archive, member)
        instruction_fragments: list[str] = []
        for element in root.iter():
            local = _local_name(element.tag)
            if local == "attachedtemplate":
                findings.append(f"attachedTemplate markup in {member}")
            elif local == "altchunk":
                findings.append(f"altChunk markup in {member}")
            elif local in {"oleobject", "object", "control"}:
                findings.append(f"embedded/active object markup <{local}> in {member}")
            elif local == "blip" and _attribute(element, "link"):
                findings.append(f"externally linked image markup in {member}")
            elif local == "imagedata" and (
                _attribute(element, "href") or _attribute(element, "src")
            ):
                findings.append(f"externally linked image/object markup in {member}")

            if local == "instrtext" and element.text:
                instruction_fragments.append(element.text)
            elif local == "fldsimple":
                instruction_fragments.append(_attribute(element, "instr"))

        # Field instructions may be split across multiple w:instrText runs, so
        # inspect both the separated form and the run-concatenated form.
        separated = " ".join(instruction_fragments)
        concatenated = "".join(instruction_fragments)
        if DDE_FIELD_RE.search(separated) or DDE_FIELD_RE.search(concatenated):
            findings.append(f"DDE/DDEAUTO field instruction in {member}")
        if EXTERNAL_CONTENT_FIELD_RE.search(separated) or EXTERNAL_CONTENT_FIELD_RE.search(
            concatenated
        ):
            findings.append(f"external content/object field instruction in {member}")
    return findings


def inspect_docx(path: Path) -> dict[str, object]:
    """Reject active/external DOCX content before starting an Office process."""
    if path.suffix.casefold() != ".docx":
        raise RenderError("Input must be a .docx file; macro-enabled Office formats are not accepted")
    try:
        with ZipFile(path) as archive:
            members = archive.namelist()
            folded_members = [member.casefold() for member in members]
            if len(members) > MAX_PACKAGE_PARTS:
                raise RenderError(
                    f"DOCX has too many package parts for safe preflight: {len(members)}"
                )
            total_size = sum(info.file_size for info in archive.infolist())
            if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise RenderError(
                    "DOCX expands beyond the safe preflight limit "
                    f"({total_size} bytes uncompressed)"
                )
            if len(set(folded_members)) != len(folded_members):
                raise RenderError("DOCX contains duplicate or case-colliding package part names")
            if any(
                member.startswith(("/", "\\"))
                or "\\" in member
                or ".." in Path(member).parts
                for member in members
            ):
                raise RenderError("DOCX contains an unsafe package part path")
            if "word/document.xml" not in folded_members:
                raise RenderError("The input is not a valid WordprocessingML DOCX package")
            macro_hits = sorted(
                original
                for original in members
                if any(part in original.casefold() for part in MACRO_PARTS)
            )
            unsafe_part_hits = sorted(
                original
                for original in members
                if any(original.casefold().startswith(prefix) for prefix in UNSAFE_PART_PREFIXES)
            )

            findings: list[str] = []
            if macro_hits:
                findings.append("macro parts: " + ", ".join(macro_hits))
            if unsafe_part_hits:
                findings.append("embedded/ActiveX parts: " + ", ".join(unsafe_part_hits))

            content_types = _parse_xml(archive, "[Content_Types].xml")
            for element in content_types.iter():
                content_type = _attribute(element, "ContentType").casefold()
                if content_type and any(
                    token in content_type for token in UNSAFE_CONTENT_TYPE_TOKENS
                ):
                    findings.append(f"unsafe content type: {content_type}")

            findings.extend(_relationship_findings(archive, members))
            findings.extend(_markup_findings(archive, members))
    except (BadZipFile, KeyError, OSError) as exc:
        raise RenderError(f"The input is not a readable DOCX package: {exc}") from exc

    if findings:
        unique_findings = list(dict.fromkeys(findings))
        preview = "; ".join(unique_findings[:12])
        if len(unique_findings) > 12:
            preview += f"; and {len(unique_findings) - 12} more finding(s)"
        raise RenderError(
            "Unsafe active or externally linked DOCX content was refused; "
            f"convert to a clean, self-contained .docx first ({preview})"
        )
    return {
        "valid_docx": True,
        "contains_macros": False,
        "contains_external_relationships": False,
        "contains_embedded_or_active_content": False,
        "contains_dde_fields": False,
    }


def _powershell() -> str | None:
    if os.name != "nt":
        return None
    return shutil.which("powershell") or shutil.which("pwsh")


def render_with_word(docx: Path, pdf: Path, timeout: int) -> tuple[bool, str]:
    """Render through Word COM with macros, alerts and link updates disabled."""
    shell = _powershell()
    if not shell:
        return False, "PowerShell is unavailable"

    # Paths are passed as process arguments, not interpolated into PowerShell,
    # so quotes, apostrophes and shell metacharacters in filenames stay inert.
    script = r"""
param(
  [Parameter(Mandatory=$true)][string]$InputDocx,
  [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference = 'Stop'
$word = $null
$doc = $null
try {
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $word.DisplayAlerts = 0
  # msoAutomationSecurityForceDisable.  Never execute document macros.
  $word.AutomationSecurity = 3
  $word.Options.UpdateLinksAtOpen = $false
  $word.Options.SaveNormalPrompt = $false
  # ConfirmConversions=false, ReadOnly=true, AddToRecentFiles=false.
  $doc = $word.Documents.Open($InputDocx, $false, $true, $false)
  # wdExportFormatPDF = 17. ExportAsFixedFormat does not modify the DOCX.
  $doc.ExportAsFixedFormat($OutputPdf, 17)
} finally {
  if ($null -ne $doc) { try { $doc.Close($false) } catch {} }
  if ($null -ne $word) { try { $word.Quit() } catch {} }
}
"""
    script_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ps1", delete=False, encoding="utf-8-sig", newline="\n"
        ) as handle:
            handle.write(script)
            script_path = Path(handle.name)
        proc = subprocess.run(
            [
                shell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-InputDocx",
                str(docx),
                "-OutputPdf",
                str(pdf),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"Microsoft Word conversion timed out after {timeout} seconds"
    finally:
        if script_path is not None:
            script_path.unlink(missing_ok=True)

    if proc.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 0:
        return True, ""
    detail = (proc.stderr or proc.stdout or "Word did not create a PDF").strip()
    return False, detail[-2000:]


def find_soffice() -> str | None:
    configured = os.environ.get("SOFFICE")
    candidates = [
        configured,
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "C:/Program Files/LibreOffice/program/soffice.exe",
        "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())
    return None


def render_with_libreoffice(docx: Path, pdf: Path, timeout: int) -> tuple[bool, str]:
    """Render through LibreOffice using a disposable, isolated user profile."""
    soffice = find_soffice()
    if not soffice:
        return False, "LibreOffice (soffice) is unavailable"
    try:
        with tempfile.TemporaryDirectory(prefix="soe-pir-lo-") as temp_name:
            temp_root = Path(temp_name)
            out_dir = temp_root / "out"
            profile_dir = temp_root / "profile"
            out_dir.mkdir()
            profile_dir.mkdir()
            proc = subprocess.run(
                [
                    soffice,
                    f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
                    "--headless",
                    "--nologo",
                    "--nodefault",
                    "--nofirststartwizard",
                    "--norestore",
                    "--nolockcheck",
                    "--convert-to",
                    "pdf:writer_pdf_Export",
                    "--outdir",
                    str(out_dir),
                    str(docx),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            produced = out_dir / f"{docx.stem}.pdf"
            if proc.returncode != 0 or not produced.is_file() or produced.stat().st_size == 0:
                detail = (proc.stderr or proc.stdout or "LibreOffice did not create a PDF").strip()
                return False, detail[-2000:]
            shutil.copyfile(produced, pdf)
            return True, ""
    except subprocess.TimeoutExpired:
        return False, f"LibreOffice conversion timed out after {timeout} seconds"


def find_pdftoppm() -> str | None:
    configured = os.environ.get("PDFTOPPM")
    candidates = [configured, shutil.which("pdftoppm")]
    for candidate in candidates:
        if candidate and Path(candidate).expanduser().is_file():
            return str(Path(candidate).expanduser().resolve())
    return None


def pdf_page_count(pdf: Path) -> int | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        data = pdf.read_bytes()
        count = len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", data))
        return count or None
    try:
        return len(PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001 - page count is supplementary evidence
        return None


def render_pngs(pdf: Path, output_dir: Path, dpi: int, timeout: int) -> list[Path]:
    converter = find_pdftoppm()
    if not converter:
        raise RenderError("PNG output requires Poppler's pdftoppm (or the PDFTOPPM environment variable)")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_prefix = output_dir / "page"
    try:
        proc = subprocess.run(
            [converter, "-png", "-r", str(dpi), str(pdf), str(raw_prefix)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"PNG conversion timed out after {timeout} seconds") from exc
    raw = sorted(
        output_dir.glob("page-*.png"),
        key=lambda item: int(item.stem.rsplit("-", 1)[-1]),
    )
    if proc.returncode != 0 or not raw:
        detail = (proc.stderr or proc.stdout or "pdftoppm did not create page images").strip()
        raise RenderError(detail[-2000:])
    renamed: list[Path] = []
    width = max(3, len(str(len(raw))))
    for index, current in enumerate(raw, start=1):
        target = output_dir / f"page-{index:0{width}d}.png"
        current.rename(target)
        renamed.append(target)
    return renamed


def _commit_file(source: Path, destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise RenderError(f"Output already exists (use --force to replace it): {destination}")
    staged = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copyfile(source, staged)
        os.replace(staged, destination)
    finally:
        staged.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="passive, self-contained input DOCX"
    )
    parser.add_argument("--output", type=Path, help="PDF path (default: beside the DOCX)")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="render-binding manifest path (default: <output>.render.json)",
    )
    parser.add_argument(
        "--renderer",
        choices=("auto", "word", "libreoffice"),
        default="auto",
        help="renderer selection (default: Word on Windows, then LibreOffice)",
    )
    parser.add_argument(
        "--png-dir",
        type=Path,
        help="render every page as PNGs here (optional for drafts; required for final certification)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="PNG resolution, 72-600 (default: 150)")
    parser.add_argument("--timeout", type=int, default=300, help="per-process timeout in seconds")
    parser.add_argument("--force", action="store_true", help="replace colliding PDF/PNG output files")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    try:
        docx = args.input.expanduser().resolve()
        if not docx.is_file():
            raise RenderError(f"Input DOCX not found: {docx}")
        package = inspect_docx(docx)
        pdf = (args.output or docx.with_suffix(".pdf")).expanduser().resolve()
        if pdf.suffix.casefold() != ".pdf":
            raise RenderError("--output must use the .pdf extension")
        manifest = (
            args.manifest.expanduser().resolve()
            if args.manifest
            else pdf.with_suffix(pdf.suffix + ".render.json")
        )
        if manifest.suffix.casefold() != ".json":
            raise RenderError("--manifest must use the .json extension")
        png_dir = args.png_dir.expanduser().resolve() if args.png_dir else None
        if not 72 <= args.dpi <= 600:
            raise RenderError("--dpi must be between 72 and 600")
        if args.timeout < 10:
            raise RenderError("--timeout must be at least 10 seconds")
        if pdf.exists() and not args.force:
            raise RenderError(f"Output already exists (use --force to replace it): {pdf}")
        if manifest.exists() and not args.force:
            raise RenderError(f"Render manifest already exists (use --force to replace it): {manifest}")

        attempts: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="soe-pir-render-") as temp_name:
            temp_root = Path(temp_name)
            temp_pdf = temp_root / "rendered.pdf"
            renderer: str | None = None
            candidates = (
                (["word", "libreoffice"] if os.name == "nt" else ["libreoffice"])
                if args.renderer == "auto"
                else [args.renderer]
            )
            for candidate in candidates:
                if candidate == "word":
                    ok, detail = render_with_word(docx, temp_pdf, args.timeout)
                else:
                    ok, detail = render_with_libreoffice(docx, temp_pdf, args.timeout)
                attempts.append({"renderer": candidate, "status": "ok" if ok else "failed", "detail": detail})
                if ok:
                    renderer = candidate
                    break
                temp_pdf.unlink(missing_ok=True)
            if renderer is None:
                raise RenderError("No renderer succeeded: " + "; ".join(
                    f"{item['renderer']}: {item['detail']}" for item in attempts
                ))

            temp_pngs: list[Path] = []
            if png_dir is not None:
                temp_pngs = render_pngs(temp_pdf, temp_root / "png", args.dpi, args.timeout)
                collisions = [
                    png_dir / f"{pdf.stem}-page-{index:03d}.png"
                    for index in range(1, len(temp_pngs) + 1)
                    if (png_dir / f"{pdf.stem}-page-{index:03d}.png").exists()
                ]
                if collisions and not args.force:
                    raise RenderError(
                        "PNG output already exists (use --force to replace): "
                        + ", ".join(str(path) for path in collisions[:5])
                    )

            # Commit only after rendering and all collision checks succeed.
            _commit_file(temp_pdf, pdf, args.force)
            committed_pngs: list[Path] = []
            if png_dir is not None:
                png_dir.mkdir(parents=True, exist_ok=True)
                for index, source in enumerate(temp_pngs, start=1):
                    destination = png_dir / f"{pdf.stem}-page-{index:03d}.png"
                    _commit_file(source, destination, args.force)
                    committed_pngs.append(destination)

            manifest_payload = {
                "schema_version": "1.0",
                "input_name": docx.name,
                "input_sha256": _sha256(docx),
                "pdf_name": pdf.name,
                "pdf_sha256": _sha256(pdf),
                "renderer": renderer,
                "pages": pdf_page_count(pdf),
                "png_files": [
                    {
                        "path": os.path.relpath(path, manifest.parent),
                        "sha256": _sha256(path),
                    }
                    for path in committed_pngs
                ],
            }
            temp_manifest = temp_root / "render-manifest.json"
            temp_manifest.write_text(
                json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _commit_file(temp_manifest, manifest, args.force)

        _emit(
            {
                "ok": True,
                "input": str(docx),
                **package,
                "renderer": renderer,
                "pdf": str(pdf),
                "manifest": str(manifest),
                "pages": pdf_page_count(pdf),
                "png_files": [str(path) for path in committed_pngs],
                "dpi": args.dpi if committed_pngs else None,
                "attempts": attempts,
                "note": (
                    "Inspect every rendered page before delivery; active and externally linked "
                    "package content was refused before rendering."
                ),
            }
        )
        return 0
    except RenderError as exc:
        _emit({"ok": False, "error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
