"""一天的三个阶段：
- start_day（上午）：触发事件 → 演习今天的工作 → 导演写上午剧本（P1）→ 演员写群消息和会议实录（P2、P6）
- noon_day（下午）：导演先结算玩家上午的动作（P5）→ 带着这些动作重新演习 → 写下午剧本，NPC 对上午的动作做出反应
- end_day（收工）：导演评估玩家下午新增的动作（P5）→ 结算事件 → 引擎算今天的真实进度 → 日报（P4）→ 晚间群消息
"""

import copy
import json
import random
import re

from . import config, engine, llm, schemas, texts
from .events import story_events
from .state import KEY_BY_NAME, NAMES, date_str, save, snapshot, weekday

GROUPS = ["品牌项目组", "小暖 S2 发布会筹备"]
PHASES = ("morning", "afternoon", "evening")
NOON = "12:00"


def phase_of(time: str) -> str:
    return "morning" if time < NOON else "afternoon" if time < "17:30" else "evening"


def norm_clock(t: str) -> str | None:
    """"9:30" → "09:30"；不是合法时间返回 None。时间都按字符串比较，所以必须补零。"""
    m = re.fullmatch(r"\s*(\d{1,2})[:：](\d{2})\s*", t or "")
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return f"{int(m[1]):02d}:{m[2]}"


def clock_window(state: dict) -> tuple[str, str]:
    """玩家现在能用的模拟时间范围：上午 09:00–11:59，下午 12:00–23:59。"""
    return ("09:00", "11:59") if state.get("half") == "am" else (NOON, "23:59")


def set_clock(state: dict, t: str) -> str:
    """返回错误提示；成功返回空字符串。"""
    c = norm_clock(t)
    if not c:
        return f"「{t}」不是时间，写成 14:30 这样"
    lo, hi = clock_window(state)
    if not lo <= c <= hi:
        return f"现在只能在 {lo}–{hi} 之间（{'上午还没结束，下午的事等 sim noon 之后再做' if state.get('half') == 'am' else '已经是下午了'}）"
    state["clock"] = c
    return ""


# ------------------------------------------------------------------ 提示词与文件

def prompt(file_prefix: str, /, **kw) -> str:
    path = next(config.PROMPTS_DIR.glob(f"{file_prefix}*.md"))
    s = path.read_text(encoding="utf-8")
    for k, v in kw.items():
        s = s.replace("{{" + k + "}}", v if isinstance(v, str) else llm.dump(v))
    return s


def p0() -> str:
    cal = "；".join(f"{k}={v}" for k, v in json.loads((config.DATA_DIR / "initial_state.json").read_text(encoding="utf-8"))["calendar"].items())
    return prompt("P0", world=texts.world(), calendar=cal)


def out_dir(day: int):
    d = config.OUTPUT_DIR / f"D{day}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def director_dir():
    config.DIRECTOR_OUT_DIR.mkdir(parents=True, exist_ok=True)
    return config.DIRECTOR_OUT_DIR


def load_msgs(day: int, phase: str) -> list[dict]:
    f = config.OUTPUT_DIR / f"D{day}" / f"{phase}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def recent_msgs(day: int, n: int = 30) -> list[dict]:
    msgs = []
    for d in range(max(1, day - 2), day + 1):
        for ph in PHASES:
            msgs += sorted((m for m in load_msgs(d, ph) if m.get("kind") == "msg"), key=lambda m: m["time"])
    return msgs[-n:]


def fmt_msgs(msgs: list[dict]) -> str:
    return "\n".join(f"[{m['time']}][{m['group']}] {m['sender']}：{m['text']}" for m in msgs) or "（无）"


# 公开的项目关键日期（玩家手册第 3 章里就有），让大家说日期时不出错
KEY_DATES = ("项目关键日期：发布会 11月18日（周三）14:00，前一天 11月17日 14:00 彩排；"
             "物料要在 11月12日（周四）17:00 前下单；入职优化 11月20日（周五）向人事汇报；"
             "公众号每周二、四 20:00 发，小红书每周一、三、五 12:00 发；周报每周五 17:30 前交王丽。")


def story_so_far(state: dict, day: int) -> str:
    """每天收工时写的"公开纪要"，让后面几天的对话记得前面发生过什么。"""
    sums = state.get("daily_summaries", {})
    lines = [f"{date_str(state, int(d))}：{t}" for d, t in sorted(sums.items(), key=lambda x: int(x[0])) if int(d) < day]
    return "\n".join(lines) or "（今天是第一天）"


def context(state: dict, day: int, n: int = 30) -> str:
    return f"【前情提要（之前每天的公开纪要）】\n{story_so_far(state, day)}\n\n{KEY_DATES}\n\n【最近群聊】\n{fmt_msgs(recent_msgs(day, n))}"


def write_daily_summary(state: dict, day: int) -> None:
    msgs = [m for ph in PHASES for m in load_msgs(day, ph)]
    text = []
    for m in msgs:
        if m["kind"] == "meeting":
            text.append(f"【{m['name']}】" + " / ".join(f"{l['speaker']}：{l['text']}" for l in m["lines"]))
        else:
            text.append(f"[{m['time']}][{m['group']}] {m['sender']}：{m['text']}")
    p = ("下面是一个市场部项目组今天两个群的全部聊天和会议记录。请写一段 150–250 字的「公开纪要」，"
         "只记录大家都能看到的事实：谁说了要做什么、交了什么、发了什么、遇到了什么问题、有什么承诺和约定的时间。"
         "不要评价，不要推测，不要编造，忽略闲聊。\n\n" + "\n".join(text)[:30000])
    text = llm.text_call(f"今日纪要 D{day}", p, lambda: f"（离线占位纪要 D{day}）")
    if text:
        state.setdefault("daily_summaries", {})[str(day)] = text
    else:
        print(f"  （D{day} 纪要没写出来，不影响进度；之后可以用 uv run sim summary {day} 补写）")


def backstage_so_far(state: dict, day: int, days: int = 3) -> str:
    """导演纪要：玩家前几天做了什么、私聊里谁答应了什么。只给导演看，不给演员（演员不该知道别人的私聊）。"""
    sums = state.get("backstage", {})
    lines = [f"{date_str(state, int(d))}：{t}" for d, t in sorted(sums.items(), key=lambda x: int(x[0])) if day - days <= int(d) < day]
    return "\n".join(lines) or "（无）"


