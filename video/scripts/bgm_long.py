# 背景音乐长版：1c「钢琴加木琴」铺满全片，中间分段变化，避免一首 96 秒的曲子循环听出重复
# 用法：uv run --with numpy python -I scripts/bgm_long.py <输出文件夹> <秒数>
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out, secs = sys.argv[1], float(sys.argv[2])
sys.argv = [sys.argv[0], out, "lib"]
import synth
synth.SECS = secs
from synth import *
from piano2 import warm_piano, soft_mallet

beat = 60 / 76; bar = 4 * beat
A = [("F", "maj"), ("C", "maj"), ("D", "min"), ("Bb", "maj")]
B = [("D", "min"), ("Bb", "maj"), ("F", "maj"), ("C", "maj")]
nbars = int(secs / bar) + 1
# 每 8 小节一段：前奏（只有钢琴）→ 主歌（加木琴）→ 换和弦 → 安静段 …… 循环
PLAN = ["intro", "main", "main", "alt", "quiet", "main", "alt", "alt", "quiet", "main", "main", "alt", "quiet", "main", "main"]
tr = Track(secs)
for k in range(nbars):
    part = PLAN[min(k // 8, len(PLAN) - 1)]
    prog = B if part == "alt" else A
    root, kind = prog[k % 4]; ch = chord(root, kind, 2); t = k * bar
    tr.add(warm_piano(midi(ch[0]), bar, 0.8), t)
    if part == "quiet":  # 安静段：长和弦 + 偶尔一个高音
        for i, m in enumerate(ch): tr.add(warm_piano(midi(m + 12), bar * 0.7, 0.35), t + i * 0.04, -0.2 + 0.2 * i)
        if k % 2: tr.add(soft_mallet(midi(ch[2] + 24), 0.3), t + 2 * beat, 0.35)
    else:
        for i, m in enumerate([ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12]):
            tr.add(warm_piano(midi(m), beat, 0.45), t + i * beat + rng.normal(0, 0.008), -0.2)
        if part != "intro":
            mel = [ch[2] + 24, ch[1] + 24, ch[0] + 36, ch[2] + 24] if part == "main" else [ch[0] + 36, ch[2] + 24, ch[1] + 24, ch[2] + 24]
            for r, m in zip([0.5, 1.5, 2.75, 3.5], mel): tr.add(soft_mallet(midi(m), 0.4), t + r * beat, 0.35)
    tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.5, 600), t, gain=0.4 if part != "quiet" else 0.55)
finish(tr, "bgm-long", rev=0.35, tone=2400)
