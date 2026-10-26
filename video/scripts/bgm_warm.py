# 背景音乐长版：1b「温暖和弦」铺满全片，中间分段变化，避免一首 96 秒的曲子循环听出重复
# 用法：uv run --with numpy python -I scripts/bgm_warm.py <输出文件夹> <秒数>
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out, secs = sys.argv[1], float(sys.argv[2])
sys.argv = [sys.argv[0], out, "lib"]
import synth
synth.SECS = secs
from synth import *
from piano2 import warm_piano

beat = 60 / 62; bar = 4 * beat
A = [("F", "maj7"), ("C", "add9"), ("D", "min7"), ("Bb", "maj7")]
B = [("D", "min7"), ("Bb", "maj7"), ("F", "maj7"), ("C", "add9")]
nbars = int(secs / bar) + 1
# 每 8 小节一段：前奏（只有和弦）→ 主段（加两个高音点缀）→ 换和弦 → 安静段（只剩垫子和一个长和弦）…… 循环
PLAN = ["intro", "main", "alt", "quiet", "main", "main", "alt", "quiet", "main", "alt", "main", "main"]
tr = Track(secs)
for k in range(nbars):
    part = PLAN[min(k // 8, len(PLAN) - 1)]
    prog = B if part == "alt" else A
    root, kind = prog[k % 4]; ch = chord(root, kind, 3); t = k * bar
    tr.add(warm_piano(midi(ch[0] - 12), bar, 0.8), t)
    for i, m in enumerate(ch): tr.add(warm_piano(midi(m), bar * 0.6, 0.4 if part != "quiet" else 0.3), t + i * 0.03, -0.3 + 0.2 * i)
    if part != "quiet":
        for i, m in enumerate(ch[1:]): tr.add(warm_piano(midi(m), bar * 0.3, 0.3), t + 2.5 * beat + i * 0.03, 0.2)
    if part in ("main", "alt") and k % 2 == 1:
        mel = [ch[2] + 12, ch[1] + 12] if part == "main" else [ch[1] + 12, ch[3] + 12]
        for i, m in enumerate(mel): tr.add(warm_piano(midi(m), beat, 0.3), t + beat * (1 + 1.5 * i), 0.3)
    tr.add(pad([midi(x) for x in ch], bar, 0.7, 550), t, gain=0.6 if part != "quiet" else 0.75)
finish(tr, "bgm-warm", rev=0.42, tone=1800)
