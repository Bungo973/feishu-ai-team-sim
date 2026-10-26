# 合成几段免版权背景音乐（全部程序生成），输出 wav 到 argv[1]
import sys, os
import numpy as np

SR = 44100
OUT = sys.argv[1]
rng = np.random.default_rng(7)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
def n(s):  # "C4" -> midi
    name, octv = s[:-1], int(s[-1])
    return 12 * (octv + 1) + NOTE[name]

def env(length, a=0.005, decay=1.0, release=0.05):
    t = np.arange(length) / SR
    e = np.minimum(1, t / a) * np.exp(-t / decay)
    r = int(release * SR)
    if r and length > r: e[-r:] *= np.linspace(1, 0, r)
    return e

# ---------- 乐器 ----------
def piano(f, dur, vel=1.0):
    L = int((dur + 1.5) * SR); t = np.arange(L) / SR
    x = np.zeros(L)
    for k, amp in enumerate([1, 0.45, 0.22, 0.12, 0.06], 1):
        x += amp * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (1.2 + 0.9 * k) * (f / 400) ** 0.3)
    x *= np.minimum(1, t / 0.004)
    off = int(dur * SR); x[off:] *= np.exp(-(t[off:] - dur) * 6)
    return x * vel * 0.3

def rhodes(f, dur, vel=1.0):
    L = int((dur + 1.0) * SR); t = np.arange(L) / SR
    mod = np.sin(2 * np.pi * f * t) * 1.2 * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 0.9) + 0.15 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 2)
    x *= (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))  # 轻微颤音
    x *= np.minimum(1, t / 0.006)
    off = int(dur * SR); x[off:] *= np.exp(-(t[off:] - dur) * 5)
    return x * vel * 0.28

def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    # 一阶低通，用 FFT 频响近似（向量化）
    N = len(x); X = np.fft.rfft(x); fr = np.fft.rfftfreq(N, 1 / SR)
    H = 1 / np.sqrt(1 + (fr / cutoff) ** 4)
    return np.fft.irfft(X * H, N)

def pad(freqs, dur, vel=1.0, bright=1200):
    L = int((dur + 2.0) * SR); t = np.arange(L) / SR
    x = np.zeros(L)
    for f in freqs:
        for det in (-0.006, 0, 0.007):
            ph = rng.random()
            saw = 2 * ((f * (1 + det) * t + ph) % 1) - 1
            x += saw
    x = lowpass(x, bright) / (len(freqs) * 3)
    a = np.minimum(1, t / 1.2); r = np.clip((dur + 2.0 - t) / 2.0, 0, 1)
    return x * a * r * vel * 0.5

def pluck(f, dur, vel=1.0, bright=0.5):
    L = int((dur + 2.0) * SR); N = max(2, int(SR / f))
    y = np.zeros(L + N + 1)
    burst = rng.uniform(-1, 1, N)
    burst = lowpass(np.concatenate([burst, np.zeros(N)]), 800 + 4000 * bright)[:N]
    y[1:N + 1] = burst
    d = 0.996
    s = N + 1
    while s < len(y):
        e = min(s + N, len(y))
        y[s:e] = d * 0.5 * (y[s - N:e - N] + y[s - N - 1:e - N - 1])
        s = e
    x = y[1:L + 1]
    return x / (np.abs(burst).max() + 1e-9) * vel * 0.3

def mallet(f, dur, vel=1.0):
    L = int(1.8 * SR); t = np.arange(L) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 3.5) + 0.35 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t * 14) + 0.12 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 30)
    return x * np.minimum(1, t / 0.002) * vel * 0.3

def bell(f, dur, vel=1.0):
    L = int(4 * SR); t = np.arange(L) / SR
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in [(1, 1, 0.9), (2.76, 0.4, 2), (5.4, 0.2, 4), (8.9, 0.1, 7)])
    return x * np.minimum(1, t / 0.003) * vel * 0.18

def kick(vel=1.0):
    L = int(0.4 * SR); t = np.arange(L) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * vel * 0.55

def hat(vel=1.0):
    L = int(0.08 * SR); x = rng.uniform(-1, 1, L)
    x = x - lowpass(x, 6000)
    return x * np.exp(-np.arange(L) / SR * 60) * vel * 0.12

def snare(vel=1.0):
    L = int(0.25 * SR); t = np.arange(L) / SR
    x = lowpass(rng.uniform(-1, 1, L), 3500) * np.exp(-t * 18) + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    return x * vel * 0.25

def shaker(vel=1.0):
    L = int(0.06 * SR); x = rng.uniform(-1, 1, L); x = x - lowpass(x, 4000)
    t = np.arange(L) / SR
    return x * np.minimum(1, t / 0.01) * np.exp(-t * 50) * vel * 0.08

