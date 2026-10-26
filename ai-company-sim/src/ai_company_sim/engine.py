"""确定性引擎：工时、进度、审批、内容发布、事件触发与结算、指标（设定包第 4 章）。

这里没有任何 AI 调用。同一个 seed、同样的玩家动作，结果完全一样。
"""

import copy
import random

from . import events as evlib
from .state import NAMES, weekday

WORKERS = ["zhangwei", "lixiang", "chenyue", "zhoutao"]
PERSON_IDX = {k: i for i, k in enumerate(["wangli", "zhangwei", "lixiang", "chenyue", "zhoutao", "liumin", "sunlei", "huang"])}
DONE = ("已完成", "已取消")


def rng_for(state: dict, day: int, salt: str) -> random.Random:
    return random.Random(f"{state['randomized']['seed']}-{day}-{salt}")


def tasks_by_id(state: dict) -> dict:
    return {t["id"]: t for t in state["tasks"]}


def hm(h: float) -> str:
    h = max(0.0, h)
    return f"{int(h):02d}:{int(round((h - int(h)) * 60)) % 60:02d}"


def to_h(s: str) -> float:
    a, b = s.split(":")
    return int(a) + int(b) / 60


def event_obj(state: dict, eid: str) -> evlib.Event:
    if eid.startswith("E"):
        return next(e for e in evlib.story_events(state["randomized"]) if e.id == eid)
    return evlib.random_event(eid)


# ------------------------------------------------------------------ 日程

def meetings_today(day: int) -> list[dict]:
    wd = weekday(day)
    team = ["wangli", "zhangwei", "lixiang", "chenyue", "player"]
    m = []
    if wd == "周一":
        m.append({"name": "周例会", "time": "10:00", "hours": 1, "group": "品牌项目组", "attendees": team})
    if wd == "周三" and day != 13:
        m.append({"name": "发布会筹备会", "time": "15:00", "hours": 1, "group": "小暖 S2 发布会筹备",
                  "attendees": ["wangli", "zhangwei", "player", "zhoutao", "sunlei"]})
    if wd == "周五" and day != 15:
        m.append({"name": "周会", "time": "16:00", "hours": 1, "group": "品牌项目组", "attendees": team})
    if day == 12:
        m.append({"name": "彩排", "time": "14:00", "hours": 2, "group": "小暖 S2 发布会筹备",
                  "attendees": team + ["zhoutao", "sunlei"]})
    if day == 15:
        m.append({"name": "项目复盘会", "time": "15:00", "hours": 1, "group": "品牌项目组", "attendees": team})
    return m


def fixed_schedule(state: dict, day: int) -> list[str]:
    out = [f"{m['time']} {m['name']}（{m['group']}）" for m in meetings_today(day)]
    for t in state["tasks"]:
        if t.get("platform") and t["id"].endswith("-文") and t.get("publish_day") == day:
            out.append(f"{t['publish_time']} {t['platform']}发布：{t['id'][:3]} {t['name'].replace('（文案）', '')}")
    if day == 13:
        out.append("14:00–16:30 小暖 S2 发布会（深圳南山海岸酒店 3 楼宴会厅）")
    if weekday(day) == "周五":
        out.append("17:30 前 项目助理把周报发给王丽" if day != 15 else "17:30 前 发出月度总结")
    out.append("17:30 日报")
    return sorted(out, key=lambda x: x.split(" ")[0].split("–")[0])


# ------------------------------------------------------------------ 工时

def available_hours(state: dict, person: str, day: int) -> float:
    p = state["people"][person]
    if day == 13:
        return 0.0 if person != "lixiang" else 1.0   # 发布会当天全员在现场
    h = p.get("base_hours", 6)
    away = state["unavail"].get(person, {}).get(str(day), 0)
    if person != "zhoutao":
        if away < 4:                      # 被整天借调 / 请假的人不参加会议
            h -= sum(m["hours"] for m in meetings_today(day) if person in m["attendees"])
        h -= p.get("fixed_daily_h", 0)
    h -= away
    return max(0.0, h)


