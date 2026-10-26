"""离线跑完整 15 天（不调用大模型），检查引擎和导演流程。运行：uv run python tests/test_offline.py

三种玩法，数据都放在临时目录，不碰 state/、logs/、output/：
- idle：什么都不做
- chase：每天追问所有到期 / 逾期的任务，别的什么都不做
- good：按关键动作处理事件、上线改进（含 I12、I13 和一个清单外的改进）、发周报
- plan：good + 每天按真实工作量，把排不下的活请王丽缩减范围（检查"重新排期"确实比"催促"有效）
"""

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["LLM_MODE"] = "offline"

from ai_company_sim import config  # noqa: E402


def isolate(root: Path) -> None:
    config.LLM_MODE = "offline"
    config.STATE_DIR = root / "state"
    config.STATE_FILE = config.STATE_DIR / "state.json"
    config.HISTORY_DIR = config.STATE_DIR / "history"
    config.DIRECTOR_OUT_DIR = config.STATE_DIR / "director"
    config.LOGS_DIR = root / "logs"
    config.ACTIONS_DIR = config.LOGS_DIR / "actions"
    config.CHATS_DIR = config.LOGS_DIR / "chats"
    config.FEISHU_LOG_DIR = config.LOGS_DIR / "feishu"
    config.OUTPUT_DIR = root / "output"


def actions(s: dict, day: int, mode: str) -> str:
    from ai_company_sim import engine
    lines = []
    if mode in ("chase", "good"):
        lines += [f"- #chase {t['id']}" for t in s["tasks"]
                  if t.get("exists", True) and t["due_day"] <= day and t["status"] not in engine.DONE]
    if mode in ("good", "plan"):
        for eid, rec in s["events"].items():
            if rec["start"] <= day and rec["result"] is None:
                lines += [f"- [09:30] #K {eid} {k} 09:30" for k in engine.event_obj(s, eid).keys]
        lines += [f"- [10:00] #K {r['id']} K1" for r in s["random_active"] if r["result"] is None]
        lines += [f"- #summary {t['id']}" for t in s["tasks"] if t["status"] == "待审核"]
        if day == 3:
            lines += ["- #I I1", "- #I I2", "- #I I3", "- #I I12", "- #I I13", "- #X 会议纪要模板"]
        if day in (5, 10):
            lines.append("- #weekly")
    if mode == "plan":
        lines += replan(s, day)
    return "\n".join(lines)


def replan(s: dict, day: int) -> list[str]:
    """接下来 5 天排不下的活：先砍入职优化，再砍内容，最后才动发布会；每次砍掉剩余工作量的一半。"""
    from ai_company_sim import engine
    out, last = [], min(15, day + 4)
    for p in engine.WORKERS:
        open_ = [t for t in s["tasks"] if p in t["owners"] and t.get("exists", True) and not t.get("planned_change")
                 and t["status"] not in engine.DONE + ("待审核",) and t["due_day"] <= last]
        need = sum((t["est_h"] - t["done_h"]) / engine.eff(s, p) for t in open_)
        have = sum(engine.available_hours(s, p, d) for d in range(day, last + 1))
        for t in sorted(open_, key=lambda t: ({"C": 0, "B": 1, "A": 2}[t["project"]], -t["due_day"])):
            if need <= have:
                break
            out.append(f"- #adj scope_cut {t['id']} {round(t['done_h'] + (t['est_h'] - t['done_h']) * 0.5, 1)}")
            need -= (t["est_h"] - t["done_h"]) / engine.eff(s, p) * 0.5
    return out


def run(mode: str, seed: int, root: Path) -> dict:
    isolate(root)
    from ai_company_sim import director, report
    from ai_company_sim import state as st
    st.save(st.init(seed, "standard"))
    for _ in range(15):
        director.start_day(st.load())
        s = st.load()
        day = s["sim_day"]
        config.ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
        (config.ACTIONS_DIR / f"D{day}.md").write_text(actions(s, day, mode), encoding="utf-8")
        director.noon_day(st.load())
        director.end_day(st.load())
    s = st.load()
    report.metrics_csv(s)
    report.final_report(s)
    return s


def check(mode: str, s: dict) -> dict:
    from ai_company_sim import engine
    out = config.OUTPUT_DIR
    assert s["sim_day"] == 15 and s["phase"] == "night", "没跑完 15 天"
    for d in range(1, 16):
        assert (out / f"D{d}" / "recap-evening.txt").exists(), f"D{d} 没有下班复盘"
        assert (out / f"D{d}" / "recap-noon.txt").exists(), f"D{d} 没有中午复盘"
    assert (out / "结局报告.md").exists() and (out / "metrics.csv").exists()
    # 物料到场：后果描述和引擎算的时间一致
    if s["events"]["E12"]["result"]:
        text = engine.narrate(s, engine.event_obj(s, "E12").outcomes[s["events"]["E12"]["result"]])
        assert engine.delivery(s) in text, text
    # 催促加班：每人每周最多 3 次
    for p, days in s.get("chase_overtime", {}).items():
        for w in range(3):
            assert sum((d - 1) // 5 == w for d in days) <= 3, (p, days)
    if mode == "idle":
        assert not s.get("chase_overtime") or not any(s["chase_overtime"].values()), "没追问却加了班"
    if mode in ("good", "plan"):
        imp = s["improvements"]
        assert imp["I12"]["active"] and imp["I13"]["active"], "I12 / I13 没记上"
        assert any(v.get("name") == "会议纪要模板" for v in imp.values()), "清单外的改进没记上"
        assert "会议纪要模板" in (out / "D3" / "recap-evening.txt").read_text(encoding="utf-8") \
            or "会议纪要模板" in (out / "D3" / "recap-noon.txt").read_text(encoding="utf-8")
    done = sum(t["status"] == "已完成" for t in s["tasks"])
    ot = sum(len(v) for v in s.get("chase_overtime", {}).values())
    return {"score": engine.final_scores(s)["发布会"]["总分"], "已完成": done, "催促加班次数": ot,
            "周五逾期": [m["overdue"] for m in s["metrics_daily"] if m["day"] in (5, 10, 15)]}


def main() -> None:
    seeds = [int(x) for x in sys.argv[1:]] or [1118, 7]
    base = Path(tempfile.mkdtemp(prefix="sim-offline-"))
    for seed in seeds:
        res = {}
        for mode in ("idle", "chase", "good", "plan"):
            s = run(mode, seed, base / f"{seed}-{mode}")
            res[mode] = check(mode, s)
            print(f"seed {seed} {mode:5}: {json.dumps(res[mode], ensure_ascii=False)}")
        assert res["chase"]["已完成"] >= res["idle"]["已完成"], "追问反而完成得更少"
        assert res["good"]["score"] > res["idle"]["score"], "好好玩的分数不比摆烂高"
        assert res["plan"]["周五逾期"][-1] < res["chase"]["周五逾期"][-1], "重新排期没有比催促更能减少逾期"
    print(f"全部通过（临时数据在 {base}）")


if __name__ == "__main__":
    main()
