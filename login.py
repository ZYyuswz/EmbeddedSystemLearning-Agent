import streamlit as st
from user_data_storage import credentials, write_credentials, storage_file, Credentials
from webui import main
from ui_style import inject_global_css

st.set_page_config(
    page_title="嵌入式系统学习 AGENT",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

# 初始化会话状态
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "admin" not in st.session_state:
    st.session_state.admin = False
if "usname" not in st.session_state:
    st.session_state.usname = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


def _auth_shell_css() -> None:
    """未登录：隐藏侧栏占位；主区拉满；表单字号加大（静态字符串）。"""
    st.markdown(
        """
<style>
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }
  section[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
  }
  form[data-testid="stForm"] input {
    font-size: 1.12rem !important;
    min-height: 2.65rem !important;
  }
  form[data-testid="stForm"] [data-baseweb="input"] {
    font-size: 1.12rem !important;
    min-height: 2.65rem !important;
  }
  form[data-testid="stForm"] label p {
    font-size: 1rem !important;
  }
  form[data-testid="stForm"] button[kind="formSubmit"] {
    font-size: 1.05rem !important;
    min-height: 2.6rem !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def login_page() -> None:
    with st.form("login_form"):
        st.subheader("登录")
        username = st.text_input("用户名", value="", placeholder="请输入用户名")
        password = st.text_input("密码", value="", type="password", placeholder="请输入密码")
        submit = st.form_submit_button("登录", type="primary", use_container_width=True)

        if submit:
            user_cred = credentials.get(username)
            if user_cred and user_cred.password == password:
                st.success("登录成功！")
                st.session_state.logged_in = True
                st.session_state.admin = user_cred.is_admin
                st.session_state.usname = username
                st.rerun()
            else:
                st.error("用户名或密码错误，请重新输入。")


def register_page() -> None:
    with st.form("register_form"):
        st.subheader("注册")
        new_username = st.text_input("设置用户名", value="", placeholder="新用户名")
        new_password = st.text_input("设置密码", value="", type="password", placeholder="新密码")
        is_admin = False
        register_submit = st.form_submit_button("注册", type="primary", use_container_width=True)

        if register_submit:
            if new_username in credentials:
                st.error("用户名已存在，请使用其他用户名。")
            else:
                new_user = Credentials(new_username, new_password, is_admin)
                credentials[new_username] = new_user
                write_credentials(storage_file, credentials)
                st.success(f"用户 {new_username} 注册成功！请登录。")
                st.session_state.auth_mode = "login"
                st.rerun()


if __name__ == "__main__":
    if not st.session_state.logged_in:
        _auth_shell_css()

        top_l, top_r = st.columns([3.6, 1.9], vertical_alignment="center")
        with top_l:
            st.markdown(
                """
<div class="auth-headline">
  <h2 style="margin:0;padding:0;font-size:1.55rem;line-height:1.25;">嵌入式学习助手</h2>
  <p style="margin:0.35rem 0 0;padding:0;font-size:1rem;line-height:1.45;color:#5a6578;">
    本地知识库 + 通义 / DeepSeek · RAG 答疑
  </p>
</div>
                """,
                unsafe_allow_html=True,
            )
        with top_r:
            c_login, c_reg = st.columns(2)
            with c_login:
                if st.button(
                    "登录",
                    key="auth_tab_login",
                    use_container_width=True,
                    type="primary" if st.session_state.auth_mode == "login" else "secondary",
                ):
                    st.session_state.auth_mode = "login"
                    st.rerun()
            with c_reg:
                if st.button(
                    "注册",
                    key="auth_tab_register",
                    use_container_width=True,
                    type="primary" if st.session_state.auth_mode == "register" else "secondary",
                ):
                    st.session_state.auth_mode = "register"
                    st.rerun()

        st.divider()

        _, mid, _ = st.columns([1, 1.35, 1])
        with mid:
            if st.session_state.auth_mode == "login":
                login_page()
            else:
                register_page()
    else:
        main(st.session_state.admin, st.session_state.usname)
