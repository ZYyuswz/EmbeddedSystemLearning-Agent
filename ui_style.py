"""全局静态样式注入：白色主题设计系统，对齐 DeepSeek 风格。

设计语言：白底极简，浅灰侧边栏，蓝色强调（#4f6ef7），参考 DeepSeek Chat。
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────
#  全局 CSS：主界面（登录后）—— 白色主题
# ─────────────────────────────────────────────────────────────
_APP_CSS = """
<style>
/* ── 设计变量 ── */
:root {
  --bg-base:        #ffffff;
  --bg-sidebar:     #f7f7f8;
  --bg-surface:     #f4f4f5;
  --bg-hover:       #ebebec;
  --bg-input:       #ffffff;
  --border:         #e5e5e6;
  --border-focus:   #4f6ef7;
  --accent:         #4f6ef7;
  --accent-hover:   #3b5ef5;
  --accent-dim:     rgba(79,110,247,0.08);
  --accent-text:    #4f6ef7;
  --green:          #16a34a;
  --green-bg:       #f0fdf4;
  --green-border:   #bbf7d0;
  --yellow:         #d97706;
  --yellow-bg:      #fffbeb;
  --yellow-border:  #fde68a;
  --red:            #dc2626;
  --red-bg:         #fef2f2;
  --red-border:     #fecaca;
  --blue-bg:        #eff6ff;
  --blue-border:    #bfdbfe;
  --text-primary:   #1a1a1a;
  --text-secondary: #6b7280;
  --text-muted:     #9ca3af;
  --text-placeholder: #c4c4c8;
  --radius-sm:      8px;
  --radius-md:      12px;
  --radius-lg:      20px;
  --shadow-sm:      0 1px 3px rgba(0,0,0,0.08);
  --shadow-md:      0 4px 12px rgba(0,0,0,0.08);
}

/* ── 整体背景 ── */
.stApp,
section[data-testid="stAppViewContainer"] {
  background: var(--bg-base) !important;
}
section[data-testid="stAppViewContainer"] > .main {
  background: var(--bg-base) !important;
}
section[data-testid="stAppViewContainer"] > .main .block-container {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
  max-width: 56rem;
}
@media (min-width: 1200px) {
  section[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: 62rem;
  }
}

/* ── 全局文字颜色 ── */
body, p, li, span, div, label {
  color: var(--text-primary);
}

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
  background: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border) !important;
  min-width: 230px !important;
  max-width: 265px !important;
}
[data-testid="stSidebar"] > div {
  background: var(--bg-sidebar) !important;
}
[data-testid="stSidebar"] .block-container {
  padding-top: 0.75rem !important;
  padding-bottom: 1rem !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  font-size: 0.92rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin-bottom: 0.2rem !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  font-size: 0.8rem !important;
  line-height: 1.4 !important;
  color: var(--text-secondary) !important;
}
[data-testid="stSidebar"] [data-testid="stCaption"] {
  font-size: 0.7rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted) !important;
  margin: 0.6rem 0 0.3rem !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
  margin: 0.5rem 0 !important;
}
[data-testid="stSidebar"] [data-testid="element-container"] {
  margin-bottom: 0.2rem !important;
}
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] .stSelectbox label p {
  font-size: 0.78rem !important;
  color: var(--text-secondary) !important;
}

/* ── 侧边栏 "开启新对话" 按钮 —— DeepSeek 空心圆角款式 ── */
div[data-testid="stSidebar"] div[class*="st-key-new_conv_top"] button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text-primary) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  height: 2.4rem !important;
  letter-spacing: 0.01em !important;
  transition: background 0.15s ease, border-color 0.15s ease !important;
  margin-bottom: 0.5rem !important;
}
div[data-testid="stSidebar"] div[class*="st-key-new_conv_top"] button:hover {
  background: var(--bg-hover) !important;
  border-color: #c4c4c8 !important;
  color: var(--text-primary) !important;
}

/* ── 历史对话列表容器 —— 去掉边框和背景，直接铺开 ── */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"] {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* 每个条目所在的 element-container 行 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="element-container"] {
  margin-bottom: 0 !important;
}