def write_backstage(state: dict, day: int) -> None:
    from .chat import load_history     # 避免循环引用
    chats = []
    for f in sorted(config.CHATS_DIR.glob(f"D{day}-*.json")):
        name = f.stem.split("-", 1)[1]
        chats += [f"[{h['clock']}] {'项目助理' if h['role'] == 'user' else name}（私聊）：{h['text']}" for h in load_history(day, name)]
    log = read_actions(day).strip()
    posts = player_posts(state, day)
    if posts.startswith("（"):
        posts = ""
    if not chats and not log and not posts:
        return
    p = (f"今天是 {date_str(state, day)}（D{day}）。下面是项目助理（玩家）今天的动作日志和私聊记录。"
         "请写一段 100–250 字的「导演纪要」，只记事实：项目助理做了什么（核查、追问、上报、改表、建流程、写纪要）；"
         "私聊里谁答应了什么、给了什么时间（把\"明天\"\"今晚\"换算成具体日期）；项目助理答应了别人什么；还悬着没兑现的事。"
         "不要评价，不要编造。\n\n【动作日志】\n" + (log or "（没写）") + "\n\n【私聊】\n" + ("\n".join(chats) or "（无）")
         + "\n\n【项目助理在群里的发言】\n" + (posts or "（无）"))
    text = llm.text_call(f"导演纪要 D{day}", p[:30000], lambda: f"（离线占位导演纪要 D{day}）")
    if text:
        state.setdefault("backstage", {})[str(day)] = text


# ------------------------------------------------------------------ 给导演看的状态

def state_summary(state: dict, day: int) -> str:
    rows = ["ID | 任务 | 负责人 | 状态 | 真实% | 汇报 | 截止 | 备注"]
    for t in state["tasks"]:
        if not t.get("exists", True) or "all" in t["owners"]:
            continue
        if t["status"] in engine.DONE and (t.get("completed_day") or 0) < day - 2:
            continue
        if t["start_day"] > day + 3:
            continue
        note = []
        if t.get("stale"):
            note.append("老张做完了但没更新状态")
        if t["status"] == "待审核":
            note.append(f"送审于D{t['submitted_day']}，预计D{t['approve_day']}审完")
        if t.get("ready_day", 0) > day:
            note.append(f"D{t['ready_day']}前交不出")
        owner = "+".join(NAMES.get(o, o) for o in t["owners"])
        rows.append(f"{t['id']} | {t['name']} | {owner} | {t['status']} | {engine.true_progress(t)} | "
                    f"{engine.reported_progress(state, t, day)} | D{t['due_day']} | {'；'.join(note)}")
    inv = engine.invites(state)
    rows.append(f"\n邀约确认（真实）：媒体 {inv['media_confirmed']}/20，经销商 {inv['dealer_confirmed']}/40")
    rows.append(f"产品：{state['product']}")
    rows.append(KEY_DATES)
    pub = [f"{k} {v['result']}（D{v['day']} {v['time']}）" for k, v in sorted(state["content"].items()) if v.get("day")]
    rows.append("已发布内容：" + ("；".join(pub) or "无"))
    return "\n".join(rows)


def public_product(state: dict, day: int) -> str:
    """群里大家默认知道的产品信息：变更只有在被弄清楚之后才算"公开"。"""
    e08 = state["events"]["E08"]
    known = e08["start"] <= day and ("K1" in e08["done_k"] or e08.get("result") is not None)
    if known or day < e08["start"]:
        return f"价格 {state['product']['price']} 元；卖点：{'、'.join(state['product']['claims'])}"
    return "价格 399 元；卖点：3秒速热、巴掌大小、静音30分贝（周涛今天改了文档，但群里大多数人还不知道改了什么）"


def events_for_script(state: dict, day: int, phase: str) -> list[dict]:
    out = []
    for item in engine.active_events(state, day):
        ev, rec = item["ev"], item["rec"]
        sigs = []
        for s in ev.signals:
            if ev.level == "剧情" and rec["start"] + s["day"] != day:
                continue
            if ev.level != "剧情" and rec["start"] != day:
                continue
            if phase_of(s.get("time") or "11:00") != phase:
                continue                  # 只给导演这个时段的信号
            if s.get("when") == "unresolved":
                status = engine.provisional(state, ev.id) if ev.id.startswith("E") else "未处理"
                if status == "化解":
                    continue
            sigs.append({k: v for k, v in s.items() if k != "day"})
        if not sigs and ev.level == "剧情" and rec["stage"] == "潜伏":
            continue
        out.append({"id": ev.id, "name": ev.name, "stage": rec["stage"], "today_signals": sigs,
                    "current_judgement": engine.provisional(state, ev.id) if ev.id.startswith("E") else "未处理",
                    "truth_hidden": ev.truth, "secrets_hidden": ev.secrets,
                    "burst": f"D{rec['burst']} {ev.burst_time}"})
    return out


def consequences(state: dict, day: int, phase: str) -> list[str]:
    out = []
    for eid, rec in state["events"].items():
        if rec.get("resolved_day") is None:
            continue
        o = engine.event_obj(state, eid).outcomes[rec["result"]]
        if (phase == "morning" and rec["resolved_day"] == day - 1) or (phase == "evening" and rec["resolved_day"] == day):
            out.append(f"{eid} {rec['result']}：{engine.narrate(state, o)}")
    for rec in state["random_active"]:
        if rec.get("resolved_day") == (day - 1 if phase == "morning" else day) and rec["result"] == "未处理":
            out.append(f"{rec['id']}：{engine.narrate(state, engine.event_obj(state, rec['id']).outcomes['未处理'])}")
    if phase == "morning" and state["flags"].get("e08_second_burst") == day:
        out.append("彩排时发现价格牌、PPT 上还是旧价格（E08 二次爆发）")
    if phase == "morning" and day == 12 and state.get("delivery") and not state["delivery"].startswith("D12 12"):
        out.append(f"物料预计 {state['delivery']} 才到场，彩排时没有实物")
    return out


def trust_line(state: dict) -> str:
    return "，".join(f"{NAMES[k]} {v['trust']}" for k, v in state["people"].items() if k not in ("player",) and "trust" in v)


def player_posts(state: dict, day: int) -> str:
    f = config.FEISHU_LOG_DIR / f"D{day}.jsonl"
    lines = []
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            m = json.loads(ln)
            lines.append(f"[{m.get('clock', '')}][{m.get('group', '')}] {m.get('npc', '项目助理')}：{m['text']}")
    return "\n".join(lines) or "（没有采集到。如果玩家在群里发了消息，会写在动作日志里）"


# ------------------------------------------------------------------ 剧本 → 消息

def forbidden_tokens(state: dict, day: int) -> list[str]:
    """引擎层面的硬性防泄露词：玩家还没弄清楚时，群消息里绝不能出现。"""
    toks = []
    e08, e07 = state["events"]["E08"], state["events"]["E07"]
    if e08["start"] <= day and "K1" not in e08["done_k"] and e08["result"] is None:
        toks += [str(state["randomized"]["new_price"]), state["randomized"]["claim_change"][1]]
    if e07["start"] <= day <= e07["start"] + 1 and "K1" not in e07["done_k"]:
        toks += ["借调"]
    return toks


