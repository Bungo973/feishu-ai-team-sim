"""在终端里和某个角色私聊（P3）。记录写进 logs/chats/D{n}-{名字}.md，导演收工时会读。"""

import json
import random
from datetime import datetime

try:
    import readline  # noqa: F401  有了它，input() 才能正确删除中文、用方向键移动光标
except ImportError:
    pass

from . import config, engine, llm, texts
from .director import (KEY_DATES, PHASES, clock_window, due_words, fmt_msgs, humanize, load_msgs, p0, prompt,
                       public_product, set_clock, story_so_far)
from .state import KEY_BY_NAME, NAMES, date_str, save, weekday


def delivered_today(state: dict) -> dict:
    """今天白天群里已经"说出去"的交付（引擎收工时才结算，白天先按这个算）。"""
    clock = state.get("clock", "09:00")
    return {tid: t for tid, t in state.get("committed", {}).items() if t <= clock}


def chat_context(state: dict, day: int) -> str:
    """前情提要 + 昨天最后几条 + 今天到现在为止两个群里的消息（看不到"未来"的消息）。"""
    clock = state.get("clock", "09:00")
    today = []
    for ph in PHASES:
        for m in load_msgs(day, ph):
            if m["time"] > clock:
                continue
            if m["kind"] == "meeting":
                today.append({"time": m["time"], "group": m["group"], "sender": f"【{m['name']}】",
                              "text": " / ".join(f"{l['speaker']}：{l['text']}" for l in m["lines"])[:1500]})
            else:
                today.append(m)
    today.sort(key=lambda m: m["time"])
    yday = [m for ph in PHASES for m in load_msgs(day - 1, ph) if m.get("kind") == "msg"][-8:] if day > 1 else []
    return (f"【前情提要（之前每天的公开纪要）】\n{story_so_far(state, day)}\n\n{KEY_DATES}\n\n"
            f"【昨天群里最后几条】\n{fmt_msgs(yday)}\n\n【今天到现在（{clock}）两个群里的消息】\n{fmt_msgs(today[-60:])}")


def workload(state: dict, day: int, key: str) -> str:
    """接下来 5 个工作日：手上的活还要多少小时 vs 自己有多少小时。被问到排期、工作量时照这个说实话。"""
    last = min(15, day + 4)
    need = sum((t["est_h"] - t["done_h"]) / engine.eff(state, key) for t in state["tasks"]
               if key in t["owners"] and t.get("exists", True) and t["status"] not in engine.DONE + ("待审核",)
               and t["due_day"] <= last)
    have = sum(engine.available_hours(state, key, d) for d in range(day, last + 1))
    verdict = "排得过来" if need <= have else f"排不过来，差约 {need - have:.0f} 小时"
    return (f"你的真实工作量：{due_words(last)}前截止的活还要约 {need:.0f} 小时，你这几天一共只有约 {have:.0f} 小时（已经扣掉会议和日常事务），{verdict}。"
            "（被问到排期、工作量、还有多少时间时，按这个说实话）")


