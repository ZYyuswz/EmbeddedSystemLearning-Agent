"""
嵌入式系统学习 AGENT — Streamlit 主界面（无 Neo4j / 无医疗图谱 / 无 torch 主路径）。
"""
from __future__ import annotations

import re

import streamlit as st

from embedded_glossary import GlossaryMatcher
from embedded_kb import EmbeddedKB
from llm_client import (
    answer_from_kb_only,
    chat_completion,
    format_intents_for_ui,
    has_dashscope_key,
    has_deepseek_key,
    load_secrets,
    recognize_intent,
)

load_secrets()

PLATFORMS = ["全部", "STM32", "ESP32", "华为开发板", "飞腾开发板"]
PROVIDERS = ["通义千问", "DeepSeek"]
DEFAULT_MODELS = {"通义千问": "qwen-turbo", "DeepSeek": "deepseek-chat"}

_SAMPLE_QUESTIONS = [
    "STM32 里 NVIC 中断优先级如何分组？",
    "ESP32 使用 ESP-IDF 做 WiFi Station 的大致步骤？",
    "飞腾开发板上做嵌入式 Linux 时常用哪些调试手段？",
]
_SAMPLE_LABELS = ["NVIC 与中断", "ESP-IDF WiFi", "飞腾 Linux 调试"]


def _rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


@st.cache_resource
def get_kb() -> EmbeddedKB:
    return EmbeddedKB()


@st.cache_resource
def get_glossary() -> GlossaryMatcher:
    return GlossaryMatcher()


def _provider_key(label: str) -> str:
    return "dashscope" if label == "通义千问" else "deepseek"


def _key_ok(label: str) -> bool:
    return has_dashscope_key() if label == "通义千问" else has_deepseek_key()


def _ensure_session_chat_lists() -> None:
    if "chat_windows" not in st.session_state:
        st.session_state.chat_windows = [[]]
        st.session_state.messages = [[]]
        st.session_state.chat_titles = ["新对话"]
        st.session_state.active_window_index = 0
        return
    titles = st.session_state.setdefault("chat_titles", [])
    wins = st.session_state.chat_windows
    while len(titles) < len(wins):
        titles.append("新对话")
    if len(titles) > len(wins):
        st.session_state.chat_titles = titles[: len(wins)]
    if "active_window_index" not in st.session_state:
        st.session_state.active_window_index = 0
    st.session_state.active_window_index = max(
        0, min(int(st.session_state.active_window_index), len(wins) - 1)
    )


def _is_auto_title(title: str) -> bool:
    if not title or title.startswith("新对话"):
        return True
    if re.match(r"^对话窗口 \d+$", title):
        return True
    if re.match(r"^对话 \d+$", title):
        return True
    return False


def _title_from_query(q: str) -> str:
    q = (q or "").strip().replace("\n", " ")
    if not q:
        return "新对话"
    if len(q) <= 26:
        return q
    return q[:26].rstrip() + "…"


def _conv_row_label(title: str) -> str:
    t = (title or "新对话").strip()
    if len(t) <= 34:
        return t
    return t[:32].rstrip() + "…"