def stub_script(state: dict, day: int, events: list[dict], phase: str, meetings: list[dict]) -> schemas.Script:
    items = []
    for ev in events:
        for s in ev["today_signals"]:
            items.append(schemas.ScriptItem(time=s.get("time") or "11:00", group=s["group"] if s["group"] in GROUPS else GROUPS[0],
                                            sender=s["sender"], intent=s["hint"]))
    for m in meetings:
        items.append(schemas.ScriptItem(time=m["time"], group=m["group"], sender="王丽", type="meeting", name=m["name"],
                                        attendees=[NAMES[a] for a in m["attendees"]], agenda=["过一下各项目进展"]))
    first = {"morning": "09:05", "afternoon": "13:10", "evening": "18:40"}[phase]
    items.append(schemas.ScriptItem(time=first, group="品牌项目组", sender="李想", intent="闲聊"))
    items.sort(key=lambda x: x.time)
    return schemas.Script(script=items, director_notes="(offline stub)")


def write_script(state: dict, day: int, phase: str, facts: list[str], alloc: dict, meetings: list[dict]) -> schemas.Script:
    events = events_for_script(state, day, phase)
    if phase == "morning":
        window = "09:00–11:59（上午。12:00 以后的事留给下午，不要写）"
        quota = "品牌项目组 5–11 条，发布会筹备群 2–6 条" if day != 13 else "品牌项目组 3–6 条，发布会筹备群 10–20 条（发布会当天，上午在布场）"
        desc = "上午时段"
    elif phase == "afternoon":
        window = "12:00–17:20（下午。17:30 以后的事、日报都不要写）"
        quota = "品牌项目组 5–11 条，发布会筹备群 2–7 条" if day != 13 else "品牌项目组 2–5 条，发布会筹备群 20–30 条（发布会当天，节奏很快）"
        desc = "下午时段"
    else:
        window = "17:30–23:30（下班前后。日报另外生成，不用写在剧本里）"
        quota = "品牌项目组 3–8 条，发布会筹备群 0–4 条"
        desc = "下班时段"
    p = prompt(
        "P1", day=f"D{day}", date=date_str(state, day), weekday=weekday(day), phase_desc=desc, window=window,
        product=public_product(state, day), state_summary=state_summary(state, day),
        alloc=llm.dump({NAMES[k]: v for k, v in alloc.items()}), facts="\n".join(facts) or "（无）",
        events=llm.dump(events), consequences="\n".join(consequences(state, day, phase)) or "（无）",
        schedule="\n".join(engine.fixed_schedule(state, day)), player_posts=player_posts(state, day),
        player_actions=player_actions(state, day, phase),
        trust=trust_line(state), recent=context(state, day), quota=quota,
    )
    return llm.json_call(f"P1 导演剧本 D{day} {phase}", p, schemas.Script,
                         lambda: stub_script(state, day, events, phase, meetings),
                         model=config.MODEL_DIRECTOR, effort="high")


def today(state: dict, day: int) -> str:
    return f"{date_str(state, day)}（说日期时以这个为准）"


def personas_for(names: set[str]) -> str:
    return "\n\n".join(texts.persona(n) for n in sorted(names) if n in texts.personas())


_CAL = json.loads((config.DATA_DIR / "initial_state.json").read_text(encoding="utf-8"))["calendar"]


def _day_words(n: int) -> str:
    ymd, wd = _CAL[f"D{n}"].split()          # "2026-11-04 周三"
    _, m, d = ymd.split("-")
    return f"{int(m)}月{int(d)}日（{wd}）"


def due_words(n: int) -> str:
    return _day_words(n) if f"D{n}" in _CAL else "无"


def humanize(text: str) -> str:
    """演员偶尔照抄内部写法：B03-文 / B03-图 → "B03 文案 / 配图"；D3 → "11月4日（周三）"。"""
    text = re.sub(r"(B\d\d)\s*-\s*([文图])", lambda m: f"{m[1]} {'文案' if m[2] == '文' else '配图'}", text)
    return re.sub(r"(?<![A-Za-z0-9])D(\d{1,2})(?![0-9])", lambda m: _day_words(int(m[1])) if f"D{m[1]}" in _CAL else m[0], text)


def act_messages(state: dict, day: int, script: schemas.Script) -> list[dict]:
    items = [s for s in script.script if s.type == "message"]
    if not items:
        return []
    forbid = forbidden_tokens(state, day)

    def stub():
        return schemas.Messages(messages=[schemas.Msg(time=s.time, group=s.group, sender=s.sender,
                                                      text=f"（{s.intent}）") for s in items])

    p = prompt("P2", P0=p0(), today=today(state, day), personas=personas_for({s.sender for s in items}), recent=context(state, day),
               script=llm.dump([s.model_dump(exclude={"name", "attendees", "agenda", "key_points", "type"}) for s in items]))
    res = llm.json_call(f"P2 群消息 D{day}", p, schemas.Messages, stub)
    bad = [m for m in res.messages if any(tok in m.text for tok in forbid)
           or any(len(x) >= 4 and x in m.text for s in items for x in s.must_not_reveal if s.sender == m.sender)]
    if bad and not llm.offline():
        warn = "\n\n【注意】上一次生成的这些消息泄露了不该说的信息，必须改写，绝对不能出现：" + "、".join(forbid) + \
               "\n" + "\n".join(m.text for m in bad)
        res = llm.json_call(f"P2 群消息（重写）D{day}", p + warn, schemas.Messages, stub)
        res.messages = [m for m in res.messages if not any(tok in m.text for tok in forbid)]
    out = [dict(m.model_dump(), kind="msg", text=humanize(m.text)) for m in res.messages if m.sender != "系统"]
    if all(i.time < "17:25" for i in items):        # 上班时段：演员偶尔会自己加日报，去掉
        out = [m for m in out if m["time"] < "17:25" and not m["text"].lstrip().startswith("日报")]
    return fix_membership(out)


