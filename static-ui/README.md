# 静态 UI 示意（`static-ui/`）

| 文件 | 说明 |
|------|------|
| `auth.html` | 登录 + 注册（顶栏右上切换、居中表单）。 |
| `chat-user.html` / `chat-admin.html` | 登录后主界面：侧栏 **左上** 标题与当前平台/模型；**可滚动**会话列表 + 自动生成标题示意；**左下**悬停账户区 + 返回登录；主区 **左右气泡**（`assets/chat.css`）。 |
| `assets/chat.css` | 仅对话页引用的布局与字号。 |

`login.html` / `register.html` 跳转至 `auth.html`。

打开 `index.html` 浏览全部链接。