def _build_answer_messages(intents_display: str, query: str, hits: list[tuple[dict, float]]) -> list[dict[str, str]]:
    system = (
        "你是嵌入式系统学习助手，面向 STM32、ESP32、华为开发板、飞腾开发板等场景的通用技术答疑。"
        "回答必须主要依据「参考资料」；若资料不足以严谨作答，请先说明依据有限，再给出谨慎的简短建议，"
        "不要编造具体手册未给出的寄存器位与引脚号。"
    )
    blocks: list[str] = []
    for i, (d, _) in enumerate(hits, 1):
        plats = d.get("platform") or []
        if isinstance(plats, str):
            plats = [plats]
        blocks.append(
            f"【{i}】{d.get('title', '')}\n适用平台: {','.join(plats)}\n来源: {d.get('source', '')}\n{d.get('body', '')}"
        )
    ref = "\n\n---\n\n".join(blocks) if blocks else "（无检索结果）"
    user = f"用户意图（参考）: {intents_display}\n\n参考资料:\n{ref}\n\n用户问题: {query}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _run_chat_turn(
    *,
    active_window_index: int,
    query: str,
    platform: str,
    provider_label: str,
    model_name: str,
    default_m: str,
    show_ent: bool,
    show_int: bool,
    show_prompt: bool,
    show_graph: bool,
) -> None:
    kb = get_kb()
    gloss = get_glossary()
    prov = _provider_key(provider_label)
    use_llm = _key_ok(provider_label)
    messages_state = st.session_state.messages
    current_messages = messages_state[active_window_index]

    was_empty = len(current_messages) == 0
    current_messages.append({"role": "user", "content": query})
    if was_empty:
        titles = st.session_state.chat_titles
        if active_window_index < len(titles) and _is_auto_title(titles[active_window_index]):
            titles[active_window_index] = _title_from_query(query)

    with st.chat_message("user"):
        st.markdown(query)

    with st.status("检索知识库并识别意图…", expanded=False) as status:
        hits = kb.search(query, None if platform == "全部" else platform, top_k=5)
        intent_raw = recognize_intent(query, prov, model_name.strip() or default_m)
        yitu = format_intents_for_ui(intent_raw)
        terms_hit = "、".join(gloss.find(query)) or "（无）"
        messages = _build_answer_messages(yitu, query, hits)
        prompt_text = messages[0]["content"] + "\n\n" + messages[1]["content"]
        nodes, edges = kb.subgraph_for_docs([d for d, _ in hits])
        mermaid = EmbeddedKB.mermaid_from_subgraph(nodes, edges)

        status.update(label="生成回答中…", state="running")

        if use_llm:
            try:
                last = chat_completion(
                    prov,
                    model_name.strip() or default_m,
                    messages,
                    timeout=120.0,
                    max_tokens=2048,
                )
            except Exception as e:
                last = f"**大模型调用失败：** {e}\n\n---\n\n" + answer_from_kb_only(query, hits)
        else:
            last = answer_from_kb_only(query, hits)

        status.update(label="完成", state="complete")

    with st.chat_message("assistant"):
        st.markdown(last)
        if show_ent:
            with st.expander("术语命中（glossary）"):
                st.write(terms_hit)
        if show_int:
            with st.expander("意图"):
                st.write(yitu)
        if show_prompt:
            with st.expander("上下文（发给模型的文本）"):
                st.text(prompt_text)
        if show_graph and mermaid:
            with st.expander("知识点关联（Mermaid 源码）"):
                st.code(mermaid, language="text")

    current_messages.append(
        {
            "role": "assistant",
            "content": last,
            "yitu": yitu,
            "prompt": prompt_text,
            "terms": terms_hit,
            "mermaid": mermaid or "",
        }
    )


