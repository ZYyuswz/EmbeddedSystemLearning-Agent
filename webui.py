"""
嵌入式系统学习 AGENT — Streamlit 主界面（无 Neo4j / 无医疗图谱 / 无 torch 主路径）。
"""
from __future__ import annotations

import os

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

PLATFORMS = ["全部", "STM32", "ESP32", "华为开发板", "沸腾开发板"]
PROVIDERS = ["通义千问", "DeepSeek"]
DEFAULT_MODELS = {"通义千问": "qwen-turbo", "DeepSeek": "deepseek-chat"}


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


def _build_answer_messages(intents_display: str, query: str, hits: list[tuple[dict, float]]) -> list[dict[str, str]]:
    system = (
        "你是嵌入式系统学习助手，面向 STM32、ESP32、华为开发板、沸腾开发板等场景的通用技术答疑。"
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


def main(is_admin: bool, usname: str) -> None:
    st.set_page_config(page_title="嵌入式系统学习 AGENT", layout="wide")
    st.title("嵌入式系统学习 AGENT")

    with st.sidebar:
        c1, _ = st.columns([1, 1])
        with c1:
            logo = os.path.join("img", "logo.jpg")
            if os.path.isfile(logo):
                st.image(logo, use_column_width=True)

        st.caption(
            f"欢迎，{'管理员' if is_admin else '用户'} **{usname}** · 本地知识库 + 通义/DeepSeek"
        )

        if "chat_windows" not in st.session_state:
            st.session_state.chat_windows = [[]]
            st.session_state.messages = [[]]

        if st.button("新建对话窗口"):
            st.session_state.chat_windows.append([])
            st.session_state.messages.append([])
            _rerun()

        window_labels = [f"对话窗口 {i + 1}" for i in range(len(st.session_state.chat_windows))]
        selected_window = st.selectbox("当前窗口", window_labels)
        active_window_index = int(selected_window.split()[1]) - 1

        platform = st.selectbox("开发板 / 平台侧重", PLATFORMS, index=0)
        provider_label = st.selectbox("大模型提供方", PROVIDERS, index=0)
        default_m = DEFAULT_MODELS[provider_label]
        model_name = st.text_input("模型名", value=st.session_state.get("llm_model", default_m), key="llm_model_input")
        st.session_state["llm_model"] = model_name

        if not _key_ok(provider_label):
            st.warning(
                f"「{provider_label}」未配置 API Key。请复制 `config/secrets.example.env` 为 `config/secrets.env` 并填写对应 Key。"
            )
        if not has_dashscope_key() and not has_deepseek_key():
            st.info("提示：通义与 DeepSeek 均未配置 Key 时，将仅使用知识库检索摘要。")

        show_ent = show_int = show_prompt = show_graph = False
        if is_admin:
            show_ent = st.checkbox("显示术语命中", value=False)
            show_int = st.checkbox("显示意图", value=False)
            show_prompt = st.checkbox("显示拼装上下文", value=False)
            show_graph = st.checkbox("显示轻量图谱源码", value=True)
        st.caption("知识库数据：`data/embedded/` · 不依赖 Neo4j")

        if st.button("返回登录"):
            st.session_state.logged_in = False
            st.session_state.admin = False
            _rerun()

    kb = get_kb()
    gloss = get_glossary()
    prov = _provider_key(provider_label)
    use_llm = _key_ok(provider_label)

    current_messages = st.session_state.messages[active_window_index]

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
                    with st.expander("知识点关联（轻量图谱）"):
                        st.code(message["mermaid"], language="text")

    if query := st.chat_input("输入嵌入式相关问题…", key=f"chat_input_{active_window_index}"):
        current_messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        status = st.empty()
        status.caption("检索知识库并识别意图…")

        hits = kb.search(query, None if platform == "全部" else platform, top_k=5)
        intent_raw = recognize_intent(query, prov, model_name.strip() or default_m)
        yitu = format_intents_for_ui(intent_raw)
        terms_hit = "、".join(gloss.find(query)) or "（无）"

        messages = _build_answer_messages(yitu, query, hits)
        prompt_text = messages[0]["content"] + "\n\n" + messages[1]["content"]

        nodes, edges = kb.subgraph_for_docs([d for d, _ in hits])
        mermaid = EmbeddedKB.mermaid_from_subgraph(nodes, edges)

        status.empty()

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
                with st.expander("知识点关联（Mermaid）"):
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

    st.session_state.messages[active_window_index] = current_messages