/* 列宽布局：整行 padding 清零，防止溢出 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 0 !important;
  overflow: hidden !important;
}
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"] {
  padding: 0 1px !important;
  min-width: 0 !important;
}
/* 文字列可压缩，操作列固定不压缩 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:first-child {
  flex: 1 1 auto !important;
  overflow: hidden !important;
}
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:not(:first-child) {
  flex: 0 0 26px !important;
  width: 26px !important;
  max-width: 26px !important;
  overflow: hidden !important;
}

/* ── 对话名称选择按钮（宽列）—— 纯文本行样式 ── */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:first-child button {
  all: unset !important;
  display: block !important;
  width: 100% !important;
  box-sizing: border-box !important;
  cursor: pointer !important;
  font-size: 0.85rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
  color: var(--text-primary) !important;
  padding: 0.4rem 0.4rem 0.4rem 0.75rem !important;
  border-radius: 6px !important;
  border-left: 2px solid transparent !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  transition: background 0.12s ease !important;
}
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:first-child button:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}
/* 激活态：左侧蓝色竖线 + 极浅背景，不用色块 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:first-child button[kind="primary"] {
  background: var(--bg-surface) !important;
  border-left-color: var(--accent) !important;
  font-weight: 500 !important;
  color: var(--text-primary) !important;
}

/* ── 操作按钮（✏ 编辑、× 删除）—— 22×22 正方形，图标严格居中，默认隐藏 ── */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:not(:first-child) button {
  all: unset !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  width: 22px !important;
  height: 22px !important;
  min-width: 22px !important;
  min-height: 22px !important;
  border-radius: 5px !important;
  font-size: 0.8rem !important;
  line-height: 22px !important;
  text-align: center !important;
  color: var(--text-muted) !important;
  opacity: 0 !important;
  transition: opacity 0.15s ease, background 0.12s ease, color 0.12s ease !important;
}
/* 按钮内 p/span 子元素也居中 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:not(:first-child) button p,
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:not(:first-child) button span {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
}
/* 整行悬停时操作按钮显现 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="stHorizontalBlock"]:hover
  [data-testid="column"]:not(:first-child) button {
  opacity: 1 !important;
}
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:not(:first-child) button:hover {
  background: var(--bg-hover) !important;
  color: var(--text-secondary) !important;
  opacity: 1 !important;
}
/* 删除（× 按钮）悬停时红色 */
div[data-testid="stSidebar"] div[class*="st-key-conv_list"]
  [data-testid="column"]:last-child button:hover {
  background: #fef2f2 !important;
  color: var(--red) !important;
}

/* ── Popover（账户弹出）—— 强制白底深色文字 ── */
[data-testid="stPopoverBody"],
[data-testid="stPopoverBody"] * {
  background: #ffffff !important;
  color: var(--text-primary) !important;
}
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] span,
[data-testid="stPopoverBody"] div {
  color: var(--text-primary) !important;
}
[data-testid="stPopoverBody"] [data-testid="stCaption"],
[data-testid="stPopoverBody"] [data-testid="stCaption"] p {
  color: var(--text-muted) !important;
}
[data-testid="stPopover"] > div {
  background: #ffffff !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-md) !important;
}

/* ── 全局按钮 ── */
.stButton > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 500 !important;
  font-size: 0.875rem !important;
  transition: all 0.15s ease !important;
  color: var(--text-primary) !important;
}
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
}
.stButton > button[kind="secondary"] {
  background: var(--bg-base) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-secondary) !important;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
  border-color: #c4c4c8 !important;
}

/* ── 输入框 ── */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
  font-size: 0.9rem !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color: var(--text-placeholder) !important;
}
.stTextInput label p,
.stTextArea label p,
.stNumberInput label p,
.stSelectbox label p {
  font-size: 0.82rem !important;
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
}

/* ── 下拉选择框 ── */
.stSelectbox > div > div {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
}

/* ── 复选框 ── */
.stCheckbox label span {
  font-size: 0.85rem !important;
  color: var(--text-secondary) !important;
}

