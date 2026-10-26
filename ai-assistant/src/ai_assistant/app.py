"""AI 进度助手的飞书机器人：私聊它随便聊（查进度、问情况、让它改表、让它核对），或者打开自动推送（每天中午、下班各一次）。"""
from __future__ import annotations

import json
import threading
import time

import lark_oapi as lark

from . import agent, check, clock, config, feishu

HELP = """我是 AI 进度助手，项目助理自己搭的小工具。直接跟我说话就行，比如：
· “核对一下” / “今天有什么要催的？”
· “A4 现在什么情况？群里谁提过？”
· “A4 王丽确认过了，标成已完成”（改错了说“撤销”）
我能看的只有：我所在群的聊天记录、「任务进度」表、「日报」表（不读任何人的私聊）。能改的只有任务表。

快捷命令：开启自动 / 关闭自动（每天中午和下班各推一次核对）；新对话（清空我记得的聊天）"""

busy = threading.Lock()
seen: list[str] = []


def load() -> dict:
    if config.DATA_FILE.exists():
        return json.loads(config.DATA_FILE.read_text(encoding="utf-8"))
    return {"chat_id": "", "auto": False, "pushed": []}


def save(d: dict) -> None:
    config.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.DATA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def talk(chat_id: str, text: str) -> None:
    with busy:       # 一次只处理一句，按顺序来
        try:
            agent.chat(text, lambda s: feishu.send(chat_id, s))
        except Exception as e:      # noqa: BLE001
            feishu.send(chat_id, f"（出错了：{e}）")


def push_check(chat_id: str, label: str) -> None:
    with busy:
        try:
            feishu.send(chat_id, "🤖 到点了，正在做 AI 进度核对……（约半分钟）")
            text = check.run(label)
            feishu.send(chat_id, text)
            agent.remember("assistant", text)
        except Exception as e:      # noqa: BLE001
            feishu.send(chat_id, f"（核对没跑成：{e}）")


def on_message(data) -> None:
    m, s = data.event.message, data.event.sender
    if m.message_id in seen or m.chat_type != "p2p" or s.sender_type != "user":
        return
    seen.append(m.message_id)
    d = load()
    d["chat_id"] = m.chat_id
    save(d)
    try:
        text = json.loads(m.content or "{}").get("text", "").strip()
    except json.JSONDecodeError:
        text = ""
    if text in ("开启自动", "关闭自动"):
        d["auto"] = text == "开启自动"
        save(d)
        return feishu.send(m.chat_id, "好，每天中午和下班各推送一次核对。" if d["auto"] else "好，不再自动推送。")
    if text == "新对话":
        agent.reset()
        return feishu.send(m.chat_id, "好，之前聊的我都忘了。")
    if text in ("", "你好", "帮助", "help"):
        return feishu.send(m.chat_id, HELP)
    threading.Thread(target=talk, args=(m.chat_id, text), daemon=True).start()


def due(now: dict) -> tuple[str, str] | None:
    """时钟走到了该推送的点：返回（记号, 标签）。"""
    if now["working"] and now["time"] >= "12:00":
        return f"{now['date']}-中午", "中午"
    if not now["working"]:
        return f"{now['date']}-下班", "下班"
    return None


def watch() -> None:
    """看时钟，到点自动推送。助手刚启动时已经过了的点不补推。"""
    first = True
    while True:
        try:
            now = clock.now()
            hit = due(now) if now else None
            d = load()
            if hit and hit[0] not in d["pushed"]:
                d["pushed"] = (d["pushed"] + [hit[0]])[-60:]
                save(d)
                if d["auto"] and d["chat_id"] and not first:
                    push_check(d["chat_id"], hit[1])
            first = False
        except Exception as e:      # noqa: BLE001
            print(f"[助手] 看时钟出错：{e}")
        time.sleep(3)


def main() -> None:
    if not (config.FEISHU_APP_ID and config.FEISHU_APP_SECRET):
        raise SystemExit("[助手] .env 里没填 FEISHU_APP_ID / FEISHU_APP_SECRET")
    threading.Thread(target=watch, daemon=True).start()
    handler = lark.EventDispatcherHandler.builder("", "").register_p2_im_message_receive_v1(on_message).build()
    print("[助手] 已连接飞书。私聊「AI 进度助手」直接说话就行。")
    try:
        lark.ws.Client(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, event_handler=handler,
                       log_level=lark.LogLevel.WARNING).start()
    except KeyboardInterrupt:
        pass