# ---------- 混音工具 ----------
class Track:
    def __init__(self, seconds):
        self.L = int(seconds * SR); self.l = np.zeros(self.L + 6 * SR); self.r = np.zeros(self.L + 6 * SR)
    def add(self, x, at, pan=0.0, gain=1.0):
        i = max(0, int(at * SR)); j = min(i + len(x), len(self.l))
        if i >= len(self.l): return
        x = x[: j - i] * gain
        self.l[i:j] += x * np.sqrt((1 - pan) / 2); self.r[i:j] += x * np.sqrt((1 + pan) / 2)

def reverb(x, secs=2.2, mix=0.25, seed=0):
    r = np.random.default_rng(seed)
    L = int(secs * SR); t = np.arange(L) / SR
    ir = r.uniform(-1, 1, L) * np.exp(-t * 3 / secs) ; ir[:int(0.012 * SR)] = 0
    ir = lowpass(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    N = 1 << int(np.ceil(np.log2(len(x) + L)))
    wet = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.6

def finish(tr, name, rev=0.25, crackle=0.0, tone=None):
    l, r = reverb(tr.l, mix=rev, seed=1), reverb(tr.r, mix=rev, seed=2)
    if tone: l, r = lowpass(l, tone), lowpass(r, tone)  # 整体削掉高频，听着不刺
    if crackle:
        c = np.zeros(len(l)); idx = rng.integers(0, len(l), int(len(l) / SR * 6)); c[idx] = rng.uniform(-1, 1, len(idx))
        c = lowpass(c, 3000) * crackle + lowpass(rng.normal(0, 1, len(l)), 900) * crackle * 0.02
        l += c; r += c
    L = tr.L; l, r = l[:L], r[:L]
    fi, fo = int(2 * SR), int(4 * SR)
    for ch in (l, r):
        ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
    st = np.stack([l, r], 1); st /= np.abs(st).max() / 0.89
    pcm = (st * 32767).astype("<i2")
    import wave
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("ok", name)

def chord(root, kind="maj", octave=3):
    iv = {"maj": [0, 4, 7], "min": [0, 3, 7], "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "dom7": [0, 4, 7, 10], "add9": [0, 4, 7, 14], "sus2": [0, 2, 7]}[kind]
    b = n(root + str(octave)); return [b + i for i in iv]

SECS = 96

# 1 晨光钢琴：I-V-vi-IV 分解和弦 + 底下的长音铺垫，82 BPM
def t1():
    tr = Track(SECS); bpm = 82; beat = 60 / bpm; bar = 4 * beat
    prog = [("C", "add9"), ("G", "maj"), ("A", "min7"), ("F", "maj7")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 3)
        tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.5, 900), t, gain=0.5)
        tr.add(piano(midi(ch[0] - 12), bar, 0.8), t, -0.2)
        pat = [ch[0], ch[1] + 12, ch[2], ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[2], ch[1] + 12]
        for i, m in enumerate(pat):
            tr.add(piano(midi(m), beat / 2, 0.55 + 0.1 * (i % 2 == 0)), t + i * beat / 2 + rng.normal(0, 0.006), 0.15)
        if k % 2 == 1:  # 偶尔一句高音旋律
            for i, m in enumerate([ch[2] + 24, ch[1] + 24, ch[0] + 24]):
                tr.add(piano(midi(m), beat, 0.35), t + 2 * beat + i * beat * 0.66, 0.3)
        t += bar; k += 1
    finish(tr, "1-晨光钢琴", rev=0.3)

# 2 Lo-fi 电钢：ii-V-I-vi 七和弦 + 软鼓 + 黑胶底噪，74 BPM，带摇摆
def t2():
    tr = Track(SECS); bpm = 74; beat = 60 / bpm; bar = 4 * beat
    prog = [("D", "min7"), ("G", "dom7"), ("C", "maj7"), ("A", "min7")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 3)
        for m in ch: tr.add(rhodes(midi(m + 12), beat * 1.8, 0.45), t + rng.normal(0, 0.01), rng.uniform(-0.3, 0.3))
        for m in ch: tr.add(rhodes(midi(m + 12), beat * 1.2, 0.3), t + 2.5 * beat, rng.uniform(-0.3, 0.3))
        tr.add(pluck(midi(ch[0] - 12), bar, 0.9, 0.1), t)
        tr.add(pluck(midi(ch[0] - 12 + 7), beat, 0.6, 0.1), t + 2.5 * beat)
        if k >= 2:
            for b in range(4):
                swing = 0.07 * beat
                tr.add(hat(0.8 if b % 2 else 0.6), t + b * beat); tr.add(hat(0.4), t + b * beat + beat / 2 + swing)
            tr.add(kick(0.8), t); tr.add(kick(0.6), t + 2.5 * beat)
            tr.add(snare(0.6), t + beat); tr.add(snare(0.6), t + 3 * beat)
        t += bar; k += 1
    finish(tr, "2-Lofi电钢", rev=0.22, crackle=0.06)

