"""命令行入口：uv run sim <命令>"""

import argparse
import re
import shutil
import sys

from . import config, director, engine, llm
from .state import date_str, load, save, weekday
from . import state as st

ACTION_TEMPLATE = """# D{day} 动作日志（{date}）

> 如实记录，不写的等于没做。每条前面写模拟时间 [hh:mm]。上午写完运行 sim noon，下午接着往下写，再运行 sim end。
> 动作类型：核查 / 私聊 / 群消息 / 上报 / 记录 / 改进 / 协调

## 动作
- [09:30] 核查｜
- [ : ] ｜

## 我写的东西
（会议纪要、群公告、给王丽的上报、周报……贴全文或要点）

## 我改了飞书里的什么
- 任务表：
- 新建了：

## 今天的耗时（真实时间，手机秒表计）
- 总计约 {{ }} 分钟，其中 写纪要 {{ }} 分钟、核查 {{ }} 分钟、写周报 {{ }} 分钟

## 痛点笔记（给视频用，导演不看这部分的评价）
- 今天最烦 / 最花时间的事：
- 截图：
"""


def cmd_init(a):
    if config.STATE_FILE.exists() and not a.force:
        raise SystemExit("已经初始化过了。要重来请加 --force（会清空 state、logs、output）。")
    if a.force:
        for d in (config.STATE_DIR, config.LOGS_DIR, config.OUTPUT_DIR):
            shutil.rmtree(d, ignore_errors=True)
    s = st.init(a.seed, a.difficulty)
    save(s)
    st.snapshot(s, "D0")
    print(f"初始化完成（seed={a.seed}，难度={a.difficulty}）。下一步：uv run sim start")


def cmd_start(a):
    s = load()
    print(f"导演正在准备 D{s['sim_day'] + 1} 的剧情……（会调用 AI，约 1–3 分钟）")
    md = director.start_day(s)
    print(md)
    day = s["sim_day"]
    log = config.ACTIONS_DIR / f"D{day}.md"
    if not log.exists():
        config.ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
        log.write_text(ACTION_TEMPLATE.format(day=day, date=date_str(s, day), wd=weekday(day)), encoding="utf-8")
    print(f"\n✅ 上午开始了。消息也保存在 output/D{day}/morning.md")
    print(f"   今天的动作日志：logs/actions/D{day}.md（已为你建好模板）")
    print("   私聊同事：uv run sim chat 李想    上午的事做完、写好日志后：uv run sim noon")
    _auto_send(day, "morning")
    _usage()


def _log_empty(day: int) -> bool:
    """日志里没有一条填了内容的动作（模板里的 "- [09:30] 核查｜" 不算）。"""
    log = config.ACTIONS_DIR / f"D{day}.md"
    txt = log.read_text(encoding="utf-8") if log.exists() else ""
    return not re.search(r"^- \[\s*\d{1,2}:\d\d\s*\].*?｜[ \t]*\S", txt, re.M)


def _confirm_log(day: int, when: str, yes: bool) -> bool:
    if yes or not _log_empty(day):
        return True
    ans = input(f"D{day} 的动作日志里还没有写任何动作。导演只认日志、私聊和群发言里写下的动作（飞书里改表也要写进日志）。"
                f"确定{when}吗？(y/N) ")
    return ans.strip().lower() == "y"


def cmd_noon(a):
    s = load()
    day = s["sim_day"]
    if not _confirm_log(day, "进入下午", a.yes):
        return
    print("导演正在结算你上午的动作，准备下午的剧情……（约 1–3 分钟）")
    md = director.noon_day(s)
    print(md)
    print(f"\n☀️ 下午开始了。消息也保存在 output/D{day}/afternoon.md")
    print("   下午的动作接着写在同一份日志里（时间写 12:00 以后）。写完后下班：uv run sim end")
    _auto_send(day, "afternoon")
    _usage()