/* ── 对话气泡 —— DeepSeek 风格 ── */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
  display: none !important;
}
[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0.5rem 0 !important;
  gap: 0 !important;
}
/* 用户：右侧蓝色气泡 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  flex-direction: row-reverse !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
  [data-testid="stChatMessageContent"] {
  background: var(--accent) !important;
  border: none !important;
  border-radius: 16px 16px 4px 16px !important;
  padding: 0.6rem 1rem !important;
  max-width: 78% !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
  [data-testid="stChatMessageContent"] p {
  color: #fff !important;
  font-size: 0.95rem !important;
  line-height: 1.65 !important;
}
/* 助手：左侧白底浅边框 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
  [data-testid="stChatMessageContent"] {
  background: var(--bg-base) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px 16px 16px 16px !important;
  padding: 0.75rem 1.1rem !important;
  box-shadow: var(--shadow-sm) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
  [data-testid="stChatMessageContent"] p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
  [data-testid="stChatMessageContent"] li {
  color: var(--text-primary) !important;
  font-size: 0.95rem !important;
  line-height: 1.7 !important;
}
/* 代码块 */
[data-testid="stChatMessage"] pre {
  background: #f8f9fa !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  padding: 0.75rem 1rem !important;
  font-size: 0.87rem !important;
  overflow-x: auto !important;
}
[data-testid="stChatMessage"] code {
  background: #f1f1f2 !important;
  border-radius: 4px !important;
  font-size: 0.87rem !important;
  color: #c7254e !important;
  padding: 1px 4px !important;
}

/* ── 聊天输入框 ── */
[data-testid="stChatInput"] {
  background: var(--bg-base) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-sm) !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
[data-testid="stChatInput"] textarea {
  color: var(--text-primary) !important;
  background: transparent !important;
}
[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-placeholder) !important;
}
[data-testid="stChatInput"] button {
  color: var(--accent) !important;
}

/* ── 提示框 ── */
[data-testid="stAlertContainer"],
[data-testid="stAlert"] {
  border-radius: var(--radius-sm) !important;
  font-size: 0.875rem !important;
}
[data-testid="stAlert"] p {
  color: inherit !important;
}
div[class*="stInfo"] {
  background: var(--blue-bg) !important;
  border: 1px solid var(--blue-border) !important;
  color: #1d4ed8 !important;
}
div[class*="stSuccess"] {
  background: var(--green-bg) !important;
  border: 1px solid var(--green-border) !important;
  color: var(--green) !important;
}
div[class*="stWarning"] {
  background: var(--yellow-bg) !important;
  border: 1px solid var(--yellow-border) !important;
  color: var(--yellow) !important;
}
div[class*="stError"] {
  background: var(--red-bg) !important;
  border: 1px solid var(--red-border) !important;
  color: var(--red) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--bg-base) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  color: var(--text-secondary) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.55rem 0.9rem !important;
  background: var(--bg-base) !important;
}
[data-testid="stExpander"] summary:hover {
  background: var(--bg-surface) !important;
  color: var(--text-primary) !important;
}

/* ── 容器卡片（border=True）── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
  background: var(--bg-base) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  padding: 0.9rem 1rem !important;
}

/* ── 标题 ── */
h1, h2, h3 {
  color: var(--text-primary) !important;
  font-weight: 700 !important;
}
h1 { font-size: 1.4rem !important; }
h2 { font-size: 1.2rem !important; }
h3 { font-size: 1.0rem !important; }

[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
  color: var(--text-primary) !important;
  font-size: 1.1rem !important;
  font-weight: 700 !important;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.5rem;
  margin-bottom: 0.75rem;
}

/* ── 分割线 ── */
hr {
  border-color: var(--border) !important;
  margin: 0.65rem 0 !important;
}

/* ── Status 进度条 ── */
[data-testid="stStatusWidget"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  font-size: 0.875rem !important;
  color: var(--text-secondary) !important;
}
[data-testid="stStatusWidget"] p {
  color: var(--text-secondary) !important;
}

