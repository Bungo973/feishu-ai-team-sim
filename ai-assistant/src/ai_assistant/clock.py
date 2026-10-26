"""读时钟文件：现在是哪天几点、上没上班。真实公司里这就是电脑的系统时钟。

模拟时间是压缩的（现实 1 分钟 ≈ 模拟 10 分钟），所以飞书消息的真实发送时间要换算成模拟时间。
"""
from __future__ import annotations

import json

from . import config


def entries() -> list[dict]:
    if not config.CLOCK_FILE.exists():
        return []
    return [json.loads(x) for x in config.CLOCK_FILE.read_text(encoding="utf-8").splitlines() if x.strip()]


def now(es: list[dict] | None = None) -> dict | None:
    es = entries() if es is None else es
    return es[-1] if es else None


def dates(es: list[dict]) -> list[str]:
    """出现过的工作日，按顺序。"""
    return list(dict.fromkeys(e["date"] for e in es))


def day_start(es: list[dict], date: str) -> int | None:
    """这一天第一次出现在时钟里的真实时间（秒）。"""
    return next((e["ts"] for e in es if e["date"] == date), None)


def _m(hm: str) -> int:
    return int(hm[:2]) * 60 + int(hm[3:5])


def sim_at(es: list[dict], ts: float) -> tuple[str, str] | None:
    """真实时间 → （模拟日期, 模拟时间）。在两条时钟记录之间按比例估算。"""
    prev = None
    for e in es:
        if e["ts"] > ts:
            if prev and prev["date"] == e["date"] and prev["working"] and e["ts"] > prev["ts"]:
                m = _m(prev["time"]) + (_m(e["time"]) - _m(prev["time"])) * (ts - prev["ts"]) / (e["ts"] - prev["ts"])
                return prev["date"], f"{int(m) // 60:02d}:{int(m) % 60:02d}"
            break
        prev = e
    if not prev:
        return None
    return prev["date"], prev["time"] if prev["working"] else "下班后"


def workdays_between(es: list[dict], a: str, b: str) -> int:
    """从 a 到 b 隔了几个工作日（按时钟里出现过的日子数）。"""
    ds = dates(es)
    return ds.index(b) - ds.index(a) if a in ds and b in ds else 0
