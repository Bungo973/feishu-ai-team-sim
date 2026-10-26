import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)   # 只认自己的 .env

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BITABLE_URL = os.getenv("FEISHU_BITABLE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "") or None
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
CLOCK_FILE = (ROOT / os.getenv("CLOCK_FILE", "../shared/clock.jsonl")).resolve()
IGNORE_SENDERS = {x for x in os.getenv("IGNORE_SENDERS", "").split(",") if x}
PROXY_SENDERS = {x for x in os.getenv("PROXY_SENDERS", "").split(",") if x}

TASK_TABLE = os.getenv("TASK_TABLE", "任务进度")    # 链接里带了 ?table= 时，以链接里的那张表为准
REPORT_TABLE = os.getenv("REPORT_TABLE", "日报")
DATA_FILE = ROOT / "data" / "助手.json"   # 你的私聊会话、自动推送开关、推过哪些
OUT_DIR = ROOT / "核对记录"                # 每次核对的输入材料和结果，都存一份
