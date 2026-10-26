"""调用大模型。

- LLM_PROVIDER=openai（默认）：任何 OpenAI 兼容接口，例如 DeepSeek。用 JSON 模式 + pydantic 校验，不合格就带着错误重试。
- LLM_PROVIDER=anthropic：Claude，用原生结构化输出。
- LLM_MODE=offline：不联网，用调用方给的占位结果（stub）跑通流程。
"""

import json
import re
import time
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)

_client = None
_NO_JSON_MODE: set[str] = set()   # 不支持 response_format 的模型（试过一次就记住）
USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0}


def offline() -> bool:
    return config.LLM_MODE == "offline"


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)


# ================================================================== OpenAI 兼容（DeepSeek 等）

def _oa_client():
    global _client
    if _client is None:
        import openai
        if not config.LLM_API_KEY:
            raise SystemExit("没有配置 LLM_API_KEY。打开 .env 填上你的 API Key（见 README 第 1 步）。")
        _client = openai.OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, timeout=600, max_retries=2)
    return _client


_retrying: dict[str, bool] = {}


def _oa_chat(label: str, messages: list[dict], model: str, json_mode: bool, strict: bool = False) -> str:
    return _oa_chat_with(label, messages, model, json_mode, strict, config.LLM_MAX_TOKENS)


def _oa_chat_with(label: str, messages: list[dict], model: str, json_mode: bool, strict: bool, max_tokens: int) -> str:
    import openai
    kw = {"model": model, "messages": messages, "max_tokens": max_tokens,
          "temperature": 0.5 if strict else 1.1}   # 导演评估要稳，演员说话要有变化
    if json_mode and model not in _NO_JSON_MODE:
        kw["response_format"] = {"type": "json_object"}
    resp = None
    for attempt in range(4):
        try:
            resp = _oa_client().chat.completions.create(**kw)
            break
        except openai.AuthenticationError:
            raise SystemExit("API 认证失败：检查 .env 里的 LLM_API_KEY 和 LLM_BASE_URL。") from None
        except openai.BadRequestError as e:
            if "response_format" in kw and ("response_format" in str(e) or "json" in str(e).lower()):
                kw.pop("response_format")       # 有的模型（如推理模型）不支持 JSON 模式，改为从文本里提取
                _NO_JSON_MODE.add(model)
                continue
            if "max_tokens" in str(e) and kw["max_tokens"] > config.LLM_MAX_TOKENS:
                kw["max_tokens"] = config.LLM_MAX_TOKENS     # 这个模型不支持更大的额度，退回原值
                continue
            raise SystemExit(f"[{label}] 请求被拒绝：{e}") from None
        except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            if attempt == 3:
                raise SystemExit(f"[{label}] 接口连续出错：{e}。稍后重跑同一个命令即可。") from None
            time.sleep(5 * (attempt + 1))
    if resp is None:
        raise SystemExit(f"[{label}] 请求失败，稍后重跑同一个命令。")
    USAGE["calls"] += 1
    if resp.usage:
        USAGE["input_tokens"] += resp.usage.prompt_tokens or 0
        USAGE["output_tokens"] += resp.usage.completion_tokens or 0
    choice = resp.choices[0]
    content = (choice.message.content or "").strip()
    if choice.finish_reason == "length":
        # 会"先思考再回答"的模型，思考也占输出额度：额度用完时内容可能是空的或半截。加大额度再试一次。
        bigger = min(kw["max_tokens"] * 2, 32000)
        if bigger > kw["max_tokens"] and not _retrying.get(label):
            print(f"  [{label}] 输出额度不够（{kw['max_tokens']}），加大到 {bigger} 重试……")
            _retrying[label] = True
            try:
                return _oa_chat_with(label, messages, model, json_mode, strict, bigger)
            finally:
                _retrying.pop(label, None)
        print(f"  [{label}] 输出被截断（max_tokens={kw['max_tokens']}）。")
    return content


def _extract_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    return text[a:b + 1] if a >= 0 and b > a else text


def _schema_hint(schema: type[BaseModel]) -> str:
    return ("\n\n【输出格式】只输出一个 JSON 对象（不要 Markdown、不要解释），必须符合下面的 JSON Schema。"
            "所有字符串用中文；时间写成 HH:MM。\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False))


def _oa_json(label: str, prompt: str, schema: type[T], system: str, model: str, strict: bool) -> T:
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt + _schema_hint(schema)}]
    last_err = ""
    for _ in range(3):
        text = _oa_chat(label, messages, model, json_mode=True, strict=strict)
        try:
            return schema.model_validate_json(_extract_json(text))
        except (ValidationError, ValueError) as e:
            last_err = str(e)[:1500]
            print(f"  [{label}] 输出格式不对，带着错误信息重试……")
            messages = messages + [{"role": "assistant", "content": text[:6000]},
                                   {"role": "user", "content": f"上面的输出不符合要求：\n{last_err}\n请修正后重新输出完整的 JSON 对象。"}]
    raise SystemExit(f"[{label}] 模型连续 3 次没有输出合格的 JSON。可以重跑同一个命令，或在 .env 里换一个更强的 MODEL_DIRECTOR。\n{last_err}")


# ================================================================== Claude（可选）

def _an_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(max_retries=3)
    return _client


def _an_call(label: str, messages: list[dict], system: str, model: str, effort: str, schema=None):
    import anthropic
    # 服务端拒答回退（fallbacks: "default"）+ 流式请求（导演类输出 + 思考可能很长）
    kw = {"model": model, "max_tokens": 32000 if model == config.MODEL_DIRECTOR else 16000,
          "output_config": {"effort": effort}, "betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default",
          "system": system or anthropic.omit, "messages": messages}
    if schema:
        kw["output_format"] = schema
    for _ in range(3):
        try:
            with _an_client().beta.messages.stream(**kw) as stream:
                resp = stream.get_final_message()
        except anthropic.AuthenticationError:
            raise SystemExit("Claude API 认证失败：检查 .env 里的 ANTHROPIC_API_KEY。") from None
        except anthropic.BadRequestError as e:
            raise SystemExit(f"[{label}] 请求被拒绝：{e.message}") from None
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError):
            time.sleep(5)
            continue
        USAGE["calls"] += 1
        USAGE["input_tokens"] += resp.usage.input_tokens
        USAGE["output_tokens"] += resp.usage.output_tokens
        if resp.stop_reason in ("refusal", "max_tokens"):
            print(f"  [{label}] stop_reason={resp.stop_reason}，重试一次……")
            continue
        if not schema:
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        if resp.parsed_output is not None:
            return resp.parsed_output
    raise SystemExit(f"[{label}] 连续失败，稍后重跑同一个命令。")


# ================================================================== 对外接口

def json_call(label: str, prompt: str, schema: type[T], stub: Callable[[], T], *,
              system: str = "", model: str | None = None, effort: str = "medium") -> T:
    """要求模型按 pydantic schema 输出 JSON。"""
    if offline():
        return stub()
    model = model or config.MODEL_ACTOR
    if config.LLM_PROVIDER == "anthropic":
        return _an_call(label, [{"role": "user", "content": prompt}], system, model, effort, schema)
    return _oa_json(label, prompt, schema, system, model, strict=effort == "high")


def text_call(label: str, messages: list[dict] | str, stub: Callable[[], str], *,
              system: str = "", model: str | None = None, effort: str = "medium") -> str:
    if offline():
        return stub()
    model = model or config.MODEL_ACTOR
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if config.LLM_PROVIDER == "anthropic":
        return _an_call(label, messages, system, model, effort)
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    return _oa_chat(label, msgs, model, json_mode=False, strict=effort == "high")
