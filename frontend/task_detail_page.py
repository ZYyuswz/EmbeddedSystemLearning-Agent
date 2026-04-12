"""任务详情页面。"""
from __future__ import annotations

import streamlit as st

from frontend.api_client import BackendApiClient


def render_task_detail_page(client: BackendApiClient, task_id: str) -> None:
    """渲染任务详情页。"""
    st.subheader("任务详情")
    if not task_id:
        st.info("请在 URL 查询参数中提供 taskId")
        return
    try:
        detail = client.get_task(task_id)
        st.json(detail)
    except Exception as exc:
        st.error(f"任务查询失败: {exc}")
