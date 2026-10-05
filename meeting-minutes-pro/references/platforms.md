# Cross-agent installation

各客户端（Claude、ChatGPT、Codex、Kimi、豆包、智谱 GLM、WorkBuddy、TRAE、Qoder）的安装入口、调用方式、运行环境适配与验收统一见 [agent-compatibility.md](agent-compatibility.md)。本文只记录会议纪要技能特有的要求。

Install the whole directory rather than copying only `SKILL.md`: transcription, review, fact checks and DOCX output depend on the bundled scripts, references and `glossary/industry/`. DOCX fonts are supplied by the licensed user; preparation is described in `assets/fonts/README.md`.

## Installers

The recommended installer covers every supported client and keeps local user data:

```text
python meeting-minutes-pro/scripts/skill_portability.py agents
python meeting-minutes-pro/scripts/skill_portability.py install --agent claude-code --agent codex --agent workbuddy --apply
python meeting-minutes-pro/scripts/skill_portability.py install --detect --apply
```

Project glossaries and banned phrases under `glossary/` (everything except `README.md` and `industry/`) are user data: they are never packaged, never reported as stale files, and `--replace` carries them into the new version after moving the old folder to `skill-backups/`.

`scripts/install_skill.py` remains for existing automation: `--target codex|claude|workbuddy|all`, `--force` to update public files while keeping destination glossaries. Its Codex target is now `~/.agents/skills/meeting-minutes-pro/`, the folder current Codex and the ChatGPT desktop app scan; older Codex builds that still read `$CODEX_HOME/skills` can use `skill_portability.py install --agent codex-legacy`.

Restart the agent if the new skill is not detected. Invoke it as `$meeting-minutes-pro` in Codex, `@meeting-minutes-pro` in ChatGPT, `/meeting-minutes-pro` in Claude Code, `/skill:meeting-minutes-pro` in Kimi Code, or pick it from the skill list (`/` or `@`) in Kimi Work, 豆包, WorkBuddy, TRAE and Qoder. Agents may also activate it automatically when an uploaded media file and a transcription request match the description.

## Execution environment

Local transcription needs a host that runs Python on the user's machine (Claude Code, Codex, ChatGPT desktop, Kimi Work / Kimi Code, 豆包 desktop work mode, WorkBuddy, TRAE, Qoder, ZCode, AutoClaw). Cloud sandboxes such as claude.ai or ChatGPT workspace skills cannot download the ASR models or read local recordings; there the skill can only turn a user-supplied transcript into minutes, and must say so. The ASR runtime is installed separately by `scripts/bootstrap_runtime.py` with the user's permission for network downloads.

## Distribution

Publish the public skill files in a Git repository or ZIP archive; `skill_portability.py package --output-dir <dir>` builds a reproducible ZIP that already excludes private glossary files, caches and virtual environments. A hand-made ZIP does not honor `.gitignore`. Do not redistribute cached model weights inside the skill package — this applies to the Qwen3-ASR weights (Apache-2.0) and equally to the FunASR/Paraformer weights downloaded from ModelScope, which carry the ModelScope model license shown on each model card. Link to the upstream projects and preserve their license notices when redistributing derivative model code or weights.
