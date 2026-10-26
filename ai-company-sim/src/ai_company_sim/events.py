"""事件卡库（设定包第 5 章）。导演专用，玩家不要读这个文件。

每张卡：
- start / reveal / burst：相对日（剧情事件是绝对日，随机化时整体平移）
- signals：今天要放出的信号（day 是相对 start 的偏移；when 是出现条件）
- keys：关键动作；judge(done_k, ctx) 返回 化解 / 减轻 / 未处理
- decide：在哪一天"收工"时结算（默认 burst 当天），结算时只认这之前完成的关键动作
- outcomes：三种结果的叙述 + 效果（effects，由 engine.apply_effects 执行）
- secrets：只有这个角色知道的隐藏信息（私聊、剧本里用）
"""

from dataclasses import dataclass, field
from typing import Callable

# effects 支持的键（engine.apply_effects 实现）：
# 所有"日"都是相对事件开始日（start）的偏移。
#   trust: {人: 增减}              budget_over: [(说明, 金额)]
#   add_hours: {任务: 小时}        ready_day: {任务: 日}        complete_by: {任务: 日}
#   due_shift: {任务: 天}          unavail: {人: {相对日: 小时}}  bias: (值, 截止日)
#   score: {维度: 分}              content: {内容ID: 结果}      flag: {名: 值}
#   approval_extra: (天, 适用日)   exists: [任务]               forced: {任务: 截止日}
#   cancel: [任务]（范围缩减，计划内取消）    delivery_shift: 0/1/2（印刷延期程度）                    narrative: 给剧本的后果描述


@dataclass
class Event:
    id: str
    name: str
    start: int
    reveal: int
    burst: int
    keys: dict[str, str]
    outcomes: dict[str, dict]
    signals: list[dict] = field(default_factory=list)
    truth: str = ""
    secrets: dict[str, str] = field(default_factory=dict)
    on_start: dict = field(default_factory=dict)
    burst_time: str = "17:00"
    decide: int | None = None  # 结算日（绝对日），默认 = burst
    judge: Callable[[dict, dict], str] | None = None
    level: str = "剧情"
    eligible: Callable[[int], bool] | None = None
    shiftable: bool = False

    @property
    def decide_day(self) -> int:
        return self.decide if self.decide is not None else self.burst


def count_judge(required: list[str], deadline: int | None = None):
    """默认判定：截止日前完成全部 required → 化解；至少一半 → 减轻；否则未处理。"""

    def _judge(done_k: dict, ctx: dict) -> str:
        n = sum(1 for k in required if k in done_k and (deadline is None or done_k[k] <= deadline))
        if n == len(required):
            return "化解"
        if n * 2 >= len(required):
            return "减轻"
        return "未处理"

    return _judge


def _by(done_k: dict, keys: list[str], day: int) -> bool:
    return all(k in done_k and done_k[k] <= day for k in keys)


# ---------------------------------------------------------------- 剧情事件

