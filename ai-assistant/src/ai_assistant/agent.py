"""对话式助手（agent）：你随便跟它聊，它自己决定查群聊、查表、跑核对还是改表。

它手上的工具都只碰飞书：读任务表、读日报表、读群消息、改任务表（可撤销）、跑一次 AI 进度核对。
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime

from lark_oapi.api.bitable.v1 import (AppTableRecord, BatchUpdateAppTableRecordRequest,
                                      BatchUpdateAppTableRecordRequestBody, ListAppTableFieldRequest)
from openai import OpenAI

from . import check, clock, config, feishu

EDITABLE = ["状态", "负责人", "审核人", "截止日期", "开始日期", "备注"]
HISTORY_FILE = config.DATA_FILE.parent / "对话.json"
EDIT_LOG = config.DATA_FILE.parent / "改表记录.jsonl"
MAX_ROUNDS = 10

SYSTEM = """你是「AI 进度助手」，项目助理（就是正在跟你聊天的人）自己搭的飞书机器人，帮他管市场部品牌项目组的项目进度。
说话简洁、像同事，用中文。现在是 {now}。

你能看到、能做的只有这些（都通过工具）：
- 飞书多维表格「任务进度」：每个任务一行（任务编号如 A4、B09），有状态、负责人、审核人、截止日期、开始日期、备注等。你可以改这几列：{editable}。
- 多维表格「日报」：同事每天交的日报。
- 你所在的两个群的聊天记录：「品牌项目组」「小暖 S2 发布会筹备」。"我"是项目助理。
- AI 进度核对：把群聊、日报、任务表放在一起，找要核实 / 要催 / 快到期的事。
你看不到任何人的私聊，也不知道同事的真实进度，只知道上面这些材料里写了什么。不知道就说不知道，不要编。

