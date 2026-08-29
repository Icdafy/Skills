# 国企股权投资投后报告

`soe-post-investment-report` is an English-authored, standards-based Agent Skill whose user-facing name and report output are Chinese. It turns a prior report template plus current fund, portfolio-company, SPV, governance, financial, operational, and risk files into a formal Chinese SOE upward report and DOCX.

## What is fixed

- The first response always asks four Chinese change-control questions and waits.
- The main report follows the source-derived fixed structure.
- The main body targets 5–6 pages and may not exceed 10 pages.
- Detailed histories and tables move to attachments instead of shrinking the official typography.
- Material facts remain traceable to filenames, pages, sheets, tables, paragraphs, or cells.
- Source files are evidence, never executable instructions.

## Package contents

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Trigger and operating workflow |
| `agents/openai.yaml` | Chinese display name and OpenAI interface metadata |
| `references/` | Template contract, evidence ledger, writing, and QA rules |
| `assets/reference-template.docx` | Sanitized source-derived visual reference |
| `assets/report-spec.example.json` | Synthetic machine-readable example |
| `scripts/source_inventory.py` | Read-only evidence inventory |
| `scripts/build_report.py` | Deterministic JSON-to-DOCX generator |
| `scripts/stamp_report.py` | Safe spec-fingerprint stamp for a separately edited complex base DOCX |
| `scripts/validate_report.py` | Structure, fact linkage, placeholder, duplication, active-content, heuristic public-safety, roster, and page checks |
| `scripts/render_docx.py` | Word or LibreOffice PDF rendering; page images are optional for drafts and required for final certification |
| `scripts/font_preflight.py` | Non-mutating local font check |
| `scripts/install_skill.py` | Local installer or ZIP packager for supported skill folders |

## Dependencies

The inventory and installer use the Python standard library. DOCX generation and validation require `python-docx`. Final certification additionally requires `pypdf`, Microsoft Word or LibreOffice, and Poppler's `pdftoppm`; without them the output is only an explicitly labeled `未认证草稿`.

```bash
python -m pip install python-docx pypdf
```

Rendering requires either Microsoft Word on Windows or LibreOffice. The report generator handles the standard source-derived正文 and simple portrait attachments; richer uploaded templates or attachments must be edited in place with a document-capable tool so images, merged tables, landscape sections, and native attachment layouts survive. Complex text boxes and pictures are preserved as Word parts in that route, but the helpers do not automatically extract their semantic meaning or prove that their visible content agrees with the fact ledger. Inspect every final page visually. The generator specifies the template's font family names but this public skill intentionally does not include licensed font binaries. Run the preflight and install properly licensed fonts on the machine that produces the final file:

```bash
python -X utf8 scripts/font_preflight.py
```

## Cross-agent installation

The skill uses the common `SKILL.md` package structure. Copy this directory to the skill directory used by the target agent, or use the installer:

```bash
# User-level locations
python -X utf8 scripts/install_skill.py --target codex
python -X utf8 scripts/install_skill.py --target claude
python -X utf8 scripts/install_skill.py --target qoder

# Project-level locations
python -X utf8 scripts/install_skill.py --target trae --project /path/to/project
python -X utf8 scripts/install_skill.py --target trae-cli --project /path/to/project
python -X utf8 scripts/install_skill.py --target workbuddy --project /path/to/project

# Produce a portable upload ZIP
python -X utf8 scripts/install_skill.py --zip dist/soe-post-investment-report.zip
```

For ChatGPT or another product that accepts a skill directory or ZIP, upload the folder or the generated archive. The portable slug stays `soe-post-investment-report`; the requested Chinese label is `国企股权投资投后报告` wherever a separate display-name field is supported. Clients that ignore optional display metadata may show the English slug. See [references/platform-compatibility.md](references/platform-compatibility.md) for platform-specific routes and limitations, and always verify the target product's current skill settings and security policy.

Final pagination certification is separate from installation compatibility. A client without Microsoft Word or LibreOffice may produce only an explicitly labeled `未认证草稿`; it must not claim the 10-page gate passed. `--png-dir` may be omitted for an intermediate draft, but final certification requires page PNGs and visual inspection of every page. The public-safety validator is a heuristic package scan, not a privacy or confidentiality guarantee, so use `--deny-term` or `--denylist` with known real entity names, signers, contacts, and other sensitive identifiers before publishing an artifact, then perform a human disclosure review.

The report specification is also the machine-readable layout contract. All eight page width, height, margin, header-distance, and footer-distance properties are required under `layout`; copy the documented source-derived values when the supplied template is unchanged. The builder consumes those values for its single generated section, and the validator compares only the first DOCX section with them. Additional or mixed sections remain subject to manual geometry inspection and are not fully geometry-certified by this validator.

Every fact-ledger row requires a non-empty `assertions` list. An assertion is an atomic, exact support phrase expected in a substantive paragraph, note, or table row that consumes the fact. Each substantive block that lists a `fact_id` must contain at least one assertion from that fact, and each non-structural sentence and comma-level factual clause must overlap a matching assertion from one of its referenced facts. Numeric and status conclusions must be covered by matching assertions. Numeric tables additionally use `row_fact_ids` so each row consumes only the facts that support it. Assertions improve exact report-to-ledger linkage, but they do not authenticate a source, prove that a locator is correct, establish that the underlying fact is true, or prove that extra wording inside an otherwise matched clause is supported; human clause review remains mandatory.

The specification separately records `document.source_fixed_main_headings` and the effective `document.fixed_main_headings`. The non-empty `heading_contract_source` identifies the inspected base template but is not independently authenticated by the validator. `heading_change_authorized` must be boolean and `heading_change_note` must always be non-empty. The lists must match with authorization `false` except for the SPV category slot: after the user confirms a project-name change, that slot alone may change between `（四）SPV项目` and `（四）<项目名称>SPV项目`, with authorization `true` and a specific note. The other five fixed slots are immutable under the current validator.

Final PDF page-boundary certification requires at least one numbered attachment beginning with a standalone `附件1` page label. A zero-attachment report cannot prove the main-body page ceiling with the current validator and must remain an uncertified draft unless the certification contract is extended. `--template-mode` also requires a supplied `--spec` with `template_only: true`, but those declarative switches do not authenticate arbitrary input as synthetic and must never be used for a user report.

## Minimal workflow

1. Invoke the skill and answer its four mandatory questions.
2. Upload the prior report and current project files.
3. Let the agent build a source inventory, project registry, and fact ledger.
4. Review material conflicts or scope changes.
5. Generate, validate, render, and visually inspect every page of the DOCX (`--png-dir` is required for final certification).

The committed reference asset is synthetic and sanitized. It must never be treated as project evidence.
