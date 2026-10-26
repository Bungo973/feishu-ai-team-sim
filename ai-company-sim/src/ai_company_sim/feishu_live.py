"""飞书模式：整局游戏在飞书里进行（uv run sim serve）。

- 每个同事是一个飞书"企业自建应用"的机器人：在群里用自己的身份说话，也能被你私聊。
- "导演"机器人：你私聊它发命令（上班 / 中午 / 下班 / 暂停 / 继续 / 快进 / 状态 / 记录：…）。
- 模拟时间按加速的节奏走，消息到点才发；有人私聊你或 @你 时自动暂停，你回复后自动继续。
- 你在群里的发言、私聊、对多维表格任务表的修改都会自动记录，导演收工时直接读。

结构：每个应用一个子进程跑长连接，收到的消息放进同一个队列；主线程按顺序处理（游戏状态只在主线程改）。
"""

import json
import multiprocessing as mp
import queue
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import artifacts, config, director, engine, llm, tools
from .state import KEY_BY_NAME, NAMES, date_str, load, save, weekday

PEOPLE = ["wangli", "zhangwei", "lixiang", "chenyue", "zhoutao", "sunlei", "liumin", "huang"]
APP_KEYS = ["director", "others"] + PEOPLE
IDS_FILE = config.ROOT / "feishu_ids.json"        # 群 ID、你在各应用下的 open_id、私聊会话 ID（重置存档也保留）
HALF = {"morning": ("09:00", "11:59"), "afternoon": ("12:00", "17:25")}
MEETING_GAP = 2.5          # 会议里每句话间隔几秒（现实时间）
MEETING_MIN = {"彩排": 120}  # 会议占用的模拟分钟，默认 60

HELP = """可以发给我的命令：
· 上班 —— 开始新的一天（上午）
· 中午 —— 结算上午，开始下午
· 下班 —— 结束今天，看日报和晚上的消息（时段里还有消息没到时会先确认）
· 暂停 / 继续 —— 停住或恢复模拟时间
· 快进 —— 跳到下一条消息；快进 10:30 —— 跳到指定时间
· 速度 20 —— 每现实 1 分钟走 20 模拟分钟（默认 {speed}）
· 状态 —— 现在几点、还有多少消息没到
· 记录：…… —— 补记一件群聊、私聊、任务表之外的事（比如写了纪要，可以附飞书文档链接）
私聊同事：直接点开他们的机器人聊天。在群里 @某人，他会在群里回你。
AI 进度核对：私聊「AI 进度助手」发“核对”（它是独立的工具，不归导演管）。"""


# ------------------------------------------------------------------ 配置与 ID

def app_config() -> dict[str, tuple[str, str]]:
    import os
    out = {}
    for k in APP_KEYS:
        i, s = os.getenv(f"FEISHU_BOT_{k.upper()}_ID", ""), os.getenv(f"FEISHU_BOT_{k.upper()}_SECRET", "")
        if i and s:
            out[k] = (i, s)
    return out


def load_ids() -> dict:
    d = json.loads(IDS_FILE.read_text(encoding="utf-8")) if IDS_FILE.exists() else {}
    d.setdefault("chats", {})
    d.setdefault("player", {})
    return d


def save_ids(d: dict) -> None:
    IDS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def to_hm(m: float) -> str:
    m = int(m)
    return f"{m // 60:02d}:{m % 60:02d}"


# ------------------------------------------------------------------ 长连接子进程

def _listen(key: str, app_id: str, secret: str, q) -> None:
    import lark_oapi as lark

    def on_msg(data) -> None:
        ev = data.event
        m = ev.message
        try:
            content = json.loads(m.content or "{}")
        except json.JSONDecodeError:
            content = {}
        q.put({"app": key, "chat_id": m.chat_id, "chat_type": m.chat_type, "message_id": m.message_id,
               "msg_type": m.message_type, "content": content, "sender_type": ev.sender.sender_type,
               "open_id": ev.sender.sender_id.open_id if ev.sender.sender_id else "",
               "mentions": [{"key": x.key, "name": x.name} for x in (m.mentions or [])]})

    handler = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(on_msg).build()
    lark.ws.Client(app_id, secret, event_handler=handler, log_level=lark.LogLevel.WARNING).start()


# ------------------------------------------------------------------ 发消息

class Bot:
    def __init__(self, key: str, app_id: str, secret: str):
        import lark_oapi as lark
        self.key = key
        self.lark = lark
        self.client = lark.Client.builder().app_id(app_id).app_secret(secret).log_level(lark.LogLevel.WARNING).build()

    def send(self, receive_id: str, text: str, id_type: str = "chat_id") -> bool:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
        req = CreateMessageRequest.builder().receive_id_type(id_type).request_body(
            CreateMessageRequestBody.builder().receive_id(receive_id).msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False)).build()).build()
        r = self.client.im.v1.message.create(req)
        Live.api_calls += 1
        if not r.success():
            print(f"  ✗ {self.key} 发送失败：{r.code} {r.msg}")
            return False
        return True

    def send_file(self, receive_id: str, path: Path, id_type: str = "chat_id") -> bool:
        from lark_oapi.api.im.v1 import (CreateFileRequest, CreateFileRequestBody, CreateMessageRequest,
                                         CreateMessageRequestBody)
        ext = path.suffix.lstrip(".").lower()
        ftype = {"xlsx": "xls", "xls": "xls", "docx": "doc", "doc": "doc", "pdf": "pdf", "pptx": "ppt"}.get(ext, "stream")
        with open(path, "rb") as f:
            r = self.client.im.v1.file.create(CreateFileRequest.builder().request_body(
                CreateFileRequestBody.builder().file_type(ftype).file_name(path.name).file(f).build()).build())
        Live.api_calls += 1
        if not r.success():
            print(f"  ✗ {self.key} 上传文件失败：{r.code} {r.msg}（应用需要 im:resource 权限）")
            return False
        req = CreateMessageRequest.builder().receive_id_type(id_type).request_body(
            CreateMessageRequestBody.builder().receive_id(receive_id).msg_type("file")
            .content(json.dumps({"file_key": r.data.file_key})).build()).build()
        r2 = self.client.im.v1.message.create(req)
        Live.api_calls += 1
        return r2.success()

    def chats(self) -> dict[str, str]:
        from lark_oapi.api.im.v1 import ListChatRequest
        out, token = {}, None
        while True:
            b = ListChatRequest.builder().page_size(100)
            if token:
                b = b.page_token(token)
            r = self.client.im.v1.chat.list(b.build())
            Live.api_calls += 1
            if not r.success():
                raise RuntimeError(f"{self.key} 读群列表失败：{r.code} {r.msg}")
            for c in r.data.items or []:
                out[c.name] = c.chat_id
            if not r.data.has_more:
                return out
            token = r.data.page_token