def deps_ok(tm: dict, t: dict, at: dict | None = None) -> tuple[bool, float]:
    """返回 (是否满足, 满足的时刻)。at = 今天新完成的任务 {id: 小时}。"""
    latest = 0.0
    for d in t["deps"]:
        need_approved = d.endswith("!")
        dt = tm.get(d.rstrip("!"))
        if dt is None or not dt.get("exists", True):
            continue
        # 默认"交付过一次"就能开工（之后被打回修改也不影响下游）；标 ! 的必须审批通过
        ok = dt["status"] == "已完成" if need_approved else (
            t.get("deps_waived") or dt.get("delivered") or dt["done_h"] >= dt["est_h"] or dt["status"] == "已完成")
        if not ok:
            return False, 0.0
        if at and d.rstrip("!") in at:
            latest = max(latest, at[d.rstrip("!")])
    return True, latest


def is_candidate(state: dict, t: dict, person: str, day: int) -> bool:
    if person not in t["owners"] or not t.get("exists", True) or t["status"] in DONE + ("待审核",):
        return False
    if t["est_h"] <= 0 or t["done_h"] >= t["est_h"]:
        return False
    if day < t.get("ready_day", 0) and t["done_h"] >= t["est_h"] * 0.95 - 1e-6:
        return False                     # 只差"等日子"了（例如周涛承诺晚 1 天），先去做别的
    if day < t["start_day"] and t["due_day"] - day > 3:
        return False
    if person == "zhangwei" and t["project"] == "C" and not state["flags"].get("c_mandated"):
        return False
    return True


def sort_key(state: dict, t: dict, person: str, day: int, chased: set, rng: random.Random):
    forced = t["id"] in state["forced"] and state["forced"][t["id"]] >= day
    overdue_chased = t["due_day"] < day and t["id"] in chased
    due = t["due_day"] - (0.5 if person == "lixiang" and t["project"] == "B" else 0)
    pref = {"A": 0, "B": 1, "C": 2}[t["project"]] if person == "zhangwei" else 0
    if person == "chenyue" and t["id"] in chased:
        pref = -1
    return (not forced, not overdue_chased, due, pref, rng.random())


def eff(state: dict, person: str) -> float:
    return state["people"][person].get("eff", 1.0)