# 3 科技轻快：拨弦 16 分音符琶音 + 铺垫 + 轻鼓，100 BPM
def t3():
    tr = Track(SECS); bpm = 100; beat = 60 / bpm; bar = 4 * beat
    prog = [("A", "min"), ("F", "maj"), ("C", "maj"), ("G", "maj")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 4)
        tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.6, 1500), t, gain=0.45)
        seq = [ch[0], ch[1], ch[2], ch[1] + 12 - 12, ch[2], ch[0] + 12, ch[2], ch[1]]
        for i in range(16):
            tr.add(pluck(midi(seq[i % 8]), beat / 4, 0.5 if i % 4 else 0.7, 0.7), t + i * beat / 4, 0.4 * np.sin(i))
        tr.add(pluck(midi(ch[0] - 24), bar, 0.9, 0.2), t)
        if k >= 4:
            for b in range(4):
                tr.add(kick(0.7), t + b * beat) if b % 2 == 0 else tr.add(snare(0.35), t + b * beat)
                tr.add(hat(0.5), t + b * beat + beat / 2)
        t += bar; k += 1
    finish(tr, "3-科技轻快", rev=0.2)

# 4 温暖氛围：只有缓慢铺垫和零星钟声，最安静，60 BPM
def t4():
    tr = Track(SECS); bar = 6.0
    prog = [("F", "maj7"), ("C", "add9"), ("A", "min7"), ("G", "sus2")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 3)
        tr.add(pad([midi(x) for x in ch], bar + 1.5, 0.8, 700), t, gain=0.8)
        for i in range(3):
            if rng.random() < 0.7:
                tr.add(bell(midi(rng.choice(ch) + 24), 1, rng.uniform(0.4, 0.8)), t + i * 2 + rng.uniform(0, 0.6), rng.uniform(-0.6, 0.6))
        t += bar; k += 1
    finish(tr, "4-温暖氛围", rev=0.45)

# 5 木琴轻快：马林巴节奏型 + 沙锤，96 BPM，明亮
def t5():
    tr = Track(SECS); bpm = 96; beat = 60 / bpm; bar = 4 * beat
    prog = [("F", "maj"), ("C", "maj"), ("D", "min"), ("Bb", "maj")]
    rhythm = [0, 0.75, 1.5, 2, 2.75, 3.5]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 4)
        notes = [ch[0], ch[2], ch[1] + 12, ch[0] + 12, ch[2], ch[1]]
        for r, m in zip(rhythm, notes): tr.add(mallet(midi(m), 0.3, 0.6), t + r * beat, rng.uniform(-0.3, 0.3))
        tr.add(mallet(midi(ch[0] - 12), 0.5, 0.8), t); tr.add(mallet(midi(ch[0] - 12 + 7), 0.5, 0.6), t + 2 * beat)
        tr.add(pad([midi(x) for x in chord(root, kind, 3)], bar, 0.4, 1000), t, gain=0.35)
        if k >= 2:
            for i in range(8): tr.add(shaker(0.9 if i % 2 else 0.5), t + i * beat / 2, 0.3)
        t += bar; k += 1
    finish(tr, "5-木琴轻快", rev=0.2)

# 6 原声吉他感：指弹拨弦，G-D-Em-C，84 BPM
def t6():
    tr = Track(SECS); bpm = 84; beat = 60 / bpm; bar = 4 * beat
    prog = [("G", "maj"), ("D", "maj"), ("E", "min"), ("C", "add9")]
    k = 0; t = 0.0
    while t < SECS:
        root, kind = prog[k % 4]; ch = chord(root, kind, 3)
        bass = ch[0] - 12
        pat = [bass, ch[1], ch[2], ch[1] + 12, bass + 7, ch[1], ch[2], ch[1] + 12]
        for i, m in enumerate(pat):
            tr.add(pluck(midi(m), beat / 2, 0.75 if i in (0, 4) else 0.5, 0.35), t + i * beat / 2 + rng.normal(0, 0.008), -0.2 + 0.4 * (i % 2))
        if k % 4 == 3:
            for i, m in enumerate([ch[2] + 12, ch[1] + 12, ch[0] + 12]): tr.add(mallet(midi(m + 12), 0.4, 0.25), t + beat * (1 + i), 0.4)
        t += bar; k += 1
    finish(tr, "6-原声吉他", rev=0.25)

if __name__ == "__main__" and len(sys.argv) < 3:
    for f in [t1, t2, t3, t4, t5, t6]: f()