def story_events(rz: dict) -> list[Event]:
    """rz = state['randomized']，用于价格、卖点、病假人选、伴手礼变体等随机值。"""
    gift = rz.get("gift_item", "伴手礼")
    new_price = rz.get("new_price", 349)
    claim_old, claim_new = rz.get("claim_change", ["3秒速热", "5秒速热"])
    sick = rz.get("sick_person", "lixiang")
    sick_name = "李想" if sick == "lixiang" else "张伟"
    delay_to = rz.get("print_delay_to", "D13 08:00")

    ev: list[Event] = []

    ev.append(Event(
        id="E01", name="交接混乱", start=1, reveal=1, burst=3, burst_time="15:00",
        truth="A2 真实进度 30%；C 项目 0%；三个项目之间的依赖（A0→A3/A6/B06…）没人梳理过。",
        signals=[
            {"day": 0, "time": "09:20", "group": "品牌项目组", "sender": "王丽",
             "hint": "欢迎新同事，交代'三个项目你帮我盯着 有啥不清楚的问老张小李 每周五给我周报'"},
            {"day": 0, "time": "09:35", "group": "品牌项目组", "sender": "张伟",
             "hint": "甩出《发布会筹备 v2.xlsx》（只有 A1–A6，最后更新 10 天前，A2 写着'进行中'）"},
            {"day": 0, "time": "09:40", "group": "品牌项目组", "sender": "李想",
             "hint": "发内容排期文档链接（比较完整），热情欢迎"},
            {"day": 0, "time": "14:10", "group": "品牌项目组", "sender": "王丽",
             "hint": "顺口说 IT 那边说新同事账号下午才开通 先用手机看群"},
            {"day": 2, "time": "15:00", "group": "小暖 S2 发布会筹备", "sender": "王丽",
             "hint": "（仅当本事件未化解）筹备会上问'邀请函文案谁在写 什么时候出'，老张和小李说法不一致", "when": "unresolved"},
        ],
        keys={
            "K1": "建立三个项目的统一任务表（覆盖可见任务 80% 以上，含负责人和截止日期）",
            "K2": "和每位负责人确认过各自的任务和截止日期（私聊或在 D1 例会上）",
            "K3": "把任务表链接发到群里并置顶 / 发群公告",
        },
        outcomes={
            "化解": {"narrative": "D3 筹备会 40 分钟高效结束；王丽：'这个表不错 以后就按这个过'", "trust": {"wangli": 10}},
            "减轻": {"narrative": "会议正常，但有 1–2 个任务对不上，需会后确认"},
            "未处理": {"narrative": "筹备会上王丽问邀请函文案谁在写，老张和小李说法不一致，会议超时 30 分钟；王丽：'我们是不是得有个总表'",
                      "trust": {"wangli": -5}, "flag": {"e01_unresolved": True}},
        },
    ))

    ev.append(Event(
        id="E02", name="卖点文档延期", start=2, reveal=2, burst=4, decide=2, burst_time="23:59", shiftable=True,
        truth="A0 按'承诺晚 1 天'规则会在第二天下午才交；A3、A6、B06 都依赖它。",
        signals=[
            {"day": 0, "time": "10:30", "group": "小暖 S2 发布会筹备", "sender": "陈悦",
             "hint": "问'S2 的 KV 什么时候能开始 卖点出了没'"},
            {"day": 0, "time": "15:40", "group": "小暖 S2 发布会筹备", "sender": "周涛",
             "hint": "'卖点文档老板还要再看下 他今天出差 明天给哈 🙏'（不说具体时间）"},
        ],
        secrets={"zhoutao": "老板今天出差，卖点文档你最早明天下午能给；如果项目助理跟你约具体时间并提前提醒，你会努力在明天上午 11 点前交。"},
        keys={
            "K1": "识别受影响的下游任务（至少 A3、A6），在任务表中标注阻塞或风险",
            "K2": "和周涛约定具体时间（如'明天上午 11 点前可以吗？'），并在约定时间前提醒",
            "K3": "通知李想、陈悦调整当天安排（先做不依赖 A0 的工作）",
        },
        outcomes={
            "化解": {"narrative": "A0 在次日上午 11 点交付；陈悦先做了 A6 的版式框架", "ready_day": {"A0": 1}, "add_done": {"A6": 3}},
            "减轻": {"narrative": "A0 在次日下午交付；下游顺延半天", "ready_day": {"A0": 1}},
            "未处理": {"narrative": "周涛次日又说'明天一早给'，A0 拖到再下一天上午；邀请函链条整体顺延 1 天",
                      "ready_day": {"A0": 2}},
        },
    ))

    ev.append(Event(
        id="E03", name=f"口头任务：{gift}", start=3, reveal=6, burst=9, burst_time="10:30",
        truth=f"王丽在筹备会上口头布置了{gift}，老张回了'好'之后完全忘了，没人跟进。定制 logo 需要 7 个自然日，最晚 D7 下单才能在彩排前到货。预算表里有'伴手礼 2 万'但没有对应任务。",
        signals=[
            {"day": 0, "time": "15:00", "group": "小暖 S2 发布会筹备", "sender": "王丽",
             "hint": f"在筹备会中间顺口说'@张伟 {gift}也看一下哈 去年那个保温杯大家反馈一般 今年弄点有意思的'，老张回'好'。不要强调，埋在会议里", "meeting": True},
            {"day": 3, "time": "14:20", "group": "小暖 S2 发布会筹备", "sender": "孙磊",
             "hint": f"（仅当本事件未化解）'{gift}需要我们这边一起采购吗？要定制 logo 的话得提前 7 天哈'", "when": "unresolved"},
            {"day": 6, "time": "10:30", "group": "品牌项目组", "sender": "王丽",
             "hint": f"（仅当本事件未化解）'{gift}定了吗？' 全组沉默", "when": "unresolved"},
        ],
        secrets={"zhangwei": f"王丽在筹备会上让你看{gift}，你回了'好'但忘了。被具体问起时你会说'哎呀这个我还没弄'。"},
        keys={
            "K1": f"把{gift}记录为任务或会议待办（新建 A13），写明负责人和截止日期",
            "K2": "和老张确认他认领并知道截止日期（定制需 D7 前下单）",
            "K3": "（加分）在会议纪要中记录王丽的要求（不要保温杯，要有意思）",
        },
        judge=lambda d, c: "化解" if _by(d, ["K1", "K2"], 6) else ("减轻" if _by(d, ["K1"], 8) else "未处理"),
        outcomes={
            "化解": {"narrative": "老张 D6 前确定方案，D7 前下单定制款，D12 到货"},
            "减轻": {"narrative": f"有记录但截止日期没确认，D8 才下单，来不及定制 logo，改为高品质通用款"},
            "未处理": {"narrative": f"王丽在群里问'{gift}定了吗？'全组沉默；加急采购无 logo 通用礼品，加急费 3000 元；王丽对全组：'这种事以后会上说的都要记下来啊'",
                      "budget_over": [(f"{gift}加急费", 3000)], "score": {"流程顺畅": -5}},
        },
    ))

    ev.append(Event(
        id="E04", name="黄总加直播", start=4, reveal=4, burst=6, decide=5, burst_time="23:59", shiftable=True,
        truth="A14 需要 10 小时，老张本周已接近满载；直播供应商报价 3 万，会超预算 2 万。",
        on_start={"exists": ["A14"], "forced": {"A14": 99}},
        signals=[
            {"day": 0, "time": "10:40", "group": "品牌项目组", "sender": "黄建国",
             "hint": "（被临时拉进群）'这次发布会搞个直播吧 抖音视频号都上 现在不直播等于没办'"},
            {"day": 0, "time": "10:43", "group": "品牌项目组", "sender": "王丽", "hint": "'好的黄总 @张伟 直播你来弄一下'"},
            {"day": 0, "time": "10:44", "group": "品牌项目组", "sender": "张伟", "hint": "'好'"},
        ],
        secrets={"zhangwei": "直播供应商报价 3 万。你这周活已经很满，但不会主动说。",
                 "wangli": "你没算过直播对预算和老张工时的影响。"},
        keys={
            "K1": "把直播登记为变更，在任务表中新建 A14",
            "K2": "评估工时影响（老张的负载）和预算影响（+3 万，超支 2 万）",
            "K3": "给王丽发选择题：①申请追加预算 ②机动费 + 压缩其他科目 ③简易直播（约 8000 元自己推流），附建议和理由",
            "K4": "王丽决策后更新预算表和任务分工（例如替老张接手部分工作）",
        },
        judge=lambda d, c: "化解" if _by(d, ["K1", "K2", "K3"], c["decide"]) else ("减轻" if _by(d, ["K2"], c["decide"]) else "未处理"),
        outcomes={
            "化解": {"narrative": "王丽按选择题拍板，预算可控，老张负载合理", "forced": {"A14": 0}, "flag": {"live_budget_ok": True}},
            "减轻": {"narrative": "做了评估但没给选项，王丽'你们先看着办'，拖了一天才定", "forced": {"A14": 0}, "flag": {"live_budget_ok": True}},
            "未处理": {"narrative": "直播作为强制任务插进老张的工时，邀约和回执各拖 1 天；D9 付款时财务发现超预算，付款审批卡 1 天",
                      "due_shift": {"A2": 1, "A5": 1}, "budget_over": [("直播超预算", 20000)], "flag": {"finance_block": True}},
        },
    ))

    ev.append(Event(
        id="E05", name="小李隐性落后", start=2, reveal=3, burst=5, burst_time="12:00",
        truth="小李第 1 周工作量超出产能，B05 文案只有 10%，到中午发不出来。日报里报喜不报忧。",
        signals=[
            {"day": 1, "time": "17:40", "group": "品牌项目组", "sender": "李想", "hint": "日报里对 B04 说得很乐观（按引擎给的汇报进度）"},
            {"day": 3, "time": "10:20", "group": "品牌项目组", "sender": "李想", "hint": "'B05 下午发哈'"},
            {"day": 3, "time": "16:10", "group": "品牌项目组", "sender": "王丽",
             "hint": "（仅当本事件未化解）周会上当众问小李'今天小红书怎么没发'", "when": "unresolved"},
        ],
        secrets={"lixiang": "你这周其实忙不过来，B04、B05 都落后，但你不想承认。被友好地追问或被要链接时会说实话，并有点不好意思。"},
        keys={
            "K1": "发现问题（要草稿链接、指出发布时间推迟、对比日报和实际情况）",
            "K2": "私聊小李了解真实负荷（友好地问，不是质问）",
            "K3": "帮他调整：和王丽商量 B05 简化 / 延后，或请陈悦用模板出图",
            "K4": "在风险表中记录'内容组产能不足'，并在周报中体现",
        },
        outcomes={
            "化解": {"narrative": "B05 简化版 17:00 发出（计为准时）；小李轻松了不少", "trust": {"lixiang": 10},
                    "content": {"B05": "计划内调整"}, "bias": (15, 8)},
            "减轻": {"narrative": "B05 推迟到下周一发出", "content": {"B05": "延误"}},
            "未处理": {"narrative": "B05 断更；周会上王丽当众问小李'今天小红书怎么没发'；小李接下来两天汇报更乐观",
                      "content": {"B05": "断更"}, "bias": (35, 5)},
        },
    ))

    ev.append(Event(
        id="E06", name="日报敷衍与漏交", start=1, reveal=1, burst=5, burst_time="17:30",
        truth="老张的 A2 邀约真实进度：看引擎给的媒体 / 经销商确认数。他从不在日报写数字。",
        signals=[],
        secrets={"zhangwei": "被问具体数字（确认了几家）时，你会停顿一下'我看下哈……'然后给出真实数字。"},
        keys={
            "K1": "私聊老张，问出 A2 的具体数字",
            "K2": "周报中给出准确数据，而不是'推进中'",
            "K3": "在周报的改进建议中提出日报改进方案",
        },
        outcomes={
            "化解": {"narrative": "周报准确；王丽回复'邀约有点慢 下周一例会重点过一下'", "trust": {"wangli": 5}},
            "减轻": {"narrative": "周报大体准确，但王丽追问了一两个数字"},
            "未处理": {"narrative": "周报只能写'推进中'；王丽周末回复'邀约到底确认了多少家？'", "trust": {"wangli": -5}},
        },
    ))

    ev.append(Event(
        id="E07", name="陈悦被借调", start=6, reveal=6, burst=8, burst_time="17:00",
        truth="电商部双 11 大促，陈悦 D6–D7 被整天借调。A6 定稿还差不少，D9 是下单硬节点。她不会主动告诉品牌项目组。",
        on_start={"unavail": {"chenyue": {0: 4, 1: 4}}, "flag": {"chenyue_seconded": True}},
        signals=[
            {"day": 0, "time": "09:50", "group": "品牌项目组", "sender": "陈悦", "hint": "'例会我请个假 电商那边有点急事'"},
            {"day": 0, "time": "11:50", "group": "品牌项目组", "sender": "陈悦", "hint": "B06 配图踩点才给（如果 B06 有配图任务）"},
            {"day": 1, "time": "15:00", "group": "品牌项目组", "sender": "陈悦", "hint": "回复变慢：'晚点看'"},
        ],
        secrets={"chenyue": "你 D6–D7 被电商部整天借调做双 11，几乎没时间给品牌项目组。你不会主动说；只有被问'这两天还有多少时间给我们'这类问题时才如实说。"},
        keys={
            "K1": "问陈悦'这两天还有多少时间给我们'（揭穿借调）",
            "K2": "评估 A6 对物料定稿 / 下单的影响，上报王丽并给选项（协调只借 1 天 / B 配图改模板 / A6 分批交付）",
            "K3": "王丽决策后更新排期，并通知老张 / 孙磊分批下单",
        },
        outcomes={
            "化解": {"narrative": "A6 核心物料按时定稿，下单节奏正常", "complete_by": {"A6": 2}},
            "减轻": {"narrative": "A6 晚半天定稿，D9 下班前勉强下单", "complete_by": {"A6": 3}, "flag": {"a6_late": 0.5}},
            "未处理": {"narrative": "A6 拖到 D10 才定稿，下单跟着推迟", "ready_day": {"A6": 4}, "flag": {"a6_late": 2}},
        },
    ))

    ev.append(Event(
        id="E08", name="卖点与价格变更", start=7, reveal=7, burst=7, burst_time="20:00",
        truth=f"周涛 11:05 把《小暖 S2 卖点与参数》改成 v2：价格 399 → {new_price}；'{claim_old}'改为'{claim_new}'（法务认为原表述有广告法风险）。他只私聊了正在开会的王丽，群里只说一句含糊的话。",
        on_start={"product_change": True},
        signals=[
            {"day": 0, "time": "11:20", "group": "小暖 S2 发布会筹备", "sender": "周涛",
             "hint": "'卖点文档更新了下 大家以最新为准哈 🙏'——绝对不说改了什么"},
            {"day": 0, "time": "15:30", "group": "品牌项目组", "sender": "李想", "hint": "在写今晚 20:00 的 B07 推送，状态积极"},
        ],
        secrets={"zhoutao": f"你今天把文档改成 v2：价格 399→{new_price}，'{claim_old}'改成'{claim_new}'（法务要求）。被直接问'改了什么'时如实说。",
                 "wangli": f"周涛 11:10 私聊你说价格改成 {new_price}、'{claim_old}'改成'{claim_new}'，你在开会没细看，也没转发。"},
        keys={
            "K1": "当天弄清改了什么（打开文档比对，或直接问周涛）",
            "K2": "列出受影响清单（至少包含 A6、B07、B08、A9/A10 中的 4 项）",
            "K3": "通知每个受影响的负责人，并在任务表中更新（返工工时）",
            "K4": "确保 B07 在 20:00 推送前改正",
            "K5": "提出参数冻结 / 变更单机制（I5），防止再次发生",
        },
        judge=lambda d, c: "化解" if _by(d, ["K1", "K2", "K3", "K4"], c["start"]) else ("减轻" if _by(d, ["K1"], c["start"] + 1) else "未处理"),
        decide=8,
        outcomes={
            "化解": {"narrative": "只有返工工时，B07 按新信息准时推送", "add_hours": {"A6": 4, "A9": 1}},
            "减轻": {"narrative": "B07 带着旧卖点推送了，王丽决定评论区置顶更正；其余物料来得及改",
                    "content": {"B07": "错误已更正"}, "add_hours": {"A6": 4, "A9": 1}},
            "未处理": {"narrative": "D9 法务要求删除 B07 和 B08；D12 彩排时发现价格牌、PPT 上还是旧价格，加急重印 3000 元，陈悦当晚加班",
                      "content": {"B07": "删除", "B08": "删除"}, "budget_over": [("价格牌加急重印", 3000)],
                      "trust": {"chenyue": -10}, "score": {"信息正确": -15}, "flag": {"e08_second_burst": 12}},
        },
    ))

    ev.append(Event(
        id="E09", name=f"{sick_name}病假", start=8, reveal=8, burst=8, burst_time="12:00", shiftable=True,
        truth=(f"{sick_name}发烧请一天假。" + ("A9（Run-down + 主持稿）快到期，真实进度很低，前两天日报报得高；B08、B09 文案都没写完。"
                                    if sick == "lixiang" else "A5 回执统计、A14 直播供应商对接、A7 付款申请都压在他身上。")),
        on_start={"unavail": {sick: {0: 6}}},
        signals=[
            {"day": 0, "time": "08:30", "group": "品牌项目组", "sender": sick_name,
             "hint": "'王姐 我发烧了 今天请一天假 🤒 电脑带回来了 晚上看看能不能弄点'"},
            {"day": 0, "time": "15:00", "group": "小暖 S2 发布会筹备", "sender": "周涛",
             "hint": "（如果当天有筹备会）问'流程定了吗 我演讲多长时间'"},
        ],
        secrets={sick: "你今天发烧请假。被问手上任务的真实进度时，晚上会如实回复（有点不好意思）。"},
        keys={
            "K1": f"当天上午梳理{sick_name}手上的所有任务和截止日期（影响清单）",
            "K2": "上报王丽并给出选项（延后 / 用存稿替换 / 改期 / 请别人代审）",
            "K3": "弄清关键任务的真实进度（要链接）",
            "K4": "更新任务表并通知相关人",
        },
        outcomes=({
            "化解": {"narrative": "经王丽批准的调整都计为计划内调整；A9 截止改到 D10，真实情况可见", "content": {"$pub0": "计划内调整"}, "due_shift": {"A9": 1}},
            "减轻": {"narrative": "B08 晚了一天，A9 的真实进度被发现得有点晚", "content": {"$pub0": "延误"}, "due_shift": {"A9": 1}},
            "未处理": {"narrative": "B08 断更；B09 推迟；A9 到 D11 才被发现进度很低，彩排时流程粗糙",
                      "content": {"$pub0": "断更", "$pub1": "延误"}, "score": {"流程顺畅": -5}},
        } if sick == "lixiang" else {
            "化解": {"narrative": "老张的事有人兜底，节奏没乱"},
            "减轻": {"narrative": "回执统计晚了一天", "due_shift": {"A5": 1}},
            "未处理": {"narrative": "回执统计和付款申请都拖了，付款晚一天", "due_shift": {"A5": 1}, "flag": {"finance_block": True}},
        }),
    ))

    ev.append(Event(
        id="E10", name="物料下单与预付款", start=8, reveal=8, burst=9, burst_time="17:00",
        truth="付款流程 = 老张提交付款申请（需报价单 + 合同）→ 王丽审批 → 财务支付（1 天）。当天不提交，钱就晚一天到。付款申请不必等 A6 定稿；但下单确认单必须等 A6 审核通过。",
        signals=[
            {"day": 0, "time": "10:30", "group": "小暖 S2 发布会筹备", "sender": "孙磊",
             "hint": "'张哥 下单确认单和 50% 预付款明天下午 5 点前到我们这 才能保证 17 号送到哈'"},
            {"day": 1, "time": "16:50", "group": "小暖 S2 发布会筹备", "sender": "孙磊", "hint": "确认是否收到下单和款项（按结算结果）"},
        ],
        secrets={"zhangwei": "付款申请要报价单盖章件 + 合同。你本来打算明天再弄。",
                 "sunlei": "如果对方要求，你可以凭盖章的下单确认单先排产，款随后到，但需要书面确认。"},
        keys={
            "K1": "搞清楚付款流程需要多长时间（问老张或财务）",
            "K2": "推动老张当天提交付款申请，并核对材料齐全",
            "K3": "让王丽当天审批（单独提醒或放进待审汇总 / 标紧急）",
            "K4": "如来不及：和孙磊协商凭盖章下单确认单先排产（要书面确认）",
        },
        outcomes={
            "化解": {"narrative": "D9 下单成功，物料 D12 交付", "flag": {"order_ok": True}},
            "减轻": {"narrative": "下单踩线完成，物料 D12 交付", "flag": {"order_ok": True}},
            "未处理": {"narrative": "D10 才付款，物料交付推迟到 D13 早上", "flag": {"order_ok": False}},
        },
    ))

    ev.append(Event(
        id="E11", name="入职优化零进度暴露", start=1, reveal=3, burst=10, decide=11, burst_time="14:00", shiftable=True,
        truth="C 项目真实进度 0%（老张按偏好从来不做 C）。刘敏在 D5 私聊过老张，老张说'在弄了'。",
        signals=[
            {"day": 9, "time": "14:00", "group": "品牌项目组", "sender": "王丽",
             "hint": "（仅当本事件未化解）'@张伟 入职那个怎么样了 刘敏刚问我 下周五就要汇报了'", "when": "unresolved"},
        ],
        secrets={"zhangwei": "入职优化你一点都没做，你觉得那是 HR 的事。D5 刘敏私聊问你，你说'在弄了'。被具体问时承认。",
                 "liumin": "D5 你私聊问过老张，他说'在弄了'。如果项目助理主动、提前同步真实情况并提出缩减方案，你会接受（'能先出清单也行 手册下个月补'）。"},
        keys={
            "K1": "在 D7 前就识别出 C 零进度并上报王丽（越早越好）",
            "K2": "弄清真实状态",
            "K3": "给王丽选项：①缩减范围 ②在王丽同意后自己认领整理工作 ③和刘敏协商延期",
            "K4": "和刘敏同步真实情况并确认缩减后的范围",
        },
        judge=lambda d, c: ("化解" if _by(d, ["K1", "K2", "K3", "K4"], 7) and d["K1"] <= 7
                            else ("减轻" if _by(d, ["K3"], c["decide"]) else "未处理")),
        outcomes={
            "化解": {"narrative": "C 交付缩减版，质量不错；刘敏：'能先出清单也很好 手册下个月补'", "trust": {"liumin": 10}, "flag": {"c_result": "缩减但获认可"}, "cancel": ["C4", "C5"]},
            "减轻": {"narrative": "交付缩减版，但比较仓促；刘敏满意度一般", "flag": {"c_result": "缩减·仓促"}, "cancel": ["C4", "C5"]},
            "未处理": {"narrative": "C 未交付；王丽在人事部面前很被动", "trust": {"wangli": -10}, "flag": {"c_result": "未交付"}},
        },
    ))

    ev.append(Event(
        id="E12", name="印刷延期", start=11, reveal=11, burst=12, burst_time="14:00",
        truth=f"印刷厂机器坏了半天，背景板和易拉宝预计 {delay_to} 才能送到场地。",
        signals=[
            {"day": 0, "time": "16:00", "group": "小暖 S2 发布会筹备", "sender": "孙磊",
             "hint": f"'张哥 不好意思 印刷厂机器坏了半天 背景板和易拉宝可能要 {delay_to.replace('D13', '18 号')} 送到场地'"},
        ],
        secrets={"sunlei": "如果被要求书面承诺并协商补救，你可以安排加班，D12 晚上 20:00 前送到。"},
        keys={
            "K1": "当天评估影响（彩排没有实物；发布会当天布置时间压缩）",
            "K2": "要求孙磊书面承诺最终交期，并协商补救（加班、分批送货）",
            "K3": "准备备份方案（本地快印店出价格牌和桌卡；彩排用电子版）",
            "K4": "上报王丽并给出选项",
        },
        outcomes={
            "化解": {"narrative": "孙磊加班，物料 {到场} 送到；彩排用电子版走流程", "delivery_shift": 0},
            "减轻": {"narrative": "物料 {到场} 到场，布置紧张但完成", "delivery_shift": 1},
            "未处理": {"narrative": "物料 {到场} 才到，布置仓促", "delivery_shift": 2},
        },
    ))

    ev.append(Event(
        id="E13", name="彩排：PPT 版本混乱", start=10, reveal=10, burst=12, burst_time="14:00",
        truth="群里先后出现 v3、v4、v5_final 等 PPT 附件；周涛 A10 内容 D11 晚上才给最终版（v5），陈悦是基于 v3 美化的。",
        signals=[
            {"day": 0, "time": "10:20", "group": "小暖 S2 发布会筹备", "sender": "周涛", "hint": "发「小暖S2发布会v3.pptx」附件"},
            {"day": 0, "time": "16:40", "group": "小暖 S2 发布会筹备", "sender": "周涛", "hint": "又发「小暖S2发布会v4.pptx」：'改了几页哈'"},
            {"day": 1, "time": "21:00", "group": "小暖 S2 发布会筹备", "sender": "周涛", "hint": "发「小暖S2发布会v5_final.pptx」：'这个是最终的哈'"},
        ],
        secrets={"chenyue": "你一直在按 v3 美化 PPT，不知道后面有 v4、v5。", "zhoutao": "v5_final 才是最终版，你以为大家都会用最新的。"},
        keys={
            "K1": "在 D12 前建立'单一文件源'规则（云文档链接，禁止发附件）",
            "K2": "彩排前按清单核对 PPT 版本和关键参数（价格、卖点）",
            "K3": "彩排后输出问题清单（问题、负责人、当晚截止），并在当晚逐项确认关闭",
        },
        outcomes={
            "化解": {"narrative": "彩排前发现版本问题，当场确认版本"},
            "减轻": {"narrative": "彩排时才发现，陈悦当晚加班修改", "trust": {"chenyue": -5}},
            "未处理": {"narrative": "发布会当天 PPT 有 2 页是旧内容", "score": {"信息正确": -5}},
        },
    ))

    ev.append(Event(
        id="E14", name="发布会现场", start=13, reveal=13, burst=13, burst_time="16:30",
        truth="现场问题：①2 位 KOL 没回执直接来了、1 位经销商带了同事，座位不够；②14:20 直播画面卡顿；③（好消息）某科技媒体想会后专访周涛 15 分钟。",
        signals=[
            {"day": 0, "time": "13:30", "group": "小暖 S2 发布会筹备", "sender": "张伟", "hint": "签到开始；名单和回执对不上，座位紧张"},
            {"day": 0, "time": "14:20", "group": "小暖 S2 发布会筹备", "sender": "张伟", "hint": "直播画面卡顿（如果有直播）"},
            {"day": 0, "time": "15:30", "group": "小暖 S2 发布会筹备", "sender": "王丽", "hint": "某科技媒体想会后专访周涛 15 分钟"},
        ],
        keys={
            "K1": "D12 前把签到表和回执核对一遍，并预留 10% 机动座位",
            "K2": "彩排时做过直播推流测试",
            "K3": "现场问题在群里明确分配负责人，并实时同步进展",
            "K4": "安排好专访（协调周涛的时间和场地）",
        },
        judge=lambda d, c: "化解" if all(k in d for k in ["K1", "K2", "K3", "K4"]) else ("减轻" if len([k for k in ["K1", "K2", "K3"] if k in d]) >= 2 else "未处理"),
        outcomes={
            "化解": {"narrative": "现场问题都有人接、有闭环；专访顺利安排"},
            "减轻": {"narrative": "大部分问题处理了，但有一处手忙脚乱"},
            "未处理": {"narrative": "现场比较混乱"},
        },
    ))

    ev.append(Event(
        id="E15", name="会后数据急要", start=14, reveal=14, burst=15, burst_time="10:00",
        truth="数据分散在四个地方：签到表（纸质，老张拍了照片）、直播后台（老张的账号）、经销商意向登记（一部分纸质、一部分扫码）、媒体发稿链接（小李在收集）。",
        signals=[
            {"day": 0, "time": "09:30", "group": "品牌项目组", "sender": "黄建国",
             "hint": "'明天 10 点前给我一个发布会数据 到场人数 直播观看 经销商意向 媒体发稿 @王丽'"},
        ],
        keys={
            "K1": "D14 上午列出数据口径和来源，分派给对应的人收集",
            "K2": "建一张汇总表（多维表格）",
            "K3": "D14 晚上把初稿给王丽审",
            "K4": "D15 10:00 前提交",
        },
        outcomes={
            "化解": {"narrative": "按时准确提交；黄总在群里回复'👍'", "trust": {"wangli": 10}},
            "减轻": {"narrative": "按时提交，但口径有一两处要补"},
            "未处理": {"narrative": "数据延迟或口径混乱", "trust": {"wangli": -10}},
        },
    ))

    return ev


