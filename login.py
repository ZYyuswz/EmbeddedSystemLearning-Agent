"""登录 / 注册入口页。"""
import streamlit as st
from user_data_storage import credentials, write_credentials, storage_file, Credentials
from webui import APP_NAME, APP_TAGLINE, main
from ui_style import inject_auth_css, inject_global_css

st.set_page_config(
    page_title=APP_NAME,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

# ── 初始化会话状态 ──
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "admin" not in st.session_state:
    st.session_state.admin = False
if "usname" not in st.session_state:
    st.session_state.usname = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


def login_page() -> None:
    """渲染登录表单并处理登录提交。"""
    with st.form("login_form"):
        st.markdown(
            "<p style='font-size:1.35rem;font-weight:700;color:#1a1a1a;margin:0 0 1.25rem;'>登录</p>",
            unsafe_allow_html=True,
        )
        username = st.text_input("用户名", value="", placeholder="请输入用户名")
        password = st.text_input("密码", value="", type="password", placeholder="请输入密码")
        submit = st.form_submit_button("登 录", type="primary", use_container_width=True)

        if submit:
            user_cred = credentials.get(username.strip())
            if user_cred and user_cred.password == password:
                st.session_state.logged_in = True
                st.session_state.admin = user_cred.is_admin
                st.session_state.usname = username.strip()
                st.toast("✓ 登录成功")
                st.rerun()
            else:
                st.error("用户名或密码错误，请重新输入。")

    # 表单外 —— 切换到注册
    st.markdown(
        """<div style="text-align:center;margin-top:1.1rem;">
          <span style="color:#9ca3af;font-size:0.875rem;">还没有账号？</span>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("创建账号", key="goto_register", use_container_width=True, type="secondary"):
        st.session_state.auth_mode = "register"
        st.rerun()


def register_page() -> None:
    """渲染注册表单并处理注册提交（含非空、长度与一致性校验）。"""
    with st.form("register_form"):
        st.markdown(
            "<p style='font-size:1.35rem;font-weight:700;color:#1a1a1a;margin:0 0 1.25rem;'>创建账号</p>",
            unsafe_allow_html=True,
        )
        new_username = st.text_input("用户名", value="", placeholder="至少 3 个字符")
        new_password = st.text_input("密码", value="", type="password", placeholder="至少 6 个字符")
        confirm_password = st.text_input("确认密码", value="", type="password", placeholder="再次输入密码")
        register_submit = st.form_submit_button("注 册", type="primary", use_container_width=True)

        if register_submit:
            username = new_username.strip()
            if not username or not new_password:
                st.error("用户名和密码不能为空。")
            elif len(username) < 3:
                st.error("用户名至少需要 3 个字符。")
            elif len(new_password) < 6:
                st.error("密码至少需要 6 个字符。")
            elif new_password != confirm_password:
                st.error("两次输入的密码不一致。")
            elif username in credentials:
                st.error("用户名已存在，请使用其他用户名。")
            else:
                new_user = Credentials(username, new_password, False)
                credentials[username] = new_user
                write_credentials(storage_file, credentials)
                st.success(f"✓ 账号 {username} 创建成功，请登录！")
                st.session_state.auth_mode = "login"
                st.rerun()

    # 表单外 —— 返回登录
    st.markdown(
        """<div style="text-align:center;margin-top:1.1rem;">
          <span style="color:#9ca3af;font-size:0.875rem;">已有账号？</span>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("返回登录", key="goto_login", use_container_width=True, type="secondary"):
        st.session_state.auth_mode = "login"
        st.rerun()


if __name__ == "__main__":
    if not st.session_state.logged_in:
        inject_auth_css()

        # ── 顶部品牌区 ──
        st.markdown(
            """
<div style="text-align:center;padding:3rem 0 2rem;">
  <div style="display:inline-flex;align-items:center;gap:0.7rem;margin-bottom:0.65rem;">
    <div style="width:42px;height:42px;background:linear-gradient(135deg,#4f6ef7,#3b5ef5);
                border-radius:12px;display:flex;align-items:center;justify-content:center;
                font-size:1.3rem;flex-shrink:0;box-shadow:0 4px 12px rgba(79,110,247,0.3);">⚡</div>
    <span style="font-size:1.6rem;font-weight:800;color:#1a1a1a;letter-spacing:-0.03em;">
      嵌入式系统学习助手
    </span>
  </div>
  <p style="color:#9ca3af;font-size:0.9rem;margin:0;">
    本地知识库 · 通义千问 / DeepSeek · RAG 答疑
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )

        # ── 表单区域（不需要额外居中列，_AUTH_CSS 已限宽） ──
        if st.session_state.auth_mode == "login":
            login_page()
        else:
            register_page()

    else:
        main(st.session_state.admin, st.session_state.usname)