改表的规矩：
- 他明确让你改（例如"A4 标成已完成"），就直接改，改完告诉他改了什么（旧 → 新）。
- 是你自己推断出来的改动，先说清楚要改什么、为什么，等他同意再改。
- 改错了可以用 undo_last_edit 撤销。"""

TOOLS = [
    {"name": "get_tasks", "description": "读「任务进度」表。可以只看某几个任务，或者按关键词筛（任务名、负责人、状态、备注里包含）。",
     "parameters": {"type": "object", "properties": {
         "codes": {"type": "array", "items": {"type": "string"}, "description": "任务编号，例如 [\"A4\",\"B09\"]；不填就看全部"},
         "keyword": {"type": "string"}}}},
    {"name": "get_reports", "description": "读「日报」表。可以按日期（YYYY-MM-DD）和提交人筛。",
     "parameters": {"type": "object", "properties": {"date": {"type": "string"}, "who": {"type": "string"}}}},
    {"name": "get_messages", "description": "读群聊消息（时间已换算成模拟时间）。默认今天，可以选从昨天开始；可以按群、人、关键词筛。",
     "parameters": {"type": "object", "properties": {
         "since": {"type": "string", "enum": ["today", "yesterday"]},
         "group": {"type": "string"}, "who": {"type": "string"}, "keyword": {"type": "string"},
         "limit": {"type": "integer", "description": "最多返回几条（最新的），默认 80"}}}},
    {"name": "update_task", "description": f"改「任务进度」表里的一个任务。只能改：{'、'.join(EDITABLE)}。日期写 YYYY-MM-DD；单选列只能填已有选项。备注会整格替换，要追加就把原备注带上。",
     "parameters": {"type": "object", "required": ["code", "changes"], "properties": {
         "code": {"type": "string", "description": "任务编号，例如 A4"},
         "changes": {"type": "object", "description": "{列名: 新值}，例如 {\"状态\": \"已完成\"}", "additionalProperties": {"type": "string"}}}}},
    {"name": "undo_last_edit", "description": "撤销你上一次 update_task 的改动（恢复成改之前的值）。",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "run_check", "description": "跑一次完整的 AI 进度核对（约半分钟），返回核对清单。",
     "parameters": {"type": "object", "properties": {}}},
]


# ------------------------------------------------------------------ 工具

def _rows() -> dict[str, dict]:
    out = {}
    for r in feishu.table(config.TASK_TABLE) or []:
        m = re.match(r"^([ABC]\d{1,2})\b", r["fields"].get("任务", ""))
        if m:
            out[m[1]] = r
    return out


def _fmt(r: dict) -> str:
    f = r["fields"]
    return "｜".join(f"{k} {f.get(k, '') or '空'}" for k in ["任务", "项目", "负责人", "状态", "截止日期", "开始日期", "审核人", "前置任务", "备注"])


def get_tasks(codes: list[str] | None = None, keyword: str = "") -> str:
    rows = _rows()
    sel = [rows[c.upper()] for c in codes or [] if c.upper() in rows] if codes else list(rows.values())
    if keyword:
        sel = [r for r in sel if keyword in _fmt(r)]
    return "\n".join(_fmt(r) for r in sel) or "没有符合的任务"


def get_reports(date: str = "", who: str = "") -> str:
    out = []
    for r in feishu.table(config.REPORT_TABLE) or []:
        f = r["fields"]
        if (not date or date in f.get("模拟日", "")) and (not who or who in f.get("提交人", "")):
            out.append("；".join(f"{k}={v}" for k, v in f.items() if v))
    return "\n".join(out[-40:]) or "没有符合的日报"


def get_messages(since: str = "today", group: str = "", who: str = "", keyword: str = "", limit: int = 80) -> str:
    es = clock.entries()
    now = clock.now(es)
    if not now:
        return "还没有时钟，读不了"
    ds = clock.dates(es)
    i = ds.index(now["date"])
    start = clock.day_start(es, ds[i - 1] if since == "yesterday" and i > 0 else now["date"])
    out = []
    for g, cid in feishu.groups().items():
        if group and group not in g:
            continue
        for m in feishu.messages(cid, int(start), int(time.time())):
            if (who and who not in m["who"]) or (keyword and keyword not in m["text"]):
                continue
            at = clock.sim_at(es, m["ts"])
            out.append((m["ts"], f"[{at[0][5:]} {at[1]} {g}] {m['who']}：{m['text']}" if at else f"[{g}] {m['who']}：{m['text']}"))
    return "\n".join(x for _, x in sorted(out)[-max(1, min(limit, 300)):]) or "没有符合的消息"


def _fields(tid: str) -> dict[str, dict]:
    r = feishu.client.bitable.v1.app_table_field.list(
        ListAppTableFieldRequest.builder().app_token(feishu._app()).table_id(tid).page_size(100).build())
    if not r.success():
        raise RuntimeError(f"读表头失败：{r.code} {r.msg}")
    return {x.field_name: {"type": x.type, "options": [o.name for o in (x.property.options or [])] if x.property else []}
            for x in r.data.items or []}


def _write(tid: str, record_id: str, values: dict[str, str], fields: dict) -> None:
    out = {}
    for k, v in values.items():
        if fields[k]["type"] == 5:
            out[k] = int(datetime.strptime(v, "%Y-%m-%d").timestamp() * 1000) if v else None
        else:
            out[k] = v or None
    r = feishu.client.bitable.v1.app_table_record.batch_update(BatchUpdateAppTableRecordRequest.builder()
        .app_token(feishu._app()).table_id(tid).request_body(BatchUpdateAppTableRecordRequestBody.builder().records(
            [AppTableRecord.builder().record_id(record_id).fields(out).build()]).build()).build())
    if not r.success():
        raise RuntimeError(f"写任务表失败：{r.code} {r.msg}（助手要有多维表格编辑权限，并在表格里给它“可编辑”）")


def _log(code: str, record_id: str, old: dict, new: dict, undo: bool = False) -> None:
    now = clock.now() or {}
    EDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": round(time.time()), "模拟日": now.get("date"), "模拟时间": now.get("time"), "任务": code,
                            "record_id": record_id, "旧": old, "新": new, "撤销": undo}, ensure_ascii=False) + "\n")


def update_task(code: str, changes: dict[str, str]) -> str:
    tid = feishu.table_id(config.TASK_TABLE)
    fields = _fields(tid)
    r = _rows().get(code.strip().upper())
    if not r:
        return f"表里没有 {code}"
    for k, v in changes.items():
        if k not in EDITABLE or k not in fields:
            return f"「{k}」不能改，只能改：{'、'.join(EDITABLE)}"
        if fields[k]["options"] and v and v not in fields[k]["options"]:
            return f"「{k}」只能选：{'、'.join(fields[k]['options'])}"
        if fields[k]["type"] == 5 and v and not re.fullmatch(r"\d{4}-\d\d-\d\d", v):
            return f"「{k}」要写成 YYYY-MM-DD"
    old = {k: r["fields"].get(k, "") for k in changes}
    _write(tid, r["record_id"], changes, fields)
    _log(code.upper(), r["record_id"], old, changes)
    return "已改：" + "；".join(f"{code.upper()} {k}：{old[k] or '空'} → {v or '空'}" for k, v in changes.items())


def undo_last_edit() -> str:
    if not EDIT_LOG.exists():
        return "还没有改过表"
    logs = [json.loads(x) for x in EDIT_LOG.read_text(encoding="utf-8").splitlines() if x.strip()]
    last = next((x for x in reversed(logs) if not x["撤销"]), None)
    if not last or any(x["撤销"] and x["ts"] >= last["ts"] for x in logs):
        return "没有可以撤销的改动"
    tid = feishu.table_id(config.TASK_TABLE)
    _write(tid, last["record_id"], last["旧"], _fields(tid))
    _log(last["任务"], last["record_id"], last["新"], last["旧"], undo=True)
    return "已撤销：" + "；".join(f"{last['任务']} {k}：{last['新'][k] or '空'} → {v or '空'}" for k, v in last["旧"].items())


def run_check() -> str:
    now = clock.now()
    return check.run("随时" if now and now["working"] else "下班后")


IMPL = {"get_tasks": get_tasks, "get_reports": get_reports, "get_messages": get_messages,
        "update_task": update_task, "undo_last_edit": undo_last_edit, "run_check": run_check}


# ------------------------------------------------------------------ 对话

def history() -> list[dict]:
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []


def remember(role: str, content: str) -> None:
    """记一句到对话历史（自动推送的核对也记进来，你可以接着问"第二条怎么回事"）。"""
    h = (history() + [{"role": role, "content": content}])[-40:]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


def reset() -> None:
    HISTORY_FILE.unlink(missing_ok=True)


def chat(text: str, say) -> None:
    """回答一句话。中间要调工具时，先用 say() 告诉他在干什么。"""
    now = clock.now() or {}
    when = f"{now.get('date', '')} {now.get('weekday', '')} " + (now.get("time", "") if now.get("working") else "下班后")
    msgs = [{"role": "system", "content": SYSTEM.format(now=when, editable="、".join(EDITABLE))}] + history() \
        + [{"role": "user", "content": text}]
    cli = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, timeout=300, max_retries=2)
    tools = [{"type": "function", "function": t} for t in TOOLS]
    for _ in range(MAX_ROUNDS):
        m = cli.chat.completions.create(model=config.LLM_MODEL, messages=msgs, tools=tools).choices[0].message
        if not m.tool_calls:
            reply = (m.content or "").strip() or "（没想好怎么回答，换个说法试试）"
            remember("user", text)
            remember("assistant", reply)
            return say(reply)
        msgs.append(m.model_dump(exclude_none=True))
        for c in m.tool_calls:
            try:
                args = json.loads(c.function.arguments or "{}")
                if c.function.name == "run_check":
                    say("🤖 正在跑 AI 进度核对……（约半分钟）")
                out = IMPL[c.function.name](**args)
                if c.function.name == "run_check":      # 清单原样发给他，格式最清楚
                    say(out)
                    remember("assistant", out)
                    out += "\n\n（这份清单已经原样发给他了，不要重复，补一两句重点就行）"
            except Exception as e:      # noqa: BLE001
                out = f"出错了：{e}"
            print(f"[助手] 工具 {c.function.name}({c.function.arguments[:80]}) → {str(out)[:60]!r}")
            msgs.append({"role": "tool", "tool_call_id": c.id, "content": str(out)[:12000]})
    say("（查了太多步还没结论，换个问法试试）")
