"""AI 进度核对：把群聊、任务表、日报表摆在一起，让大模型找出对不上、没下文、快到期的事。

输入材料只有这三样，外加"现在几点"。每次的输入原文都存到 核对记录/，可以随时打开看它到底看到了什么。
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from . import clock, config, feishu


class Item(BaseModel):
    任务: str
    类型: Literal["要核实", "要催", "快到期"]
    发现: str
    依据: str
    建议: str


class Result(BaseModel):
    items: list[Item]
    一句话: str


def _days(today: str, due: str) -> int:
    return (date.fromisoformat(due[:10]) - date.fromisoformat(today)).days


def materials(label: str) -> tuple[str, str]:
    """返回（标题, 给大模型的全部输入）。"""
    es = clock.entries()
    now = clock.now(es)
    if not now:
        raise RuntimeError("还没有时钟（../shared/clock.jsonl），模拟器开始一天后再试")
    today = now["date"]
    ds = clock.dates(es)
    yesterday = ds[ds.index(today) - 1] if ds.index(today) > 0 else today
    title = f"{today[5:]} {now['weekday']} {label}" + (f"（{now['time']}）" if now["working"] else "")

    rows, rules = [], []
    for r in feishu.table(config.TASK_TABLE) or []:
        f = r["fields"]
        name, st, due = f.get("任务", ""), f.get("状态", ""), f.get("截止日期", "")
        if not name:
            continue
        rows.append(f"{name}｜负责人 {f.get('负责人', '')}｜状态 {st or '空'}｜截止 {due or '无'}｜前置 {f.get('前置任务', '')}｜备注 {f.get('备注', '')}")
        if st == "已完成":
            continue
        at = clock.sim_at(es, r["modified"])
        if at and (gap := clock.workdays_between(es, at[0], today)) >= 2:
            rules.append(f"{name}：任务表已经 {gap} 个工作日没更新（最后一次改是 {at[0][5:]}）")
        if due and _days(today, due) < 0:
            rules.append(f"{name}：已经过了截止日期 {-_days(today, due)} 天（{due[5:10]}），状态 {st or '空'}")
        elif due and _days(today, due) <= 2:
            rules.append(f"{name}：{_days(today, due)} 天后截止（{due[5:10]}），状态 {st or '空'}")

    reports = [r["fields"] for r in feishu.table(config.REPORT_TABLE) or []
               if today in r["fields"].get("模拟日", "") or yesterday in r["fields"].get("模拟日", "")]
    reports = ["；".join(f"{k}={v}" for k, v in f.items() if v) for f in reports]

    msgs = []
    start = clock.day_start(es, yesterday) or now["ts"] - 3600
    for g, cid in feishu.groups().items():
        for m in feishu.messages(cid, int(start), int(time.time())):
            at = clock.sim_at(es, m["ts"])
            when = f"{at[0][5:]} {at[1]}" if at else "?"
            msgs.append((m["ts"], f"[{when} {g}] {m['who']}：{m['text']}"))
    msgs = [x for _, x in sorted(msgs)][-400:]

    p = f"""你是项目助理自己搭的"AI 进度核对"小工具。现在是 {today} {now['weekday']} {label}，时间 {now['time'] if now['working'] else '下班后'}。
你只能用下面给你的材料，不知道材料以外的任何事。不要编造，不确定就写"需要问一下"。

【任务表（当前）】
{chr(10).join(rows) or "（读不到任务表）"}

【程序算出来的规则提醒】
{chr(10).join(rules) or "无"}

【日报表（今天和昨天）】
{chr(10).join(reports) or "（还没有日报表的记录）"}

【群聊消息（昨天到现在，"我"是项目助理）】
{chr(10).join(msgs) or "无"}

请列出项目助理接下来最该处理的事，最多 8 条，按紧急程度排序：
- 要核实：群聊 / 日报里的说法和任务表对不上（例如有人说"做完了""交了""卡住了"，表上状态没变；或者日报说的进度和表不一致；或者日报没附交付物）
- 要催：任务表很久没更新、日报没交、答应的事没下文
- 快到期：2 天内截止或已经过了截止日期，但看起来还没完成
每条写清楚：哪个任务（用任务编号开头）、发现了什么、依据（引用原话，带时间和人）、建议找谁问什么（一句话）。
"一句话"字段：用一句话总结今天的整体情况。"""
    return title, p


def _ask(prompt: str) -> Result:
    cli = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, timeout=300, max_retries=2)
    sys = "只输出一个 JSON 对象，符合这个 JSON Schema，所有字符串用中文：\n" + json.dumps(Result.model_json_schema(), ensure_ascii=False)
    err = ""
    for _ in range(2):
        r = cli.chat.completions.create(model=config.LLM_MODEL, response_format={"type": "json_object"},
                                        messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt + err}])
        text = r.choices[0].message.content or ""
        try:
            return Result.model_validate_json(text[text.find("{"): text.rfind("}") + 1])
        except ValidationError as e:
            err = f"\n\n（上一次输出格式不对：{str(e)[:300]}，请严格按 Schema 重新输出）"
    raise RuntimeError("大模型两次都没按格式输出")


def run(label: str) -> str:
    """跑一次核对，返回飞书消息正文。输入和结果都存进 核对记录/。"""
    title, prompt = materials(label)
    res = _ask(prompt)
    icon = {"要核实": "🔍", "要催": "⏰", "快到期": "⚠️"}
    lines = [f"🤖 AI 进度核对 · {title}", res.一句话, ""]
    for kind in ("要核实", "要催", "快到期"):
        its = [i for i in res.items if i.类型 == kind]
        if its:
            lines.append(f"{icon[kind]} {kind}（{len(its)}）")
            lines += [f"· {i.任务}：{i.发现}\n  依据：{i.依据}\n  → {i.建议}" for i in its]
            lines.append("")
    if not res.items:
        lines.append("✅ 没发现要处理的事。")
    lines.append("（只根据群聊、日报表和任务表生成，不读私聊；结论请自己再判断）")
    text = "\n".join(lines).strip()
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w\-]+", "-", title).strip("-")
    (config.OUT_DIR / f"{stem}-输入.md").write_text(prompt + "\n", encoding="utf-8")
    (config.OUT_DIR / f"{stem}.md").write_text(text + "\n", encoding="utf-8")
    return text
