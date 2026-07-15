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

Use `--target codex`, `--target claude`, or `--target workbuddy` for one platform. Add `--force` only when deliberately replacing an older installed copy.

Restart the agent if the new skill is not detected. Invoke it explicitly as `$meeting-minutes-pro` in Codex, `/meeting-minutes-pro` in Claude Code, or select/call the installed skill in WorkBuddy. Agents may also activate it automatically when an uploaded media file and a transcription request match the description.

WorkBuddy's installation UI and marketplace behavior can vary by release. If a manually copied folder is not detected after restart, use WorkBuddy's Skills panel to import or install the extracted skill/repository instead of guessing another filesystem location.

Platform documentation:

- Codex skills: <https://learn.chatgpt.com/docs/build-skills>
- Claude Code skills: <https://code.claude.com/docs/en/skills>
- Tencent WorkBuddy skills: <https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Practice-Cases/Create-Skills>

## Distribution

Publish the whole `meeting-minutes-pro` directory in a Git repository or ZIP archive. Do not redistribute cached model weights inside the skill package. Link to the Qwen3-ASR upstream project and preserve its Apache-2.0 license notices when redistributing derivative model code or weights.
