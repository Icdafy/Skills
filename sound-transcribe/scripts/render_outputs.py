"""Render final artifacts from a schema-v2 transcript JSON (sound-transcribe v2).

Regenerates txt / md / srt / vtt / html from the JSON so that diarization,
refinement, and renaming steps only need to update the JSON once and then
re-render everything consistently.

Subtitle quality: SRT/VTT cues are re-split using word timestamps when
available — max 2 lines, ~20 CJK units per line, max 6s per cue, preferring
breaks at punctuation. Without word timestamps it falls back to proportional
splitting by punctuation.

The HTML output is a single self-contained reader: embedded transcript,
audio player with click-to-seek, speaker colors, search, and low-confidence
highlighting.
"""

import argparse
import html as html_mod
import json
import os
import pathlib
import re
import sys

BREAK_AFTER = "。！？!?；;，,、：:…"
CJK_RE = re.compile(r"[⺀-鿿　-〿豈-﫿＀-￯]")
TOKEN_RE = re.compile(r"\s+|[⺀-鿿　-〿豈-﫿＀-￯]|[^\s⺀-鿿　-〿豈-﫿＀-￯]+")


def ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    hours, rem = divmod(whole, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_srt_time(seconds: float) -> str:
    return format_time(seconds).replace(".", ",")


def text_units(text: str) -> float:
    """CJK char = 1 unit, everything else = 0.5 (subtitle width heuristic)."""
    units = 0.0
    for ch in text:
        units += 1.0 if CJK_RE.match(ch) else 0.5
    return units


# ---------------------------------------------------------------- cue building

def words_to_clauses(words: list) -> list:
    clauses, current = [], []
    for word in words:
        current.append(word)
        token = word["word"].strip()
        if token and token[-1] in BREAK_AFTER:
            clauses.append(current)
            current = []
    if current:
        clauses.append(current)
    return clauses


def pack_word_clauses(clauses: list, max_units: float, max_seconds: float) -> list:
    cues, current = [], []
    for clause in clauses:
        candidate = current + clause
        candidate_text = "".join(w["word"] for w in candidate)
        candidate_dur = candidate[-1]["end"] - candidate[0]["start"]
        if current and (text_units(candidate_text) > max_units or candidate_dur > max_seconds):
            cues.append(current)
            current = list(clause)
        else:
            current = candidate
        # Hard-split a single clause that is itself far too long.
        while len(current) > 1 and text_units("".join(w["word"] for w in current)) > max_units * 1.5:
            acc, cut = 0.0, len(current) - 1
            for index, word in enumerate(current):
                acc += text_units(word["word"])
                if acc > max_units:
                    cut = max(1, index)
                    break
            cues.append(current[:cut])
            current = current[cut:]
    if current:
        cues.append(current)
    return cues


def split_text_proportionally(item: dict, max_units: float) -> list:
    """Fallback when no word timestamps: split at punctuation, allocate time by width."""
    text = item["text"]
    parts = [p for p in re.split(f"(?<=[{re.escape(BREAK_AFTER)}])", text) if p.strip()]
    chunks, current = [], ""
    for part in parts:
        if current and text_units(current + part) > max_units:
            chunks.append(current)
            current = part
        else:
            current += part
    if current:
        chunks.append(current)
    if not chunks:
        return []
    total_units = sum(text_units(c) for c in chunks) or 1.0
    duration = item["end"] - item["start"]
    cues, cursor = [], item["start"]
    for chunk in chunks:
        share = duration * text_units(chunk) / total_units
        cues.append({"start": cursor, "end": min(item["end"], cursor + share), "text": chunk.strip()})
        cursor += share
    cues[-1]["end"] = item["end"]
    return cues


def build_cues(segments: list, max_line_units: float, max_lines: int, max_seconds: float) -> list:
    max_units = max_line_units * max_lines
    cues = []
    for item in segments:
        if not item.get("text"):
            continue
        if item.get("words"):
            packed = pack_word_clauses(words_to_clauses(item["words"]), max_units, max_seconds)
            for group in packed:
                text = "".join(w["word"] for w in group).strip()
                if text:
                    cues.append({
                        "start": group[0]["start"],
                        "end": group[-1]["end"],
                        "text": text,
                        "speaker": item.get("speaker"),
                    })
        else:
            for cue in split_text_proportionally(item, max_units):
                cue["speaker"] = item.get("speaker")
                cues.append(cue)
    # Guard against zero/negative display duration.
    for cue in cues:
        if cue["end"] - cue["start"] < 0.3:
            cue["end"] = cue["start"] + 0.3
    return cues


def wrap_lines(text: str, max_line_units: float, max_lines: int) -> str:
    tokens = TOKEN_RE.findall(text)
    lines, current = [], ""
    for token in tokens:
        # Never start a new line with punctuation (orphan-punct rule).
        starts_with_punct = token.strip() and token.strip()[0] in BREAK_AFTER + "」』）】》”’"
        if (current and not starts_with_punct
                and text_units(current + token) > max_line_units
                and len(lines) < max_lines - 1):
            lines.append(current.strip())
            current = token.lstrip()
        else:
            current += token
    if current.strip():
        lines.append(current.strip())
    return "\n".join(lines)


# ------------------------------------------------------------------- renderers

def render_txt(segments: list) -> str:
    has_speakers = any(item.get("speaker") for item in segments)
    if not has_speakers:
        body = "\n".join(item["text"] for item in segments if item["text"])
        return body + ("\n" if body else "")
    blocks, cur_speaker, cur_texts = [], None, []
    for item in segments:
        if not item["text"]:
            continue
        speaker = item.get("speaker") or "S?"
        if speaker != cur_speaker and cur_texts:
            blocks.append(f"{cur_speaker}：{''.join(cur_texts)}")
            cur_texts = []
        cur_speaker = speaker
        cur_texts.append(item["text"])
    if cur_texts:
        blocks.append(f"{cur_speaker}：{''.join(cur_texts)}")
    return "\n\n".join(blocks) + "\n"


def render_md(segments: list, metadata: dict) -> str:
    flagged = [item for item in segments if item.get("flags")]
    duration = metadata.get("duration")
    lines = [
        "# 语音转录",
        "",
        f"- 音频文件: `{metadata.get('audio_file', '未知')}`",
        f"- 模型: `{metadata.get('model', '未知')}`"
        + (f"（精修: `{metadata['refine_model']}`）" if metadata.get("refine_model") else ""),
        f"- 检测语言: `{metadata.get('language', '未知')}`",
        f"- 音频时长: `{format_time(duration)}`" if duration else "- 音频时长: `未知`",
        f"- 段落数: `{len(segments)}`，低置信标记 `{len(flagged)}` 段",
    ]
    diarization = metadata.get("diarization")
    if diarization:
        lines.append(f"- 说话人: `{diarization.get('num_speakers', '?')}` 位（{diarization.get('backend', '')}）")
    lines += ["", "## 带时间戳文本", ""]
    for item in segments:
        if not item["text"]:
            continue
        speaker = f"**{item['speaker']}**：" if item.get("speaker") else ""
        warn = f" ⚠({','.join(item['flags'])})" if item.get("flags") else ""
        lines.append(f"[{item['start_text']} - {item['end_text']}] {speaker}{item['text']}{warn}")
    if flagged:
        lines += ["", "## 待核实事项", ""]
        for item in flagged:
            lines.append(f"- [{item['start_text']}] {item['text']} （{','.join(item['flags'])}）")
    return "\n".join(lines) + "\n"


def render_srt(cues: list, max_line_units: float, max_lines: int) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        text = wrap_lines(cue["text"], max_line_units, max_lines)
        blocks.append(f"{index}\n{format_srt_time(cue['start'])} --> {format_srt_time(cue['end'])}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def render_vtt(cues: list, max_line_units: float, max_lines: int) -> str:
    lines = ["WEBVTT", ""]
    for cue in cues:
        text = wrap_lines(cue["text"], max_line_units, max_lines)
        if cue.get("speaker"):
            text = f"<v {cue['speaker']}>{text}"
        lines.append(f"{format_time(cue['start'])} --> {format_time(cue['end'])}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#f7f7f8; --card:#ffffff; --ink:#1f2328; --muted:#6b7280; --accent:#2563eb;
          --warn-bg:#fef3c7; --active:#dbeafe; --border:#e5e7eb; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif; }
  header { position:sticky; top:0; z-index:10; background:var(--card);
           border-bottom:1px solid var(--border); padding:12px 20px; }
  h1 { font-size:18px; margin:0 0 8px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
  .chip { font-size:12px; color:var(--muted); background:var(--bg);
          border:1px solid var(--border); border-radius:999px; padding:2px 10px; }
  audio { width:100%; margin:4px 0; }
  .controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  .controls input[type=search] { flex:1; min-width:200px; padding:6px 10px;
          border:1px solid var(--border); border-radius:8px; font-size:14px; }
  .legend { display:flex; gap:8px; flex-wrap:wrap; font-size:12px; }
  .legend span { padding:2px 8px; border-radius:999px; color:#fff; }
  main { max-width:900px; margin:0 auto; padding:16px 20px 60px; }
  .row { display:flex; gap:10px; padding:6px 10px; border-radius:8px; align-items:baseline; }
  .row.active { background:var(--active); }
  .row.flagged { background:var(--warn-bg); }
  .row.hidden { display:none; }
  .t { flex:0 0 auto; font-variant-numeric:tabular-nums; font-size:12px; color:var(--accent);
       cursor:pointer; border:none; background:none; padding:0; }
  .t:hover { text-decoration:underline; }
  .spk { flex:0 0 auto; font-size:12px; color:#fff; border-radius:999px; padding:1px 8px; }
  .tx { font-size:15px; line-height:1.7; }
  .warn-tag { font-size:11px; color:#b45309; margin-left:6px; }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="chips" id="chips"></div>
  <audio id="player" controls preload="metadata" src="__AUDIO_SRC__"></audio>
  <div class="controls">
    <input type="search" id="q" placeholder="搜索转录内容…">
    <label style="font-size:13px"><input type="checkbox" id="flaggedOnly"> 只看低置信段</label>
    <div class="legend" id="legend"></div>
  </div>
</header>
<main id="list"></main>
<script type="application/json" id="data">__DATA_JSON__</script>
<script>
(function () {
  var payload = JSON.parse(document.getElementById('data').textContent);
  var segs = payload.segments.filter(function (s) { return s.text; });
  var meta = payload.metadata || {};
  var palette = ['#2563eb','#059669','#d97706','#dc2626','#7c3aed','#0891b2','#be185d','#4d7c0f'];
  var speakers = [];
  segs.forEach(function (s) {
    if (s.speaker && speakers.indexOf(s.speaker) < 0) speakers.push(s.speaker);
  });
  function color(sp) { return palette[speakers.indexOf(sp) % palette.length]; }

  function fmt(t) {
    t = Math.max(0, t | 0);
    var h = (t / 3600) | 0, m = ((t % 3600) / 60) | 0, s = t % 60;
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return p(h) + ':' + p(m) + ':' + p(s);
  }

  var chips = document.getElementById('chips');
  [['模型', meta.model], ['语言', meta.language],
   ['时长', meta.duration ? fmt(meta.duration) : null],
   ['段落', segs.length], ['低置信', (meta.counts || {}).flagged],
   ['说话人', (meta.diarization || {}).num_speakers]].forEach(function (kv) {
    if (kv[1] === null || kv[1] === undefined) return;
    var el = document.createElement('span');
    el.className = 'chip';
    el.textContent = kv[0] + ': ' + kv[1];
    chips.appendChild(el);
  });

  var legend = document.getElementById('legend');
  speakers.forEach(function (sp) {
    var el = document.createElement('span');
    el.style.background = color(sp);
    el.textContent = sp;
    legend.appendChild(el);
  });

  var player = document.getElementById('player');
  var list = document.getElementById('list');
  var rows = [];
  segs.forEach(function (s) {
    var row = document.createElement('div');
    row.className = 'row' + (s.flags && s.flags.length ? ' flagged' : '');
    var bt = document.createElement('button');
    bt.className = 't';
    bt.textContent = fmt(s.start);
    bt.addEventListener('click', function () {
      player.currentTime = s.start;
      player.play();
    });
    row.appendChild(bt);
    if (s.speaker) {
      var badge = document.createElement('span');
      badge.className = 'spk';
      badge.style.background = color(s.speaker);
      badge.textContent = s.speaker;
      row.appendChild(badge);
    }
    var tx = document.createElement('span');
    tx.className = 'tx';
    tx.textContent = s.text;
    if (s.flags && s.flags.length) {
      var w = document.createElement('span');
      w.className = 'warn-tag';
      w.textContent = '⚠ ' + s.flags.join(',');
      tx.appendChild(w);
    }
    row.appendChild(tx);
    list.appendChild(row);
    rows.push({ el: row, seg: s });
  });

  function applyFilter() {
    var q = document.getElementById('q').value.trim().toLowerCase();
    var flaggedOnly = document.getElementById('flaggedOnly').checked;
    rows.forEach(function (r) {
      var ok = (!q || r.seg.text.toLowerCase().indexOf(q) >= 0)
            && (!flaggedOnly || (r.seg.flags && r.seg.flags.length));
      r.el.className = r.el.className.replace(' hidden', '') + (ok ? '' : ' hidden');
    });
  }
  document.getElementById('q').addEventListener('input', applyFilter);
  document.getElementById('flaggedOnly').addEventListener('change', applyFilter);

  var activeRow = null;
  player.addEventListener('timeupdate', function () {
    var t = player.currentTime;
    var found = null;
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].seg.start <= t && t < rows[i].seg.end) { found = rows[i].el; break; }
    }
    if (found !== activeRow) {
      if (activeRow) activeRow.classList.remove('active');
      if (found) {
        found.classList.add('active');
        found.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
      activeRow = found;
    }
  });
})();
</script>
</body>
</html>
"""


def render_html(payload: dict, title: str, audio_src: str) -> str:
    # The reader never uses word-level timestamps; dropping them keeps the
    # single-file HTML small even for hours-long recordings.
    slim = {
        "metadata": payload.get("metadata", {}),
        "segments": [
            {key: value for key, value in item.items() if key != "words"}
            for item in payload.get("segments", [])
        ],
    }
    data_json = json.dumps(slim, ensure_ascii=False).replace("</", "<\\/")
    return (HTML_TEMPLATE
            .replace("__TITLE__", html_mod.escape(title))
            .replace("__AUDIO_SRC__", html_mod.escape(audio_src, quote=True))
            .replace("__DATA_JSON__", data_json))


def default_audio_src(metadata: dict, html_dir: pathlib.Path) -> str:
    audio_file = metadata.get("audio_file")
    if not audio_file:
        return ""
    audio_path = pathlib.Path(audio_file)
    try:
        return os.path.relpath(audio_path, start=html_dir).replace("\\", "/")
    except ValueError:  # different drive on Windows
        try:
            return audio_path.as_uri()
        except ValueError:
            return str(audio_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render txt/md/srt/vtt/html from transcript JSON.")
    parser.add_argument("--json", dest="json_path", required=True, help="Schema-v2 transcript JSON.")
    parser.add_argument("--out-prefix", default=None, help="Output prefix; default = JSON path without .json.")
    parser.add_argument("--formats", default="txt,md,srt,vtt,html", help="Comma list: txt,md,srt,vtt,html")
    parser.add_argument("--audio-src", default=None, help="Audio src for the HTML player (relative path or URL).")
    parser.add_argument("--title", default=None, help="Title for the HTML reader.")
    parser.add_argument("--max-line-chars", type=float, default=20.0, help="Max CJK units per subtitle line.")
    parser.add_argument("--max-lines", type=int, default=2, help="Max lines per subtitle cue.")
    parser.add_argument("--max-cue-seconds", type=float, default=6.0, help="Max seconds per subtitle cue.")
    args = parser.parse_args()

    ensure_utf8_stdout()

    json_path = pathlib.Path(args.json_path).resolve()
    if not json_path.exists():
        raise SystemExit(f"Transcript JSON not found: {json_path}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    segments = payload.get("segments", [])

    prefix = pathlib.Path(args.out_prefix).resolve() if args.out_prefix else json_path.with_suffix("")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    written = {}

    if "txt" in formats:
        path = pathlib.Path(f"{prefix}.txt")
        path.write_text(render_txt(segments), encoding="utf-8")
        written["txt"] = path
    if "md" in formats:
        path = pathlib.Path(f"{prefix}.md")
        path.write_text(render_md(segments, metadata), encoding="utf-8")
        written["md"] = path
    if "srt" in formats or "vtt" in formats:
        cues = build_cues(segments, args.max_line_chars, args.max_lines, args.max_cue_seconds)
        if "srt" in formats:
            path = pathlib.Path(f"{prefix}.srt")
            path.write_text(render_srt(cues, args.max_line_chars, args.max_lines), encoding="utf-8")
            written["srt"] = path
        if "vtt" in formats:
            path = pathlib.Path(f"{prefix}.vtt")
            path.write_text(render_vtt(cues, args.max_line_chars, args.max_lines), encoding="utf-8")
            written["vtt"] = path
    if "html" in formats:
        path = pathlib.Path(f"{prefix}.html")
        title = args.title or f"语音转录 · {pathlib.Path(metadata.get('audio_file', prefix.name)).name}"
        audio_src = args.audio_src or default_audio_src(metadata, path.parent)
        path.write_text(render_html(payload, title, audio_src), encoding="utf-8")
        written["html"] = path

    for key, path in written.items():
        print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
