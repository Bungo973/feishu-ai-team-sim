"""把某一天已经发生过的群聊导出成视频用的 JSON。

只读你在飞书里已经收到的东西（output/Dn/*.json 的群消息 + logs/feishu/Dn.jsonl 里你的发言和同事回复），
不读导演的剧本。只导出已经下班的日子。

用法：python3 scripts/export_day.py 1
"""

import csv
import shutil
import subprocess
import json
import re
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parents[2] / "ai-company-sim"
OUT = Path(__file__).resolve().parents[1] / "src" / "data"
FAKE_URL = re.compile(r"https?://\S+")  # 同事编的假链接，飞书里也是这样替换掉的


def load(day: int) -> dict:
    msgs = []
    for part in ("morning", "afternoon", "evening"):
        p = SIM / "output" / f"D{day}" / f"{part}.json"
        if not p.exists():
            continue
        for m in json.loads(p.read_text()):
            if m.get("kind") == "msg":
                msgs.append({"time": m["time"], "group": m["group"], "sender": m["sender"], "text": FAKE_URL.sub("[链接]", m["text"])})
    p = SIM / "logs" / "feishu" / f"D{day}.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            m = json.loads(line)
            msgs.append({"time": m["clock"], "group": m["group"], "sender": m.get("npc", "我"), "text": m["text"]})
    msgs.sort(key=lambda m: m["time"])  # 稳定排序：同一分钟内保持原顺序

    # 私聊：logs/chats/Dn-名字.json，assistant 是同事，user 是你
    dms = {}
    for f in sorted((SIM / "logs" / "chats").glob(f"D{day}-*.json")):
        who = f.stem.split("-", 1)[1]
        dms[who] = [{"time": m["clock"], "sender": who if m["role"] == "assistant" else "我",
                     "text": FAKE_URL.sub("[链接]", m["text"])} for m in json.loads(f.read_text())]

    stats = {}
    w = SIM / "output" / "workload.csv"
    if w.exists():
        for row in csv.DictReader(w.open(encoding="utf-8-sig")):
            if row["模拟日"] == f"D{day}":
                stats = {"追问": int(row["私聊追问(条)"]), "改表": int(row["改表(处)"])}
    return {"day": day, "messages": msgs, "dms": dms, "stats": stats}


if __name__ == "__main__":
    day = int(sys.argv[1])
    if not (SIM / "output" / f"D{day}" / "evening.json").exists():
        sys.exit(f"D{day} 还没下班，先别导出")
    OUT.mkdir(parents=True, exist_ok=True)
    data = load(day)
    # 头像：素材/头像/*.png（包括你自己的 我.png）
    avatars = SIM.parents[1] / "素材" / "头像"
    dst = OUT.parents[1] / "public" / "avatars"
    for f in avatars.glob("*.png"):
        shutil.copy(f, dst / f.name)
    # 你的头像：我.png / 我.jpg / 我的头像.jpg 都行，统一转成 我.png
    me = [f for f in avatars.iterdir() if f.stem in ("我", "我的头像") and f.suffix.lower() in (".png", ".jpg", ".jpeg")]
    if me:
        subprocess.run(["sips", "-s", "format", "png", str(me[0]), "--out", str(dst / "我.png")], check=True, capture_output=True)
    data["meAvatar"] = bool(me)
    (OUT / f"D{day}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"D{day}: {len(data['messages'])} 条消息 → src/data/D{day}.json")