def knowledge(state: dict, day: int, key: str) -> str:
    lines = []
    done = delivered_today(state)
    if key in engine.WORKERS:
        lines.append("你自己的任务（真实情况，你心里清楚；对外按人设的汇报规则说）：")
        for t in state["tasks"]:
            if key in t["owners"] and t.get("exists", True) and t["start_day"] <= day + 3 and t["status"] != "已取消":
                if t["id"] in done:
                    lines.append(f"- {t['id']} {t['name']}：今天 {done[t['id']]} 已经做完交出去了（群里说过）"
                                 + ("，等王丽审" if t.get("approver") else "") + f"，截止 {due_words(t['due_day'])}")
                    continue
                lines.append(f"- {t['id']} {t['name']}：状态 {t['status']}，真实进度 {engine.true_progress(t)}%，"
                             f"你对外汇报的是 {engine.reported_progress(state, t, day)}，截止 {due_words(t['due_day'])}")
        lines.append(f"你今天可用的工时大约 {engine.available_hours(state, key, day)} 小时。")
        lines.append(workload(state, day, key))
        if key == "zhangwei":
            inv = engine.invites(state)
            lines.append(f"邀约确认的真实数字：媒体 {inv['media_confirmed']}/20，经销商 {inv['dealer_confirmed']}/40。")
    if key == "wangli":
        lines.append("你看到的项目情况（来自大家的汇报，不一定准）：")
        for t in state["tasks"]:
            if t.get("exists", True) and t["status"] not in engine.DONE and t["start_day"] <= day + 2 and "all" not in t["owners"]:
                lines.append(f"- {t['id']} {t['name']}（{'+'.join(NAMES.get(o, o) for o in t['owners'])}）："
                             f"{t['status']}，汇报 {engine.reported_progress(state, t, day)}，截止 {due_words(t['due_day'])}")
        pend = [t["id"] for t in state["tasks"] if t["status"] == "待审核"]
        tm = engine.tasks_by_id(state)
        pend += [f"{tid}（今天 {tm_} 刚交）" for tid, tm_ in done.items() if tid not in pend and tm[tid].get("approver")]
        lines.append(f"等你审批的：{'、'.join(pend) or '无'}")
        lines.append(f"预算总额 15 万（场地 3 万已签、会务 4 万、物料 2 万、餐饮 3 万、伴手礼及礼品 2 万、机动 1 万）。")
    if key == "zhoutao":
        lines.append(f"产品文档当前版本：{state['product']['doc_version']}；价格 {state['product']['price']}；卖点 {'、'.join(state['product']['claims'])}。")
    lines.append(f"群里大家知道的产品信息：{public_product(state, day)}")
    lines.append("\n" + chat_context(state, day))
    from .director import table_view
    tv = table_view(state, limit=40)
    if tv:
        lines.append("\n" + tv + "\n（你可以引用这张表上的内容；表上和你知道的不一致时，可以指出来。）")
    lines.append("\n" + past_chats(state, day, key))
    return "\n".join(lines)


def past_chats(state: dict, day: int, key: str, days: int = 3) -> str:
    """前几天你和项目助理的私聊：答应过的事要记得（"明天上午给你"指的是哪天，按日期换算）。"""
    name = NAMES[key]
    out = []
    for d in range(max(1, day - days), day):
        hist = load_history(d, name)
        if hist:
            out.append(f"{date_str(state, d)}（D{d}）：")
            out += [f"  [{h['clock']}] {'项目助理' if h['role'] == 'user' else name}：{h['text']}" for h in hist]
    if not out:
        return "【你和项目助理前几天的私聊】（无）"
    return ("【你和项目助理前几天的私聊】你在里面答应过的事、给过的日期，现在要记得并对得上"
            "（当时说的\"明天\"\"今晚\"按当时的日期换算成具体哪天）：\n" + "\n".join(out))


def secrets(state: dict, day: int, key: str) -> str:
    out = []
    for item in engine.active_events(state, day):
        s = item["ev"].secrets.get(key)
        if s:
            out.append(f"- {s}")
    t = state["people"][key].get("trust", 50)
    if t >= 70:
        out.append("- 你对项目助理很信任，愿意主动提到你看到的风险。")
    return "\n".join(out) or "（无）"


def system_prompt(state: dict, day: int, key: str, turn: int = 0) -> str:
    name = NAMES[key]
    wl = ""
    if key == "wangli":
        adopt = 0.9 if state["improvements"]["I11"]["active"] else 0.8
        r = random.Random(f"{state['randomized']['seed']}-{day}-wangli-{turn}").random()   # 重跑同一轮对话结果一致
        rule = "采纳项目助理的建议" if r < adopt else "选另一个合理选项并说明原因"
        wl = prompt("P3_王丽附加规则", rand=f"{r:.2f}", adopt_rule=rule)
    return prompt("P3_角色", P0=p0(), name=name, persona=texts.persona(name), day=f"D{day}", date=date_str(state, day),
                  weekday=weekday(day), clock=state.get("clock", "10:00"), knowledge=knowledge(state, day, key),
                  secrets=secrets(state, day, key), trust=str(state["people"][key].get("trust", 50)), wangli_rules=wl)


