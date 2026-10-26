"""从设定包里读人设卡、世界观、改进规则等原文，拼进提示词（模型看不到整份设定包）。"""

import re
from functools import cache

from . import config

DOC = config.ROOT / "director" / "设定包-完整.md"


@cache
def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def _section(start_pat: str, end_pat: str) -> str:
    t = _doc()
    s = re.search(start_pat, t, re.M)
    e = re.search(end_pat, t[s.end():], re.M)
    return t[s.start(): s.end() + e.start()].strip()


@cache
def world() -> str:
    return _section(r"^### 1\.1 公司", r"^### 1\.4")


@cache
def personas() -> dict[str, dict]:
    t = _section(r"^### 2\.1 ", r"^### 2\.9 ")
    out = {}
    for block in re.split(r"(?=^### 2\.\d )", t, flags=re.M):
        m = re.match(r"### 2\.\d (\S+?)（|### 2\.\d (\S+?) ", block)
        if not m:
            continue
        name = m.group(1) or m.group(2)
        name = name.split("（")[0].split("·")[0].strip()
        public = block.split("**隐藏规则")[0].strip()
        out[name] = {"full": block.strip(), "public": public}
    return out


# 给演员（群消息、私聊、日报、会议）用的"行为习惯"。
# 设定包里的隐藏规则提到了以后才会发生的事件，演员看到会提前说漏嘴，所以这里只保留习惯，不提任何具体事件；
# 正在发生的事件，由导演通过"今天的剧本 / 你知道的隐藏信息"单独告诉演员。
ACTOR_HABITS = {
    "王丽": ["经常在群里或会上顺口布置任务，不给截止时间，也不进任何表；说完自己也不会再追。",
             "审批慢，但不会承认自己慢。", "上级提的新要求，会直接转给执行的人，不评估工时和预算。",
             "给她有选项、有建议的汇报，她拍板很快；只给问题不给选项，她会说'你们先看着办'。"],
    "张伟": ["日报经常不交，交了也只写一句'推进中''在跟'。", "汇报从不给数字；只有被问到具体数字（几家、多少）时，才会停顿一下说真实数字。",
             "优先级：发布会 > 内容 > 入职优化（觉得那是 HR 的事）。", "活干完了经常不改状态。", "被当众追问会不舒服，私下问更愿意说实话。"],
    "李想": ["估时总是太乐观。", "落后的时候报喜不报忧，日报的卡点永远写'无'。",
             "被要草稿链接、被问具体字数或进度时，会不好意思地说实话。", "被当众点名落后会很受打击。"],
    "陈悦": ["她有一部分时间被其他部门占用，但不会主动告诉品牌项目组，被问'你这周还有多少时间给我们'才说。",
             "只认写清楚的书面需求；口头需求会做，但经常理解错要返工。", "同一个东西改稿超过两轮会有怨气。"],
    "周涛": ["承诺的日期普遍晚一天兑现。", "回复慢，常说'快了快了''我跟老板确认下''以最新文档为准哈'。",
             "改了文档不会主动说改了什么。"],
    "刘敏": ["对进度有要求；得到含糊答复会去找王丽。", "对方主动、提前说真实情况并给出方案，她很好说话。"],
    "孙磊": ["承诺很爽快'没问题 包在我身上'。", "要书面确认单和款项到了才排产。", "出了问题往往当天才说。"],
    "黄建国": ["很少出现，话少，提的要求不会撤回，但预算可以谈。"],
}


def persona(name: str, hidden: bool = True) -> str:
    """hidden=True：给演员用（公开人设 + 行为习惯，不含任何事件）；hidden=False：只有公开部分。"""
    p = personas().get(name)
    if not p:
        return f"### {name}\n（跨部门同事，按常识扮演，礼貌、简短）"
    public = (p["public"].replace("还有伴手礼也看一下哈", "还有签到那块也看一下哈")
              .replace('"这次发布会搞个直播吧，现在不直播等于没办。"', "提的要求很少撤回。"))
    if not hidden:
        return public
    habits = "\n".join(f"- {h}" for h in ACTOR_HABITS.get(name, []))
    return f"{public}\n\n**行为习惯（只用来决定你怎么说话、怎么汇报；不要把这些习惯本身说出来）**\n{habits}"


@cache
def improvement_rules() -> str:
    return _section(r"^\| 编号 \| 改进 \|", r"^\*\*注意改进的代价")


@cache
def trust_rules() -> str:
    return _section(r"^### 4\.9 信任值", r"^### 4\.10")


@cache
def improvement_names() -> dict[str, str]:
    return dict(re.findall(r"^\| (I\d+) \| ([^|]+?) \|", improvement_rules(), re.M))