def main(is_admin: bool, usname: str) -> None:
    _ensure_session_chat_lists()

    with st.sidebar:
        st.markdown("### 嵌入式系统学习 AGENT")
        st.caption("基于本地知识库与 TF-IDF 检索；结合所选模型生成回答。")
        meta_slot = st.empty()

        st.caption("历史对话")
        n = len(st.session_state.chat_windows)
        titles = st.session_state.chat_titles
        with st.container(height=240, border=True, key="conv_list"):
            for i in range(n):
                title = titles[i] if i < len(titles) else f"对话 {i + 1}"
                is_active = i == int(st.session_state.active_window_index)
                if st.button(
                    _conv_row_label(title),
                    key=f"conv_sel_{i}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    help=title,
                ):
                    st.session_state.active_window_index = i
                    _rerun()
        active_window_index = int(st.session_state.active_window_index)

        if st.button("新建对话", type="primary", use_container_width=True):
            st.session_state.chat_windows.append([])
            st.session_state.messages.append([])
            st.session_state.chat_titles.append("新对话")
            st.session_state.active_window_index = len(st.session_state.chat_windows) - 1
            _rerun()

        st.divider()
        st.caption("模型与平台")
        platform = st.selectbox("开发板 / 平台侧重", PLATFORMS, index=0)
        provider_label = st.selectbox("大模型提供方", PROVIDERS, index=0)
        default_m = DEFAULT_MODELS[provider_label]
        model_name = st.text_input(
            "模型名",
            value=st.session_state.get("llm_model", default_m),
            key="llm_model_input",
            help="通义示例：qwen-turbo；DeepSeek 示例：deepseek-chat（以厂商文档为准）。",
        )
        st.session_state["llm_model"] = model_name

        if not _key_ok(provider_label):
            with st.expander("API Key 未配置", expanded=False):
                st.warning(
                    f"「{provider_label}」未配置 API Key。请复制 `config/secrets.example.env` 为 `config/secrets.env` 并填写对应 Key。"
                )
        if not has_dashscope_key() and not has_deepseek_key():
            st.info("通义与 DeepSeek 均未配置 Key 时，将仅使用知识库检索摘要。")

        show_ent = show_int = show_prompt = show_graph = False
        if is_admin:
            st.divider()
            st.caption("管理员调试")
            show_ent = st.checkbox("显示术语命中", value=False)
            show_int = st.checkbox("显示意图", value=False)
            show_prompt = st.checkbox("显示拼装上下文", value=False)
            show_graph = st.checkbox("显示轻量图谱源码", value=True)

        meta_slot.markdown(
            f"当前平台侧重：**{platform}**\n\n当前模型：**{model_name.strip() or default_m}**"
        )

        role_label = "管理员" if is_admin else "用户"
        with st.popover(f"👤 {usname}", use_container_width=True):
            st.markdown(f"欢迎，**{role_label} {usname}**")
            st.caption("本地知识库检索 · 通义 / DeepSeek 模型回答")
            if st.button("返回登录", use_container_width=True, key="logout_in_popover"):
                st.session_state.logged_in = False
                st.session_state.admin = False
                _rerun()

    current_messages = st.session_state.messages[active_window_index]

    if not current_messages:
        st.info("在下方输入问题开始对话；也可点击示例发起一轮提问。")
        cols = st.columns(len(_SAMPLE_QUESTIONS))
        for i, (col, q, lab) in enumerate(zip(cols, _SAMPLE_QUESTIONS, _SAMPLE_LABELS)):
            with col:
                if st.button(lab, key=f"sample_q_{active_window_index}_{i}", help=q):
                    st.session_state[f"_inject_q_{active_window_index}"] = q
                    _rerun()

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if show_ent and message.get("terms"):
                    with st.expander("术语命中（glossary）"):
                        st.write(message["terms"])
                if show_int and message.get("yitu"):
                    with st.expander("意图"):
                        st.write(message["yitu"])
                if show_prompt and message.get("prompt"):
                    with st.expander("上下文（发给模型的文本）"):
                        st.text(message["prompt"])
                if message.get("mermaid") and (show_graph or not is_admin):
                    with st.expander("知识点关联（Mermaid 源码）"):
                        st.code(message["mermaid"], language="text")

    inj_key = f"_inject_q_{active_window_index}"
    pending = st.session_state.pop(inj_key, None)
    raw_query = st.chat_input("输入嵌入式相关问题…", key=f"chat_input_{active_window_index}")
    query = pending or raw_query
    if query:
        _run_chat_turn(
            active_window_index=active_window_index,
            query=query,
            platform=platform,
            provider_label=provider_label,
            model_name=model_name,
            default_m=default_m,
            show_ent=show_ent,
            show_int=show_int,
            show_prompt=show_prompt,
            show_graph=show_graph,
        )
