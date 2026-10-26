"""结局报告（P8）、指标导出、AI 周报初稿（P9，台前工具）。"""

import csv
import json

from . import config, engine, llm
from .director import improvement_name, prompt, read_actions
from .state import NAMES


def metrics_csv(state: dict) -> str:
    path = config.OUTPUT_DIR / "metrics.csv"
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        people = ["wangli", "zhangwei", "lixiang", "chenyue", "zhoutao", "liumin", "sunlei", "huang"]
        w.writerow(["模拟日", "周", "逾期任务数", "应交日报", "实交日报", "有效日报", "待审批数", "当天审批等待(天)"]
                   + [f"信任-{NAMES[p]}" for p in people])
        for m in state["metrics_daily"]:
            w.writerow([f"D{m['day']}", (m["day"] - 1) // 5 + 1, m["overdue"], m["reports_expected"], m["reports_submitted"],
                        m["reports_valid"], m["pending_approval"], ";".join(map(str, m["approval_waits"]))]
                       + [m["trust"].get(p) for p in people])
    return str(path)


def weekly_table(state: dict) -> list[dict]:
    rows = []
    for w in (1, 2, 3):
        ms = [m for m in state["metrics_daily"] if (m["day"] - 1) // 5 + 1 == w]
        if not ms:
            continue
        exp = sum(m["reports_expected"] for m in ms) or 1
        sub = sum(m["reports_submitted"] for m in ms)
        waits = [x for m in ms for x in m["approval_waits"]]
        rows.append({"周": w, "日报提交率": f"{sub / exp:.0%}", "日报有效率": f"{sum(m['reports_valid'] for m in ms) / (sub or 1):.0%}",
                     "周五逾期任务数": ms[-1]["overdue"], "王丽平均审批等待(天)": round(sum(waits) / len(waits), 1) if waits else "-"})
    return rows


def final_report(state: dict) -> str:
    scores = engine.final_scores(state)
    ev_results = {eid: {"name": engine.event_obj(state, eid).name, "result": r["result"], "done": r["done_k"]}
                  for eid, r in state["events"].items()}
    ev_results.update({r["id"]: {"name": engine.event_obj(state, r["id"]).name, "result": r["result"]} for r in state["random_active"]})
    imps = {f"{k} {improvement_name(state, k)}": f"D{v['day']}" for k, v in state["improvements"].items() if v["active"]}
    actions = "\n\n".join(f"## D{d}\n{read_actions(d)[:3000]}" for d in range(1, state["sim_day"] + 1) if read_actions(d))
    p = prompt("P8", scores=llm.dump(scores), event_results=llm.dump(ev_results), improvements=llm.dump(imps),
               metrics=llm.dump(weekly_table(state)), trust=llm.dump(state["trust_history"][-80:]), actions=actions or "（无）")
    text = llm.text_call("P8 结局报告", p, lambda: "# 结局报告（离线占位）\n\n" + llm.dump(scores),
                         model=config.MODEL_DIRECTOR, effort="high")
    path = config.OUTPUT_DIR / "结局报告.md"
    path.write_text(text, encoding="utf-8")
    (config.OUTPUT_DIR / "结局数据.json").write_text(json.dumps({"scores": scores, "events": ev_results, "weekly": weekly_table(state)},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    return str(path)


def weekly_draft(state: dict, week: int, extra_files: list[str]) -> str:
    """P9：你给团队做的提效工具。输入本周群里的日报 + 你导出的任务表 / 风险表 / 待办（可选）。"""
    days = range((week - 1) * 5 + 1, week * 5 + 1)
    reports = []
    for d in days:
        f = config.OUTPUT_DIR / f"D{d}" / "evening.json"
        if f.exists():
            reports += [f"D{d} {m['sender']}：{m['text']}" for m in json.loads(f.read_text(encoding="utf-8")) if m.get("report")]
    extras = {}
    for path in extra_files:
        extras[path] = open(path, encoding="utf-8-sig").read()[:20000]
    p = prompt("P9", daily_reports="\n\n".join(reports) or "（本周没有日报）",
               task_changes=llm.dump(extras) if extras else "（未提供，可以用 --file 传入导出的任务表 CSV）",
               risks="（见上方文件）" if extras else "（未提供）", action_items="（见上方文件）" if extras else "（未提供）")
    return llm.text_call("P9 周报初稿", p, lambda: "（离线占位周报初稿）", model=config.MODEL_ACTOR)


def daily_stats(state: dict) -> tuple[list[list], str]:
    """你每天"跟进"和"手动改表"的工作量（不用计时，直接从记录里数）。也存一份 output/workload.csv。"""
    from .feishu_live import AUTO, diff_bitable
    snaps = sorted(config.STATE_DIR.glob("bitable-D*.json"), key=lambda p: p.stat().st_mtime)
    edits: dict[int, list[int]] = {}
    autos: dict[int, int] = {}
    prev = None
    for p in snaps:
        day = int(p.stem.split("-")[1][1:])
        cur = json.loads(p.read_text(encoding="utf-8"))
        if prev is None:       # 第一张快照之前没有底：导入的计划表"状态"全是空的，填了的都算你改的
            rows = sum(1 for r in cur.values() if r["fields"].get("状态"))
            fields = rows
        else:
            ch = diff_bitable(prev, cur)
            autos[day] = autos.get(day, 0) + sum(1 for c in ch if AUTO in c)
            ch = [c for c in ch if AUTO not in c]
            rows, fields = len(ch), sum(c.count("→") or 1 for c in ch)
        e = edits.setdefault(day, [0, 0])
        e[0] += rows
        e[1] += fields
        prev = cur
    out = [["模拟日", "私聊追问(条)", "追问了几个人", "群里发言(条)", "改表(行)", "改表(处)", "补记(条)", "工作流自动标记(行)"]]
    for day in range(1, state["sim_day"] + 1):
        msgs, people = 0, 0
        for f in config.CHATS_DIR.glob(f"D{day}-*.json"):
            n = sum(1 for h in json.loads(f.read_text(encoding="utf-8")) if h["role"] == "user")
            msgs += n
            people += 1 if n else 0
        fl = config.FEISHU_LOG_DIR / f"D{day}.jsonl"
        posts = sum(1 for ln in fl.read_text(encoding="utf-8").splitlines() if ln and "npc" not in json.loads(ln)) if fl.exists() else 0
        notes = read_actions(day).count("记录｜")
        r, c = edits.get(day, [0, 0])
        out.append([f"D{day}", msgs, people, posts, r, c, notes, autos.get(day, 0)])
    path = config.OUTPUT_DIR / "workload.csv"
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(out)
    return out, str(path)
