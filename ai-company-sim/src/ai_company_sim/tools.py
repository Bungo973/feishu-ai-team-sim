"""工具 2 结构化日报：同事的日报写进多维表格「日报」表（你搭的表单 + 17:30 提醒生效后，也就是 I2 生效后）。

工具 3 AI 进度核对不在这里：它是单独的项目 ../ai-assistant，不读模拟器的任何东西，只读飞书和 ../shared/clock.jsonl。
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from . import config
from .state import date_str

REPORT_TABLE = "日报"
TASK_TABLE = "任务进度"
CODE = re.compile(r"\b([ABC]\d{1,2})\b")


# ------------------------------------------------------------------ 多维表格

def _app() -> str:
    return urlparse(config.FEISHU_BITABLE_URL).path.rstrip("/").split("/")[-1]


def task_table_id(bot) -> str:
    """任务表：.env 里链接的 ?table= 那张（表名随你起）；链接里没带就找叫「任务进度」的表。"""
    tid = parse_qs(urlparse(config.FEISHU_BITABLE_URL).query).get("table", [""])[0]
    return tid or tables(bot).get(TASK_TABLE, "")


def field_names(bot, table_id: str) -> set[str]:
    from lark_oapi.api.bitable.v1 import ListAppTableFieldRequest
    r = bot.client.bitable.v1.app_table_field.list(
        ListAppTableFieldRequest.builder().app_token(_app()).table_id(table_id).page_size(100).build())
    return {f.field_name for f in (r.data.items or [])} if r.success() else set()


def tables(bot) -> dict[str, str]:
    from lark_oapi.api.bitable.v1 import ListAppTableRequest
    r = bot.client.bitable.v1.app_table.list(ListAppTableRequest.builder().app_token(_app()).build())
    return {t.name: t.table_id for t in (r.data.items or [])} if r.success() else {}


def _text(v) -> str:
    if isinstance(v, list):
        return "、".join(_text(x) for x in v if _text(x))
    if isinstance(v, dict):
        return str(v.get("text") or v.get("name") or v.get("link") or "")
    return "" if v is None else str(v)


def _records(bot, table_id: str) -> list:
    from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest
    out, token = [], None
    while True:
        b = ListAppTableRecordRequest.builder().app_token(_app()).table_id(table_id).page_size(500)
        if token:
            b = b.page_token(token)
        r = bot.client.bitable.v1.app_table_record.list(b.build())
        if not r.success():
            raise RuntimeError(f"读多维表格失败：{r.code} {r.msg}")
        out += r.data.items or []
        if not r.data.has_more:
            return out
        token = r.data.page_token


REPORT_FIELDS = [  # (字段名, 类型)；手写的只有 今日完成 / 进度 / 明日计划 / 卡点 四项
    ("提交人", 3), ("模拟日", 1), ("关联任务", 18), ("今日完成", 1), ("进度", 1), ("明日计划", 1), ("卡点", 1), ("交付物链接", 15)]


def setup_report_table(bot) -> str:
    """建「日报」表（已有就跳过）。返回表 ID。"""
    from lark_oapi.api.bitable.v1 import (AppTableCreateHeader, AppTableFieldProperty, AppTableFieldPropertyOption,
                                          CreateAppTableRequest, CreateAppTableRequestBody, ReqTable)
    ts = tables(bot)
    if REPORT_TABLE in ts:
        return ts[REPORT_TABLE]
    names = ["张伟", "李想", "陈悦", "周涛", "王丽"]
    fields = []
    for name, typ in REPORT_FIELDS:
        f = AppTableCreateHeader.builder().field_name(name).type(typ)
        if typ == 3:
            f = f.property(AppTableFieldProperty.builder().options([AppTableFieldPropertyOption.builder().name(n).build() for n in names]).build())
        if typ == 18:
            f = f.property(AppTableFieldProperty.builder().table_id(task_table_id(bot)).multiple(True).build())
        fields.append(f.build())
    r = bot.client.bitable.v1.app_table.create(CreateAppTableRequest.builder().app_token(_app()).request_body(
        CreateAppTableRequestBody.builder().table(ReqTable.builder().name(REPORT_TABLE).default_view_name("全部日报")
                                                  .fields(fields).build()).build()).build())
    if not r.success():
        raise RuntimeError(f"建日报表失败：{r.code} {r.msg}")
    return r.data.table_id


def save_reports(bot, state: dict, day: int, msgs: list[dict]) -> int:
    """同事交的日报写进「日报」表。表单生效（I2）之前，同事还在群里随手写，就不写表。返回写了几条。"""
    from lark_oapi.api.bitable.v1 import (AppTableRecord, BatchCreateAppTableRecordRequest,
                                          BatchCreateAppTableRecordRequestBody)
    reps = [m for m in msgs if m.get("report") and m.get("fields")]
    if not reps or not state["improvements"]["I2"]["active"] or not config.FEISHU_BITABLE_URL:
        return 0
    ts = tables(bot)
    if REPORT_TABLE not in ts:
        return 0
    have = field_names(bot, ts[REPORT_TABLE])
    missing = [n for n, _ in REPORT_FIELDS if n not in have]
    if missing:
        print(f"  ！「日报」表里没有这些字段，跳过不写：{'、'.join(missing)}（字段名见玩家手册第 9 章「表 3：日报」）")
    rid = {}
    for rec in _records(bot, task_table_id(bot)):
        m = CODE.match(_text(rec.fields.get("任务")))
        if m:
            rid[m[1]] = rec.record_id
    rows = []
    for m in reps:
        f = m["fields"]
        codes = list(dict.fromkeys(CODE.findall(f"{f['今日完成']} {f['进度']}")))
        row = {"提交人": m["sender"], "模拟日": f"D{day}（{date_str(state, day)}）",
               "今日完成": f["今日完成"], "进度": f["进度"], "明日计划": f["明日计划"], "卡点": f["卡点"]}
        if [rid[c] for c in codes if c in rid]:
            row["关联任务"] = [rid[c] for c in codes if c in rid]
        if f.get("交付物链接", "").startswith("http"):
            row["交付物链接"] = {"text": f["交付物链接"], "link": f["交付物链接"]}
        rows.append(AppTableRecord.builder().fields({k: v for k, v in row.items() if k in have}).build())
    r = bot.client.bitable.v1.app_table_record.batch_create(BatchCreateAppTableRecordRequest.builder()
        .app_token(_app()).table_id(ts[REPORT_TABLE]).request_body(BatchCreateAppTableRecordRequestBody.builder().records(rows).build()).build())
    if not r.success():
        print(f"  ✗ 日报写表失败：{r.code} {r.msg}")
        return 0
    return len(rows)
