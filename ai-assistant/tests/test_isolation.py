"""隔离检查：助手的代码里不能出现模拟器的任何东西。运行：uv run python tests/test_isolation.py"""
from pathlib import Path

BANNED = ["ai_company_sim", "ai-company-sim", "state/", "output/", "logs/", "director", "events", "剧本"]
src = Path(__file__).resolve().parents[1] / "src"
bad = [(p.name, w) for p in src.rglob("*.py") for w in BANNED if w in p.read_text(encoding="utf-8")]
assert not bad, f"发现和模拟器有关的引用：{bad}"
print(f"✅ 隔离检查通过：{len(list(src.rglob('*.py')))} 个代码文件，没有引用模拟器的代码、存档、日志和剧本。")