# ------------------------------------------------------------------ 多维表格比对（导演机器人读）

def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "、".join(_cell(x) for x in v if _cell(x))
    if isinstance(v, dict):
        return str(v.get("text") or v.get("name") or v.get("link") or "")
    if isinstance(v, (int, float)) and v > 1e12:          # 日期：毫秒时间戳
        return time.strftime("%Y-%m-%d", time.localtime(v / 1000))
    return str(v).strip()


def read_bitable(bot: Bot, url: str) -> dict[str, dict]:
    from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest
    p = urlparse(url)
    app_token = p.path.rstrip("/").split("/")[-1]
    table_id = parse_qs(p.query).get("table", [""])[0]
    rows, token = {}, None
    while True:
        b = ListAppTableRecordRequest.builder().app_token(app_token).table_id(table_id).page_size(500)
        if token:
            b = b.page_token(token)
        r = bot.client.bitable.v1.app_table_record.list(b.build())
        Live.api_calls += 1
        if not r.success():
            raise RuntimeError(f"读多维表格失败：{r.code} {r.msg}（导演应用要有多维表格权限，并在表格里“添加文档应用”）")
        for rec in r.data.items or []:
            f = {k: _cell(v) for k, v in (rec.fields or {}).items()}
            name = f.get("任务") or next(iter(f.values()), rec.record_id)
            rows[rec.record_id] = {"name": name, "fields": f}
        if not r.data.has_more:
            return rows
        token = r.data.page_token


def post_text(c: dict) -> str:
    """富文本（post）消息 → 文字：标题 + 每一行。群公告、带格式的长消息都是这种。"""
    if "content" not in c:      # 有的版本外面还包一层语言：{"zh_cn": {...}}
        c = next((v for v in c.values() if isinstance(v, dict) and "content" in v), {})
    def seg(x: dict) -> str:
        if x.get("tag") == "a":
            return f"{x.get('text', '')}（{x.get('href', '')}）" if x.get("text") else x.get("href", "")
        if x.get("tag") == "at":
            return f"@{x.get('user_name', '')}"
        return x.get("text", "")
    lines = ["".join(seg(x) for x in line) for line in c.get("content") or []]
    return "\n".join(x for x in [c.get("title", "")] + lines if x.strip()).strip()


def write_clock(s: dict, hm: str, working: bool) -> None:
    """模拟时钟写进 ../shared/clock.jsonl。这是 AI 进度助手唯一能从模拟器拿到的东西：现在是哪天几点、上没上班。"""
    if s["sim_day"] < 1:
        return
    d = date_str(s, s["sim_day"])
    config.CLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with config.CLOCK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": round(time.time()), "date": d[:10], "weekday": d[11:], "time": hm, "working": working},
                           ensure_ascii=False) + "\n")


def start_assistant():
    """顺带把 AI 进度助手（独立项目，单独的进程）拉起来。没配置就跳过。"""
    import subprocess
    if not (config.ASSISTANT_DIR / ".env").exists():
        return None
    import os
    from dotenv import dotenv_values
    mine = set(dotenv_values(config.ROOT / ".env")) | {"VIRTUAL_ENV"}   # 模拟器的配置一项都不传给它
    env = {k: v for k, v in os.environ.items() if k not in mine} | {"PYTHONUNBUFFERED": "1"}
    print("AI 进度助手：已在后台启动（独立进程，日志前缀 [助手]）")
    return subprocess.Popen(["uv", "run", "--project", str(config.ASSISTANT_DIR), "assistant"], cwd=config.ASSISTANT_DIR, env=env)


AUTO = "（工作流自动）"       # 飞书工作流改的表，带这个标记，统计时不算你手动改的
AUTO_STATUS = "受影响-待确认"
AUTO_COLS = {"曾完成", "提醒用"}  # 只给工作流用的辅助列，不进日志


def diff_bitable(old: dict, new: dict) -> list[str]:
    out = []
    # 上次还没有的列（新加的公式、编号等）整列填出来不算改表；这次整列没了的（改名、删列）也不算
    cols = ({k for r in old.values() for k in r["fields"]} & {k for r in new.values() for k in r["fields"]}) - AUTO_COLS
    for rid, row in new.items():
        if rid not in old:
            out.append(f"新增「{row['name']}」：" + "；".join(f"{k}={v}" for k, v in row["fields"].items() if v and k != "任务"))
            continue
        of, nf = old[rid]["fields"], row["fields"]
        ch, auto = [], []
        for k in [k for k in {**of, **nf} if k in cols]:     # 清空的格子接口不返回，所以两边的列都要看
            a, b = of.get(k, ""), nf.get(k, "")
            if a != b:
                (auto if k == "状态" and b == AUTO_STATUS else ch).append(f"{k}：{a or '空'} → {b or '空'}")
        if ch:
            out.append(f"「{row['name']}」" + "；".join(ch))
        if auto:
            out.append(f"「{row['name']}」{AUTO}" + "；".join(auto))
    out += [f"删除「{row['name']}」" for rid, row in old.items() if rid not in new]
    return out


def read_doc(bot: Bot, url: str) -> str:
    """补记里附了飞书文档链接：读出正文，导演就能看到你写的纪要 / 周报。读不到就只留链接。"""
    m = re.search(r"/(docx|wiki)/([A-Za-z0-9]+)", url)
    if not m:
        return ""
    try:
        token = m[2]
        if m[1] == "wiki":
            from lark_oapi.api.wiki.v2 import GetNodeSpaceRequest
            r = bot.client.wiki.v2.space.get_node(GetNodeSpaceRequest.builder().token(token).build())
            Live.api_calls += 1
            if not r.success() or r.data.node.obj_type != "docx":
                return ""
            token = r.data.node.obj_token
        from lark_oapi.api.docx.v1 import RawContentDocumentRequest
        r = bot.client.docx.v1.document.raw_content(RawContentDocumentRequest.builder().document_id(token).build())
        Live.api_calls += 1
        return r.data.content[:6000] if r.success() else ""
    except Exception as e:      # noqa: BLE001  读文档是锦上添花，失败不影响游戏
        print(f"  （读文档失败：{e}）")
        return ""


