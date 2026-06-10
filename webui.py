"""
嵌入式系统学习助手 — Streamlit 主界面。
"""
from __future__ import annotations

import os
import re

import streamlit as st

from embedded_glossary import GlossaryMatcher
from embedded_kb import EmbeddedKB
from frontend.api_client import BackendApiClient
from frontend.board_assistant_page import render_board_assistant_page
from llm_client import (
    answer_from_kb_only,
    chat_completion_stream,
    format_intents_for_ui,
    has_dashscope_key,
    has_deepseek_key,
    load_secrets,
    recognize_intent,
)

load_secrets()

# ── 全局常量 ──
APP_NAME = "嵌入式系统学习助手"
APP_TAGLINE = "本地知识库 + 通义 / DeepSeek · RAG 答疑"

PLATFORMS = ["全部", "STM32", "ESP32", "华为开发板", "飞腾开发板"]
PROVIDERS = ["通义千问", "DeepSeek"]
DEFAULT_MODELS = {"通义千问": "qwen-turbo", "DeepSeek": "deepseek-chat"}
MODEL_OPTIONS = {
    "通义千问": ["qwen-turbo", "qwen-plus", "qwen-max"],
    "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
}
_CUSTOM_MODEL_LABEL = "自定义…"
_LLM_MODEL_STATE_KEY = {
    "通义千问": "llm_model_input_dashscope",
    "DeepSeek": "llm_model_input_deepseek",
}
NAV_PAGES = ["学习问答", "板卡助手"]

_SAMPLE_QUESTIONS = [
    "STM32 里 NVIC 中断优先级如何分组？",
    "ESP32 使用 ESP-IDF 做 WiFi Station 的大致步骤？",
    "飞腾开发板上做嵌入式 Linux 时常用哪些调试手段？",
]
_SAMPLE_LABELS = ["NVIC 与中断", "ESP-IDF WiFi", "飞腾 Linux 调试"]


def _rerun() -> None:
    """兼容新旧版本 Streamlit 的重渲染。"""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


@st.cache_resource
def get_kb() -> EmbeddedKB:
    """加载并缓存嵌入式知识库。"""
    return EmbeddedKB()


@st.cache_resource
def get_glossary() -> GlossaryMatcher:
    """加载并缓存术语表。"""
    return GlossaryMatcher()


def _provider_key(label: str) -> str:
    """将显示名称转换为内部 provider 键。"""
    return "dashscope" if label == "通义千问" else "deepseek"


def _key_ok(label: str) -> bool:
    """检查对应 provider 的 API Key 是否已配置。"""
    return has_dashscope_key() if label == "通义千问" else has_deepseek_key()


def _ensure_session_chat_lists() -> None:
    """初始化或修复历史对话状态。"""
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
    """判断对话标题是否仍是自动生成的默认名称。"""
    if not title or title.startswith("新对话"):
        return True
    if re.match(r"^对话窗口 \d+$", title):
        return True
    if re.match(r"^对话 \d+$", title):
        return True
    return False


def _title_from_query(q: str) -> str:
    """从首条提问截取对话标题。"""
    q = (q or "").strip().replace("\n", " ")
    if not q:
        return "新对话"
    if len(q) <= 26:
        return q
    return q[:26].rstrip() + "…"


def _build_backend_client() -> BackendApiClient:
    """构建板卡助手后端客户端。"""
    base_url = os.getenv("BOARD_ASSISTANT_API_BASE_URL", "http://127.0.0.1:8000")
    token = os.getenv("BOARD_ASSISTANT_API_TOKEN", "dev-token")
    return BackendApiClient(base_url=base_url, token=token)


def _conv_row_label(title: str) -> str:
    """截断过长的对话标题用于侧边栏展示。"""
    t = (title or "新对话").strip()
    if len(t) <= 30:
        return t
    return t[:28].rstrip() + "…"