def cmd_end(a):
    s = load()
    day = s["sim_day"]
    if s.get("phase") == "day" and s.get("half") == "am":
        print("你还在上午，先进入下午……")
        cmd_noon(a)
        s = load()
        if s.get("half") == "am":
            return
        print("\n（下午的消息在上面。要先在下午做事的话，现在按 Ctrl+C，做完再运行 uv run sim end）")
        try:
            input("直接下班请按回车……")
        except (EOFError, KeyboardInterrupt):
            print()
            return
    if not _confirm_log(day, "收工", a.yes):
        return
    print("导演正在评估你今天的工作、推进进度……（约 1–3 分钟）")
    md = director.end_day(s)
    print(md)
    print(f"\n🌙 D{day} 结束。消息保存在 output/D{day}/evening.md")
    print("   下一天：uv run sim start" if day < 15 else "   模拟结束！生成结局报告：uv run sim report")
    _auto_send(day, "evening")
    _usage()


def _auto_send(day, phase):
    if config.FEISHU_SEND == "auto":
        from .feishu import send_phase
        n = send_phase(day, phase)
        print(f"   已发送 {n} 条消息到飞书。")


def _usage():
    u = llm.USAGE
    if u["calls"]:
        print(f"   （本次调用 AI {u['calls']} 次，输入 {u['input_tokens']} / 输出 {u['output_tokens']} tokens）")


def cmd_chat(a):
    from .chat import repl
    repl(load(), a.who)


def cmd_clock(a):
    s = load()
    err = director.set_clock(s, a.time)
    if err:
        raise SystemExit(err)
    save(s)
    print(f"模拟时间：D{s['sim_day']} {s['clock']}")


def cmd_status(a):
    s = load()
    day = s["sim_day"]
    when = {"am": "上午", "pm": "下午"}.get(s.get("half"), "上班中") if s["phase"] == "day" else "下班了"
    print(f"现在：D{day}（{date_str(s, day) if day else '还没开始'}），{when}，模拟时间 {s['clock']}")
    nxt = day if s["phase"] == "day" else day + 1
    if nxt <= 15:
        print(f"\nD{nxt} 日程：")
        for x in engine.fixed_schedule(s, nxt):
            print("  ·", x)
    pub = [(k, v) for k, v in sorted(s["content"].items()) if v.get("day")]
    if pub:
        print("\n已发布内容（公开数据）：")
        for k, v in pub:
            data = "，".join(f"{a}{b}" for a, b in v.get("data", {}).items())
            print(f"  · {k} D{v['day']} {v['time']} {data}")
    imps = [k for k, v in s["improvements"].items() if v["active"]]
    print(f"\n已上线的改进：{'、'.join(imps) or '无'}")
    nxt_cmd = ("写动作日志 → uv run sim noon" if s.get("half") == "am" else "写动作日志 → uv run sim end") \
        if s["phase"] == "day" else "uv run sim start"
    print("\n下一步：" + nxt_cmd)


def cmd_send(a):
    from .feishu import send_phase
    s = load()
    day = a.day or s["sim_day"]
    n = send_phase(day, a.phase, dry=a.dry)
    print(f"{'预览' if a.dry else '已发送'} {n} 条。")


def cmd_listen(a):
    from .feishu import listen
    listen(reply=a.reply)


def cmd_serve(a):
    from .feishu_live import serve
    serve(a.speed or config.FEISHU_SPEED)


def cmd_feishu_check(a):
    from .feishu_live import check
    check()


def cmd_stats(a):
    from .report import daily_stats
    rows, path = daily_stats(load())
    w = [max(len(str(r[i])) for r in rows) + 2 for i in range(len(rows[0]))]
    for r in rows:
        print("".join(str(v).ljust(w[i]) for i, v in enumerate(r)))
    print(f"\n已存：{path}（可以导入多维表格画对比图）")


def cmd_report(a):
    from .report import final_report, metrics_csv
    s = load()
    if s["sim_day"] < 15 or s["phase"] != "night":
        print("（模拟还没结束，先生成阶段性报告）")
    print("指标已导出：", metrics_csv(s))
    print("结局报告：", final_report(s))