/* ── 步骤进度条（板卡助手）── */
.ba-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 0 0 1.25rem;
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.ba-steps .ba-step {
  flex: 1;
  text-align: center;
  font-size: 0.8rem;
  font-weight: 500;
  padding: 0.5rem 0.4rem;
  color: var(--text-muted);
  background: transparent;
  border-right: 1px solid var(--border);
  white-space: nowrap;
}
.ba-steps .ba-step:last-child { border-right: none; }
.ba-steps .ba-step.done {
  color: var(--green);
  background: var(--green-bg);
}
.ba-steps .ba-step.done::before { content: "✓ "; }
.ba-steps .ba-step.active {
  color: var(--accent);
  background: var(--accent-dim);
  font-weight: 700;
  border-bottom: 2px solid var(--accent);
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
}

/* ── 滚动条 ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── 隐藏 Streamlit 水印、原生导航栏、顶部横条 Header ── */
footer, #MainMenu { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
/* 收起侧边栏时出现的顶部蓝色横条（stAppHeader）直接隐藏 */
header[data-testid="stHeader"],
header.stAppHeader {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  visibility: hidden !important;
}

/* 原生侧边栏展开按钮：移到屏幕左上角不可见位置，保留 JS 可 click */
[data-testid="collapsedControl"] {
  position: fixed !important;
  top: -200px !important;
  left: 0 !important;
  z-index: -1 !important;
  pointer-events: auto !important;
  opacity: 0 !important;
}

/* ── 顶部固定工具栏（类 DeepSeek 左上角三按钮）── */
#esa-toolbar {
  position: fixed;
  top: 10px;
  left: 12px;
  z-index: 99999;
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(255,255,255,0.92);
  border: 1px solid #e5e5e6;
  border-radius: 24px;
  padding: 5px 10px;
  box-shadow: 0 1px 8px rgba(0,0,0,0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: opacity 0.2s ease;
}
#esa-toolbar:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.12);
}
#esa-toolbar button {
  all: unset;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #374151;
  transition: background 0.15s ease, color 0.15s ease;
  font-size: 0;
}
#esa-toolbar button:hover {
  background: #f0f0f1;
  color: #1a1a1a;
}
#esa-toolbar button svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  pointer-events: none;
}

/* ── 搜索对话浮层 ── */
#esa-search-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 99998;
  background: rgba(0,0,0,0.25);
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
}
#esa-search-overlay.visible {
  display: flex;
}
#esa-search-box {
  background: #fff;
  border: 1px solid #e5e5e6;
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  width: 460px;
  max-width: calc(100vw - 32px);
  overflow: hidden;
}
#esa-search-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #f0f0f1;
}
#esa-search-input-wrap svg {
  width: 16px;
  height: 16px;
  color: #9ca3af;
  flex-shrink: 0;
}
#esa-search-input {
  all: unset;
  flex: 1;
  font-size: 0.95rem;
  color: #1a1a1a;
}
#esa-search-input::placeholder { color: #c4c4c8; }
#esa-search-close {
all: unset;
cursor: pointer;
width: 24px;
height: 24px;
display: flex;
align-items: center;
justify-content: center;
border-radius: 6px;
color: #9ca3af;
font-size: 1rem;
flex-shrink: 0;
transition: background 0.12s ease, color 0.12s ease;
}
#esa-search-close:hover { background: #f0f0f1; color: #374151; }
#esa-search-results {
max-height: 320px;
  overflow-y: auto;
  padding: 0.4rem 0;
}
.esa-search-item {
  padding: 0.55rem 1rem;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.1s ease;
}
.esa-search-item:hover,
.esa-search-item.active {
  background: #f4f4f5;
  color: #1a1a1a;
}
.esa-search-empty {
  padding: 1.5rem 1rem;
  text-align: center;
  color: #9ca3af;
  font-size: 0.875rem;
}