def act_meeting(state: dict, day: int, item: schemas.ScriptItem, host: str = "王丽") -> dict:
    names = set(item.attendees) - {"项目助理"}

    def stub():
        return schemas.Transcript(lines=[schemas.Line(speaker="王丽", text=f"（{item.name}：{'；'.join(item.key_points or item.agenda)}）"),
                                         schemas.Line(speaker="项目助理", text="[项目助理发言]")])

    length = "60–100" if item.name in ("彩排", "项目复盘会") else "40–80"
    forbid = forbidden_tokens(state, day)
    forbidden = "\n".join([f"- {x}" for x in forbid] + [
        "- 任何没有写在要点或事实里的新任务、新需求、需求变更、人员借调或请假、礼品采购、预算花费、媒体回复数量",
        "- 参会人以外的人发言"])
    p = prompt("P6", P0=p0(), today=today(state, day), name=item.name, time=item.time, attendees="、".join(item.attendees),
               agenda=llm.dump(item.agenda), key_points=llm.dump(item.key_points), personas=personas_for(names),
               recent=context(state, day, 15), length=length, host=host,
               facts=meeting_facts(state, day, item.attendees), forbidden=forbidden)
    res = llm.json_call(f"P6 会议 {item.name}", p, schemas.Transcript, stub)
    allowed = set(item.attendees) | {"项目助理"}
    res.lines = [l for l in res.lines if l.speaker in allowed and not any(tok in l.text for tok in forbid)]
    return {"kind": "meeting", "time": item.time, "group": item.group, "sender": "会议记录", "name": item.name,
            "lines": [dict(l.model_dump(), text=humanize(l.text)) for l in res.lines]}


# ------------------------------------------------------------------ 渲染给玩家看

def render(state: dict, day: int, phase: str, msgs: list[dict], extra: str = "") -> str:
    title = {"morning": "上午", "afternoon": "下午", "evening": "下班"}[phase]
    out = [f"# D{day} · {date_str(state, day)} · {title}\n"]
    for g in GROUPS:
        gm = sorted([m for m in msgs if m["group"] == g], key=lambda m: m["time"])
        if not gm:
            continue
        out.append(f"\n## 群：{g}\n")
        for m in gm:
            if m["kind"] == "meeting":
                out.append(f"\n**【{m['time']} {m['name']} · 文字记录】**\n")
                out += [f"> {l['speaker']}：{l['text']}" for l in m["lines"]]
                out.append("")
            else:
                out.append(f"[{m['time']}] **{m['sender']}**：{m['text']}")
    if extra:
        out.append("\n" + extra)
    return "\n".join(out) + "\n"


def save_phase(state: dict, day: int, phase: str, msgs: list[dict], extra: str = "") -> str:
    d = out_dir(day)
    (d / f"{phase}.json").write_text(llm.dump(msgs), encoding="utf-8")
    md = render(state, day, phase, msgs, extra)
    (d / f"{phase}.md").write_text(md, encoding="utf-8")
    return md


# ------------------------------------------------------------------ 给玩家的复盘

def improvement_name(state: dict, iid: str) -> str:
    return texts.improvement_names().get(iid) or state["improvements"].get(iid, {}).get("name", "")


ADJ_WORDS = {"reschedule": "改期", "extend_due": "延后截止", "cancel": "取消", "reassign": "换人",
             "scope_cut": "缩减范围", "start_early": "不等前置先开工"}


def recap(state: dict, day: int, ev: schemas.Evaluation, notes: list[str], overtime: list | None = None,
          label: str = "下午") -> str:
    """每半天结束时告诉玩家：导演记下了哪些动作、带来了什么变化。只说结果，不说判定标准和事件编号。"""
    def names(ids: list[str]) -> str:
        return "、".join(f"{t}「{tasks_name(state, t)}」" for t in ids)

    iv, out = ev.interventions, []
    if iv.chased_tasks:
        out.append(f"· 追问：{names(iv.chased_tasks)}")
    if iv.unmasked_tasks:
        out.append(f"· 说出了真实情况：{names(iv.unmasked_tasks)}")
    if iv.forced_tasks:
        out.append(f"· 当天优先做：{names(iv.forced_tasks)}")
    applied = {n.split(" ", 2)[2] for n in notes if n.startswith("调整 ")}
    for a in iv.adjustments:
        if a.task in applied:
            more = f" → D{a.new_day}" if a.new_day else f" → {a.new_owner}" if a.new_owner else ""
            out.append(f"· 生效的调整：{ADJ_WORDS.get(a.action, a.action)} {names([a.task])}{more}")
    for n in notes:
        if n.startswith("改进 "):
            iid = n.split()[1]
            out.append(f"· 改进上线：{iid} {improvement_name(state, iid)}")
    for who, tid in overtime or []:
        out.append(f"· {NAMES.get(who, who)} 被追问后当晚加班 1 小时赶 {names([tid])}")
    k = sum(bool(re.match(r"[ER]\d+ K\d", n)) for n in notes)
    if k:
        out.append(f"· 对正在发生的风险，记下 {k} 个有效应对")
    for t in ev.trust_changes:
        if t.delta:
            why = re.split(r"[；。]", t.reason)[0]
            out.append(f"· {NAMES.get(t.who, t.who)} 对你的信任{'上升' if t.delta > 0 else '下降'}："
                       + (why[:70] + "…" if len(why) > 70 else why))
    if ev.notes_for_player:
        out.append(f"· 旁白：{ev.notes_for_player}")
    body = "\n".join(out) or "· 导演没有记下会影响进度或关系的动作。"
    text = f"📋 导演复盘（D{day} {label}）\n{body}"
    (out_dir(day) / f"recap-{'noon' if label == '上午' else 'evening'}.txt").write_text(text, encoding="utf-8")
    return text


# ------------------------------------------------------------------ 上班

def start_day(state: dict) -> str:
    if state["phase"] == "day":
        nxt = "uv run sim noon" if state.get("half") == "am" else "uv run sim end"
        raise SystemExit(f"D{state['sim_day']} 还没收工。先写动作日志，再运行：{nxt}")
    day = state["sim_day"] + 1
    if day > 15:
        raise SystemExit("模拟已经结束。运行 uv run sim report 生成结局报告。")
    state.update({"sim_day": day, "phase": "day", "half": "am", "clock": "09:00", "committed": {}})
    started = engine.trigger_story_events(state, day)
    drawn = engine.draw_random(state, day, len(started))
    md, info = run_half(state, day, "morning")
    state["log"].append({"day": day, "phase": "start", "started": started, "random": drawn})
    (director_dir() / f"D{day}-morning.json").write_text(llm.dump(dict(info, started=started, random=drawn)), encoding="utf-8")
    save(state)
    snapshot(state, f"D{day}-morning")
    return md


def noon_day(state: dict) -> str:
    if state["phase"] != "day" or state.get("half") != "am":
        raise SystemExit("现在不是上午。上午：uv run sim start；下班：uv run sim end")
    day = state["sim_day"]
    ev = evaluate(state, day, "noon")
    notes = apply_eval(state, day, ev)
    state.setdefault("noon_eval", {})[str(day)] = ev.model_dump()
    rc = recap(state, day, ev, notes, label="上午")
    state["half"] = "pm"
    state["clock"] = max(state.get("clock", NOON), NOON)
    md, info = run_half(state, day, "afternoon")
    (director_dir() / f"D{day}-noon.json").write_text(llm.dump(dict(info, evaluation=ev.model_dump(), applied=notes)),
                                                      encoding="utf-8")
    save(state)
    snapshot(state, f"D{day}-noon")
    return md + "\n\n" + rc + "\n"