def cmd_weekly(a):
    from .report import weekly_draft
    s = load()
    print(weekly_draft(s, a.week or ((max(s["sim_day"], 1) - 1) // 5 + 1), a.file or []))


def cmd_undo(a):
    """回到某天开始前（重录视频 / 改动作日志后重算用）。"""
    s = load()
    label = a.to
    f = config.HISTORY_DIR / f"{label}.json"
    if not f.exists():
        raise SystemExit(f"没有快照 {label}。可选：{', '.join(p.stem for p in sorted(config.HISTORY_DIR.glob('*.json')))}")
    config.STATE_FILE.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"已回到 {label}（输出文件和日志没有删除，重跑会覆盖）。")


def cmd_summary(a):
    s = load()
    director.write_daily_summary(s, a.day)
    director.write_backstage(s, a.day)
    save(s)
    print(s.get("daily_summaries", {}).get(str(a.day), "（没写出来）"))
    print("（导演纪要也已补写，只有导演能看到）")


def main():
    p = argparse.ArgumentParser(prog="sim", description="AI 模拟公司 · 项目助理演练")
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("init", help="初始化（开跑前一次）")
    x.add_argument("--seed", type=int, default=42)
    x.add_argument("--difficulty", choices=["easy", "standard", "hard"], default="standard")
    x.add_argument("--force", action="store_true")
    x.set_defaults(f=cmd_init)
    sub.add_parser("start", help="上班：生成今天上午的群消息").set_defaults(f=cmd_start)
    x = sub.add_parser("noon", help="中午：结算上午的动作，生成下午的群消息")
    x.add_argument("-y", "--yes", action="store_true")
    x.set_defaults(f=cmd_noon)
    x = sub.add_parser("end", help="下班：评估今天的动作，推进进度，生成日报和晚间消息")
    x.add_argument("-y", "--yes", action="store_true")
    x.set_defaults(f=cmd_end)
    x = sub.add_parser("chat", help="私聊某个角色，例如 sim chat 李想")
    x.add_argument("who")
    x.set_defaults(f=cmd_chat)
    x = sub.add_parser("clock", help="设置模拟时间，例如 sim clock 14:30")
    x.add_argument("time")
    x.set_defaults(f=cmd_clock)
    sub.add_parser("status", help="玩家视角的状态").set_defaults(f=cmd_status)
    x = sub.add_parser("send", help="把消息发到飞书群")
    x.add_argument("phase", choices=["morning", "afternoon", "evening"])
    x.add_argument("--day", type=int)
    x.add_argument("--dry", action="store_true", help="只预览不发送")
    x.set_defaults(f=cmd_send)
    x = sub.add_parser("listen", help="（进阶）采集你在飞书群里的发言")
    x.add_argument("--reply", action="store_true", help="你 @同事 时让同事自动回复（实验）")
    x.set_defaults(f=cmd_listen)
    x = sub.add_parser("serve", help="飞书模式：整局在飞书里玩（见 docs/飞书配置指南.md）")
    x.add_argument("--speed", type=float, help="模拟分钟 / 现实分钟，默认 15")
    x.set_defaults(f=cmd_serve)
    sub.add_parser("feishu-check", help="检查飞书机器人配置").set_defaults(f=cmd_feishu_check)
    x = sub.add_parser("summary", help="补写某一天的公开纪要，例如 sim summary 1")
    x.add_argument("day", type=int)
    x.set_defaults(f=cmd_summary)
    sub.add_parser("stats", help="你每天的跟进和改表工作量（私聊追问、群发言、改表次数）").set_defaults(f=cmd_stats)
    sub.add_parser("report", help="结局报告 + 指标导出").set_defaults(f=cmd_report)
    x = sub.add_parser("weekly", help="AI 周报初稿（你的提效工具，P9）")
    x.add_argument("--week", type=int)
    x.add_argument("--file", action="append", help="导出的任务表 / 风险表 CSV，可多次")
    x.set_defaults(f=cmd_weekly)
    x = sub.add_parser("undo", help="回到某个快照，例如 sim undo D6-morning 或 sim undo D5")
    x.add_argument("to")
    x.set_defaults(f=cmd_undo)
    a = p.parse_args()
    try:
        a.f(a)
    except KeyboardInterrupt:
        sys.exit(130)