/* ── 管理员调试区域 ── */
.admin-debug-panel {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.75rem;
  margin-top: 0.5rem;
}
.admin-debug-panel p,
.admin-debug-panel label span,
.admin-debug-panel [data-testid="stCheckbox"] span {
  color: #92400e !important;
  font-size: 0.78rem !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────
#  登录 / 注册页专用 CSS —— 白色主题
# ─────────────────────────────────────────────────────────────
_AUTH_CSS = """
<style>
/* 隐藏侧栏与工具栏 */
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
#MainMenu,
footer,
[data-testid="stToolbar"] {
  display: none !important;
}

/* 整页白色背景 */
.stApp,
section[data-testid="stAppViewContainer"],
section[data-testid="stAppViewContainer"] > .main {
  background: #f7f7f8 !important;
}

/* 内容区居中 */
section[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 440px !important;
  padding: 0 1rem !important;
  margin: 0 auto !important;
}

/* 表单卡片 */
form[data-testid="stForm"] {
  background: #ffffff !important;
  border: 1px solid #e5e5e6 !important;
  border-radius: 16px !important;
  padding: 2rem 2rem 1.75rem !important;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06) !important;
}
form[data-testid="stForm"] input {
  background: #f7f7f8 !important;
  border: 1px solid #e5e5e6 !important;
  border-radius: 8px !important;
  color: #1a1a1a !important;
  font-size: 0.95rem !important;
  min-height: 2.6rem !important;
}
form[data-testid="stForm"] input:focus {
  border-color: #4f6ef7 !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 3px rgba(79,110,247,0.1) !important;
}
form[data-testid="stForm"] input::placeholder {
  color: #c4c4c8 !important;
}
form[data-testid="stForm"] label p {
  font-size: 0.85rem !important;
  color: #6b7280 !important;
  font-weight: 500 !important;
}
form[data-testid="stForm"] button[kind="formSubmit"] {
  background: #4f6ef7 !important;
  border: none !important;
  border-radius: 10px !important;
  color: #fff !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  min-height: 2.65rem !important;
  letter-spacing: 0.01em;
}
form[data-testid="stForm"] button[kind="formSubmit"]:hover {
  background: #3b5ef5 !important;
}

/* 登录页警告/错误框 */
[data-testid="stAlertContainer"] {
  border-radius: 8px !important;
  font-size: 0.875rem !important;
}
div[class*="stError"] {
  background: #fef2f2 !important;
  border: 1px solid #fecaca !important;
  color: #dc2626 !important;
}
div[class*="stSuccess"] {
  background: #f0fdf4 !important;
  border: 1px solid #bbf7d0 !important;
  color: #16a34a !important;
}

/* 页面整体文字 */
body, p, span, div, label {
  color: #1a1a1a;
}
</style>
"""


def inject_global_css() -> None:
    """注入登录后主界面的全局样式。"""
    st.markdown(_APP_CSS, unsafe_allow_html=True)


def inject_auth_css() -> None:
    """注入登录 / 注册页的专用样式（未登录时调用）。"""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)


