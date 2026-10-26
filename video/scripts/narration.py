"""把 口播稿.md 拆成视频用的 JSON（src/data/narration.json），顺便导出给 MiniMax 用的配音稿。

- 每个【】是一段（section），段里每个自然段对应一个画面。
- 口播稿里的 <#0.3#> 是 MiniMax 的停顿标记（单位：秒）。字幕里会去掉，配音稿里保留。
- 导出的 口播稿-MiniMax.txt：去掉【】标题，自然段之间加 <#1.2#> 的长停顿，整篇一次生成配音。
- 配音存成 public/voice/全片.mp3。这里用静音检测找出段落之间的长停顿，把配音切回每个画面；
  没有配音时按每秒 4.2 个字加上停顿时长估算。
- 改了口播稿或换了配音，重新跑一次：python3 scripts/narration.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "口播稿.md"
TTS = ROOT / "口播稿-MiniMax.txt"
VOICE = ROOT / "public" / "voice" / "全片.mp3"
OUT = ROOT / "src" / "data" / "narration.json"
GAP = 1.2  # 段落之间的停顿（秒）
FIND = 0.9  # 静音至少这么长才算段落分界（句中停顿都比它短）
PAUSE = re.compile(r"<#([\d.]+)#>")


def silences(p: Path) -> tuple[float, list[tuple[float, float]]]:
    r = subprocess.run(["ffmpeg", "-i", str(p), "-af", f"silencedetect=noise=-35dB:d={FIND}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    total = int(h) * 3600 + int(m) * 60 + float(s)
    return total, list(zip(starts, ends + [total] * (len(starts) - len(ends))))


def clips(p: Path, n: int) -> list[dict]:
    total, sil = silences(p)
    # 开头和结尾的静音不算分界
    inner = [(a, b) for a, b in sil if a > 0.05 and b < total - 0.05]
    if len(inner) < n - 1:
        raise SystemExit(f"配音里只找到 {len(inner)} 处长停顿，需要 {n - 1} 处。请确认是用 {TTS.name} 生成的（段落之间有 <#{GAP}#>）。")
    # 多出来的（句中偶尔停得久）去掉最短的
    inner = sorted(sorted(inner, key=lambda x: x[1] - x[0], reverse=True)[: n - 1])
    lead = sil[0][1] if sil and sil[0][0] <= 0.05 else 0.0
    starts = [lead] + [b for _, b in inner]
    ends = [a for a, _ in inner] + [next((a for a, b in sil if a >= starts[-1] and b >= total - 0.05), total)]
    return [{"start": round(s, 2), "end": round(e, 2)} for s, e in zip(starts, ends)]


def main() -> None:
    sections = []
    for block in re.split(r"^【", SRC.read_text(), flags=re.M)[1:]:
        head, _, body = block.partition("】")
        num, _, title = head.partition(" ")
        raw = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
        sections.append({
            "id": int(num), "title": title,
            "paragraphs": [PAUSE.sub("", p) for p in raw],
            "pauses": [round(sum(float(x) for x in PAUSE.findall(p)), 2) for p in raw],
            "voice": raw,
        })
    paras = [p for s in sections for p in s["voice"]]
    TTS.write_text(f"<#{GAP}#>\n".join(p + "\n" for p in paras))

    cl = clips(VOICE, len(paras)) if VOICE.exists() else None
    k = 0
    for s in sections:
        s["clips"] = cl[k:k + len(s["paragraphs"])] if cl else None
        k += len(s["paragraphs"])
        del s["voice"]
    OUT.write_text(json.dumps({"audio": f"voice/{VOICE.name}" if cl else None, "sections": sections}, ensure_ascii=False, indent=1))
    print(f"{len(sections)} 段、{len(paras)} 个画面；配音：{'已按停顿切成 ' + str(len(cl)) + ' 段' if cl else '无（按字数估算）'}；已导出 {TTS.name}")


if __name__ == "__main__":
    main()