# ------------------------------------------------------------------ 动作日志

LOG_TEMPLATE = """# D{day} 动作日志（{date}）· 飞书模式

> 群发言、私聊、任务表修改会自动记录；这里主要是你发给导演的"记录：…"和任务表的自动比对。
> 也可以直接在这个文件里补写，每条前面写模拟时间 [hh:mm]。

## 动作

## 我写的东西

## 痛点笔记（给视频用）
- 今天最烦 / 最花时间的事：
- 截图：
"""


def ensure_log(state: dict, day: int) -> Path:
    f = config.ACTIONS_DIR / f"D{day}.md"
    if not f.exists():
        config.ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
        f.write_text(LOG_TEMPLATE.format(day=day, date=date_str(state, day)), encoding="utf-8")
    return f


def add_log(state: dict, day: int, line: str, section: str = "## 我写的东西") -> None:
    """在某一节前面插入一行（默认插在"动作"一节末尾）。"""
    f = ensure_log(state, day)
    s = f.read_text(encoding="utf-8")
    i = s.find(section)
    s = s + "\n" + line + "\n" if i < 0 else s[:i] + line + "\n" + s[i:]
    f.write_text(s, encoding="utf-8")


# ------------------------------------------------------------------ 主循环

class Live:
    api_calls = 0

    def __init__(self, speed: float):
        self.apps = app_config()
        if "director" not in self.apps:
            raise SystemExit("没有配置导演机器人：.env 里填 FEISHU_BOT_DIRECTOR_ID / FEISHU_BOT_DIRECTOR_SECRET。见 docs/飞书配置指南.md")
        self.bots = {k: Bot(k, *v) for k, v in self.apps.items()}
        self.ids = load_ids()
        self.q = mp.Queue()
        self.seen: list[str] = []
        self.speed = speed               # 模拟分钟 / 现实分钟
        self.paused: str | None = "hard"  # None / "hard" / "soft:<会话>"
        self.pending: list[dict] = []    # 这个时段还没发出去的消息（按时间）
        self.half_end = ""
        self.end_notified = False
        self.last_tick = time.time()
        self.sim_min = 0.0
        self.forcing = False             # 一次发完剩余消息时，不因为私聊 / @ 而暂停
        self.meeting: dict | None = None  # 正在群里"文字开会"
        self.last_speaker: dict[str, tuple[str, float]] = {}   # 每个群最近说话的同事（名字, 模拟分钟）
        self._released_key = ""

    # ---------- 基础

    def bot_for(self, key: str) -> tuple[Bot, bool]:
        """同事自己的机器人；没有就用"其他同事"，再没有就用导演（第二个值 = 是否要在消息前加名字）。"""
        if key in self.bots:
            return self.bots[key], False
        return self.bots.get("others") or self.bots["director"], True

    def player_chat(self, app: str) -> str:
        return self.ids["player"].get(app, {}).get("chat_id", "")

    def tell(self, text: str) -> None:
        """导演机器人私聊你。"""
        cid = self.player_chat("director")
        if cid:
            self.bots["director"].send(cid, text)
        print(f"[导演] {text}")

    def at_player(self, bot: Bot, text: str) -> str:
        oid = self.ids["player"].get(bot.key, {}).get("open_id", "")
        return text.replace("@项目助理", f'<at user_id="{oid}">项目助理</at>') if oid else text

    def state(self) -> dict:
        return load()

    def set_clock(self, minutes: float) -> None:
        self.sim_min = minutes
        s = load()
        hm = to_hm(minutes)
        if s.get("clock") != hm:
            s["clock"] = hm
            save(s)
            write_clock(s, hm, working=s["phase"] == "day")

    # ---------- 启动

    def resolve_chats(self) -> None:
        names = list(config.GROUP_KEYS)
        try:
            found = self.bots["director"].chats()
        except Exception as e:      # noqa: BLE001  配置到一半（还没发布 / 没权限）时也要能启动
            print(f"⚠️ 暂时读不到群列表：{e}")
            return
        for g in names:
            if g in found:
                self.ids["chats"][g] = found[g]
        save_ids(self.ids)
        miss = [g for g in names if g not in self.ids["chats"]]
        if miss:
            print(f"⚠️ 导演机器人不在这些群里：{'、'.join(miss)}。把所有机器人都拉进两个群（群名要一模一样）。")

    def run(self) -> None:
        procs = [mp.Process(target=_listen, args=(k, *v, self.q), daemon=True) for k, v in self.apps.items()]
        for p in procs:
            p.start()
        self.resolve_chats()
        s = load()
        self.sim_min = to_min(s.get("clock") or "09:00")
        if s["phase"] == "day":
            self.restore_half(s)
        print(f"飞书模式已启动：{len(self.apps)} 个机器人（{'、'.join(NAMES.get(k, k) for k in self.apps)}）。Ctrl+C 停止。")
        if not self.player_chat("director"):
            print("👉 先在飞书里私聊“导演”机器人随便发一句（比如“你好”），之后它才能给你发消息。")
        else:
            if s["phase"] == "day":
                when = "上午" if s.get("half") == "am" else "下午"
                self.tell(f"飞书模式已连接。D{s['sim_day']} {when}进行中，时间停在 {to_hm(self.sim_min)}，发“继续”接着走。")
            else:
                self.tell("飞书模式已连接。发“上班”开始新的一天。")
        helper = start_assistant()
        try:
            while True:
                try:
                    ev = self.q.get(timeout=1)
                    self.safe(self.handle, ev)
                except queue.Empty:
                    pass
                self.safe(self.tick)
        except KeyboardInterrupt:
            print("\n已停止。下次 uv run sim serve 会接着当前进度。")
        finally:
            if helper:
                helper.terminate()

    def safe(self, fn, *a) -> None:
        """出错不退出：把错误告诉你，游戏状态停在出错前（命令可以重发）。"""
        try:
            fn(*a)
        except (Exception, SystemExit) as e:   # noqa: BLE001
            import traceback
            traceback.print_exc()
            self.paused = "hard"
            try:
                self.tell(f"⚠️ 出错了：{e}\n时间已暂停。AI 偶尔超时，重发刚才的命令通常就好；一直出错的话把终端的报错发给 Claude。")
            except Exception:              # noqa: BLE001
                pass

    # ---------- 时间推进

    def tick(self) -> None:
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now
        if self.meeting:
            if self.paused != "hard":
                self.meeting_step(now)
            return
        if self.paused or not self.half_end:
            return
        new = min(self.sim_min + self.speed * dt / 60, to_min(self.half_end))
        self.release_until(new)
        if self.sim_min >= to_min(self.half_end) and not self.end_notified and not self.pending:
            self.end_notified = True
            nxt = "中午" if self.half_end == HALF["morning"][1] else "下班"
            self.tell(f"🕐 {self.half_end}，这个时段的消息都到了。手上的事做完后发“{nxt}”。")

    def release_until(self, minutes: float) -> None:
        while self.pending and to_min(self.pending[0]["time"]) <= minutes and (self.forcing or not self.paused) \
                and not self.meeting:
            m = self.pending.pop(0)
            self.set_clock(max(self.sim_min, to_min(m["time"])))
            self.post(m)
            if self._released_key:
                self.ids.setdefault("released", {}).setdefault(self._released_key, []).append(m["_id"])
                save_ids(self.ids)
        if (self.forcing or not self.paused) and not self.meeting:
            self.set_clock(max(self.sim_min, minutes))

    def post(self, m: dict) -> None:
        if m["kind"] == "private":
            from . import chat
            key = KEY_BY_NAME.get(m["sender"], "")
            bot, prefix = self.bot_for(key)
            if m.get("intent") and not self.forcing:    # 到点再写：带上今天到这一刻为止你们聊过的内容
                try:
                    m = dict(m, text=chat.npc_opening(load(), load()["sim_day"], key, m["intent"], m["time"]))
                except Exception as e:      # noqa: BLE001
                    print(f"  （重写主动私聊失败，用中午生成的版本：{e}）")
            chat.deliver(load()["sim_day"], m["sender"], m["time"], m["text"])
            cid = self.player_chat(bot.key)
            if not cid:
                self.tell(f"（{m['sender']}想私聊你，但你还没和 TA 的机器人说过话。先私聊 TA 的机器人发一句“你好”。）\n{m['sender']}：{m['text']}")
            else:
                body = artifacts.scrub(m["text"], False)
                bot.send(cid, f"{m['sender']}：{body}" if prefix else body)
            self.pause(f"soft:p2p:{key}", f"{m['sender']} 私聊了你")
            return
        cid = self.ids["chats"].get(m["group"])
        if not cid:
            self.resolve_chats()              # 机器人可能是 serve 启动后才拉进群的
            cid = self.ids["chats"].get(m["group"])
        if not cid:
            print(f"  ✗ 不知道群「{m['group']}」的 ID，跳过一条消息")
            return
        if m["kind"] == "meeting":
            if self.forcing:                  # 一次发完：会议也直接贴记录
                return self.dump_meeting(cid, m, m["lines"])
            names = "、".join(dict.fromkeys(l["speaker"] for l in m["lines"] if l["speaker"] != "项目助理"))
            self.bots["director"].send(cid, f"📞 {m['time']} {m['name']}开始（群里文字开会）\n参会：{names}、项目助理")
            self.meeting = {"m": m, "cid": cid, "idx": 0, "next_at": time.time() + MEETING_GAP, "waiting": False,
                            "end_min": to_min(m["time"]) + MEETING_MIN.get(m["name"], 60), "heard": []}
            return
        key = KEY_BY_NAME.get(m["sender"], "")
        bot, prefix = self.bot_for(key)
        if not self.forcing and key in NAMES and self.half_end:
            m = dict(m, text=self.live_text(m, key))
        file = self.artifact_for(m["sender"], m["text"])
        body = artifacts.scrub(m["text"], bool(file))
        text = f"{m['sender']}：{body}" if prefix else body
        bot.send(cid, self.at_player(bot, text))
        if file:
            bot.send_file(cid, file)
        self.last_speaker[m["group"]] = (m["sender"], self.sim_min)
        print(f"  [{m['time']}][{m['group']}] {m['sender']}：{m['text'][:40]}")
        if "@项目助理" in m["text"]:
            self.pause(f"soft:group:{m['group']}:{m['sender']}", f"{m['sender']} 在「{m['group']}」@了你")

    def live_text(self, m: dict, key: str) -> str:
        """台词到点再写：这个人 / 这个群在剧本写好之后和你有过相关来往，就按现在的情况重写（事实不变）；否则原样发。"""
        from . import chat
        s = load()
        day, now = s["sim_day"], to_hm(self.sim_min)
        since = "12:00" if s.get("half") == "pm" else "09:00"
        name = m["sender"]
        dm = any(h["role"] == "user" and since <= h["clock"] <= now for h in chat.load_history(day, name))
        posts = []
        fl = config.FEISHU_LOG_DIR / f"D{day}.jsonl"
        if fl.exists():
            for ln in fl.read_text(encoding="utf-8").splitlines():
                r = json.loads(ln)
                if "npc" not in r and since <= r.get("clock", "") <= now:
                    posts.append(r)
        in_group = any(p["group"] == m["group"] for p in posts)
        named = any(name in p["text"] or KEY_BY_NAME.get(name, "-") in p["text"] for p in posts)
        if not (dm or in_group or named):
            return m["text"]
        must_not = list(director.forbidden_tokens(s, day))
        try:
            d = json.loads((config.DIRECTOR_OUT_DIR / f"D{day}-{'noon' if s.get('half') == 'pm' else 'morning'}.json").read_text(encoding="utf-8"))
            for it in d["script"]["script"]:
                if it.get("time") == m["time"] and it.get("sender") == name:
                    must_not += it.get("must_not_reveal", [])
        except Exception:      # noqa: BLE001
            pass
        try:
            new = chat.group_line(s, day, key, m["group"], m["text"], now, since, must_not)
        except Exception as e:      # noqa: BLE001
            print(f"  （台词重写失败，原样发：{e}）")
            return m["text"]
        if not new.strip() or any(t and len(t) >= 2 and t in new for t in must_not):
            return m["text"]
        print(f"  （到点重写 {name}：{m['text'][:30]} → {new[:30]}）")
        return new

    def artifact_for(self, sender: str, text: str) -> Path | None:
        """同事提到自己的工作底稿时，生成真的文件一起发（每份只发一次）。"""
        hit = artifacts.match(sender, text)
        if not hit:
            return None
        name, fn = hit
        sent = self.ids.setdefault("artifacts", [])
        if name in sent:
            return None
        try:
            s = load()
            path = fn(s, s["sim_day"])
        except Exception as e:      # noqa: BLE001  文件只是锦上添花
            print(f"  （生成文件失败：{e}）")
            return None
        sent.append(name)
        save_ids(self.ids)
        return path

    # ---------- 会议：一句一句说，轮到项目助理时停下来等你发言

    def meeting_step(self, now: float) -> None:
        mt = self.meeting
        if mt["waiting"] or now < mt["next_at"]:
            return
        lines = mt["m"]["lines"]
        if mt["idx"] >= len(lines):
            return self.end_meeting()
        line = lines[mt["idx"]]
        mt["idx"] += 1
        if line["speaker"] == "项目助理":
            if mt["idx"] >= 2 and lines[mt["idx"] - 2]["speaker"] == "项目助理":
                return                          # 连着两个空位只停一次
            mt["waiting"] = True
            last = mt["heard"][-1] if mt["heard"] else ""
            self.tell(f"🎤 {mt['m']['name']}上轮到你发言了（在「{mt['m']['group']}」群里直接说）。"
                      + (f"\n刚才：{last}" if last else "") + "\n不想说就发“继续”。")
            return
        key = KEY_BY_NAME.get(line["speaker"], "")
        bot, prefix = self.bot_for(key)
        body = artifacts.scrub(line["text"], False)
        bot.send(mt["cid"], self.at_player(bot, f"{line['speaker']}：{body}" if prefix else body))
        mt["heard"].append(f"{line['speaker']}：{line['text']}")
        mt["next_at"] = now + MEETING_GAP

    def meeting_reply(self, text: str) -> None:
        """你在会上发言：主持人先接一句，会议再按剧本往下走。"""
        from . import chat
        mt = self.meeting
        s = load()
        s["clock"] = to_hm(self.sim_min)
        host = "王丽" if any(l["speaker"] == "王丽" for l in mt["m"]["lines"]) else mt["m"]["lines"][0]["speaker"]
        key = KEY_BY_NAME[host]
        ctx = "\n".join(mt["heard"][-8:])
        hist = [{"role": "user", "clock": s["clock"],
                 "text": f"（{mt['m']['name']}正在群里开，你是主持人。刚才的发言：\n{ctx}\n现在项目助理在会上说：）{text}\n"
                         f"（用一两句会议里的口吻回应项目助理，然后把会议往下带，不要散会。）"}]
        r = chat.reply(s, s["sim_day"], key, hist)
        bot, prefix = self.bot_for(key)
        bot.send(mt["cid"], f"{host}：{r}" if prefix else r)
        mt["heard"] += [f"项目助理：{text}", f"{host}：{r}"]
        mt["waiting"] = False
        mt["next_at"] = time.time() + MEETING_GAP

    def dump_meeting(self, cid: str, m: dict, lines: list[dict]) -> None:
        body = [f"{l['speaker']}：{l['text']}" for l in lines if l["speaker"] != "项目助理"]
        if body:
            self.bots["director"].send(cid, f"【{m['time']} {m['name']} · 文字记录】\n" + "\n".join(body))

    def end_meeting(self, fast: bool = False) -> None:
        mt = self.meeting
        if fast:
            self.dump_meeting(mt["cid"], mt["m"], mt["m"]["lines"][mt["idx"]:])
        self.bots["director"].send(mt["cid"], f"📞 {mt['m']['name']}结束。")
        self.meeting = None
        self.set_clock(max(self.sim_min, min(mt["end_min"], to_min(self.half_end or "17:25"))))
        self.last_tick = time.time()

    def pause(self, kind: str, why: str) -> None:
        if self.paused == "hard" or self.forcing or not self.half_end:
            return
        self.paused = kind
        where = "去群里回复" if kind.startswith("soft:group") else "去私聊里回复"
        self.tell(f"⏸ {to_hm(self.sim_min)} {why}，时间已暂停。{where}后会自动继续（不想回就发“继续”；想多停一会儿发“暂停”）。")

    def resume(self, why: str = "", quiet: bool = False) -> None:
        self.paused = None
        self.last_tick = time.time()
        if not quiet:
            nxt = ""
            if self.pending:
                wait = (to_min(self.pending[0]["time"]) - self.sim_min) / self.speed      # 现实分钟
                nxt = f"，下一条消息 {self.pending[0]['time']}"
                if wait >= 1:
                    nxt += f"（约 {wait:.0f} 分钟后，不想等就发“快进”）"
            self.tell(f"▶️ {to_hm(self.sim_min)} 时间继续{why}{nxt}。")

    # ---------- 载入一个时段

    def load_half(self, day: int, phase: str) -> None:
        d = config.OUTPUT_DIR / f"D{day}"
        msgs = json.loads((d / f"{phase}.json").read_text(encoding="utf-8"))
        pf = d / f"{phase}-private.json"
        privates = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else []
        sent = set(self.ids.get("released", {}).get(f"D{day}-{phase}", []))
        items = [dict(m) for m in msgs] + [dict(p, kind="private") for p in privates]
        for i, m in enumerate(items):
            m["_id"] = f"{m['kind']}-{m['time']}-{m.get('sender', '')}-{i}"
        self.pending = sorted((m for m in items if m["_id"] not in sent), key=lambda m: m["time"])
        self.half_end = HALF[phase][1]
        self.end_notified = False
        self._released_key = f"D{day}-{phase}"

    def restore_half(self, s: dict) -> None:
        phase = "morning" if s.get("half") == "am" else "afternoon"
        if (config.OUTPUT_DIR / f"D{s['sim_day']}" / f"{phase}.json").exists():
            self.load_half(s["sim_day"], phase)
            self.paused = "hard"

    # ---------- 收到消息

    def handle(self, ev: dict) -> None:
        if ev["sender_type"] != "user" or ev["message_id"] in self.seen:
            return
        self.seen = (self.seen + [ev["message_id"]])[-500:]
        app = ev["app"]
        first = ev["chat_type"] == "p2p" and app not in self.ids["player"]
        if ev["chat_type"] == "p2p":
            self.ids["player"][app] = {"open_id": ev["open_id"], "chat_id": ev["chat_id"]}
            save_ids(self.ids)
        if first and app != "director":       # 第一次私聊同事机器人是在"打招呼登记"，不算游戏里的私聊
            name = NAMES.get(app, "这个机器人")
            return self.bots[app].send(ev["chat_id"], f"（{name}的机器人已连接。游戏开始后，直接在这里私聊{name}就行。）")
        text = ev["content"].get("text") or post_text(ev["content"])
        for mt in ev["mentions"]:
            text = text.replace(mt["key"], "@" + mt["name"])
        if not text:
            text = "（发了一条非文字消息）"
        print(f"→ 收到 [{app}/{ev['chat_type']}] {text[:60]}")
        if ev["chat_type"] == "p2p" and app == "director":
            self.command(text.strip())
        elif ev["chat_type"] == "p2p":
            self.private(app, text)
        else:
            self.group(ev["chat_id"], text, [m["name"] for m in ev["mentions"]])

    def command(self, t: str) -> None:
        s = load()
        if t in ("帮助", "help", "?", "？", "你好"):
            return self.tell(HELP.format(speed=self.speed))
        if t == "上班":
            return self.start_day()
        if t in ("中午", "下班", "确定中午", "确定下班"):
            want = t[-2:]
            ahead = [m for m in self.pending if m["time"] < ("12:00" if want == "中午" else "17:30")]
            if ahead and not t.startswith("确定") and s["phase"] == "day":
                return self.tell(f"这个时段还有 {len(ahead)} 条消息没到（下一条 {ahead[0]['time']}）。"
                                 f"现在结束会一次发完，你来不及回应。\n继续玩发“继续”；确实要结束发“确定{want}”。")
            return self.noon() if want == "中午" else self.end()
        if t == "暂停":
            self.paused = "hard"
            return self.tell(f"⏸ 已暂停在 {to_hm(self.sim_min)}。发“继续”恢复。")
        if t == "继续":
            if s["phase"] != "day":
                return self.tell("现在是下班时间。发“上班”开始新的一天。")
            if self.meeting and self.meeting["waiting"]:
                self.meeting["waiting"] = False
                self.meeting["next_at"] = time.time()
                if self.paused != "hard":
                    return self.tell("好，会议继续。")
            return self.resume()
        if t.startswith("快进"):
            return self.fast_forward(t[2:].strip())
        if t.startswith("速度"):
            try:
                self.speed = max(1.0, float(t[2:].strip()))
                return self.tell(f"速度：现实 1 分钟 = 模拟 {self.speed:g} 分钟。")
            except ValueError:
                return self.tell("写成“速度 20”这样。")
        if t == "状态":
            when = {"am": "上午", "pm": "下午"}.get(s.get("half"), "") if s["phase"] == "day" else "下班了"
            nxt = self.pending[0]["time"] if self.pending else "无"
            if self.meeting:
                nxt = f"正在开{self.meeting['m']['name']}（第 {self.meeting['idx']}/{len(self.meeting['m']['lines'])} 句）"
            return self.tell(f"D{s['sim_day']} {when} {to_hm(self.sim_min)}｜{'暂停中' if self.paused else '时间在走'}"
                             f"｜还有 {len(self.pending)} 条消息没到（下一条 {nxt}）｜速度 {self.speed:g}｜今天接口调用约 {Live.api_calls} 次")
        if t in ("核对", "开启核对", "关闭核对"):
            return self.tell("AI 核对搬家了：私聊「AI 进度助手」发“核对”或“开启自动”。")
        m = re.match(r"^(记录|补记)[:：]\s*(.+)", t, re.S)
        if m:
            return self.note(m[2])
        self.tell("没看懂。发“帮助”看命令。")

    def note(self, text: str) -> None:
        s = load()
        if s["phase"] != "day":
            return self.tell("现在是下班时间，补记请在明天上班后发，或者直接写进 logs/actions 里的日志。")
        day, clock = s["sim_day"], to_hm(self.sim_min)
        add_log(s, day, f"- [{clock}] 记录｜{text.splitlines()[0][:200]}")
        url = re.search(r"https?://\S+", text)
        doc = read_doc(self.bots["director"], url[0]) if url else ""
        if doc or len(text) > 200:
            add_log(s, day, f"### [{clock}] {text.splitlines()[0][:60]}\n{doc or text}\n", section="## 痛点笔记")
        self.tell(f"已记录（{clock}）" + ("，文档正文也读到了。" if doc else "。"))

    def fast_forward(self, arg: str) -> None:
        if not self.half_end:
            return self.tell("现在没有进行中的时段。")
        if self.meeting:
            self.end_meeting(fast=True)
            if not arg:
                return self.tell(f"⏩ 会议快进完了，现在 {to_hm(self.sim_min)}。")
        if arg:
            c = director.norm_clock(arg)
            if not c:
                return self.tell("写成“快进 10:30”这样。")
            target = min(to_min(c), to_min(self.half_end))
        else:
            target = to_min(self.pending[0]["time"]) if self.pending else to_min(self.half_end)
        was = self.paused
        self.paused = None
        self.release_until(target)
        if self.paused is None and was == "hard":
            self.paused = "hard"
        self.tell(f"⏩ 现在 {to_hm(self.sim_min)}。")

    # ---------- 私聊 / 群聊

    def private(self, app: str, text: str) -> None:
        from . import chat
        s = load()
        key = app
        if app == "others":
            m = re.match(r"^@?(\S{2,3}?)[\s:：,，]+(.+)", text, re.S)
            key = KEY_BY_NAME.get(m[1], "") if m else ""
            if not key or key in self.bots:
                return self.bots["others"].send(self.player_chat("others"), "（这个机器人代表没有单独机器人的同事。开头写名字，比如“孙磊：物料清单什么时候给？”）")
            text = m[2]
        bot, prefix = self.bot_for(key)
        cid = self.player_chat(app)
        if s["phase"] != "day":
            return bot.send(cid, "（下班时间，对方没回。发“上班”给导演开始新的一天后再聊。）")
        name = NAMES[key]
        self.refresh_table()
        s = load()
        day = s["sim_day"]
        s["clock"] = to_hm(self.sim_min)
        hist = chat.load_history(day, name)
        hist.append({"role": "user", "clock": s["clock"], "text": text, "via": "feishu"})
        chat.save_history(day, name, hist)
        r = chat.reply(s, day, key, hist)
        hist.append({"role": "assistant", "clock": s["clock"], "text": r})
        chat.save_history(day, name, hist)
        r = artifacts.scrub(r, False)
        for part in [p for p in r.split("\n\n") if p.strip()]:     # 像真人一样分几条发
            bot.send(cid, f"{name}：{part}" if prefix else part)
        if self.paused == f"soft:p2p:{key}":
            self.resume()

    def group(self, chat_id: str, text: str, mentioned: list[str]) -> None:
        from . import chat
        s = load()
        g = next((n for n, c in self.ids["chats"].items() if c == chat_id), "")
        if not g:
            self.resolve_chats()
            g = next((n for n, c in self.ids["chats"].items() if c == chat_id), "")
        if not g:
            return
        day, clock = s["sim_day"], to_hm(self.sim_min)
        config.FEISHU_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.FEISHU_LOG_DIR / f"D{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, "clock": clock, "group": g, "text": text}, ensure_ascii=False) + "\n")
        token = urlparse(config.FEISHU_BITABLE_URL).path.rstrip("/").split("/")[-1] if config.FEISHU_BITABLE_URL else ""
        if token and token in text and not s.get("table_shared"):
            s["table_shared"] = day                # 任务表链接发到群里了：从此大家都能看到这张表
            save(s)
            self.bitable_check(s, "公告")
            s = load()
        if s["phase"] != "day":
            return
        if self.meeting and self.meeting["cid"] == chat_id and self.meeting["waiting"]:
            return self.meeting_reply(text)
        waiting_on = self.paused.split(":", 3)[3] if (self.paused or "").startswith(f"soft:group:{g}:") else ""
        responders = list(mentioned)
        if not mentioned:                       # 没 @ 谁：按内容判断谁会接（刚 @你的人优先），也可能没人接
            responders = self.who_replies(s, g, text, waiting_on)
        replying = not mentioned
        for name in responders:
            key = KEY_BY_NAME.get(name)
            if not key or key == "player":
                continue
            how = f"在群「{g}」里说了一句（没有 @ 人，你判断这话跟你有关，来接一下）" if replying else f"在群「{g}」里 @你"
            hist = [{"role": "user", "clock": clock, "text": f"（项目助理{how}）{text}"}]
            s["clock"] = clock
            r = artifacts.scrub(chat.reply(s, day, key, hist), False)
            bot, prefix = self.bot_for(key)
            bot.send(chat_id, f"{name}：{r}" if prefix else r)
            self.last_speaker[g] = (name, self.sim_min)
            with open(config.FEISHU_LOG_DIR / f"D{day}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"day": day, "clock": clock, "group": g, "text": r, "npc": name}, ensure_ascii=False) + "\n")
        if (self.paused or "").startswith(f"soft:group:{g}"):
            self.resume()

    def who_replies(self, s: dict, g: str, text: str, waiting_on: str) -> list[str]:
        from . import schemas
        members = sorted(director.GROUP_MEMBERS[g])
        owners = {}
        for t in s["tasks"]:
            if t.get("exists", True) and (t["project"] != "B" or t["id"].endswith("-文")):
                for o in t["owners"]:
                    if o in NAMES and NAMES[o] in members:
                        owners.setdefault(NAMES[o], []).append(t["name"].replace("（文案）", ""))
        recent = f"{self.last_speaker[g][0]}（{to_hm(self.last_speaker[g][1])}）" if g in self.last_speaker else ""
        p = (f"群「{g}」里，项目助理刚发了一句（没有 @ 任何人）：「{text}」\n"
             f"群成员：{'、'.join(members)}\n各人负责的事：" + "；".join(f"{k}：{'、'.join(v[:8])}" for k, v in owners.items())
             + f"\n刚才最后一个说话的：{recent or '无'}" + (f"\n刚才 @项目助理 的人：{waiting_on}" if waiting_on else "")
             + f"\n最近群聊：\n{director.fmt_msgs([m for m in director.recent_msgs(s['sim_day'], 12) if m.get('group') == g])}"
             + "\n\n真实职场里，谁会接这句话？规则：问到某件事，由负责这件事或明显知道答案的人回答；点名提到的人通常会回；"
               "是在回复刚才 @项目助理 的人，就由那个人回；纯闲聊、通知、自言自语可以没人回。最多 2 人。"
               "输出 JSON：{\"who\": [名字...], \"reason\": \"一句话\"}")
        stub = lambda: schemas.Responders(who=[waiting_on] if waiting_on else [])     # noqa: E731
        try:
            r = llm.json_call("群聊谁来接话", p, schemas.Responders, stub)
        except Exception:          # noqa: BLE001
            r = stub()
        who = [w for w in r.who if w in members and w != "项目助理"][:2]
        print(f"  （谁接话：{who or '没人'}｜{r.reason}）")
        return who

    # ---------- 一天的三个阶段

    def refresh_table(self) -> None:
        s = load()
        if s.get("table_shared") and time.time() - getattr(self, "_table_at", 0) > 300 and s["phase"] == "day":
            self._table_at = time.time()
            self.bitable_check(s, "查看")

    def bitable_check(self, s: dict, label: str) -> None:
        self._table_at = time.time()
        if not config.FEISHU_BITABLE_URL:
            return
        snap = config.STATE_DIR / "bitable-latest.json"
        try:
            new = read_bitable(self.bots["director"], config.FEISHU_BITABLE_URL)
        except Exception as e:      # noqa: BLE001
            return self.tell(f"（没读到任务表：{e}）")
        old = json.loads(snap.read_text(encoding="utf-8")) if snap.exists() else None
        snap.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
        (config.STATE_DIR / f"bitable-D{s['sim_day']}-{label}.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
        if old is None:
            return
        changes = diff_bitable(old, new)
        if changes:
            add_log(s, s["sim_day"], f"- [{to_hm(self.sim_min)}] 任务表（自动比对，{label}前）｜" + "；".join(changes)[:3000])
            self.tell(f"📋 任务表有 {len(changes)} 处修改，已记进日志。")

    def flush_half(self) -> None:
        """把这个时段还没到的消息一次发完（玩家提前发了"中午"/"下班"）。"""
        if self.meeting:
            self.end_meeting(fast=True)
        if self.pending:
            self.tell(f"先把这个时段剩下的 {len(self.pending)} 条消息发完……")
            self.forcing = True
            try:
                self.release_until(to_min(self.half_end))
            finally:
                self.forcing = False
        self.pending = []

    def start_day(self) -> None:
        s = load()
        if s["phase"] == "day":
            when = "上午" if s.get("half") == "am" else "下午"
            return self.tell(f"D{s['sim_day']} {when}已经开始了（模拟时间 {to_hm(self.sim_min)}）。发“继续”接着走时间；这个时段做完了发“{'中午' if when == '上午' else '下班'}”。")
        if s["sim_day"] >= 15:
            return self.tell("模拟已经结束。")
        self.tell(f"导演正在准备 D{s['sim_day'] + 1} 上午……（1–3 分钟）")
        if s["sim_day"] == 0:
            self.bitable_check(s, "开局")          # 开局拍一张任务表快照，之后只记变化
        director.start_day(s)
        s = load()
        day = s["sim_day"]
        ensure_log(s, day)
        sched = "\n".join(f"· {x}" for x in engine.fixed_schedule(s, day))
        self.load_half(day, "morning")
        self.sim_min = to_min("09:00")
        self.set_clock(self.sim_min)
        self.paused = None
        self.last_tick = time.time()
        self.tell(f"☀️ D{day} · {date_str(s, day)} 上午开始（模拟时间 09:00，速度 {self.speed:g}）\n今日日程：\n{sched}\n\n"
                  f"消息会陆续到。发“暂停”随时停住，发“帮助”看命令。")

    def noon(self) -> None:
        s = load()
        if s["phase"] != "day" or s.get("half") != "am":
            return self.tell("现在不是上午。")
        self.flush_half()
        self.bitable_check(s, "中午")
        self.tell("导演正在结算上午、准备下午……（1–3 分钟）")
        director.noon_day(load())
        s = load()
        self.load_half(s["sim_day"], "afternoon")
        self.sim_min = to_min("12:00")
        self.set_clock(self.sim_min)
        self.paused = None
        self.last_tick = time.time()
        self.tell_recap(s["sim_day"], "noon")
        self.tell("🌤 下午开始（12:00）。")

    def tell_recap(self, day: int, half: str) -> None:
        f = config.OUTPUT_DIR / f"D{day}" / f"recap-{half}.txt"
        if f.exists():
            self.tell(f.read_text(encoding="utf-8"))

    def end(self) -> None:
        s = load()
        if s["phase"] != "day":
            return self.tell("今天还没开始。")
        if s.get("half") == "am":
            return self.tell("还在上午，先发“中午”。")
        self.flush_half()
        self.bitable_check(s, "下班")
        self.tell("导演正在评估今天、生成日报和晚上的消息……（1–3 分钟）")
        director.end_day(load())
        s = load()
        day = s["sim_day"]
        self.half_end = ""
        msgs = json.loads((config.OUTPUT_DIR / f"D{day}" / "evening.json").read_text(encoding="utf-8"))
        for m in sorted(msgs, key=lambda m: m["time"]):
            self.post(dict(m))
            time.sleep(0.3)
        self.paused = "hard"
        try:
            n = tools.save_reports(self.bots["director"], s, day, msgs)
            if n:
                self.tell(f"📋 {n} 份日报已经写进多维表格「日报」表。")
        except Exception as e:      # noqa: BLE001
            print(f"  ✗ 日报写表失败：{e}")
        ex = config.OUTPUT_DIR / f"D{day}" / "evening-extra.json"
        weekly = json.loads(ex.read_text(encoding="utf-8")).get("weekly_reply", "") if ex.exists() else ""
        if weekly:
            bot, prefix = self.bot_for("wangli")
            cid = self.player_chat(bot.key)
            if cid:
                bot.send(cid, ("王丽：" if prefix else "") + "周报我看了\n" + weekly)
            else:
                self.tell("王丽对周报的回复：\n" + weekly)
        write_clock(s, "17:30", working=False)
        self.tell_recap(day, "evening")
        self.tell(f"🌙 D{day} 结束。今天接口调用约 {Live.api_calls} 次。"
                  + ("发“上班”开始下一天。" if day < 15 else "模拟结束！终端运行 uv run sim report 生成结局报告。"))


def serve(speed: float) -> None:
    try:
        import lark_oapi  # noqa: F401
    except ImportError:
        raise SystemExit("缺少飞书 SDK。运行：uv sync --extra feishu") from None
    Live(speed).run()


def check() -> None:
    """检查每个机器人的配置：能不能拿到令牌、在哪些群里、你有没有私聊过它、能不能读任务表。"""
    apps = app_config()
    if not apps:
        raise SystemExit("还没有配置任何机器人（.env 里的 FEISHU_BOT_…）。见 docs/飞书配置指南.md")
    ids = load_ids()
    groups = list(config.GROUP_KEYS)
    for k, v in apps.items():
        b = Bot(k, *v)
        try:
            chats = b.chats()
            inn = [g for g in groups if g in chats]
            lack = [g for g in groups if g not in chats]
            p2p = "✓ 你私聊过" if ids["player"].get(k) else "✗ 还没私聊过（发一句“你好”）"
            print(f"{NAMES.get(k, k):6} ✓ 连接正常｜在群：{'、'.join(inn) or '无'}{('｜缺：' + '、'.join(lack)) if lack else ''}｜{p2p}")
        except Exception as e:      # noqa: BLE001
            print(f"{NAMES.get(k, k):6} ✗ {e}")
    if config.FEISHU_BITABLE_URL and "director" in apps:
        try:
            rows = read_bitable(Bot("director", *apps["director"]), config.FEISHU_BITABLE_URL)
            print(f"任务表   ✓ 能读到 {len(rows)} 行")
        except Exception as e:      # noqa: BLE001
            print(f"任务表   ✗ {e}")
    missing = [NAMES[k] for k in PEOPLE if k not in apps]
    if missing:
        print(f"没有单独机器人的同事：{'、'.join(missing)}（由“其他同事”或导演机器人代发，消息前带名字）")