# ---------------------------------------------------------------- 随机事件（设定包 5.2）

def _r(id, level, name, signal, sender, key, fail, effects=None, eligible=None, on_start=None):
    return Event(
        id=id, name=name, start=0, reveal=0, burst=1, level=level, burst_time="12:00",
        signals=[{"day": 0, "time": "", "group": "品牌项目组", "sender": sender, "hint": signal}],
        keys={"K1": key},
        outcomes={"化解": {"narrative": "处理得当，没有后果"}, "减轻": {"narrative": "处理得当，没有后果"},
                  "未处理": dict({"narrative": fail}, **(effects or {}))},
        eligible=eligible, on_start=on_start or {},
    )


RANDOM_EVENTS = [
    _r("R01", "轻", "会议室被占", "例会前 10 分钟有人说'3 号会议室被销售部占了'", "李想",
       "提前确认会议室 / 发线上会议链接", "会议推迟 15 分钟", eligible=lambda d: d in (1, 3, 5, 6, 8, 10, 11, 15)),
    _r("R02", "轻", "重要文件被刷屏淹没", "陈悦问'邀请函最终文案是哪个？我往上翻没找到'", "陈悦",
       "群公告 / 置顶 / 知识库归档", "陈悦用错版本，返工 1 小时", {"add_hours": {"$chenyue_current": 1}}),
    _r("R03", "轻", "文件命名混乱", "小李发「最终版2.docx」", "李想",
       "提出命名规范（项目_内容_日期_版本）", "王丽审错版本，审批多拖 1 天", {"approval_extra": (1, 1)}),
    _r("R04", "中", "王丽出差一天", "王丽说'明天我去广州 一天会 消息可能回不了'", "王丽",
       "当天把待审事项汇总给她，请她出发前或在路上审批", "所有王丽审批 +1 天", {"approval_extra": (1, 1)},
       eligible=lambda d: d not in (12, 13, 14)),
    _r("R05", "轻", "重复提问", "小李和陈悦先后私聊问周涛同一个参数（周涛在群里抱怨了一句）", "周涛",
       "统一由一个人对接，或整理 FAQ", "周涛不耐烦，回复变慢", {"trust": {"zhoutao": -5}}),
    _r("R06", "中", "报价与合同不一致", "会务执行报价单比合同多 2000 元（老张在群里发了报价单）", "张伟",
       "核对并请老张找孙磊确认", "多付 2000 元", {"budget_over": [("会务报价差额", 2000)]}),
    _r("R07", "轻", "做完未更新状态", "老张的某个任务实际已完成，表格上还是'进行中'（没有直接信号，只有日报含糊）", "张伟",
       "抽查或问一句", "周报数据错误", {"trust": {"wangli": -5}}),
    _r("R08", "中", "小红书违规词被限流", "某条笔记互动量异常低；小李说'好像被限流了'", "李想",
       "建立发布前敏感词检查清单（'最''第一''秒杀'等）", "该条数据很差，需改文重发 +1 小时", {"add_hours": {"$lixiang_current": 1}},
       eligible=lambda d: d >= 3),
    _r("R09", "轻", "@所有人误用", "有人@所有人问只和一个人有关的问题", "李想",
       "群公告里写清群规", "只是噪音，无后果"),
    _r("R10", "中", "销售部索要名单", "销售部同事私聊项目助理，要经销商邀约名单（含手机号）", "销售部小赵",
       "确认用途，征得王丽同意，脱敏后再给", "（如果直接发出了，P5 会扣王丽信任）", eligible=lambda d: d >= 4),
    _r("R11", "中", "'之前不是说好了吗'", "周涛：'演讲不是说好 20 分钟吗？'（流程里写的是 15 分钟）", "周涛",
       "能在会议纪要中找到记录 / 当场确认并书面化", "A9 返工 2 小时", {"add_hours": {"A9": 2}}, eligible=lambda d: 7 <= d <= 12),
    _r("R12", "中", "改稿抱怨", "陈悦：'这个改第三轮了 能不能一次说完'", "陈悦",
       "合并修改意见一次提；用需求单", "陈悦信任 -10，下次响应慢", {"trust": {"chenyue": -10}}, eligible=lambda d: d >= 4),
    _r("R13", "中", "财务退回付款申请", "财务：'缺报价单盖章件 退回了'", "张伟",
       "提交前按材料清单核对", "付款多拖 1 天", {"flag": {"finance_block": True}}, eligible=lambda d: d in (8, 9)),
    _r("R14", "轻", "外部打不开文档", "孙磊：'这个链接我打不开哎'", "孙磊",
       "检查外部协作权限", "延误半天"),
    _r("R15", "中", "KOL 临时要车马费", "老张私聊项目助理：'有个 KOL 说要 2000 车马费'", "张伟",
       "上报王丽，附预算余额", "老张自己答应了，超预算 2000", {"budget_over": [("KOL 车马费", 2000)]}, eligible=lambda d: 6 <= d <= 12),
    _r("R16", "轻", "媒体要专访", "某媒体：'能约周涛老师专访吗？'（老张转述）", "张伟",
       "协调周涛时间，王丽确认", "错过曝光机会"),
    _r("R17", "轻", "文章爆了", "某篇内容阅读量 1 万+，王丽：'这个热度要接一下 再出一篇'", "王丽",
       "评估小李负荷，给王丽排期建议", "直接塞给小李，下一篇延误", {"add_hours": {"$lixiang_current": 2}}, eligible=lambda d: d >= 3),
    _r("R18", "轻", "半天事假", "老张或陈悦：'下午家里有事请半天假'", "张伟",
       "调整当天安排，通知相关人", "当事人当天少 3 小时，没人知道", on_start={"unavail": {"$half_day": {0: 3}}}),
]

LIGHT_POOL = ["R01", "R02", "R03", "R05", "R07", "R09", "R14", "R16", "R17", "R18"]
MEDIUM_POOL = ["R04", "R06", "R08", "R10", "R11", "R12", "R13", "R15"]


def random_event(rid: str) -> Event:
    return next(e for e in RANDOM_EVENTS if e.id == rid)