def paths(day: int, name: str):
    config.CHATS_DIR.mkdir(parents=True, exist_ok=True)
    return config.CHATS_DIR / f"D{day}-{name}.json", config.CHATS_DIR / f"D{day}-{name}.md"


def load_history(day: int, name: str) -> list[dict]:
    j, _ = paths(day, name)
    return json.loads(j.read_text(encoding="utf-8")) if j.exists() else []


def save_history(day: int, name: str, hist: list[dict]) -> None:
    j, md = paths(day, name)
    j.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# D{day} 私聊：项目助理 ↔ {name}\n"]
    for h in hist:
        who = "项目助理" if h["role"] == "user" else name
        lines.append(f"[{h['clock']}] {who}：{h['text']}")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def to_api(hist: list[dict]) -> list[dict]:
    msgs = []
    for h in hist:
        role = h["role"]
        text = f"[{h['clock']}] {h['text']}" if role == "user" else h["text"]
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n" + text
        else:
            msgs.append({"role": role, "content": text})
    if msgs and msgs[0]["role"] == "assistant":
        msgs.insert(0, {"role": "user", "content": "（项目助理打开了和你的私聊窗口）"})
    return msgs


def reply(state: dict, day: int, key: str, hist: list[dict]) -> str:
    return humanize(llm.text_call(f"P3 私聊 {NAMES[key]}", to_api(hist), lambda: "（离线模式：角色回复占位）",
                                  system=system_prompt(state, day, key, turn=len(hist))))


def npc_opening(state: dict, day: int, key: str, intent: str, clock: str) -> str:
    """NPC 主动私聊项目助理的第一句话（P1 的 private_initiatives）。只生成，不写进记录：到点"发出"时才写（deliver）。
    会带上今天到这个时刻为止你们的私聊，避免把已经说过、对方已经答复过的事再说一遍。"""
    name = NAMES[key]
    st = dict(state, clock=clock)
    sys_ = system_prompt(st, day, key)
    hist = [h for h in load_history(day, name) if h["clock"] <= clock]
    ask = (f"（现在 {clock}，你决定主动私聊项目助理——对方是项目助理本人，不是王丽或别的同事，称呼用'你'。"
           f"你想表达的意思：{intent}。如果上面今天已经聊过这件事、对方也答复过，就别重复，接着说新的或者干脆简短确认。"
           f"直接写你发的消息。）")
    msgs = to_api(hist)
    if msgs and msgs[-1]["role"] == "user":
        msgs[-1]["content"] += "\n" + ask
    else:
        msgs.append({"role": "user", "content": ask})
    return humanize(llm.text_call(f"P3 主动私聊 {name}", msgs, lambda: f"（{intent}）", system=sys_))