def _select_model(provider_label: str, default_m: str) -> str:
    """侧边栏模型选择：常用下拉 + 自定义输入，返回最终模型名。"""
    state_key = _LLM_MODEL_STATE_KEY[provider_label]
    options = MODEL_OPTIONS.get(provider_label, [default_m])
    saved = st.session_state.get(state_key, default_m)
    default_index = options.index(saved) if saved in options else len(options)
    choice = st.selectbox(
        "模型",
        options + [_CUSTOM_MODEL_LABEL],
        index=default_index,
        key=f"model_select_{provider_label}",
    )
    if choice == _CUSTOM_MODEL_LABEL:
        custom = st.text_input(
            "自定义模型名",
            value=saved if saved not in options else "",
            key=f"model_custom_{provider_label}",
            placeholder="填写控制台支持的模型名",
        )
        model_name = custom.strip() or default_m
    else:
        model_name = choice
    st.session_state[state_key] = model_name
    return model_name


def _delete_conversation(index: int) -> None:
    """删除指定历史对话，并将激活索引收敛到有效范围。"""
    for key in ("chat_windows", "messages", "chat_titles"):
        seq = st.session_state.get(key)
        if isinstance(seq, list) and 0 <= index < len(seq):
            seq.pop(index)
    if not st.session_state.chat_windows:
        st.session_state.chat_windows = [[]]
        st.session_state.messages = [[]]
        st.session_state.chat_titles = ["新对话"]
    st.session_state.active_window_index = max(
        0, min(int(st.session_state.active_window_index), len(st.session_state.chat_windows) - 1)
    )


def _clear_all_conversations() -> None:
    """清空全部历史对话，仅保留一个空白新对话。"""
    st.session_state.chat_windows = [[]]
    st.session_state.messages = [[]]
    st.session_state.chat_titles = ["新对话"]
    st.session_state.active_window_index = 0


