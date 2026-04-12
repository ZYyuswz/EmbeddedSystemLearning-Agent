# 嵌入式系统学习 AGENT

基于 **本地 JSON 知识库 + 字符 n-gram TF-IDF 检索** 与 **通义千问（DashScope）/ DeepSeek** 云端 API 的 RAG 问答；**不使用 Neo4j**。适合 STM32、ESP32、华为开发板、飞腾开发板等方向的通用概念学习与答疑（内容来自公开资料整理，具体引脚/寄存器以各厂商手册为准）。

详细设计见：`docs/嵌入式系统学习AGENT-改造说明.md`。

## 功能概要

- 登录 / 注册（`login.py`，用户数据在 `tmp_data/user_credentials.json`）
- 侧栏选择**平台侧重**、**大模型提供方**（通义 / DeepSeek）与**模型名**
- 检索 `data/embedded/embedded_kb.json`，将 Top-K 片段与意图（规则或 LLM）拼入 Prompt
- **轻量知识关联**：条目间 `related_ids` / `prerequisite_ids` 可生成 Mermaid 子图（加分项）
- 未配置 API Key 或调用失败时，自动降级为**知识库摘要**回答

## 环境

```bash
conda create -n embedded-agent python=3.10
conda activate embedded-agent
pip install -r requirements.txt
```

复制密钥模板并填写（**勿提交**真实 Key）：

```bash
copy config\secrets.example.env config\secrets.env
# 编辑 config\secrets.env，填写 DASHSCOPE_API_KEY 和/或 DEEPSEEK_API_KEY
```

## 运行

```bash
python -m streamlit run login.py --server.port 8502
```

浏览器访问 `http://localhost:8502` 。

## 配置说明

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope，通义千问（OpenAI 兼容接口） |
| `DEEPSEEK_API_KEY` | DeepSeek 官方 API Key |
| `DASHSCOPE_BASE_URL` / `DEEPSEEK_BASE_URL` | 可选，默认见 `llm_client.py` |

默认模型名可在侧栏修改：通义示例 `qwen-turbo`，DeepSeek 示例 `deepseek-chat`（以厂商文档为准）。

## 知识库维护

- 主数据：`data/embedded/embedded_kb.json`（字段含 `id`、`title`、`tags`、`platform`、`body`、`source`、`related_ids`、`prerequisite_ids`）
- 术语表：`data/embedded/glossary.txt`（一行一词，供管理端展示命中）

修改 JSON 后**刷新页面**即可（`@st.cache_resource` 在进程内缓存；开发时重启 Streamlit 可确保重载）。