def run_half(state: dict, day: int, phase: str) -> tuple[str, dict]:
    """上午 / 下午：在副本上演习今天剩下的工作，把这个时段会发生的事实交给导演写剧本，再让演员说出来。"""
    lo, hi = ("09:00", NOON) if phase == "morning" else (NOON, "17:25")
    sim = copy.deepcopy(state)
    engine.resolve_due_events(sim, day)
    chased = set(state["chased"].get(str(day), []))
    plan = engine.plan_day(sim, day, chased)
    # 上午已经在群里说出去的完成要兑现；这个时段新增的完成也算"说好了"
    keep = dict(state.get("committed", {}))
    keep.update({tid: t for tid, t in plan["committed"].items() if lo <= t < hi and tid not in keep})
    state["committed"] = keep
    sim["committed"] = keep
    dry = engine.compute_day(copy.deepcopy(sim), day, chased, False)

    tm = engine.tasks_by_id(state)
    facts = [f"{t} {fact_done(state, tid)}" for tid, t in sorted(keep.items(), key=lambda x: x[1]) if lo <= t < hi]
    if phase == "afternoon":                  # 审批、返工、中午的发布都归下午
        facts += [fact_approval(state, a) for a in dry["approvals"]]
        facts += [f"陈悦做的「{tasks_name(state, t)}」理解错了需求，需要返工（她自己发现或被王丽指出）" for t in dry["rework"]]
    for p in dry["published"]:
        when = p.get("time") or tm[p["item"] + "-文"]["publish_time"]
        if lo <= when < hi:
            facts.append(fact_publish(p))

    meetings = [m for m in engine.meetings_today(day) if lo <= m["time"] < hi]
    script = write_script(state, day, phase, facts, plan["alloc"], meetings)
    script.script = [i for i in script.script if i.type == "meeting" or lo <= i.time < hi]
    script.script = align_meetings(script.script, meetings)
    msgs = act_messages(state, day, script)
    for item in script.script:
        if item.type == "meeting":
            msgs.append(act_meeting(state, day, item))
    script.private_initiatives = [i for i in script.private_initiatives if lo <= (norm_clock(i.time) or "99") < hi]
    privates = private_initiatives(state, day, script)
    (out_dir(day) / f"{phase}-private.json").write_text(llm.dump(privates), encoding="utf-8")   # 飞书模式按时间私聊发出
    md = save_phase(state, day, phase, msgs, render_private(privates))
    return md, {"script": script.model_dump(), "facts": facts, "plan": plan}


def tasks_name(state: dict, tid: str) -> str:
    return engine.tasks_by_id(state).get(tid, {}).get("name", "")


def fact_done(state: dict, tid: str) -> str:
    t = engine.tasks_by_id(state)[tid]
    who = "、".join(NAMES.get(o, o) for o in t["owners"])
    return f"{who} 交付了 {tid[:3] if t['project'] == 'B' else tid}「{t['name']}」" + ("，提交给王丽审" if t.get("approver") else "")


def fact_approval(state: dict, a: dict) -> str:
    t = engine.tasks_by_id(state)[a["task"]]
    verdict = "通过了" if a["result"] == "审批通过" else "提了修改意见，要返工"
    return f"王丽看了「{t['name']}」，{verdict}"


def fact_publish(p: dict) -> str:
    if p["result"] == "未发出":
        return f"「{p['title']}」到点没发出来（原定今天发）"
    return f"{p.get('time', '')} 「{p['title']}」发布了（{p['result']}）"


def align_meetings(items: list, meetings: list[dict]) -> list:
    """只保留固定流程里的会议；名字、时间、参会人以日程为准。导演漏写的补上。"""
    msgs = [i for i in items if i.type != "meeting"]
    mtgs = [i for i in items if i.type == "meeting"]
    out = []
    for m in meetings:
        cand = next((i for i in mtgs if i.time == m["time"] or m["name"] in i.name or i.name in m["name"]), None)
        item = cand or schemas.ScriptItem(time=m["time"], group=m["group"], sender="王丽", type="meeting",
                                          agenda=["过一下各项目进展和本周重点"])
        item.name, item.time, item.group = m["name"], m["time"], m["group"]
        item.attendees = [NAMES[a] for a in m["attendees"]]
        out.append(item)
        if cand:
            mtgs.remove(cand)
    return sorted(msgs + out, key=lambda i: i.time)


GROUP_MEMBERS = {
    "品牌项目组": {"王丽", "张伟", "李想", "陈悦", "黄建国"},
    "小暖 S2 发布会筹备": {"王丽", "张伟", "李想", "陈悦", "周涛", "孙磊"},
}


def fix_membership(msgs: list[dict]) -> list[dict]:
    """不是群成员的人不能在群里说话：能挪到另一个群就挪，否则丢掉。"""
    out = []
    for m in msgs:
        if m["sender"] in GROUP_MEMBERS[m["group"]]:
            out.append(m)
        elif m["sender"] in GROUP_MEMBERS["小暖 S2 发布会筹备"]:
            out.append(dict(m, group="小暖 S2 发布会筹备"))
    return out


def meeting_facts(state: dict, day: int, attendees: list[str]) -> str:
    keys = [KEY_BY_NAME[a] for a in attendees if a in KEY_BY_NAME]
    lines = [f"产品信息：{public_product(state, day)}", "各人手上的任务（汇报口径 = 这个人在会上会怎么说；真实进度只有本人心里清楚）："]
    for t in state["tasks"]:
        if not t.get("exists", True) or t["start_day"] > day + 3 or "all" in t["owners"]:
            continue
        if t["status"] in engine.DONE and (t.get("completed_day") or 0) < day - 1:
            continue
        if not set(t["owners"]) & set(keys):
            continue
        lines.append(f"- {'、'.join(NAMES.get(o, o) for o in t['owners'])}：{t['id'][:3] if t['project'] == 'B' else t['id']}「{t['name']}」"
                     f" 状态 {t['status']}，汇报口径 {engine.reported_progress(state, t, day)}，真实 {engine.true_progress(t)}%，截止 {due_words(t['due_day'])}")
    inv = engine.invites(state)
    lines.append(f"邀约确认（真实数字，张伟只有被具体追问才说）：媒体 {inv['media_confirmed']}/20，经销商 {inv['dealer_confirmed']}/40")
    lines.append("本周内容排期：" + "；".join(f"D{t['publish_day']} {t['platform']}「{t['name'].replace('（文案）', '')}」"
                                         for t in state["tasks"] if t["id"].endswith("-文") and 0 <= t["publish_day"] - day <= 4))
    lines.append("今天日程：" + "；".join(engine.fixed_schedule(state, day)))
    lines.append(KEY_DATES)
    return "\n".join(lines)


