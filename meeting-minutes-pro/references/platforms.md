# Cross-agent installation

The same skill directory follows the shared `SKILL.md` agent-skill convention used by Codex and Claude Code and supported by current Tencent WorkBuddy desktop builds. Install the directory rather than copying only `SKILL.md`, because transcription depends on bundled scripts and references.

## User-level locations

- Codex: `$CODEX_HOME/skills/meeting-minutes-pro/`；未设置 `CODEX_HOME` 时使用 `~/.codex/skills/meeting-minutes-pro/`
- Claude Code: `~/.claude/skills/meeting-minutes-pro/`
- Tencent WorkBuddy: `~/.workbuddy/skills/meeting-minutes-pro/`

If `CLAUDE_CONFIG_DIR` is set, the installer places the Claude Code copy under that directory's `skills/` folder.

From an extracted release, run:

```text
python meeting-minutes-pro/scripts/install_skill.py --target all
```

Use `--target codex`, `--target claude`, or `--target workbuddy` for one platform. Add `--force` to update public skill files. The updater preserves destination project glossaries and banned phrases and excludes source private glossary files; it does not delete the destination directory.

Restart the agent if the new skill is not detected. Invoke it explicitly as `$meeting-minutes-pro` in Codex, `/meeting-minutes-pro` in Claude Code, or select/call the installed skill in WorkBuddy. Agents may also activate it automatically when an uploaded media file and a transcription request match the description.

WorkBuddy's installation UI and marketplace behavior can vary by release. If a manually copied folder is not detected after restart, use WorkBuddy's Skills panel to import or install the extracted skill/repository instead of guessing another filesystem location.

Platform documentation:

- Codex skills: <https://learn.chatgpt.com/docs/build-skills>
- Claude Code skills: <https://code.claude.com/docs/en/skills>
- Tencent WorkBuddy skills: <https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Create-Skills>

## Distribution

Publish the public skill files in a Git repository or ZIP archive. Exclude project files and banned phrases at the root of `glossary/`; include only its README and public `industry/` subtree. A manual ZIP does not honor `.gitignore`. Do not redistribute cached model weights inside the skill package — this applies to the Qwen3-ASR weights (Apache-2.0) and equally to the FunASR/Paraformer weights downloaded from ModelScope, which carry the ModelScope model license shown on each model card. Link to the upstream projects and preserve their license notices when redistributing derivative model code or weights.
