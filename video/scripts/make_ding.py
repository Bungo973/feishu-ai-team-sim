"""合成一个类似苹果"叮咚"消息提示音（自己生成，没有版权问题）。"""
import math
import struct
import wave
from pathlib import Path

RATE = 44100
NOTES = ((0.0, 659.3), (0.13, 987.8))  # E5 → B5，"叮咚"两个音（中音区，不刺耳）
out = Path(__file__).resolve().parents[1] / "public" / "sfx" / "ding.wav"


def tone(u: float, f: float) -> float:
    # 柔和的音色：基音 + 很弱的 2 倍泛音，起音稍缓、自然衰减
    env = min(u * 120, 1) * math.exp(-u * 7)
    return env * (math.sin(2 * math.pi * f * u) + 0.08 * math.sin(2 * math.pi * f * 2 * u))


frames = []
for i in range(int(RATE * 0.7)):
    t = i / RATE
    v = sum(tone(t - s, f) for s, f in NOTES if t >= s)
    frames.append(struct.pack("<h", int(max(-1, min(1, v * 0.28)) * 32767)))
with wave.open(str(out), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(b"".join(frames))
print(out)