def allocate(state: dict, day: int, chased: set) -> dict:
    """把每个人当天的工时分到任务上。返回 {completions: {任务: 小时(钟点)}, alloc: {人: [(任务, 小时)]}}。"""
    tm = tasks_by_id(state)
    rng = rng_for(state, day, "alloc")
    completions: dict[str, float] = {}
    alloc: dict[str, list] = {p: [] for p in WORKERS}
    left = {p: available_hours(state, p, day) for p in WORKERS}
    total = {p: max(left[p], 0.01) for p in WORKERS}
    cursor = {p: 9.5 for p in WORKERS}   # 钟点

    def work(p: str, t: dict, start_at: float, budget: float | None = None, overtime: bool = False) -> None:
        e = eff(state, p)
        need = (t["est_h"] - t["done_h"]) / e
        give = min(need, left[p] if budget is None else budget)
        if give <= 0:
            return
        cap = t["est_h"] if day >= t.get("ready_day", 0) else t["est_h"] * 0.95
        t["done_h"] = min(cap, t["done_h"] + give * e)
        if not overtime:
            left[p] -= give
        span = give if overtime else give * 8.5 / total[p]
        cursor[p] = max(cursor[p], start_at) + span
        alloc[p].append((t["id"], round(give, 2)))
        if t["status"] in ("未开始", "阻塞"):
            t["status"] = "进行中"
        if t["done_h"] >= t["est_h"] - 1e-6:
            completions[t["id"]] = cursor[p]

    for pass_no in (1, 2):
        for p in WORKERS:
            cands = [t for t in state["tasks"] if is_candidate(state, t, p, day)]
            cands.sort(key=lambda t: sort_key(state, t, p, day, chased, rng))
            for t in cands:
                if left[p] <= 0.01:
                    break
                # 前置今天才完成的，要等它几点完成之后才能接着做（下游不能比上游先交）
                ok, at = deps_ok(tm, t, completions)
                if not ok:
                    if t["status"] == "未开始" and day >= t["start_day"]:
                        t["status"] = "阻塞"
                    continue
                if at >= 17.0:
                    continue
                work(p, t, at)

    # 加班：小李（以及陈悦少量）为当天 20:00 的推送赶工（设定包：小李经常熬夜赶稿）
    for p, limit in (("lixiang", 2.5), ("chenyue", 1.0)):
        for t in state["tasks"]:
            if p in t["owners"] and t.get("publish_day") == day and t.get("platform") == "公众号" \
                    and t["status"] not in DONE and t["done_h"] < t["est_h"] and t.get("exists", True):
                ok, at = deps_ok(tm, t, completions)
                if ok:
                    cursor[p] = max(cursor[p], 18.5, at)
                    work(p, t, cursor[p], budget=limit, overtime=True)

    # 被追问的到期 / 逾期任务：负责人当晚挤 1 小时赶一下。每人每周最多 3 次，对你信任低于 40 的人不加班。
    # 催促能救急，但补不上结构性超载（超载要靠找王丽砍范围、换人、改期）。
    overtime = []
    week = (day - 1) // 5
    for p in WORKERS:
        used = state.setdefault("chase_overtime", {}).setdefault(p, [])
        if state["people"][p].get("trust", 50) < 40 or available_hours(state, p, day) <= 0 \
                or sum((d - 1) // 5 == week for d in used) >= 3:
            continue
        due = [t for t in state["tasks"] if t["id"] in chased and t["due_day"] <= day and is_candidate(state, t, p, day)]
        for t in sorted(due, key=lambda t: t["due_day"]):
            ok, at = deps_ok(tm, t, completions)
            if ok:
                cursor[p] = max(cursor[p], 18.5, at)
                work(p, t, cursor[p], budget=1.0, overtime=True)
                used.append(day)
                overtime.append((p, t["id"]))
                break
    return {"completions": completions, "alloc": alloc, "hours": {p: round(total[p], 2) for p in WORKERS},
            "overtime": overtime}


# ------------------------------------------------------------------ 审批

def approval_delay(state: dict, t: dict, day: int) -> int:
    ap = t.get("approver") or ""
    if "wangli" not in ap:
        return 1
    if t.get("platform") and t.get("publish_day", 99) - day <= 1:
        return 0                      # 内容临发布才送审，王丽当天审（"先这样发吧"）
    if 11 <= day <= 13:
        return 0
    d = 1 if state["improvements"]["I7"]["active"] else 2
    if state["randomized"].get("difficulty") == "easy":
        d = 1
    return d + state["approval_extra"].get(str(day), 0)


def submit(state: dict, t: dict, day: int, at: float) -> None:
    t["completed_time"] = hm(at)
    t["delivered"] = True
    if not t.get("approver"):
        t["status"] = "已完成"
        t["completed_day"] = day
        return
    t["status"] = "待审核"
    t["submitted_day"] = day
    t["approve_day"] = day + approval_delay(state, t, day)
    t["approve_time"] = hm(at + 0.3) if t["approve_day"] == day else "10:00"


def process_approvals(state: dict, day: int) -> list[dict]:
    out = []
    for t in state["tasks"]:
        if t["status"] != "待审核" or t.get("approve_day", 99) > day:
            continue
        rng = rng_for(state, day, "approve-" + t["id"])
        last_minute = t.get("platform") and t.get("publish_day", 99) - day <= 1
        if not last_minute and t["revisions"] == 0 and "wangli" in (t.get("approver") or "") and rng.random() < 0.2:
            t["revisions"] += 1
            t["est_h"] = round(t["est_h"] * 1.2, 2)
            t["status"] = "需返工"
            out.append({"task": t["id"], "result": "王丽提了修改意见，需返工"})
            continue
        t["status"] = "已完成"
        t["completed_day"] = day
        t["approved_day"] = day
        out.append({"task": t["id"], "result": "审批通过"})
    return out


# ------------------------------------------------------------------ 内容发布（项目 B）

def ready_time(state: dict, item: str, day: int, completions: dict) -> float | None:
    tm = tasks_by_id(state)
    times = []
    for suffix in ("-文", "-图"):
        t = tm[item + suffix]
        if t["status"] == "已完成" and (t["completed_day"] or 0) < day:
            times.append(0.0)
        elif t["status"] == "已完成":
            times.append(to_h(t.get("approve_time") or t.get("completed_time") or "09:30"))
        else:
            return None
    return max(times)


def publish(state: dict, day: int, completions: dict) -> list[dict]:
    out = []
    tm = tasks_by_id(state)
    items = sorted({t["id"][:3] for t in state["tasks"] if t["project"] == "B"})
    for it in items:
        txt = tm[it + "-文"]
        c = state["content"].setdefault(it, {"result": None, "day": None, "time": None, "planned_day": txt["publish_day"]})
        if c["day"] or c["result"] in ("断更", "删除", "取消"):
            continue                      # 已经发了，或被事件 / 王丽决定取消
        pday = c["planned_day"]
        if day < pday:
            continue
        rt = ready_time(state, it, day, completions)
        slot = to_h(txt["publish_time"])
        if rt is None:
            if day == pday and c["result"] is None:
                c["result_pending"] = "未发出"
                out.append({"item": it, "result": "未发出", "title": txt["name"]})
            continue
        if day == pday and rt <= slot:
            natural, at = ("计划内调整" if txt.get("planned_change") else "准时"), slot
        elif day == pday:
            natural, at = "晚发", rt + 0.2
        else:
            natural, at = ("计划内调整" if txt.get("planned_change") else "延误" if day - pday <= 1 else "断更后补发"), 10.0
        preset = c["result"] if c["result"] not in (None, "未发出") else None   # 事件结果优先（卡片优先）
        res = preset or natural
        c.update({"result": res, "day": day, "time": hm(at)})
        rng = rng_for(state, day, "data-" + it)
        if txt["platform"] == "公众号":
            c["data"] = {"阅读": rng.randint(800, 3200), "在看": rng.randint(10, 80)}
        else:
            c["data"] = {"点赞": rng.randint(40, 600), "收藏": rng.randint(10, 200), "评论": rng.randint(3, 60)}
        out.append({"item": it, "result": res, "time": hm(at), "title": txt["name"].replace("（文案）", "")})
    return out


def finalize_missed(state: dict, day: int) -> None:
    """当天该发没发的，记为断更（之后补发记为延误/断更后补发）。"""
    for it, c in state["content"].items():
        if c.get("result_pending") == "未发出" and c["result"] is None and c["planned_day"] == day:
            c["result"] = "未发出"
        c.pop("result_pending", None)


# ------------------------------------------------------------------ 汇报进度与日报

def plan_progress(t: dict, day: int) -> float:
    span = t["due_day"] - t["start_day"] + 1
    if span <= 0:
        return 100.0
    return max(0.0, min(1.0, (day - t["start_day"] + 1) / span)) * 100


def true_progress(t: dict) -> int:
    if t["status"] == "已完成":
        return 100
    if t["est_h"] <= 0:
        return 0
    return int(min(100, t["done_h"] / t["est_h"] * 100))


def lixiang_bias(state: dict, day: int) -> int:
    bo = state.get("bias_override")
    if bo and day <= bo[1]:
        return bo[0]
    if state["improvements"]["I3"]["active"]:
        return 10
    return state["people"]["lixiang"].get("bias", 25)


def reported_progress(state: dict, t: dict, day: int):
    tp = true_progress(t)
    owner = t["owners"][0]
    if t["unmasked"] or owner in ("chenyue",):
        return tp
    if owner == "lixiang":
        if tp < plan_progress(t, day) - 10 and t["status"] not in DONE:
            return min(95, tp + lixiang_bias(state, day))
        return tp
    if owner == "zhangwei":
        return "（不给数字）" + ("差不多了" if tp >= 80 else "在跟" if tp >= 30 else "推进中")
    if owner == "zhoutao":
        return "快了"
    return tp


def report_rate(state: dict, person: str, day: int, prefill: bool) -> float:
    imp = state["improvements"]
    if person == "zhangwei":
        if imp["I2"]["active"]:
            return 0.95 if prefill else 0.8
        return 0.4
    if person == "chenyue":
        if state["unavail"].get("chenyue", {}).get(str(day), 0) >= 4:
            return 0.0
        return 0.9 if imp["I2"]["active"] else 0.7
    return 1.0


def daily_reports(state: dict, day: int, alloc: dict, prefill: bool) -> list[dict]:
    out = []
    if day == 13:
        return out
    for p in ("zhangwei", "lixiang", "chenyue"):
        if available_hours(state, p, day) <= 0 and p != "chenyue":
            continue
        rng = random.Random(state["randomized"]["seed"] + day * 100 + PERSON_IDX[p])
        submitted = rng.random() < report_rate(state, p, day, prefill)
        worked = [tid for tid, _ in alloc.get(p, [])]
        tm = tasks_by_id(state)
        items = []
        for tid in dict.fromkeys(worked):
            t = tm[tid]
            items.append({"task": tid, "name": t["name"], "true": true_progress(t), "reported": reported_progress(state, t, day),
                          "status": t["status"], "stale": t.get("stale", False)})
        behind = [i for i in items if isinstance(i["reported"], int) and i["reported"] != i["true"]]
        out.append({"person": p, "name": NAMES[p], "submitted": submitted, "items": items,
                    "valid": submitted and (p != "zhangwei" or prefill or state["improvements"]["I3"]["active"]),
                    "inflated": bool(behind)})
    return out


# ------------------------------------------------------------------ 事件


def judge(state: dict, eid: str, rec: dict) -> str:
    e = event_obj(state, eid)
    if eid == "E13" and state["improvements"]["I8"]["active"] and state["improvements"]["I8"]["day"] <= rec["burst"]:
        return "化解"
    if e.judge:
        return e.judge(rec["done_k"], {"start": rec["start"], "decide": rec.get("decide", rec["burst"])})
    return evlib.count_judge(list(e.keys))(rec["done_k"], {})


def provisional(state: dict, eid: str) -> str:
    rec = state["events"][eid]
    if rec["result"]:
        return rec["result"]
    return judge(state, eid, rec)


def trigger_story_events(state: dict, day: int) -> list[str]:
    started = []
    for eid, rec in state["events"].items():
        if rec["start"] == day and rec["stage"] == "未触发":
            rec["stage"] = "潜伏" if rec["reveal"] > day else "显露"
            apply_effects(state, event_obj(state, eid).on_start, rec["start"], eid)
            started.append(eid)
        elif rec["stage"] == "潜伏" and rec["reveal"] <= day:
            rec["stage"] = "显露"
        if rec["stage"] in ("潜伏", "显露") and rec["burst"] == day:
            rec["stage"] = "爆发日"
    return started


def draw_random(state: dict, day: int, n_story_today: int) -> list[str]:
    if day == 13:
        return []
    rng = rng_for(state, day, "random")
    hard = state["randomized"].get("difficulty") == "hard"
    roll = rng.randint(1, 4 if hard else 6)
    tier = None
    if hard:
        tier = "中" if roll == 4 else ("轻" if roll == 3 else None)
    else:
        tier = "中" if roll == 6 else ("轻" if roll >= 4 else None)
    if state["randomized"].get("difficulty") == "easy" and tier == "中":
        tier = "轻"
    if tier and n_story_today >= 2:
        tier = "轻" if tier == "中" else None
    if not tier:
        return []
    pool = evlib.MEDIUM_POOL if tier == "中" else evlib.LIGHT_POOL
    if state["improvements"]["I8"]["active"]:
        pool = [r for r in pool if r != "R03"]
    if state["improvements"]["I1"]["active"] and rng.random() < 0.5:
        pool = [r for r in pool if r not in ("R02", "R07")]
    pool = [r for r in pool if r not in state["random_drawn"]
            and (evlib.random_event(r).eligible is None or evlib.random_event(r).eligible(day))]
    if not pool:
        return []
    rid = rng.choice(pool)
    state["random_drawn"].append(rid)
    rec = {"id": rid, "start": day, "reveal": day, "burst": day + 1, "decide": day + 1,
           "done_k": {}, "result": None, "stage": "显露"}
    if rid == "R18":
        rec["person"] = state["randomized"]["half_day_person"]
    state["random_active"].append(rec)
    eff_ = copy.deepcopy(evlib.random_event(rid).on_start)
    if rid == "R18":
        eff_ = {"unavail": {rec["person"]: {0: 3}}}
    apply_effects(state, eff_, day, rid)
    return [rid]


def active_events(state: dict, day: int) -> list[dict]:
    """当前在进行中的事件（给评估和剧本用），含卡片内容。"""
    out = []
    for eid, rec in state["events"].items():
        if rec["stage"] in ("潜伏", "显露", "爆发日") or (rec["result"] is None and rec["start"] <= day):
            out.append({"rec": rec, "ev": event_obj(state, eid), "id": eid})
    for rec in state["random_active"]:
        if rec["result"] is None:
            out.append({"rec": rec, "ev": evlib.random_event(rec["id"]), "id": rec["id"]})
    return out


def resolve_due_events(state: dict, day: int) -> list[dict]:
    out = []
    for eid, rec in state["events"].items():
        if rec["result"] is None and rec["start"] <= day and rec["decide"] <= day:
            res = judge(state, eid, rec)
            rec.update({"result": res, "stage": res, "resolved_day": day})
            o = event_obj(state, eid).outcomes[res]
            apply_effects(state, o, rec["start"], eid)
            out.append({"id": eid, "name": event_obj(state, eid).name, "result": res, "narrative": narrate(state, o)})
    for rec in state["random_active"]:
        if rec["result"] is None and rec["decide"] <= day:
            res = "化解" if "K1" in rec["done_k"] else "未处理"
            rec.update({"result": res, "stage": res, "resolved_day": day})
            o = evlib.random_event(rec["id"]).outcomes[res]
            apply_effects(state, o, rec["start"], rec["id"])
            out.append({"id": rec["id"], "name": evlib.random_event(rec["id"]).name, "result": res, "narrative": narrate(state, o)})
    return out


def _current_task(state: dict, person: str) -> str | None:
    open_ = [t for t in state["tasks"] if person in t["owners"] and t["status"] in ("进行中", "需返工") and t.get("exists", True)]
    open_.sort(key=lambda t: t["due_day"])
    return open_[0]["id"] if open_ else None


def apply_effects(state: dict, eff_: dict, start: int, source: str) -> None:
    tm = tasks_by_id(state)
    for who, d in eff_.get("trust", {}).items():
        change_trust(state, who, d, f"{source} 结果")
    for label, amt in eff_.get("budget_over", []):
        state["budget_over"].append([label, amt, source])
    for tid, h in eff_.get("add_hours", {}).items():
        if tid.startswith("$"):
            tid = _current_task(state, tid[1:].replace("_current", ""))
        if tid and tid in tm and tm[tid]["status"] not in DONE:
            tm[tid]["est_h"] = round(tm[tid]["est_h"] + h, 2)
            if tm[tid]["status"] == "待审核":
                tm[tid]["status"] = "需返工"
    for tid, h in eff_.get("add_done", {}).items():
        t = tm[tid]
        t["done_h"] = min(t["est_h"] * 0.95, t["done_h"] + h)
    for tid, rel in eff_.get("ready_day", {}).items():
        tm[tid]["ready_day"] = start + rel
    for tid, rel in eff_.get("complete_by", {}).items():
        state.setdefault("complete_by", {})[tid] = start + rel
    for tid, n in eff_.get("due_shift", {}).items():
        if tm[tid]["status"] not in DONE:
            tm[tid]["due_day"] += n
    for person, days in eff_.get("unavail", {}).items():
        for rel, h in days.items():
            u = state["unavail"].setdefault(person, {})
            u[str(start + int(rel))] = u.get(str(start + int(rel)), 0) + h
    if "bias" in eff_:
        v, until = eff_["bias"]
        state["bias_override"] = [v, start + until]
    for dim, d in eff_.get("score", {}).items():
        state["score_adj"][dim] = state["score_adj"].get(dim, 0) + d
    for it, res in eff_.get("content", {}).items():
        if it.startswith("$pub"):            # $pub0 = 事件开始当天发布的内容，$pub1 = 第二天的
            pday = start + int(it[4:])
            it = next((t["id"][:3] for t in state["tasks"] if t["id"].endswith("-文") and t.get("publish_day") == pday), None)
            if not it:
                continue
        set_content(state, it, res)
    for k, v in eff_.get("flag", {}).items():
        state["flags"][k] = v
    if "approval_extra" in eff_:
        n, rel = eff_["approval_extra"]
        key = str(start + rel)
        state["approval_extra"][key] = state["approval_extra"].get(key, 0) + n
    for tid in eff_.get("cancel", []):
        if tm[tid]["status"] not in DONE:
            tm[tid]["status"] = "已取消"
            tm[tid]["planned_change"] = True
    for tid in eff_.get("exists", []):
        tm[tid]["exists"] = True
    for tid, rel in eff_.get("forced", {}).items():
        if rel <= 0:
            state["forced"].pop(tid, None)
        else:
            state["forced"][tid] = start + rel
    if "delivery_shift" in eff_:
        state["flags"]["delivery_shift"] = eff_["delivery_shift"]
    if eff_.get("product_change"):
        rz = state["randomized"]
        state["product"]["price"] = rz["new_price"]
        state["product"]["claims"] = [rz["claim_change"][1] if c == rz["claim_change"][0] else c for c in state["product"]["claims"]]
        state["product"]["doc_version"] = "v2（D7 11:05 周涛修改）"


def set_content(state: dict, item: str, res: str) -> None:
    tm = tasks_by_id(state)
    c = state["content"].setdefault(item, {"result": None, "day": None, "time": None, "planned_day": tm[item + "-文"]["publish_day"]})
    c["result"] = res
    if res in ("断更", "删除", "取消") and not c["day"]:
        for s in ("-文", "-图"):
            if tm[item + s]["status"] not in DONE:
                tm[item + s]["status"] = "已取消"
    if res == "计划内调整" and not c["day"]:
        for s in ("-文", "-图"):
            tm[item + s]["done_h"] = tm[item + s]["est_h"]
            tm[item + s]["status"] = "已完成"
            tm[item + s]["completed_day"] = state["sim_day"]
            tm[item + s]["completed_time"] = "16:30"
        c.update({"day": state["sim_day"], "time": "17:00"})


def change_trust(state: dict, who: str, delta: int, reason: str) -> None:
    if who not in state["people"] or who == "player":
        return
    p = state["people"][who]
    p["trust"] = max(0, min(100, p.get("trust", 50) + delta))
    state["trust_history"].append({"day": state["sim_day"], "who": who, "delta": delta, "reason": reason, "now": p["trust"]})


# ------------------------------------------------------------------ 物料到场与邀约

def invites(state: dict) -> dict:
    t = tasks_by_id(state)["A2"]
    p = min(1.0, t["done_h"] / t["est_h"]) if t["est_h"] else 1.0
    f = max(0.0, (p - 0.3) / 0.7)
    return {"media_confirmed": round(5 + 13 * f), "dealer_confirmed": round(13 + 23 * f), "media_target": 20, "dealer_target": 40}


def narrate(state: dict, outcome: dict) -> str:
    """事件后果的描述。物料到场时间只认 delivery() 算出来的，剧本和结局报告说法一致。"""
    return outcome.get("narrative", "").replace("{到场}", delivery(state))


def delivery(state: dict) -> str:
    fl = state["flags"]
    late = (fl.get("order_ok") is False) or fl.get("a6_late", 0) >= 2
    if fl.get("finance_block") and fl.get("order_ok") is False:
        base = "D13 10:00"
    else:
        base = "D13 08:00" if late else "D12 12:00"
    shift = fl.get("delivery_shift")
    if shift is None:
        return base
    if base.startswith("D12"):
        return ["D12 20:00", "D13 08:00", state["randomized"]["print_delay_to"]][shift]
    return [base, "D13 10:00", "D13 13:00"][shift]


# ------------------------------------------------------------------ 一天的计算

def compute_day(state: dict, day: int, chased: set, prefill: bool) -> dict:
    """收工时调用：审批 → 分配工时 → 完成与送审 → 审批（当天） → 发布 → 日报。"""
    tm = tasks_by_id(state)
    facts = {"approvals": process_approvals(state, day)}
    before = {t["id"]: t["status"] for t in state["tasks"]}
    res = allocate(state, day, chased)
    comp = res["completions"]

    # 早上已经在群里"说好"的完成（剧本已经播出），收工时兑现
    for tid, at in state.get("committed", {}).items():
        t = tm[tid]
        if t["done_h"] < t["est_h"] and t["status"] not in DONE:
            t["done_h"] = t["est_h"]
            comp[tid] = to_h(at)
    # 事件卡要求的"最晚某日完成"
    for tid, by in list(state.get("complete_by", {}).items()):
        t = tm[tid]
        if day >= by and t["status"] not in DONE + ("待审核",) and t["done_h"] < t["est_h"]:
            t["done_h"] = t["est_h"]
            comp[tid] = 16.0

    rework = []
    for tid, at in sorted(comp.items(), key=lambda x: x[1]):
        t = tm[tid]
        if t["status"] in DONE + ("待审核",):
            continue
        # 陈悦返工（设定包 2.4）：没有设计需求单 30%，有 10%
        if t["owners"] == ["chenyue"] and not t["rework_done"]:
            p = 0.1 if state["improvements"]["I4"]["active"] else 0.3
            t["rework_done"] = True
            if rng_for(state, day, "rework-" + tid).random() < p:
                t["est_h"] = round(t["est_h"] * 1.3, 2)
                t["status"] = "需返工"
                rework.append(tid)
                continue
        submit(state, t, day, at)
        if t["owners"] == ["zhangwei"] and rng_for(state, day, "stale-" + tid).random() < 0.5:
            t["stale"] = True   # 做完了但不更新状态（设定包 4.4）
    facts["approvals"] += process_approvals(state, day)
    facts["rework"] = rework
    facts["completed"] = [{"task": tid, "time": tm[tid].get("completed_time"), "status": tm[tid]["status"]}
                          for tid in comp if before.get(tid) != tm[tid]["status"]]

    for t in state["tasks"]:
        if t["id"] == "A15" and day == 12 or t["id"] == "A16" and day == 13:
            t["status"], t["completed_day"] = "已完成", day
        if t["id"] == "A8":
            state["delivery"] = delivery(state) if state["flags"].get("order_ok") is not None else None
            if state["delivery"] and int(state["delivery"][1:3]) <= day:
                t["status"], t["completed_day"] = "已完成", day
            elif state["flags"].get("order_ok") is not None:
                t["status"] = "进行中"
    facts["published"] = publish(state, day, comp)
    finalize_missed(state, day)
    facts["alloc"] = res["alloc"]
    facts["overtime"] = res["overtime"]
    facts["hours"] = res["hours"]
    facts["reports"] = daily_reports(state, day, res["alloc"], prefill)
    return facts


def plan_day(state: dict, day: int, chased: set | None = None) -> dict:
    """做一次"演习"（不改真实状态），得到今天大概率会发生的完成，用于写剧本。
    已经在群里说出去的完成（state["committed"]）照样兑现；chased = 玩家到目前为止追过的任务。"""
    sim = copy.deepcopy(state)
    facts = compute_day(sim, day, chased or set(), False)
    committed = {c["task"]: c["time"] for c in facts["completed"] if c["time"] and to_h(c["time"]) < 17.0}
    return {"committed": committed, "alloc": facts["alloc"], "hours": facts["hours"]}


# ------------------------------------------------------------------ 指标

def overdue(state: dict, day: int) -> list[str]:
    return [t["id"] for t in state["tasks"]
            if t.get("exists", True) and t["status"] not in DONE and t["due_day"] <= day and t["due_day"] > 0
            and "all" not in t["owners"] and t["owners"] != ["sunlei"]]


def record_metrics(state: dict, day: int, facts: dict) -> None:
    reps = facts.get("reports", [])
    waits = [t["approved_day"] - t["submitted_day"] for t in state["tasks"] if t.get("approved_day") == day and t.get("submitted_day")]
    state["metrics_daily"].append({
        "day": day,
        "overdue": len(overdue(state, day)),
        "overdue_ids": overdue(state, day),
        "reports_expected": len(reps),
        "reports_submitted": sum(r["submitted"] for r in reps),
        "reports_valid": sum(r["valid"] for r in reps),
        "approval_waits": waits,
        "pending_approval": sum(1 for t in state["tasks"] if t["status"] == "待审核"),
        "trust": {k: v.get("trust") for k, v in state["people"].items() if k != "player"},
    })


def final_scores(state: dict) -> dict:
    adj = state["score_adj"]
    dl = state.get("delivery") or delivery(state)
    mat = 25 if dl.startswith("D12") else (15 if to_h(dl[4:]) <= 12 else 10)
    tm = tasks_by_id(state)
    on_time = all(tm[x]["completed_day"] is not None and tm[x]["completed_day"] <= tm[x]["orig_due"] + 1 for x in ("A2", "A5"))
    media, dealer = (16, 33) if on_time else (14, 31)
    att = max(0, 25 - max(0, 16 - media) - max(0, 32 - dealer))
    e14 = state["events"]["E14"]["done_k"]
    flow = 20 + adj.get("流程顺畅", 0) - 5 * sum(1 for k in ("K1", "K2", "K3") if k not in e14)
    info = 20 + adj.get("信息正确", 0)
    over = sum(a for _, a, _ in state["budget_over"])
    budget = 10 if over <= 0 else (5 if over <= 10000 else 0)
    contents = state["content"]
    cancelled = sum(1 for c in contents.values() if c["result"] == "取消")
    good = sum(1 for c in contents.values() if c["result"] in ("准时", "计划内调整"))
    return {
        "发布会": {"物料按时齐全": mat, "到场率": att, "信息正确": max(0, info), "流程顺畅": max(0, flow),
                 "预算": budget, "总分": mat + att + max(0, info) + max(0, flow) + budget},
        "物料到场": dl, "到场人数": {"媒体": media, "经销商": dealer}, "超支明细": state["budget_over"],
        "内容准时发布率": f"{good}/{15 - cancelled}",
        "入职优化": state["flags"].get("c_result", "未结算"),
    }
