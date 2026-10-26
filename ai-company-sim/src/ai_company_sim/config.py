"""路径、环境变量和模型配置。"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

PROMPTS_DIR = ROOT / "prompts"
STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "state.json"
HISTORY_DIR = STATE_DIR / "history"
LOGS_DIR = ROOT / "logs"
ACTIONS_DIR = LOGS_DIR / "actions"
CHATS_DIR = LOGS_DIR / "chats"
FEISHU_LOG_DIR = LOGS_DIR / "feishu"
OUTPUT_DIR = ROOT / "output"
CLOCK_FILE = ROOT.parent / "shared" / "clock.jsonl"  # 模拟时钟：AI 进度助手（../ai-assistant）唯一能从模拟器拿到的东西
ASSISTANT_DIR = ROOT.parent / "ai-assistant"
DIRECTOR_OUT_DIR = STATE_DIR / "director"  # 导演备注，玩家不看
DATA_DIR = Path(__file__).resolve().parent / "data"

# openai = 任何 OpenAI 兼容接口（DeepSeek、通义千问、Kimi、智谱……）；anthropic = Claude
LLM_PROVIDER = os.getenv("LLM_PROVIDER") or "openai"
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://api.deepseek.com"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS") or "8000")

# 评估 / 编剧类（P1、P5、P8）用强模型；演员类（P2、P3、P4、P6、P7）可以用便宜快速的模型。
_DEFAULT_MODELS = {"openai": ("deepseek-chat", "deepseek-chat"), "anthropic": ("claude-opus-5-5", "claude-sonnet-5-5")}
MODEL_DIRECTOR = os.getenv("MODEL_DIRECTOR") or _DEFAULT_MODELS.get(LLM_PROVIDER, ("", ""))[0]
MODEL_ACTOR = os.getenv("MODEL_ACTOR") or _DEFAULT_MODELS.get(LLM_PROVIDER, ("", ""))[1]

# offline = 不调用 API，用占位文本跑通流程（测试用）
LLM_MODE = os.getenv("LLM_MODE", "online")

FEISHU_SEND = os.getenv("FEISHU_SEND", "off")  # off | auto
FEISHU_SEND_INTERVAL = float(os.getenv("FEISHU_SEND_INTERVAL", "1.2"))
FEISHU_PLAYER_ID = os.getenv("FEISHU_PLAYER_ID", "")  # 用于让机器人 @ 你，见 README
# 飞书模式（uv run sim serve）：任务表链接（导演机器人每个时段比对一次）、模拟时间速度（模拟分钟 / 现实分钟）
FEISHU_BITABLE_URL = os.getenv("FEISHU_BITABLE_URL", "")
FEISHU_SPEED = float(os.getenv("FEISHU_SPEED") or "15")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 飞书自定义机器人是"按群"添加的：同一个角色在两个群里是两个机器人、两个 Webhook。
# 环境变量名：FEISHU_WEBHOOK_<群>_<角色拼音>，签名密钥：FEISHU_SECRET_<群>_<角色拼音>
# 某个角色没配置时，退回到该群的 DEFAULT 机器人，并在消息前加"角色名："。
GROUP_KEYS = {"品牌项目组": "TEAM", "小暖 S2 发布会筹备": "LAUNCH"}


def webhook_for(group: str, person_key: str) -> tuple[str, str, bool]:
    """返回 (webhook, secret, 是否是退回的 DEFAULT 机器人)。"""
    g = GROUP_KEYS.get(group, "TEAM")
    url = os.getenv(f"FEISHU_WEBHOOK_{g}_{person_key.upper()}", "")
    if url:
        return url, os.getenv(f"FEISHU_SECRET_{g}_{person_key.upper()}", ""), False
    return os.getenv(f"FEISHU_WEBHOOK_{g}_DEFAULT", ""), os.getenv(f"FEISHU_SECRET_{g}_DEFAULT", ""), True
