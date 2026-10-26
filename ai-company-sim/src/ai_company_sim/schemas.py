"""AI 输出的结构（JSON），用 pydantic 校验。"""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from .state import KEY_BY_NAME

# 非 Claude 模型没有"强制结构化输出"，这里把常见的小偏差自动纠正，而不是直接判失败。


def _group(v):
    return "小暖 S2 发布会筹备" if isinstance(v, str) and ("发布会" in v or "S2" in v) else "品牌项目组"


def _who(v):
    return KEY_BY_NAME.get(v, v) if isinstance(v, str) else v


def _day(v):
    if isinstance(v, str):
        m = re.search(r"\d+", v)
        return int(m.group()) if m else None
    return v


def _pct(v):
    if isinstance(v, str):
        m = re.search(r"\d+", v)
        return int(m.group()) if m else 0
    return v


def _kind(v):
    return "meeting" if isinstance(v, str) and ("meeting" in v or "会" in v) else "message"


def _str_list(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else [str(x) for x in v]


Group = Annotated[Literal["品牌项目组", "小暖 S2 发布会筹备"], BeforeValidator(_group)]
StrList = Annotated[list[str], BeforeValidator(_str_list)]


class ScriptItem(BaseModel):
    time: str = Field(description="HH:MM")
    group: Group
    sender: str
    type: Annotated[Literal["message", "meeting"], BeforeValidator(_kind)] = "message"
    intent: str = ""
    must_include: StrList = []
    must_not_reveal: StrList = []
    name: str = ""
    attendees: StrList = []
    agenda: StrList = []
    key_points: StrList = []


class Initiative(BaseModel):
    time: str
    sender: str
    intent: str


class Script(BaseModel):
    script: list[ScriptItem]
    private_initiatives: list[Initiative] = []
    director_notes: str = ""


class Msg(BaseModel):
    time: str
    group: Group
    sender: str
    text: str


class Messages(BaseModel):
    messages: list[Msg]


class Line(BaseModel):
    speaker: str
    text: str


class Transcript(BaseModel):
    lines: list[Line]


class ReportFields(BaseModel):
    今日完成: str
    进度: str
    明日计划: str
    卡点: str
    交付物链接: str = ""
    link_note: str = ""


class Report(BaseModel):
    sender: str
    fields: ReportFields


class Reports(BaseModel):
    reports: list[Report]


class KeyDone(BaseModel):
    k: str
    time: str = Field(default="", description="动作发生的模拟时刻 HH:MM")
    evidence: str


class EventEval(BaseModel):
    id: str
    new_actions: list[KeyDone]


class Activated(BaseModel):
    id: str              # 清单内 I1–I13；清单外的用 X1、X2……
    evidence: str
    name: str = ""       # 清单外的改进写名字


class TrustChange(BaseModel):
    who: Annotated[Literal["wangli", "zhangwei", "lixiang", "chenyue", "zhoutao", "liumin", "sunlei", "huang"], BeforeValidator(_who)]
    delta: int
    reason: str


class Adjustment(BaseModel):
    action: Literal["reschedule", "cancel", "reassign", "extend_due", "scope_cut", "start_early"]
    task: str
    new_day: Annotated[int | None, BeforeValidator(_day)] = None
    new_owner: Annotated[str | None, BeforeValidator(_who)] = None
    hours: float | None = None
    evidence: str


class PlayerTask(BaseModel):
    task: str
    progress: Annotated[int, BeforeValidator(_pct)]
    evidence: str


class Interventions(BaseModel):
    chased_tasks: StrList = []
    forced_tasks: StrList = []
    unmasked_tasks: StrList = []
    summary_tasks: StrList = []
    urgent_tasks: StrList = []
    adjustments: list[Adjustment] = []
    player_tasks: list[PlayerTask] = []
    zhangwei_prefill: bool = False
    c_mandated: bool = False
    risk_logged: StrList = []
    weekly_report: bool = False
    weekly_report_text: str = ""


class Evaluation(BaseModel):
    events: list[EventEval] = []
    improvements_activated: list[Activated] = []
    trust_changes: list[TrustChange] = []
    interventions: Interventions = Interventions()
    notes_for_player: str = ""


class Responders(BaseModel):
    """项目助理在群里没 @ 人说了一句话：谁会接（可以没人）。"""
    who: StrList = []
    reason: str = ""
