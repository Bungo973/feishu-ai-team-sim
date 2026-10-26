# 更低、更温暖的钢琴：泛音少、起音软、低音区、整体低通、混响大
import sys; sys.argv = sys.argv[:2] + ["lib"]
from synth import *

def warm_piano(f, dur, vel=1.0):
    L = int((dur + 2.5) * SR); t = np.arange(L) / SR
    x = np.zeros(L)
    for k, amp in enumerate([1, 0.32, 0.1, 0.04], 1):
        x += amp * np.sin(2 * np.pi * f * k * t * (1 + 0.0003 * k * k)) * np.exp(-t * (0.7 + 0.8 * k) * (f / 300) ** 0.3)
    x *= np.minimum(1, t / 0.015)  # 起音放软，像踩着弱音踏板
    off = int(dur * SR); x[off:] *= np.exp(-(t[off:] - dur) * 3)
    return x * vel * 0.3

def soft_mallet(f, vel=1.0):
    L = int(2.2 * SR); t = np.arange(L) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6) + 0.12 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t * 16)
    return x * np.minimum(1, t / 0.012) * vel * 0.3

# 1a 低音钢琴：分解和弦整体低一个八度，70 BPM
def a():
    tr = Track(SECS); beat = 60 / 70; bar = 4 * beat
    prog = [("C", "add9"), ("G", "maj"), ("A", "min7"), ("F", "maj7")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 2)
        tr.add(warm_piano(midi(ch[0]), bar, 0.8), t, -0.15)
        pat = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 24, ch[2] + 12, ch[1] + 12]
        for i, m in enumerate(pat):
            tr.add(warm_piano(midi(m), beat / 2, 0.5 + 0.1 * (i % 2 == 0)), t + i * beat / 2 + rng.normal(0, 0.008), 0.15)
        tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.5, 600), t, gain=0.4)
        t += bar; k += 1
    finish(tr, "1a-低音钢琴", rev=0.35, tone=2200)

# 1b 温暖和弦：慢速柱式和弦 + 厚垫子，最舒缓，62 BPM
def b():
    tr = Track(SECS); beat = 60 / 62; bar = 4 * beat
    prog = [("F", "maj7"), ("C", "add9"), ("D", "min7"), ("Bb", "maj7")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 3)
        tr.add(warm_piano(midi(ch[0] - 12), bar, 0.8), t)
        for i, m in enumerate(ch): tr.add(warm_piano(midi(m), bar * 0.6, 0.4), t + i * 0.03, -0.3 + 0.2 * i)
        for i, m in enumerate(ch[1:]): tr.add(warm_piano(midi(m), bar * 0.3, 0.3), t + 2.5 * beat + i * 0.03, 0.2)
        if k % 2 == 1:
            for i, m in enumerate([ch[2] + 12, ch[1] + 12]): tr.add(warm_piano(midi(m), beat, 0.3), t + beat * (1 + 1.5 * i), 0.3)
        tr.add(pad([midi(x) for x in ch], bar, 0.7, 550), t, gain=0.6)
        t += bar; k += 1
    finish(tr, "1b-温暖和弦", rev=0.42, tone=1800)

# 1c 低音钢琴 + 柔和木琴点缀，76 BPM（两种你喜欢的混在一起）
def c():
    tr = Track(SECS); beat = 60 / 76; bar = 4 * beat
    prog = [("F", "maj"), ("C", "maj"), ("D", "min"), ("Bb", "maj")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 2)
        tr.add(warm_piano(midi(ch[0]), bar, 0.8), t)
        for i, m in enumerate([ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12]):
            tr.add(warm_piano(midi(m), beat, 0.45), t + i * beat + rng.normal(0, 0.008), -0.2)
        if k >= 2:
            for r, m in zip([0.5, 1.5, 2.75, 3.5], [ch[2] + 24, ch[1] + 24, ch[0] + 36, ch[2] + 24]):
                tr.add(soft_mallet(midi(m), 0.4), t + r * beat, 0.35)
        tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.5, 600), t, gain=0.4)
        t += bar; k += 1
    finish(tr, "1c-钢琴加木琴", rev=0.35, tone=2400)

a(); b(); c()
