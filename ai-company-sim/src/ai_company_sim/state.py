"""state.json 的读写、初始化和开跑前随机化（设定包附录 A、4.10）。"""

import copy
import json
import random

from . import config
from .events import story_events

NAMES = {
    "wangli": "王丽", "zhangwei": "张伟", "lixiang": "李想", "chenyue": "陈悦", "zhoutao": "周涛",
    "liumin": "刘敏", "sunlei": "孙磊", "huang": "黄建国", "player": "项目助理",
}
KEY_BY_NAME = {v: k for k, v in NAMES.items()}
KEY_BY_NAME.update({"王姐": "wangli", "老张": "zhangwei", "小李": "lixiang", "小陈": "chenyue", "黄总": "huang", "我": "player", "你": "player"})

WEEKDAYS = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五"}


def weekday(day: int) -> str:
    return WEEKDAYS[(day - 1) % 5 + 1]


def date_str(state: dict, day: int) -> str:
    return state["calendar"][f"D{day}"]


def load() -> dict:
    if not config.STATE_FILE.exists():
        raise SystemExit("还没有初始化。先运行：uv run sim init")
    state = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    for iid in ("I12", "I13"):          # 旧存档没有后来加的改进
        state["improvements"].setdefault(iid, {"active": False, "day": None})
    return state


def save(state: dict) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(config.STATE_FILE)


def snapshot(state: dict, label: str) -> None:
    config.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    (config.HISTORY_DIR / f"{label}.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def _fix_tasks(tasks: list[dict]) -> None:
    """把附录 A 的任务表转成引擎能直接用的形式。"""
    for t in tasks:
        owner = t["owner"]
        t["owners"] = owner.split("+") if owner != "all" else ["all"]
        t["orig_due"] = t["due_day"]
        t.setdefault("ready_day", 0)
        t.update({"completed_day": None, "completed_time": None, "submitted_day": None,
                  "approved_day": None, "rework_done": False, "unmasked": False, "stale": False,
                  "revisions": 0, "planned_change": False})
        if t["status"] == "已完成":
            t["completed_day"] = 0
    by_id = {t["id"]: t for t in tasks}
    # 依赖调整（审查后的决定，原因写在 README 的"与设定包的差异"里）：
    by_id["A5"]["deps"] = ["A4!"]          # 发邀请函要等邀请函设计审核通过；不必等邀约名单全部确认
    by_id["A14"]["deps"] = []              # "预算审批"不是任务，改由事件 E04 控制
    by_id["B12-文"]["deps"] = []           # 直播方案在 E04 后就定了，文案不必等直播执行完
    by_id["B13-文"]["deps"] = []           # 现场预热笔记 12:00 发，早于发布会开始
    by_id["A10"]["ready_day"] = 11         # 周涛"承诺晚 1 天"：PPT 内容最终版 D11 晚上才给（E13）


def init(seed: int, difficulty: str = "standard") -> dict:
    base = json.loads((config.DATA_DIR / "initial_state.json").read_text(encoding="utf-8"))
    rng = random.Random(seed)
    rz = {
        "seed": seed,
        "difficulty": difficulty,
        "event_day_shift": {
            "E02": rng.choice([-1, 0, 1]),
            "E04": rng.choice([-1, 0, 1]),
            "E09": rng.choice([0, 1]),       # 不能和 E08（D7）同一天
            "E11": rng.choice([-1, 0, 1]),
        },
        "new_price": rng.choice([349, 369, 379]),
        "claim_change": rng.choice([["3秒速热", "5秒速热"], ["静音30分贝", "静音35分贝"]]),
        "sick_person": "lixiang" if rng.random() < 0.7 else "zhangwei",
        "print_delay_to": rng.choice(["D13 08:00", "D13 12:00"]),
        "gift_item": rng.choice(["伴手礼", "抽奖礼品"]),
        "half_day_person": rng.choice(["zhangwei", "chenyue"]),
    }
    if difficulty == "hard":
        rz["print_delay_to"] = "D13 12:00"
    state = copy.deepcopy(base)
    state["randomized"] = rz
    _fix_tasks(state["tasks"])

    events = {}
    for ev in story_events(rz):
        shift = rz["event_day_shift"].get(ev.id, 0)
        events[ev.id] = {
            "stage": "未触发", "start": ev.start + shift, "reveal": ev.reveal + shift,
            "burst": ev.burst + shift, "decide": ev.decide_day + shift,
            "done_k": {}, "result": None, "resolved_day": None,
        }
    state["events"] = events
    by_id = {t["id"]: t for t in state["tasks"]}
    by_id["A0"]["ready_day"] = events["E02"]["start"] + 1    # 周涛承诺晚 1 天
    by_id["A14"]["start_day"] = events["E04"]["start"]
    by_id["A13"]["name"] = f"{rz['gift_item']}采购"

    state.update({
        "sim_day": 0, "phase": "night", "clock": "09:00",
        "random_active": [], "random_drawn": [],
        "forced": {}, "chased": {}, "unavail": {}, "approval_extra": {},
        "bias_override": None, "urgent_used": {}, "budget_over": [], "score_adj": {},
        "content": {}, "delivery": None, "committed": {}, "wangli_decisions": [],
        "risk_logged": {}, "metrics_daily": [], "log": [],
        "trust_history": [], "player_open_id": "",
    })
    for p in state["people"].values():
        p.setdefault("trust", 50)
    state["people"]["player"] = {"name": "项目助理", "title": "项目助理"}
    if difficulty == "easy":
        state["people"]["lixiang"]["bias"] = 15
    return state