def group_line(state: dict, day: int, key: str, group: str, original: str, clock: str, since: str,
               must_not: list[str]) -> str:
    """剧本里写好的一句群消息，到点发出前按"现在"的情况重写台词（事实不变）。
    只在项目助理此后和这个人 / 在这个群谈过相关的事时调用。"""
    name = NAMES[key]
    st = dict(state, clock=clock)
    talks = [f"[{h['clock']}] {'项目助理' if h['role'] == 'user' else name}：{h['text']}"
             for h in load_history(day, name) if since <= h["clock"] <= clock]
    ask = (f"（现在 {clock}，你要在群「{group}」里发一句话。原本打算说的是：\n「{original}」\n\n"
           f"从 {since} 到现在，你和项目助理私聊过：\n" + ("\n".join(talks) or "（没有）") +
           "\n\n请按现在的情况重写这句群消息：\n"
           "1. 原话里的工作事实（谁交了什么、文件名、数字、时间、进度、遇到的问题）必须保留，不能删、不能改。\n"
           "2. 已经在私聊或群里说过、对方也回应过的话，不要再重复；可以改成简短确认、接上刚才的话，或者说新的进展。\n"
           "3. 项目助理说的话只是 TA 的说法，不一定是事实。和你自己知道的情况不一致时，按你知道的来：可以相信、可以质疑、可以按人设含糊过去。\n"
           "4. 不要编造原话和上面信息里没有的新工作内容。\n"
           + (f"5. 绝对不能出现：{'、'.join(must_not)}\n" if must_not else "") +
           "只输出这句群消息本身，口吻、长度和原话差不多。）")
    return humanize(llm.text_call(f"群消息到点重写 {name}", [{"role": "user", "content": ask}],
                                  lambda: original, system=system_prompt(st, day, key)))


def deliver(day: int, name: str, clock: str, text: str) -> None:
    """主动私聊到点发出：写进你们的私聊记录（按时间排好）。"""
    hist = load_history(day, name)
    if any(h["role"] == "assistant" and h["text"] == text for h in hist):
        return
    hist.append({"role": "assistant", "clock": clock, "text": text})
    hist.sort(key=lambda h: h["clock"])
    save_history(day, name, hist)


def deliver_due(state: dict, day: int, name: str) -> None:
    """终端玩法：打开私聊时，把已经到点的主动私聊补进记录。"""
    for ph in ("morning", "afternoon"):
        f = config.OUTPUT_DIR / f"D{day}" / f"{ph}-private.json"
        if f.exists():
            for p in json.loads(f.read_text(encoding="utf-8")):
                if p["sender"] == name and p["time"] <= state.get("clock", "09:00"):
                    deliver(day, name, p["time"], p["text"])


def resolve_name(s: str) -> str:
    key = KEY_BY_NAME.get(s) or (s if s in NAMES else None)
    if not key or key == "player":
        raise SystemExit(f"不认识「{s}」。可以私聊：{'、'.join(v for k, v in NAMES.items() if k != 'player')}")
    return key


def repl(state: dict, who: str) -> None:
    if state["phase"] != "day":
        raise SystemExit("现在是下班时间（或还没开始）。先运行 uv run sim start")
    day = state["sim_day"]
    key = resolve_name(who)
    name = NAMES[key]
    lo, hi = clock_window(state)
    deliver_due(state, day, name)
    hist = load_history(day, name)
    last = max((h["clock"] for h in hist if h["clock"] <= hi), default="")
    if last > state.get("clock", ""):        # 对方的消息比当前时钟晚（比如主动私聊），时钟跟上
        state["clock"] = last
        save(state)
    print(f"—— D{day} 私聊 {name} ——（模拟时间 {state['clock']}）")
    print(f"输入消息回车发送；/t 10:30 修改模拟时间（现在可用 {lo}–{hi}）；/q 退出\n")
    for h in hist:
        print(f"[{h['clock']}] {'你' if h['role'] == 'user' else name}：{h['text']}")
    while True:
        try:
            s = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not s:
            continue
        if s in ("/q", "/quit", "/exit"):
            break
        if s.startswith("/t"):
            err = set_clock(state, s[2:].strip())
            if err:
                print(f"（{err}）")
            else:
                save(state)
                print(f"（模拟时间改为 {state['clock']}）")
            continue
        hist.append({"role": "user", "clock": state["clock"], "text": s, "real_time": datetime.now().isoformat(timespec="seconds")})
        save_history(day, name, hist)
        r = reply(state, day, key, hist)
        hist.append({"role": "assistant", "clock": state["clock"], "text": r})
        save_history(day, name, hist)
        print(f"{name}：{r}\n")
    print(f"记录已保存：logs/chats/D{day}-{name}.md")