def _build_answer_messages(
    intents_display: str, query: str, hits: list[tuple[dict, float]]
) -> list[dict[str, str]]:
    """构建发送给大模型的完整消息列表（system + user）。"""
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
    show_ent: bool = False,
    show_int: bool = False,
    show_prompt: bool = False,
    show_graph: bool = False,
) -> None:
    """执行一轮对话：检索 → 意图识别 → 大模型回答（或 KB 摘要兜底）。"""
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

    # 将调试开关传给 chat_message 块内的内联渲染
    st.session_state["_cur_show_ent"]    = show_ent
    st.session_state["_cur_show_int"]    = show_int
    st.session_state["_cur_show_prompt"] = show_prompt
    st.session_state["_cur_show_graph"]  = show_graph

    with st.status("检索知识库…", expanded=False) as status:
        hits = kb.search(query, None if platform == "全部" else platform, top_k=5)
        intent_raw = recognize_intent(query, prov, model_name.strip() or default_m)
        yitu = format_intents_for_ui(intent_raw)
        terms_hit = "、".join(gloss.find(query)) or "（无）"
        messages = _build_answer_messages(yitu, query, hits)
        prompt_text = messages[0]["content"] + "\n\n" + messages[1]["content"]
        nodes, edges = kb.subgraph_for_docs([d for d, _ in hits])
        mermaid = EmbeddedKB.mermaid_from_subgraph(nodes, edges)
        status.update(label="检索完成", state="complete")

    with st.chat_message("assistant"):
        last = ""
        if use_llm:
            try:
                acc: list[str] = []
                model_id = model_name.strip() or default_m

                def _answer_stream():
                    for piece in chat_completion_stream(
                        prov, model_id, messages, timeout=120.0, max_tokens=2048
                    ):
                        acc.append(piece)
                        yield piece

                if hasattr(st, "write_stream"):
                    st.write_stream(_answer_stream)
                    last = "".join(acc).strip()
                    if not last:
                        last = "（模型未返回可见文本，请检查模型名与网络。）"
                else:
                    for piece in chat_completion_stream(
                        prov, model_id, messages, timeout=120.0, max_tokens=2048
                    ):
                        acc.append(piece)
                    last = "".join(acc).strip() or "（模型未返回可见文本。）"
                    st.markdown(last)
            except Exception as e:
                last = f"**大模型调用失败：** {e}\n\n---\n\n" + answer_from_kb_only(query, hits)
                st.markdown(last)
        else:
            last = answer_from_kb_only(query, hits)
            st.markdown(last)

        # 读取调用处传入的调试开关（_run_chat_turn 外层已获取）
        _show_ent    = st.session_state.get("_cur_show_ent", False)
        _show_int    = st.session_state.get("_cur_show_int", False)
        _show_prompt = st.session_state.get("_cur_show_prompt", False)
        _show_graph  = st.session_state.get("_cur_show_graph", True)
        if _show_ent:
            with st.expander("术语命中", expanded=False):
                st.write(terms_hit)
        if _show_int:
            with st.expander("意图识别", expanded=False):
                st.write(yitu)
        if _show_prompt:
            with st.expander("拼装上下文", expanded=False):
                st.text(prompt_text)
        if mermaid and _show_graph:
            with st.expander("知识点关联", expanded=False):
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
    """主界面入口：侧边栏导航 + 对话区 / 板卡助手。"""
    from ui_style import inject_toolbar

    _ensure_session_chat_lists()

    # ── 注入左上角工具栏（通过 JS append 到父页面 body，不占布局流）──
    inject_toolbar(list(st.session_state.get("chat_titles", [])))

    with st.sidebar:
        # ── 品牌标识 ──
        st.markdown(
            """
<div style="display:flex;align-items:center;gap:0.55rem;padding:0.25rem 0 0.6rem;">
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#4f6ef7,#3b5ef5);
              border-radius:7px;display:flex;align-items:center;justify-content:center;
              font-size:1rem;flex-shrink:0;box-shadow:0 2px 8px rgba(79,110,247,0.25);">⚡</div>
  <span style="font-size:0.95rem;font-weight:700;color:#1a1a1a;letter-spacing:-0.01em;">
    嵌入式学习助手
  </span>
</div>
            """,
            unsafe_allow_html=True,
        )

        # ── 页面导航 ──
        st.caption("导航")
        app_page = st.selectbox("页面", NAV_PAGES, index=0, label_visibility="collapsed")

        st.divider()

        # ── 仅学习问答页显示历史对话管理 ──
        if app_page == "学习问答":
            # 新建对话按钮（DeepSeek 风格，空心边框）
            if st.button("＋  开启新对话", key="new_conv_top", use_container_width=True):
                st.session_state.chat_windows.append([])
                st.session_state.messages.append([])
                st.session_state.chat_titles.append("新对话")
                st.session_state.active_window_index = len(st.session_state.chat_windows) - 1
                _rerun()

            n = len(st.session_state.chat_windows)
            titles = st.session_state.chat_titles
            renaming_index = st.session_state.get("renaming_conv_index")
            active_window_index = int(st.session_state.active_window_index)

            # 对话列表（无外框容器，直接铺开）
            with st.container(key="conv_list"):
                for i in range(n):
                    title = titles[i] if i < len(titles) else f"对话 {i + 1}"
                    is_active = i == active_window_index
                    if renaming_index == i:
                        new_title = st.text_input(
                            "重命名",
                            value=title,
                            key=f"conv_rename_input_{i}",
                            label_visibility="collapsed",
                        )
                        ok_col, cancel_col = st.columns(2)
                        if ok_col.button("保存", key=f"conv_rename_ok_{i}", use_container_width=True, type="primary"):
                            st.session_state.chat_titles[i] = new_title.strip() or "新对话"
                            st.session_state.renaming_conv_index = None
                            _rerun()
                        if cancel_col.button("取消", key=f"conv_rename_cancel_{i}", use_container_width=True):
                            st.session_state.renaming_conv_index = None
                            _rerun()
                        continue
                    # 每行：对话名（宽）+ 编辑图标 + 删除图标
                    row_sel, row_edit, row_del = st.columns([8, 1, 1])
                    if row_sel.button(
                        _conv_row_label(title),
                        key=f"conv_sel_{i}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                        help=title,
                    ):
                        st.session_state.active_window_index = i
                        _rerun()
                    # ✏ 铅笔朝左；🗑 删除
                    if row_edit.button("✏", key=f"conv_edit_{i}", help="重命名"):
                        st.session_state.renaming_conv_index = i
                        _rerun()
                    if row_del.button("×", key=f"conv_del_{i}", help="删除"):
                        _delete_conversation(i)
                        _rerun()

            st.divider()

            # ── 模型配置 ──
            st.caption("模型配置")
            platform = st.selectbox("平台侧重", PLATFORMS, index=0)
            provider_label = st.selectbox("大模型", PROVIDERS, index=0)
            default_m = DEFAULT_MODELS[provider_label]
            model_name = _select_model(provider_label, default_m)

            if not _key_ok(provider_label):
                st.markdown(
                    """<div style="background:#fffbeb;border:1px solid #fde68a;
                    border-radius:6px;padding:0.4rem 0.6rem;font-size:0.75rem;color:#b45309;margin-top:0.25rem;">
                    ⚠ 未配置 API Key，将使用知识库摘要回答</div>""",
                    unsafe_allow_html=True,
                )

            # ── 管理员专属调试面板 ──
            if is_admin:
                st.divider()
                st.caption("管理员调试")
                st.session_state.setdefault("show_ent", False)
                st.session_state.setdefault("show_int", False)
                st.session_state.setdefault("show_prompt", False)
                st.session_state.setdefault("show_graph", True)
                st.session_state["show_ent"] = st.checkbox(
                    "显示术语命中", value=st.session_state["show_ent"], key="dbg_ent"
                )
                st.session_state["show_int"] = st.checkbox(
                    "显示意图识别", value=st.session_state["show_int"], key="dbg_int"
                )
                st.session_state["show_prompt"] = st.checkbox(
                    "显示拼装上下文", value=st.session_state["show_prompt"], key="dbg_prompt"
                )
                st.session_state["show_graph"] = st.checkbox(
                    "显示知识图谱", value=st.session_state["show_graph"], key="dbg_graph"
                )
        else:
            active_window_index = int(st.session_state.active_window_index)
            platform = "全部"
            provider_label = PROVIDERS[0]
            default_m = DEFAULT_MODELS[provider_label]
            model_name = st.session_state.get(_LLM_MODEL_STATE_KEY[provider_label], default_m)

        st.divider()

        # ── 账户 ──
        role_label = "管理员" if is_admin else "用户"
        with st.popover(f"👤 {usname}  ·  {role_label}", use_container_width=True):
            st.markdown(
                f"<p style='color:#1a1a1a;font-weight:600;margin:0 0 0.2rem;'>{role_label} · {usname}</p>",
                unsafe_allow_html=True,
            )
            st.caption("本地知识库检索 · 大模型问答")
            if st.button("退出登录", use_container_width=True, type="secondary"):
                st.session_state.logged_in = False
                st.session_state.admin = False
                _rerun()

    # ── 主内容区 ──
    if app_page == "板卡助手":
        render_board_assistant_page(_build_backend_client())
        return

    # ── 学习问答页 ──
    current_messages = st.session_state.messages[active_window_index]

    # 读取管理员调试开关
    show_ent    = is_admin and st.session_state.get("show_ent", False)
    show_int    = is_admin and st.session_state.get("show_int", False)
    show_prompt = is_admin and st.session_state.get("show_prompt", False)
    show_graph  = is_admin and st.session_state.get("show_graph", True)

    if not current_messages:
        st.markdown(
            """
<div style="text-align:center;padding:2rem 0 1.5rem;">
  <div style="font-size:2rem;margin-bottom:0.5rem;">💬</div>
  <p style="color:#9ca3af;font-size:0.9rem;margin:0;">
    在下方输入嵌入式相关问题，或点击示例快速开始
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns(len(_SAMPLE_QUESTIONS))
        for i, (col, q, lab) in enumerate(zip(cols, _SAMPLE_QUESTIONS, _SAMPLE_LABELS)):
            with col:
                if st.button(
                    lab,
                    key=f"sample_q_{active_window_index}_{i}",
                    help=q,
                    use_container_width=True,
                ):
                    st.session_state[f"_inject_q_{active_window_index}"] = q
                    _rerun()

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if show_ent and message.get("terms"):
                    with st.expander("术语命中", expanded=False):
                        st.write(message["terms"])
                if show_int and message.get("yitu"):
                    with st.expander("意图识别", expanded=False):
                        st.write(message["yitu"])
                if show_prompt and message.get("prompt"):
                    with st.expander("拼装上下文", expanded=False):
                        st.text(message["prompt"])
                if message.get("mermaid") and show_graph:
                    with st.expander("知识点关联", expanded=False):
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