def private_initiatives(state: dict, day: int, script: schemas.Script) -> list[dict]:
    from .chat import npc_opening   # 避免循环引用
    out = []
    for ini in script.private_initiatives:
        key = KEY_BY_NAME.get(ini.sender)
        if not key or key == "player":
            continue
        text = npc_opening(state, day, key, ini.intent, ini.time)
        out.append({"time": ini.time, "sender": ini.sender, "text": text, "intent": ini.intent})
    return out


def render_private(privates: list[dict]) -> str:
    if not privates:
        return ""
    lines = ["## 📩 私聊（有人主动找你）\n"]
    for p in privates:
        lines.append(f"[{p['time']}] **{p['sender']}**（私聊）：{p['text']}")
    lines.append("\n> 想回复：`uv run sim chat 名字`")
    return "\n".join(lines)


# ------------------------------------------------------------------ 收工

def read_actions(day: int) -> str:
    f = config.ACTIONS_DIR / f"D{day}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def table_view(state: dict, limit: int = 45) -> str:
    """项目助理的任务表（飞书多维表格的最近一次快照）。只有在群里发过表格链接之后才对大家可见。"""
    f = config.STATE_DIR / "bitable-latest.json"
    if not state.get("table_shared") or not f.exists():
        return ""
    rows = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for r in list(rows.values())[:limit]:
        fd = r["fields"]
        bits = [fd.get("状态", "") or "（空）", fd.get("截止日期", ""), fd.get("负责人", ""), (fd.get("备注", "") or "")[:40]]
        out.append(f"- {r['name']}｜" + "｜".join(b for b in bits if b))
    return ("【项目助理的任务表（D{} 在群里公告过，大家都能打开看；这是项目助理记录的，不一定和真实情况一致）】\n"
            .format(state["table_shared"]) + "\n".join(out))


def player_actions(state: dict, day: int, phase: str) -> str:
    past = f"前几天（导演纪要，含私聊里的约定）：\n{backstage_so_far(state, day)}\n\n"
    tv = table_view(state)
    if tv:
        past += tv + "\n（王丽和同事会看这张表：表上写错、没更新、和实际对不上时，相关的人可能会在群里或私聊里提出来。）\n\n"
    if phase == "morning":
        return past + "今天：刚开始，还没有"
    log = read_actions(day).strip()
    return past + f"今天的动作日志：\n{log or '（没写）'}\n\n今天的私聊：\n{read_chats(day)}\n\n今天在群里的发言：\n{player_posts(state, day)}"


