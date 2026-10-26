"""飞书读写：助手只有这一个数据来源。"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest, ListAppTableRequest
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody, ListChatRequest, ListMessageRequest

from . import config

client = lark.Client.builder().app_id(config.FEISHU_APP_ID).app_secret(config.FEISHU_APP_SECRET) \
    .log_level(lark.LogLevel.WARNING).build()


def send(chat_id: str, text: str) -> None:
    r = client.im.v1.message.create(CreateMessageRequest.builder().receive_id_type("chat_id").request_body(
        CreateMessageRequestBody.builder().receive_id(chat_id).msg_type("text")
        .content(json.dumps({"text": text}, ensure_ascii=False)).build()).build())
    if not r.success():
        print(f"[助手] 发消息失败：{r.code} {r.msg}")


# ------------------------------------------------------------------ 群聊

def groups() -> dict[str, str]:
    """助手所在的群：{群名: chat_id}。"""
    out, token = {}, None
    while True:
        b = ListChatRequest.builder().page_size(100)
        if token:
            b = b.page_token(token)
        r = client.im.v1.chat.list(b.build())
        if not r.success():
            raise RuntimeError(f"读群列表失败：{r.code} {r.msg}")
        out |= {c.name: c.chat_id for c in r.data.items or []}
        if not r.data.has_more:
            return out
        token = r.data.page_token


def _body(m) -> str:
    try:
        c = json.loads(m.body.content or "{}")
    except (json.JSONDecodeError, AttributeError):
        return ""
    if m.msg_type == "text":
        t = c.get("text", "")
    elif m.msg_type == "post":
        blocks = c.get("content") or next((v.get("content") for v in c.values() if isinstance(v, dict)), []) or []
        t = "\n".join("".join(x.get("text", "") for x in line) for line in blocks)
    elif m.msg_type in ("image", "file", "media", "sticker"):
        t = {"image": "[图片]", "file": f"[文件 {c.get('file_name', '')}]", "media": "[视频]", "sticker": "[表情]"}[m.msg_type]
    else:
        return ""
    for x in m.mentions or []:
        t = t.replace(x.key, f"@{x.name}")
    return t.strip()


def messages(chat_id: str, start: int, end: int) -> list[dict]:
    """群里 [start, end] 真实时间（秒）内的消息：{ts, who, text}。"""
    out, token = [], None
    while True:
        b = ListMessageRequest.builder().container_id_type("chat").container_id(chat_id) \
            .start_time(str(start)).end_time(str(end)).sort_type("ByCreateTimeAsc").page_size(50).with_sender_name(True)
        if token:
            b = b.page_token(token)
        r = client.im.v1.message.list(b.build())
        if not r.success():
            raise RuntimeError(f"读群消息失败：{r.code} {r.msg}")
        for m in r.data.items or []:
            text = _body(m)
            if not text or m.deleted:
                continue
            s = m.sender
            who = "我" if s.sender_type == "user" else (getattr(s, "sender_name", "") or "机器人")
            if who in config.IGNORE_SENDERS:
                continue
            if who in config.PROXY_SENDERS:           # 代发机器人：名字写在正文开头"孙磊：……"
                g = re.match(r"^(\S{2,4})：(.*)", text, re.S)
                if g:
                    who, text = g[1], g[2]
            out.append({"ts": int(m.create_time) / 1000, "who": who, "text": text})
        if not r.data.has_more:
            return out
        token = r.data.page_token


# ------------------------------------------------------------------ 多维表格

def _app() -> str:
    return urlparse(config.FEISHU_BITABLE_URL).path.rstrip("/").split("/")[-1]


def cell(v) -> str:
    if isinstance(v, list):
        return "、".join(x for x in (cell(y) for y in v) if x)
    if isinstance(v, dict):
        if "text" in v and isinstance(v["text"], str):
            return v["text"]
        if "text_arr" in v:
            return "、".join(v["text_arr"])
        return str(v.get("name") or v.get("link") or cell(v.get("value")) or "")
    if isinstance(v, bool):
        return "是" if v else ""
    if isinstance(v, (int, float)) and v > 1e11:      # 日期字段是毫秒时间戳
        import datetime
        return datetime.datetime.fromtimestamp(v / 1000).strftime("%Y-%m-%d")
    return "" if v is None else str(v)


def table_id(name: str) -> str | None:
    if name == config.TASK_TABLE:
        tid = parse_qs(urlparse(config.FEISHU_BITABLE_URL).query).get("table", [""])[0]
        if tid:
            return tid
    r = client.bitable.v1.app_table.list(ListAppTableRequest.builder().app_token(_app()).page_size(100).build())
    if not r.success():
        raise RuntimeError(f"读多维表格失败：{r.code} {r.msg}（多维表格里要“添加文档应用”选 AI 进度助手）")
    return next((t.table_id for t in r.data.items or [] if t.name == name), None)


def table(name: str) -> list[dict] | None:
    """读一张表：[{record_id, fields: {列: 文字}, modified: 真实秒}]。没有这张表返回 None。"""
    tid = table_id(name)
    if not tid:
        return None
    out, token = [], None
    while True:
        b = ListAppTableRecordRequest.builder().app_token(_app()).table_id(tid).page_size(500).automatic_fields(True)
        if token:
            b = b.page_token(token)
        r = client.bitable.v1.app_table_record.list(b.build())
        if not r.success():
            raise RuntimeError(f"读「{name}」失败：{r.code} {r.msg}")
        out += [{"record_id": x.record_id, "fields": {k: cell(v) for k, v in (x.fields or {}).items()},
                 "modified": (x.last_modified_time or 0) / 1000}
                for x in r.data.items or []]
        if not r.data.has_more:
            return out
        token = r.data.page_token
