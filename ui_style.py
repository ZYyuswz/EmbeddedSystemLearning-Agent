"""全局静态样式注入：仅常量 CSS，勿拼接用户输入。"""

import streamlit as st

_APP_CSS = """
<style>
    /* 整页不横向溢出；flex 子项默认可收缩，避免主区把视口撑出横向滚动条 */
    section[data-testid="stAppViewContainer"] {
        width: 100% !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stAppViewContainer"] > .main {
        min-width: 0 !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stAppViewContainer"] > .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 52rem;
    }
    @media (min-width: 1100px) {
        section[data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 58rem;
        }
    }
    [data-testid="stChatMessage"] {
        padding-top: 0.65rem;
        padding-bottom: 0.65rem;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
        font-size: 1.08rem !important;
        line-height: 1.65 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] pre {
        background-color: #2d3748 !important;
        color: #e2e8f0 !important;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.92rem !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stAppViewContainer"] > .main [data-testid="stMarkdownContainer"] {
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    /* 气泡区域略收窄，避免一行过长（具体左右对齐由 Streamlit 默认布局承担） */
    [data-testid="stChatMessage"] {
        max-width: min(48rem, 100%);
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(61, 90, 102, 0.14);
        min-width: 220px !important;
        max-width: 260px !important;
        align-self: flex-start !important;
        max-height: 100dvh !important;
        /* 侧栏内容超出视口时保留纵向滚动条，避免被裁切到页面外 */
        overflow-y: auto !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
    }
    [data-testid="stSidebar"] > div {
        max-height: none !important;
        overflow-y: visible !important;
        overflow-x: hidden !important;
        min-height: 0 !important;
    }
    /* 侧栏内层 Emotion 容器 padding（原约 calc(1.375rem) 1.5rem 1.5rem；类名哈希会随 Streamlit 版本变化，若失效请用开发者工具重查该类名） */
    [data-testid="stSidebar"] .st-emotion-cache-kgpedg {
        padding: 0.5rem 0.85rem 0.65rem !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 0.45rem !important;
        padding-bottom: 0.35rem !important;
    }
    /* 侧栏：标题、说明、标签整体略小、行距收紧（不含主区） */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 0.98rem !important;
        line-height: 1.3 !important;
        margin-top: 0 !important;
        margin-bottom: 0.15rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
        font-size: 0.82rem !important;
        line-height: 1.35 !important;
        margin-bottom: 0.1rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaption"] {
        font-size: 0.75rem !important;
        line-height: 1.3 !important;
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
    }
    [data-testid="stSidebar"] hr {
        margin: 0.3rem 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] label p {
        font-size: 0.8rem !important;
        line-height: 1.3 !important;
    }
    [data-testid="stSidebar"] [data-testid="element-container"] {
        margin-bottom: 0.2rem !important;
    }
    /* 往期对话：列表区域固定高度内纵向滚动（侧栏整体过高时由侧栏自身滚动） */
    div[data-testid="stSidebar"] div[class*="st-key-conv_list"] {
        border-radius: 10px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        -webkit-overflow-scrolling: touch;
    }
    div[data-testid="stSidebar"] div[class*="st-key-conv_list"] button {
        border-radius: 10px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        line-height: 1.3 !important;
        padding: 0.28rem 0.5rem !important;
        min-height: 1.95rem !important;
        margin-bottom: 0.12rem !important;
    }
    div[data-testid="stSidebar"] div[class*="st-key-conv_list"] button[kind="primary"] {
        font-weight: 600 !important;
    }
</style>
"""


def inject_global_css() -> None:
    st.markdown(_APP_CSS, unsafe_allow_html=True)
