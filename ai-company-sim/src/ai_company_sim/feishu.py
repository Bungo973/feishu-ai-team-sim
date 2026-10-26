"""飞书：用自定义机器人按时间顺序发群消息；用自建应用（长连接）采集你在群里的发言。"""

import base64
import hashlib
import hmac
import json
import os
import time

import httpx

from . import config
from .state import KEY_BY_NAME, load, save

MAX_BYTES = 15000   # 自定义机器人请求体上限 20KB，留余量


def sign(secret: str, ts: int) -> str:
    string_to_sign = f"{ts}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def post(url: str, secret: str, text: str) -> None:
    body: dict = {"msg_type": "text", "content": {"text": text}}
    if secret:
        ts = int(time.time())
        body.update({"timestamp": str(ts), "sign": sign(secret, ts)})
    r = httpx.post(url, json=body, timeout=15)
    data = r.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(f"飞书返回错误：{data}")


def at_player(text: str, state: dict) -> str:
    uid = config.FEISHU_PLAYER_ID or state.get("player_open_id", "")
    if not uid:
        return text
    return text.replace("@项目助理", f'<at user_id="{uid}">项目助理</at>')


def chunks(text: str) -> list[str]:
    out, cur = [], ""
    for line in text.split("\n"):
        if len((cur + line).encode()) > MAX_BYTES:
            out.append(cur)
            cur = ""
        cur += line + "\n"
    return out + [cur] if cur.strip() else out


def send_phase(day: int, phase: str, dry: bool = False) -> int:
    state = load()
    f = config.OUTPUT_DIR / f"D{day}" / f"{phase}.json"
    if not f.exists():
        raise SystemExit(f"没有 D{day} {phase} 的消息。")
    msgs = sorted(json.loads(f.read_text(encoding="utf-8")), key=lambda m: m["time"])
    sent_flag = f.with_suffix(".sent")
    if sent_flag.exists() and not dry:
        print(f"D{day} {phase} 已经发过了（删除 {sent_flag.name} 可以重发）。")
        return 0
    n = 0
    for m in msgs:
        if m["kind"] == "meeting":
            key = "system"
            text = f"【{m['time']} {m['name']} · 文字记录】\n" + "\n".join(f"{l['speaker']}：{l['text']}" for l in m["lines"])
        else:
            key = KEY_BY_NAME.get(m["sender"], "system")
            text = f"[{m['time']}] {m['text']}"
        url, secret, fallback = config.webhook_for(m["group"], key if m["kind"] == "msg" else "system")
        if fallback and m["kind"] == "msg":
            text = f"[{m['time']}] {m['sender']}：{m['text']}"
        if not url:
            raise SystemExit(f"群「{m['group']}」没有配置机器人。见 README 第 3 步，在 .env 里填 FEISHU_WEBHOOK_…")
        for part in chunks(at_player(text, state)):
            if dry:
                print(f"→ {m['group']} / {key}{'（DEFAULT）' if fallback else ''}：{part[:60]}…")
            else:
                post(url, secret, part)
                time.sleep(config.FEISHU_SEND_INTERVAL)
            n += 1
    if not dry:
        sent_flag.write_text(str(time.time()))
    return n


# ------------------------------------------------------------------ 采集群消息（进阶，需要自建应用）

def listen(reply: bool = False) -> None:
    try:
        import lark_oapi as lark
    except ImportError:
        raise SystemExit("缺少飞书 SDK。运行：uv sync --extra feishu") from None
    if not (config.FEISHU_APP_ID and config.FEISHU_APP_SECRET):
        raise SystemExit("没有配置 FEISHU_APP_ID / FEISHU_APP_SECRET。见 README 第 5 步。")
    chat_map = {}
    for g, k in config.GROUP_KEYS.items():
        cid = os.getenv(f"FEISHU_CHAT_{k}", "")
        if cid:
            chat_map[cid] = g

    def on_msg(data) -> None:
        ev = data.event
        if ev.sender.sender_type != "user":
            return
        msg = ev.message
        try:
            content = json.loads(msg.content)
        except (TypeError, json.JSONDecodeError):
            content = {}
        text = content.get("text") or json.dumps(content, ensure_ascii=False)
        for mt in msg.mentions or []:
            text = text.replace(mt.key, "@" + mt.name)
        group = chat_map.get(msg.chat_id)
        if not group:
            print(f"（未知群 chat_id={msg.chat_id}。把它填进 .env 的 FEISHU_CHAT_TEAM 或 FEISHU_CHAT_LAUNCH）")
            group = "品牌项目组"
        state = load()
        if not state.get("player_open_id") and ev.sender.sender_id.open_id:
            state["player_open_id"] = ev.sender.sender_id.open_id
            save(state)
        rec = {"day": state["sim_day"], "clock": state.get("clock", ""), "group": group, "text": text,
               "real_time": time.strftime("%H:%M:%S"), "message_id": msg.message_id}
        config.FEISHU_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.FEISHU_LOG_DIR / f"D{state['sim_day']}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[D{state['sim_day']} {rec['clock']}][{group}] 你：{text}")
        if reply and state["phase"] == "day":
            group_reply(state, group, text)

    handler = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(on_msg).build()
    cli = lark.ws.Client(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, event_handler=handler, log_level=lark.LogLevel.WARNING)
    print("正在监听飞书群消息……（Ctrl+C 停止）")
    cli.start()


def group_reply(state: dict, group: str, text: str) -> None:
    """你在群里 @某个同事 时，让这个同事用自己的机器人回一句（实验功能）。"""
    from .chat import reply as chat_reply
    from .state import NAMES
    for key, name in NAMES.items():
        if key == "player" or f"@{name}" not in text:
            continue
        hist = [{"role": "user", "clock": state.get("clock", ""), "text": f"（在群「{group}」里 @你）{text}"}]
        r = chat_reply(state, state["sim_day"], key, hist)
        url, secret, fallback = config.webhook_for(group, key)
        if url:
            post(url, secret, f"{name}：{r}" if fallback else r)
            print(f"  ↳ {name}：{r}")
            with open(config.FEISHU_LOG_DIR / f"D{state['sim_day']}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"day": state["sim_day"], "clock": state.get("clock", ""), "group": group,
                                    "text": r, "npc": name}, ensure_ascii=False) + "\n")
