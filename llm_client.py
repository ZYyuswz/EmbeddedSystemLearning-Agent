"""
通义千问（DashScope OpenAI 兼容）与 DeepSeek 的 HTTP 调用；无 Key 时由上层走检索兜底。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

# 默认 OpenAI 兼容端点（以各厂商最新文档为准，可通过环境变量覆盖）
DEFAULT_DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

INTENT_CATEGORIES = [
    "解释概念",
    "对比方案",
    "学习路径",
    "工具链与环境",
    "调试与排错",
    "外设与寄存器",
    "RTOS与任务",
    "网络与无线",
]


def load_secrets() -> None:
    """从本地 secrets 文件注入环境变量（不覆盖已存在的环境变量）。"""
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("config/secrets.env", "secrets.env", ".env"):
        path = os.path.join(base, name) if not os.path.isabs(name) else name
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v


def has_dashscope_key() -> bool:
    return bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())


def has_deepseek_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def chat_completion(
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    timeout: float = 90.0,
    max_tokens: int | None = None,
) -> str:
    if provider == "dashscope":
        if not has_dashscope_key():
            raise RuntimeError("未配置 DASHSCOPE_API_KEY")
        url = os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_URL).strip() or DEFAULT_DASHSCOPE_URL
        key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    elif provider == "deepseek":
        if not has_deepseek_key():
            raise RuntimeError("未配置 DEEPSEEK_API_KEY")
        url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_URL).strip() or DEFAULT_DEEPSEEK_URL
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    else:
        raise ValueError(f"未知 provider: {provider}")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=body)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = r.text[:500] if r.text else str(e)
            raise RuntimeError(f"LLM HTTP {r.status_code}: {detail}") from e
        data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"LLM 响应结构异常: {json.dumps(data, ensure_ascii=False)[:800]}") from e


def fallback_intent(query: str) -> str:
    q = query
    intents: list[str] = ["解释概念"]
    if any(k in q for k in ("对比", "区别", "还是", "vs", "VS", "哪个好")):
        intents.append("对比方案")
    if any(k in q for k in ("路径", "顺序", "先学", "怎么学", "入门")):
        intents.append("学习路径")
    if any(k in q for k in ("环境", "安装", "工具链", "IDE", "编译", "CMake", "GCC")):
        intents.append("工具链与环境")
    if any(k in q for k in ("调试", "报错", "不工作", "没输出", "死机", "复位", "HardFault")):
        intents.append("调试与排错")
    if any(k in q for k in ("寄存器", "GPIO", "UART", "SPI", "I2C", "ADC", "PWM", "定时器", "中断")):
        intents.append("外设与寄存器")
    if any(k in q for k in ("RTOS", "任务", "信号量", "互斥", "FreeRTOS", "优先级")):
        intents.append("RTOS与任务")
    if any(k in q for k in ("WiFi", "蓝牙", "BLE", "网络", "TCP", "MQTT", "鸿蒙", "OpenHarmony")):
        intents.append("网络与无线")
    intents = list(dict.fromkeys(intents))[:5]
    return json.dumps(intents, ensure_ascii=False) + "  # 规则回退意图"


def intents_from_llm_text(text: str) -> list[str]:
    found = [c for c in INTENT_CATEGORIES if c in text]
    if found:
        return list(dict.fromkeys(found))[:5]
    m = re.match(r"^\s*(\[[\s\S]*?\])\s*", text.strip())
    if m:
        try:
            arr = json.loads(m.group(1))
            if isinstance(arr, list):
                ok = [str(x) for x in arr if str(x) in INTENT_CATEGORIES]
                if ok:
                    return ok[:5]
        except json.JSONDecodeError:
            pass
    return ["解释概念"]


def format_intents_for_ui(intent_block: str) -> str:
    return "、".join(intents_from_llm_text(intent_block))


def recognize_intent(query: str, provider: str, model: str) -> str:
    cats = "\n".join(f'- "{c}"' for c in INTENT_CATEGORIES)
    prompt = f"""分析用户问题，从下列意图中选出所有相关的项（最多5个），输出为 JSON 数组，例如 ["解释概念","外设与寄存器"]，然后空一格写简短 # 注释。

意图列表：
{cats}

用户问题：{query}
"""
    messages = [{"role": "user", "content": prompt}]
    try:
        if (provider == "dashscope" and has_dashscope_key()) or (provider == "deepseek" and has_deepseek_key()):
            out = chat_completion(provider, model, messages, timeout=45.0, max_tokens=256)
            if not any(c in out for c in INTENT_CATEGORIES):
                return fallback_intent(query)
            return out
    except Exception:
        pass
    return fallback_intent(query)


def answer_from_kb_only(query: str, hits: list[tuple[dict, float]]) -> str:
    if not hits:
        return "（知识库中未检索到高度相关条目。请换关键词或选择对应开发板平台后重试。）"
    lines = [
        "（当前未配置可用的通义/DeepSeek API Key，或调用失败：以下为知识库检索摘要，非大模型整合回答。）\n",
    ]
    for i, (d, sc) in enumerate(hits, 1):
        body = (d.get("body") or "")[:500]
        lines.append(f"**{i}. {d.get('title', '')}**（匹配度参考 {sc:.3f}）\n{body}")
        if len(body) >= 500:
            lines.append("…\n")
    lines.append(
        "\n---\n在 `config/secrets.env` 中填写 `DASHSCOPE_API_KEY` 或 `DEEPSEEK_API_KEY` 后刷新页面，可获得通义/DeepSeek 的整合讲解。"
    )
    return "\n".join(lines)
