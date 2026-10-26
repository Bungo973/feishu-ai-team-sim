"""同事发出的"真实文件"：群聊里提到这些资料时，飞书模式会把真的文件一起发出去（不再是打不开的假链接）。

只放各人自己的工作底稿，内容来自手册里公开的计划 + 这个人对外说的进度（不是真实进度）。
"""

import re
from pathlib import Path

from . import config, engine
from .state import NAMES, date_str

FAKE_URL = re.compile(r"https?://\S+")


def _book(path: Path, title: str, header: list[str], rows: list[list], note: str) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append([note])
    ws.append(header)
    for c in ws[2]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append(r)
    for col, w in zip("ABCDEFGH", [8, 30, 10, 12, 12, 30, 12, 20]):
        ws.column_dimensions[col].width = w
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _pct(v) -> str:
    return f"{v}%" if isinstance(v, (int, float)) or str(v).isdigit() else str(v)


def _due(state: dict, d: int) -> str:
    return date_str(state, d)[5:10] if d > 0 else ""


def launch_sheet(state: dict, day: int) -> Path:
    """张伟的《发布会筹备 v2.xlsx》：只到 A1–A6，十天前更新的旧表。"""
    tm = engine.tasks_by_id(state)
    stale = {"A1": ("已完成", "合同已签，定金已付"), "A2": ("进行中", "名单在共享盘")}
    rows = []
    for tid in ["A1", "A2", "A3", "A4", "A5", "A6"]:
        t = tm[tid]
        st, note = stale.get(tid, ("未开始", ""))
        rows.append([tid, t["name"], "、".join(NAMES.get(o, o) for o in t["owners"]), st, _due(state, t["due_day"]), note])
    return _book(config.OUTPUT_DIR / "files" / "发布会筹备 v2.xlsx", "筹备", ["编号", "任务", "负责人", "状态", "截止", "备注"],
                 rows, "小暖S2发布会筹备表（最后更新：10-23 张伟）")


def content_sheet(state: dict, day: int) -> Path:
    """李想的《11月内容排期.xlsx》：标题、平台、发布日，进度是他自己对外说的口径。"""
    tm = engine.tasks_by_id(state)
    rows = []
    for t in state["tasks"]:
        if not t["id"].endswith("-文"):
            continue
        item = t["id"][:3]
        img = tm.get(item + "-图")
        say = engine.reported_progress(state, t, day) if t["start_day"] <= day else ""
        say_img = engine.reported_progress(state, img, day) if img and img["start_day"] <= day else ""
        rows.append([item, t["name"].replace("（文案）", ""), t.get("platform", ""),
                     f"{_due(state, t['publish_day'])} {t.get('publish_time', '')}",
                     _pct(say) if say != "" else "", _pct(say_img) if say_img != "" else "", "", ""])
    return _book(config.OUTPUT_DIR / "files" / "11月内容排期.xlsx", "排期",
                 ["编号", "标题", "平台", "发布时间", "文案进度", "配图进度", "审核", "备注"], rows,
                 "11月公众号+小红书排期（李想自己维护，进度随手填的）")


# (发送人, 文字里出现的关键词) → 生成函数
CATALOG = [
    ("张伟", ("发布会筹备", "筹备 v", "筹备表"), launch_sheet),
    ("李想", ("排期",), content_sheet),
]


def match(sender: str, text: str) -> tuple[str, callable] | None:
    """这条消息是不是在发某份资料（提到了文件 / 链接 + 关键词）。"""
    if not (FAKE_URL.search(text) or re.search(r"\[[^\]]+\.(xlsx|xls|csv)\]", text) or "表" in text):
        return None
    for who, keys, fn in CATALOG:
        if who == sender and any(k in text for k in keys):
            return fn.__name__, fn
    return None


def scrub(text: str, attached: bool) -> str:
    """去掉演员编出来的假链接。"""
    return FAKE_URL.sub("（文件见下）" if attached else "[链接]", text)