def read_chats(day: int) -> str:
    parts = []
    for f in sorted(config.CHATS_DIR.glob(f"D{day}-*.md")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(parts) or "（无）"


def eval_scope(state: dict, day: int, when: str) -> str:
    if when == "noon":
        return ("现在是中午 12:00 的中途结算。只评估 12:00 之前发生的动作（动作日志里时间早于 12:00 的条目、12:00 之前的私聊）；"
                "日志里没写时间的条目按上午算。weekly_report、zhangwei_prefill 留到下班再判（这次输出 false）。")
    prior = state.get("noon_eval", {}).get(str(day))
    if not prior:
        return "评估玩家今天全天的动作。"
    return ("中午已经结算过上午的动作，结果如下（已经生效）。这次只输出新增的内容：12:00 之后的动作，"
            "或者上午确实做了、但中午漏判且有原文依据的。已经输出过的关键动作、信任值变化、调整、紧急审批不要重复。\n"
            + llm.dump(prior))


def evaluate(state: dict, day: int, when: str = "end") -> schemas.Evaluation:
    act = engine.active_events(state, day)
    ev_txt = []
    for item in act:
        ev, rec = item["ev"], item["rec"]
        ev_txt.append({"id": ev.id, "name": ev.name, "stage": rec["stage"], "burst": f"D{rec['burst']} {ev.burst_time}",
                       "truth": ev.truth, "keys": ev.keys, "already_done": rec["done_k"]})
    pending = [f"{t['id']} {t['name']}（送审 D{t['submitted_day']}）" for t in state["tasks"] if t["status"] == "待审核"]
    imps = {k: v for k, v in state["improvements"].items() if v["active"]}
    flog = config.FEISHU_LOG_DIR / f"D{day}.jsonl"
    p = prompt("P5", day=f"D{day}", date=date_str(state, day), weekday=weekday(day), active_events=llm.dump(ev_txt),
               scope=eval_scope(state, day, when), history=backstage_so_far(state, day),
               tasks=state_summary(state, day), pending="；".join(pending) or "无",
               actions_log=read_actions(day) or "（玩家没有写动作日志）", chat_logs=read_chats(day),
               feishu_log=flog.read_text(encoding="utf-8") if flog.exists() else "（无）",
               improvements=llm.dump(imps) if imps else "无", improvement_rules=texts.improvement_rules(),
               trust_rules=texts.trust_rules())
    return llm.json_call(f"P5 评估 D{day} {when}", p, schemas.Evaluation, lambda: offline_eval(state, day),
                         model=config.MODEL_DIRECTOR, effort="high")


def offline_eval(state: dict, day: int) -> schemas.Evaluation:
    """离线模式：从动作日志里找 '#K E08 K1' 这样的标记（只用于测试引擎）。"""
    txt = read_actions(day)
    evs: dict[str, list] = {}
    for eid, k, t in re.findall(r"#K (\w+) (K\d)(?: (\d\d:\d\d))?", txt):
        evs.setdefault(eid, []).append(schemas.KeyDone(k=k, time=t or "10:00", evidence="offline"))
    imps = [schemas.Activated(id=i, evidence="offline") for i in re.findall(r"#I (I\d+)", txt)]
    imps += [schemas.Activated(id="X1", name=n.strip(), evidence="offline") for n in re.findall(r"#X (.+)", txt)]
    inter = schemas.Interventions(
        chased_tasks=re.findall(r"#chase (\S+)", txt),
        urgent_tasks=re.findall(r"#urgent (\S+)", txt), summary_tasks=re.findall(r"#summary (\S+)", txt),
        unmasked_tasks=re.findall(r"#unmask (\S+)", txt), weekly_report="#weekly" in txt,
        weekly_report_text="（离线测试周报）" if "#weekly" in txt else "", c_mandated="#c_mandated" in txt,
        adjustments=[schemas.Adjustment(action=a, task=t, new_day=int(d) if d.isdigit() and a != "scope_cut" else None,
                                        hours=float(d) if a == "scope_cut" else None,
                                        new_owner=None if d.isdigit() else d, evidence="offline")
                     for a, t, d in re.findall(r"#adj (\w+) (\S+) (\S+)", txt)])
    return schemas.Evaluation(events=[schemas.EventEval(id=e, new_actions=v) for e, v in evs.items()],
                              improvements_activated=imps, interventions=inter)


def dedupe_eval(ev: schemas.Evaluation, prior: dict | None) -> None:
    """下班评估可能把中午已经结算过的东西再报一遍：去掉重复，免得信任值、紧急审批、调整被算两次。"""
    if not prior:
        return
    piv = prior["interventions"]
    seen_trust = {(t["who"], t["reason"]) for t in prior["trust_changes"]}
    ev.trust_changes = [t for t in ev.trust_changes if (t.who, t.reason) not in seen_trust]
    ev.interventions.urgent_tasks = [t for t in ev.interventions.urgent_tasks if t not in piv["urgent_tasks"]]
    seen_adj = [{k: a[k] for k in ("action", "task", "new_day", "new_owner", "hours")} for a in piv["adjustments"]]
    ev.interventions.adjustments = [a for a in ev.interventions.adjustments
                                    if a.model_dump(include={"action", "task", "new_day", "new_owner", "hours"}) not in seen_adj]


def task_ids(tm: dict, ids: list[str]) -> list[str]:
    """导演常把内容写成 "B02"，引擎里是 "B02-文" / "B02-图"：展开；不认识的 ID 丢掉。"""
    out = []
    for i in ids:
        i = i.strip().upper().replace("－", "-")
        if i.endswith(("-文", "-图")) or i in tm:
            out += [i] if i in tm else []
        else:
            out += [x for x in (i + "-文", i + "-图") if x in tm]
    return list(dict.fromkeys(out))


def apply_eval(state: dict, day: int, ev: schemas.Evaluation) -> list[str]:
    dedupe_eval(ev, state.get("noon_eval", {}).get(str(day)))
    notes = []
    tm = engine.tasks_by_id(state)
    iv = ev.interventions
    for f in ("chased_tasks", "forced_tasks", "unmasked_tasks", "summary_tasks", "urgent_tasks"):
        setattr(iv, f, task_ids(tm, getattr(iv, f)))
    recs = dict(state["events"])
    recs.update({r["id"]: r for r in state["random_active"]})
    cards = {e.id: e for e in story_events(state["randomized"])}
    for e in ev.events:
        rec = recs.get(e.id)
        if not rec or rec.get("result"):
            continue
        card = cards.get(e.id) or engine.event_obj(state, e.id)
        for a in e.new_actions:
            if a.k not in card.keys or a.k in rec["done_k"]:
                continue
            late = day == rec["burst"] and a.time > card.burst_time
            rec["done_k"][a.k] = day + (0.5 if late else 0)
            notes.append(f"{e.id} {a.k}")
            if e.id == "E03" and a.k == "K1":
                tm["A13"]["exists"] = True
    for a in ev.improvements_activated:
        imp = state["improvements"].get(a.id)
        if imp is None and re.fullmatch(r"X\d+", a.id) and a.name \
                and a.name not in {v.get("name") for v in state["improvements"].values()}:
            a.id = f"X{sum(k.startswith('X') for k in state['improvements']) + 1}"   # 清单外的改进：记下来，没有引擎效果
            imp = state["improvements"][a.id] = {"active": False, "day": None, "name": a.name}
        if imp and not imp["active"]:
            imp.update({"active": True, "day": day, "evidence": a.evidence})
            notes.append(f"改进 {a.id} 上线")
    # 改进的自动效果（第 7 章）
    imp = state["improvements"]
    auto = [("I4", "E07", "K1"), ("I5", "E08", "K1"), ("I10", "E15", "K2")]
    for iid, eid, k in auto:
        rec = state["events"][eid]
        if imp[iid]["active"] and rec["start"] <= day and rec["result"] is None and k not in rec["done_k"]:
            if iid != "I5" or imp[iid]["day"] < rec["start"]:
                rec["done_k"][k] = day
    for t in ev.trust_changes:
        engine.change_trust(state, t.who, t.delta, t.reason)

    iv = ev.interventions
    state["chased"][str(day)] = sorted(set(state["chased"].get(str(day), [])) | set(iv.chased_tasks))
    for tid in iv.forced_tasks:
        if tid in tm:
            state["forced"][tid] = max(state["forced"].get(tid, 0), day)
    for tid in iv.unmasked_tasks:
        if tid in tm:
            tm[tid]["unmasked"] = True
            tm[tid]["stale"] = False
    week = str((day - 1) // 5)
    for tid in iv.urgent_tasks:
        t = tm.get(tid)
        used = state["urgent_used"].get(week, 0)
        if t and t["status"] == "待审核" and (used < 2 or 11 <= day <= 13):
            t["approve_day"] = min(t["approve_day"], day)
            t["approve_time"] = "16:00"
            state["urgent_used"][week] = used + 1
    for tid in iv.summary_tasks:
        t = tm.get(tid)
        if t and t["status"] == "待审核":
            t["approve_day"] = min(t["approve_day"], day + 1)
    for adj in iv.adjustments:
        apply_adjustment(state, day, adj)
        notes.append(f"调整 {adj.action} {adj.task}")
    for pt in iv.player_tasks:
        t = tm.get(pt.task)
        if t and "player" in t["owners"] and t["status"] not in engine.DONE + ("待审核",):
            t["done_h"] = round(t["est_h"] * min(100, pt.progress) / 100, 2)
            if pt.progress >= 100:
                engine.submit(state, t, day, 17.0)
    if iv.c_mandated:
        state["flags"]["c_mandated"] = True
    for eid in iv.risk_logged:
        state["risk_logged"].setdefault(eid, day)
    state.setdefault("prefill", {})[str(day)] = state.get("prefill", {}).get(str(day), False) or iv.zhangwei_prefill
    if iv.weekly_report:
        state.setdefault("weekly_reports", {})[str(day)] = iv.weekly_report_text
    return notes


def apply_adjustment(state: dict, day: int, adj: schemas.Adjustment) -> None:
    tm = engine.tasks_by_id(state)
    item = adj.task[:3]
    t = tm.get(adj.task) or tm.get(item + "-文")
    if not t:
        return
    related = [x for x in (tm.get(item + "-文"), tm.get(item + "-图")) if x] if t["project"] == "B" else [t]
    if adj.action == "cancel":
        if t["project"] == "B":
            engine.set_content(state, item, "取消")
        for x in related:
            if x["status"] not in engine.DONE:
                x["status"] = "已取消"
    elif adj.action in ("reschedule", "extend_due") and adj.new_day:
        for x in related:
            x["due_day"] = adj.new_day
            x["planned_change"] = True
            if x.get("publish_day"):
                x["publish_day"] = adj.new_day
        if t["project"] == "B":
            c = state["content"].setdefault(item, {"result": None, "day": None, "time": None})
            c["planned_day"] = adj.new_day
    elif adj.action == "reassign" and adj.new_owner:
        owner = KEY_BY_NAME.get(adj.new_owner, adj.new_owner)
        t["owners"] = [owner]
    elif adj.action == "start_early":
        # 不等前置先开工（标 ! 的硬性审批依赖除外）：前置定稿后要改，工时 +25%
        x = tm.get(item + "-文") if t["project"] == "B" else t
        if x and not x.get("deps_waived") and x["status"] not in engine.DONE:
            x["deps_waived"] = True
            x["est_h"] = round(x["est_h"] * 1.25, 2)
    elif adj.action == "scope_cut":
        hours = adj.hours if adj.hours is not None else round(t["est_h"] * 0.6, 2)   # 导演没给新工时：默认砍到 60%
        t["est_h"] = max(t["done_h"], hours)
        t["planned_change"] = True
    state["wangli_decisions"].append(dict(adj.model_dump(), day=day))


def write_reports(state: dict, day: int, reports: list[dict]) -> list[dict]:
    subs = [r for r in reports if r["submitted"]]
    if not subs:
        return []
    prefill = state.get("prefill", {}).get(str(day), False)
    imp = state["improvements"]
    fmt = "飞书多维表格表单字段：今日完成 / 关联任务 + 进度 / 明日计划 / 卡点" if imp["I2"]["active"] else "在群里自由发一段话（字段可以留空）"
    if imp["I3"]["active"]:
        fmt += "；交付物链接必填"
    data = [{"人": r["name"], "今天做的任务": r["items"], "项目助理帮他预填": prefill and r["person"] == "zhangwei"} for r in subs]

    def stub():
        return schemas.Reports(reports=[schemas.Report(sender=r["name"], fields=schemas.ReportFields(
            今日完成="、".join(i["name"] for i in r["items"]) or "日常工作",
            进度="；".join(f"{i['task']} {i['reported']}" for i in r["items"]), 明日计划="继续", 卡点="无")) for r in subs])

    p = prompt("P4", P0=p0(), day=f"D{day}", date=date_str(state, day), weekday=weekday(day),
               personas=personas_for({r["name"] for r in subs}), reports=llm.dump(data), format=fmt)
    res = llm.json_call(f"P4 日报 D{day}", p, schemas.Reports, stub)
    msgs = []
    for i, r in enumerate(res.reports):
        f = r.fields
        head = "📋 日报（表单提交）" if imp["I2"]["active"] else "日报"
        body = f"{head}\n今日完成：{f.今日完成}\n进度：{f.进度}\n明日计划：{f.明日计划}\n卡点：{f.卡点}"
        if f.交付物链接:
            body += f"\n交付物链接：{f.交付物链接}"
        msgs.append({"kind": "msg", "time": f"17:{32 + i * 7:02d}", "group": "品牌项目组", "sender": r.sender,
                     "text": humanize(body), "report": True, "link_note": f.link_note,
                     "fields": f.model_dump(exclude={"link_note"})})
    return msgs


def end_day(state: dict) -> str:
    if state["phase"] != "day":
        raise SystemExit("今天还没开始。运行：uv run sim start")
    day = state["sim_day"]
    ev = evaluate(state, day, "end")
    notes = apply_eval(state, day, ev)
    resolved = engine.resolve_due_events(state, day)
    chased = set(state["chased"].get(str(day), []))
    facts = engine.compute_day(state, day, chased, state.get("prefill", {}).get(str(day), False))
    report_msgs = write_reports(state, day, facts["reports"])

    tm = engine.tasks_by_id(state)
    flist = [f"{c['time']} {fact_done(state, c['task'])}" for c in facts["completed"]]
    flist += [fact_approval(state, a) for a in facts["approvals"]]
    flist += [fact_publish(p) for p in facts["published"]]
    flist += [f"陈悦做的「{tm[t]['name']}」理解错了需求，需要返工" for t in facts["rework"]]
    flist += [f"{NAMES[p]}被追问后，当晚加班 1 小时赶「{tm[t]['name']}」" for p, t in facts["overtime"]]
    flist += ["日报：" + "；".join(f"{r['name']}{'交了' if r['submitted'] else '没交'}" for r in facts["reports"])]
    script = write_script(state, day, "evening", flist, facts["alloc"], [])
    msgs = act_messages(state, day, script) + report_msgs

    extra = []
    weekly = state.get("weekly_reports", {}).get(str(day))
    weekly_reply = wangli_weekly_reply(state, day, weekly) if weekly and day in (5, 10) else ""
    if weekly_reply:
        extra.append(f"## 📩 王丽（周末回复你的周报）\n\n{weekly_reply}")
    (out_dir(day) / "evening-extra.json").write_text(llm.dump({"weekly_reply": weekly_reply}), encoding="utf-8")
    extra.append("> " + recap(state, day, ev, notes, facts["overtime"]).replace("\n", "\n> "))
    engine.record_metrics(state, day, facts)
    state["phase"], state["half"] = "night", None
    (director_dir() / f"D{day}-evening.json").write_text(llm.dump({
        "evaluation": ev.model_dump(), "applied": notes, "resolved": resolved, "facts": {k: v for k, v in facts.items()},
        "script": script.model_dump()}), encoding="utf-8")
    md = save_phase(state, day, "evening", msgs, "\n\n".join(extra))
    write_daily_summary(state, day)        # 要在晚间消息保存之后写，纪要才包含晚上的事
    write_backstage(state, day)
    save(state)
    snapshot(state, f"D{day}")
    return md


def wangli_weekly_reply(state: dict, day: int, report: str) -> str:
    adopt = 0.9 if state["improvements"]["I11"]["active"] else 0.8
    r = random.Random(f"{state['randomized']['seed']}-weekly-{day}").random()
    rule = f"随机数 {r:.2f}，{'采纳项目助理的建议' if r < adopt else '选另一个合理选项并说明原因'}"
    from .chat import knowledge, secrets   # 王丽只知道汇报上来的情况，不知道真实进度
    facts = knowledge(state, day, "wangli") + "\n" + secrets(state, day, "wangli")
    p = prompt("P7", P0=p0(), weekly_report=report, facts=facts, trust=str(state["people"]["wangli"]["trust"]), adopt_rule=rule)
    return llm.text_call("P7 周报回复", p, lambda: "收到 按这个推", model=config.MODEL_ACTOR)