def inject_toolbar(conv_titles: list[str]) -> None:
    """注入左上角固定工具栏（仿 DeepSeek）：侧边栏开关、搜索对话、新建对话。

    通过 JS 将工具栏 DOM 直接 append 到父页面 body，完全脱离 Streamlit 布局流。
    使用 st.components.v1.html + height=0 避免占用任何页面空间。

    Args:
        conv_titles: 当前所有对话标题列表，用于搜索浮层展示。
    """
    import json
    import streamlit.components.v1 as components

    titles_json = json.dumps(conv_titles, ensure_ascii=False)

    # 工具栏 HTML + CSS + JS，通过 JS 注入到父页面 body
    toolbar_code = f"""
<script>
(function() {{
  var d = window.parent.document;

  // ── 注入样式（只注入一次）──
  if (!d.getElementById('esa-style')) {{
    var style = d.createElement('style');
    style.id = 'esa-style';
    style.textContent = `
      #esa-toolbar {{
        position: fixed;
        top: 10px;
        left: 12px;
        z-index: 99999;
        display: flex;
        align-items: center;
        gap: 2px;
        background: rgba(255,255,255,0.93);
        border: 1px solid #e5e5e6;
        border-radius: 24px;
        padding: 5px 10px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.08);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
      }}
      #esa-toolbar button {{
        all: unset;
        cursor: pointer;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        color: #374151;
        transition: background 0.15s ease;
      }}
      #esa-toolbar button:hover {{ background: #f0f0f1; color: #1a1a1a; }}
      #esa-toolbar button svg {{ width: 18px; height: 18px; pointer-events: none; }}
      #esa-search-overlay {{
        display: none;
        position: fixed;
        inset: 0;
        z-index: 99998;
        background: rgba(0,0,0,0.25);
        align-items: flex-start;
        justify-content: center;
        padding-top: 80px;
      }}
      #esa-search-overlay.visible {{ display: flex; }}
      #esa-search-box {{
        background: #fff;
        border: 1px solid #e5e5e6;
        border-radius: 14px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        width: 460px;
        max-width: calc(100vw - 32px);
        overflow: hidden;
      }}
      #esa-search-input-wrap {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.85rem 1rem;
        border-bottom: 1px solid #f0f0f1;
      }}
      #esa-search-input-wrap svg {{ width:16px; height:16px; color:#9ca3af; flex-shrink:0; }}
      #esa-search-input {{
        all: unset;
        flex: 1;
        font-size: 0.95rem;
        color: #1a1a1a;
      }}
      #esa-search-input::placeholder {{ color: #c4c4c8; }}
      #esa-search-close {{
        all: unset;
        cursor: pointer;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        color: #9ca3af;
        font-size: 1rem;
        flex-shrink: 0;
        transition: background 0.12s ease, color 0.12s ease;
      }}
      #esa-search-close:hover {{ background: #f0f0f1; color: #374151; }}
      #esa-search-results {{ max-height: 320px; overflow-y: auto; padding: 0.4rem 0; }}
      .esa-search-item {{
        padding: 0.55rem 1rem;
        font-size: 0.875rem;
        color: #374151;
        cursor: pointer;
        transition: background 0.1s ease;
      }}
      .esa-search-item:hover, .esa-search-item.active {{ background: #f4f4f5; color: #1a1a1a; }}
      .esa-search-empty {{ padding: 1.5rem 1rem; text-align: center; color: #9ca3af; font-size: 0.875rem; }}
    `;
    d.head.appendChild(style);
  }}

  // ── 注入工具栏 DOM（只创建一次，后续更新标题）──
  if (!d.getElementById('esa-toolbar')) {{
    var toolbar = d.createElement('div');
    toolbar.id = 'esa-toolbar';
    toolbar.innerHTML = `
      <button title="切换侧边栏" onclick="esaToggleSidebar()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
        </svg>
      </button>
      <button title="搜索对话" onclick="esaOpenSearch()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="7"/>
          <line x1="16.5" y1="16.5" x2="21" y2="21"/>
        </svg>
      </button>
      <button title="新建对话" onclick="esaNewConv()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9"/>
          <line x1="12" y1="8" x2="12" y2="16"/>
          <line x1="8" y1="12" x2="16" y2="12"/>
        </svg>
      </button>
    `;
    d.body.appendChild(toolbar);

    // ── 搜索浮层 ──
    var overlay = d.createElement('div');
    overlay.id = 'esa-search-overlay';
    overlay.innerHTML = `
      <div id="esa-search-box">
        <div id="esa-search-input-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>
          </svg>
          <input id="esa-search-input" placeholder="搜索对话..."
                 oninput="esaSearch()" onkeydown="esaSearchKey(event)" />
          <button id="esa-search-close" onclick="esaCloseSearch()" title="关闭">✕</button>
        </div>
        <div id="esa-search-results"></div>
      </div>
    `;
    // 点击背景遮罩关闭（用 onclick 内联，避免因 DOM 重建丢失绑定）
    overlay.setAttribute('onclick', 'if(event.target===this)esaCloseSearch()');
    d.body.appendChild(overlay);

    // 全局 Escape 键关闭搜索框（绑在父页面 document，只绑一次）
    if (!d._esaEscBound) {{
      d._esaEscBound = true;
      d.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
          var ov = d.getElementById('esa-search-overlay');
          if (ov && ov.classList.contains('visible')) {{
            ov.classList.remove('visible');
            e.stopPropagation();
          }}
        }}
      }});
    }}
  }}

  // ── 更新对话标题（每次 Streamlit 重渲染都更新）──
  d._esaTitles = {titles_json};

  // ── 工具栏功能函数（挂到父窗口）──
  d.defaultView.esaToggleSidebar = function() {{
    var expand = d.querySelector('[data-testid="collapsedControl"] button');
    var collapse = d.querySelector('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebar"] button[aria-label]');
    if (expand) {{
      expand.click();
    }} else if (collapse) {{
      collapse.click();
    }} else {{
      d.defaultView.dispatchEvent(new KeyboardEvent('keydown', {{key: '[', bubbles: true}}));
    }}
  }};

  d.defaultView.esaCloseSearch = function() {{
    var ov = d.getElementById('esa-search-overlay');
    if (ov) ov.classList.remove('visible');
  }};

  d.defaultView.esaOpenSearch = function() {{
    var overlay = d.getElementById('esa-search-overlay');
    overlay.classList.add('visible');
    setTimeout(function() {{
      var inp = d.getElementById('esa-search-input');
      if (inp) {{ inp.value = ''; inp.focus(); }}
      d.defaultView.esaSearch();
    }}, 50);
  }};

  d.defaultView.esaSearch = function() {{
    var titles = d._esaTitles || [];
    var q = (d.getElementById('esa-search-input').value || '').toLowerCase().trim();
    var results = d.getElementById('esa-search-results');
    var filtered = q ? titles.filter(function(t) {{ return t.toLowerCase().indexOf(q) !== -1; }}) : titles;
    if (filtered.length === 0) {{
      results.innerHTML = '<div class="esa-search-empty">未找到匹配的对话</div>';
      return;
    }}
    results.innerHTML = filtered.map(function(t) {{
      return '<div class="esa-search-item" onclick="esaSelectItem(this)" data-title="' + t.replace(/"/g,'&quot;') + '">' + t + '</div>';
    }}).join('');
  }};

  d.defaultView.esaSearchKey = function(e) {{
    var items = d.querySelectorAll('.esa-search-item');
    var idx = d._esaSearchIdx || -1;
    if (e.key === 'ArrowDown') {{ idx = Math.min(idx+1, items.length-1); }}
    else if (e.key === 'ArrowUp') {{ idx = Math.max(idx-1, 0); }}
    else if (e.key === 'Enter') {{ if (idx >= 0 && items[idx]) d.defaultView.esaSelectItem(items[idx]); return; }}
    else if (e.key === 'Escape') {{ d.getElementById('esa-search-overlay').classList.remove('visible'); return; }}
    d._esaSearchIdx = idx;
    items.forEach(function(it, i) {{ it.classList.toggle('active', i === idx); }});
    if (items[idx]) items[idx].scrollIntoView({{block:'nearest'}});
  }};

  d.defaultView.esaSelectItem = function(el) {{
    d.getElementById('esa-search-overlay').classList.remove('visible');
    var title = el.getAttribute('data-title');
    // 精确匹配对话标题，同时排除新建对话按钮（以"开启"开头或包含"开启新对话"）
    var btns = d.querySelectorAll('[data-testid="stSidebar"] button');
    for (var i = 0; i < btns.length; i++) {{
      var txt = btns[i].textContent.trim();
      // 排除"开启新对话"按钮
      if (txt.indexOf('开启新对话') !== -1) {{ continue; }}
      // 精确匹配：按钮文本与标题完全相同，或按钮文本以标题开头（截断省略号情况）
      if (txt === title || title.indexOf(txt.replace(/\u2026$/, '')) === 0) {{
        btns[i].click(); break;
      }}
    }}
  }};

  d.defaultView.esaNewConv = function() {{
    var sidebar = d.querySelector('[data-testid="stSidebar"]');
    var isOpen = sidebar && sidebar.offsetWidth > 50;
    var doClick = function() {{
      // 匹配侧边栏里的"开启新对话"按钮（key=new_conv_top）
      var btns = d.querySelectorAll('[data-testid="stSidebar"] button');
      for (var i = 0; i < btns.length; i++) {{
        var txt = btns[i].textContent.trim();
        if (txt.indexOf('开启新对话') !== -1) {{ btns[i].click(); return; }}
      }}
    }};
    if (!isOpen) {{ d.defaultView.esaToggleSidebar(); setTimeout(doClick, 400); }}
    else {{ doClick(); }}
  }};

}})();
</script>
"""
    components.html(toolbar_code, height=0)
