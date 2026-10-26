"""生成正片用的音效（全部用代码合成，没有版权问题）：python3 scripts/sfx.py → public/sfx/*.wav

- click：鼠标点击        - key：打字的一下
- pop：卡片弹出          - whoosh：切换、翻面
- tick：格子亮起（很轻）  - chime：完成 / 改好了
- notify：飞书消息提醒（两声）
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "public" / "sfx"
random.seed(7)


def write(name: str, samples: list[float], gain: float = 0.8) -> None:
    peak = max(1e-9, max(abs(s) for s in samples))
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * gain * s / peak)) for s in samples))


def n(sec: float) -> range:
    return range(int(RATE * sec))


def lowpass(xs: list[float], a: float) -> list[float]:
    out, y = [], 0.0
    for x in xs:
        y += a * (x - y)
        out.append(y)
    return out


def click() -> list[float]:
    noise = lowpass([random.uniform(-1, 1) for _ in n(0.035)], 0.5)
    body = [math.sin(2 * math.pi * 1800 * i / RATE) * 0.5 for i in n(0.035)]
    return [(a + b) * math.exp(-i / RATE * 160) for i, (a, b) in enumerate(zip(noise, body))]


def key() -> list[float]:
    return lowpass([random.uniform(-1, 1) * math.exp(-i / RATE * 260) for i in n(0.03)], 0.35)


def pop() -> list[float]:
    out, ph = [], 0.0
    for i in n(0.12):
        t = i / RATE
        ph += 2 * math.pi * (420 + 520 * math.exp(-t * 40)) / RATE
        out.append(math.sin(ph) * math.exp(-t * 32) * min(1, t * 400))
    return out


def whoosh() -> list[float]:
    d = 0.32
    raw = [random.uniform(-1, 1) for _ in n(d)]
    out, y = [], 0.0
    for i, x in enumerate(raw):
        t = i / RATE
        a = 0.02 + 0.18 * math.sin(math.pi * t / d)  # 先变亮再变暗，像东西划过
        y += a * (x - y)
        out.append(y * math.sin(math.pi * t / d) ** 2)
    return out


def tick() -> list[float]:
    return [math.sin(2 * math.pi * 2400 * i / RATE) * math.exp(-i / RATE * 120) for i in n(0.04)]


def tone(f: float, d: float, decay: float) -> list[float]:
    return [(math.sin(2 * math.pi * f * i / RATE) + 0.3 * math.sin(4 * math.pi * f * i / RATE)) * math.exp(-i / RATE * decay) * min(1, i / RATE * 300) for i in n(d)]


def mix(*parts: tuple[float, list[float]]) -> list[float]:
    total = max(int(at * RATE) + len(p) for at, p in parts)
    out = [0.0] * total
    for at, p in parts:
        s = int(at * RATE)
        for i, v in enumerate(p):
            out[s + i] += v
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write("click", click())
    write("key", key(), 0.6)
    write("pop", pop())
    write("whoosh", whoosh())
    write("tick", tick(), 0.5)
    write("chime", mix((0, tone(988, 0.5, 7)), (0.09, tone(1319, 0.6, 6))))
    write("notify", mix((0, tone(1175, 0.25, 14)), (0.12, tone(1568, 0.35, 11))))
    print("已生成：", ", ".join(sorted(p.name for p in OUT.glob("*.wav"))))


if __name__ == "__main__":
    main()
