# Platform compatibility and Chinese display name

The portable skill slug is `soe-post-investment-report`. Keep that ASCII, lowercase, hyphenated value in the folder name and the `SKILL.md` `name` field. Several Agent Skills clients validate that field strictly, so replacing it with Chinese would make the package invalid on those clients.

The intended user-facing label is always `国企股权投资投后报告`. This package declares it in both `metadata.display_name` and `agents/openai.yaml`. Use the same label in any platform import, marketplace, API, or settings screen that exposes a separate display-title field.

Runtime requirements are repeated in the skill body and stored as `metadata.compatibility`. The optional top-level `compatibility` extension is deliberately omitted so the same package passes stricter validators that accept only the common core frontmatter fields. Clients that recognize only the optional top-level extension may therefore ignore the machine-readable runtime note; the README and skill body remain authoritative.

| Client | Package/import route | Chinese-name behavior | Required note |
| --- | --- | --- | --- |
| Codex / OpenAI | Install under the configured skills directory or upload the directory/ZIP through a supported skills interface. `scripts/install_skill.py --target codex` uses the common user-level location. | `agents/openai.yaml` and `metadata.display_name` request the Chinese label where the client honors those fields. | Product availability and upload controls vary by account and version. |
| Claude | Install the folder under the Claude skills directory, or upload a ZIP through the Skills API. `scripts/install_skill.py --target claude` supports the common local directory. | When using the API, set `display_title` to `国企股权投资投后报告`; local clients that ignore display metadata may show the slug. | Preserve the package's top-level skill folder in ZIP uploads. |
| Qoder | Install under the Qoder skills directory; the helper supports `--target qoder`. | Qoder's required `name` is lowercase ASCII, so a client that does not honor optional display metadata will show `soe-post-investment-report`. | Do not change the standards-compliant slug to Chinese. |
| Trae IDE / CLI | Use a project skill directory; the helper supports `--target trae` and `--target trae-cli` with `--project`. | Set the Chinese label manually if the client exposes a display-name field; otherwise the slug may be visible. | Confirm the current project-level directory in the installed Trae version. |
| WorkBuddy / CodeBuddy | Use the project's skills directory; the helper supports `--target workbuddy --project ...`. | Set the Chinese label in import or marketplace UI where available; clients that ignore optional metadata may show the slug. | Tencent product naming and local directory conventions can differ by edition. |
| Other Agent Skills clients | Copy or upload the complete folder or portable ZIP. | Prefer `国企股权投资投后报告` as the display title; expect the slug on clients that expose only the required standard `name`. | Validate trigger behavior, relative resources, Python availability, and rendering before production use. |

Official references used for these compatibility decisions:

- [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
- [OpenAI Skills API create method](https://developers.openai.com/api/reference/python/resources/skills/methods/create)
- [Claude Agent Skills](https://platform.claude.com/docs/en/managed-agents/skills) and [Claude Skills create API](https://platform.claude.com/docs/en/api/beta/skills/create)
- [Qoder Skills](https://docs.qoder.com/zh/cli/Skills)
- [Trae Skills](https://docs.trae.cn/work_skills), [Trae CLI Skills](https://docs.trae.cn/cli_skills), and [Trae IDE Skills](https://docs.trae.cn/ide_skills)
- [Tencent Cloud WorkBuddy skills](https://cloud.tencent.com/document/product/1831/134516)

## Certification boundary

Folder compatibility is not document certification. A client may execute the English instructions and generate a structurally valid DOCX without being able to prove pagination. Final delivery still requires Microsoft Word on Windows or LibreOffice rendering, PDF page-count validation, a standalone `附件1` boundary, and inspection of every page. Without that renderer loop, label the output `未认证草稿`.
