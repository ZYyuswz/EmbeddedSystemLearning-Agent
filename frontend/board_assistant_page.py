"""板卡助手页面。"""
from __future__ import annotations

from typing import Any, Sequence

import streamlit as st

from frontend.api_client import BackendApiClient

# 四段流程步骤
_STEP_LABELS = ["① 识别板卡", "② 同步资料", "③ 生成工程", "④ 烧录校验"]


def _get_path(data: Any, path: str) -> Any:
    """按点号路径从嵌套字典中取值，缺失返回 None。"""
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _render_kv_grid(data: dict[str, Any], fields: Sequence[tuple[str, str]]) -> None:
    """以「标签 + 值」网格展示关键字段（空值自动跳过）。"""
    rows: list[tuple[str, Any]] = [
        (label, _get_path(data, path))
        for label, path in fields
        if _get_path(data, path) not in (None, "", [], {})
    ]
    if not rows:
        return
    cols = st.columns(min(len(rows), 4))
    for idx, (label, value) in enumerate(rows):
        with cols[idx % len(cols)]:
            st.markdown(
                f"""<div style="background:var(--bg-elevated,#22263a);border:1px solid var(--border,rgba(79,142,247,.15));
                border-radius:8px;padding:0.6rem 0.75rem;">
                <div style="font-size:0.7rem;color:var(--text-muted,#64748b);text-transform:uppercase;
                letter-spacing:.06em;margin-bottom:0.2rem;">{label}</div>
                <div style="font-size:0.9rem;font-weight:600;color:var(--text-primary,#e2e8f0);
                word-break:break-all;">{value}</div></div>""",
                unsafe_allow_html=True,
            )


def _raw_expander(data: Any, label: str = "原始响应") -> None:
    """将后端原始 JSON 收进折叠区。"""
    with st.expander(label, expanded=False):
        st.json(data)


def _show_error(message: str, exc: Exception) -> None:
    """统一友好错误提示：中文主文案 + 可折叠的技术细节。"""
    st.error(message)
    with st.expander("错误详情", expanded=False):
        st.code(str(exc))


def _render_step_bar(state: dict[str, Any]) -> None:
    """渲染四段流程步骤进度条（已完成 / 进行中 / 待办）。"""
    done = [
        bool((state.get("detect_result") or {}).get("resolvedBoard")),
        bool((state.get("knowledge_result") or {}).get("knowledgeId")),
        bool((state.get("project_result") or {}).get("projectId")),
        bool(state.get("flash_task") or state.get("check_task")),
    ]
    active = next((i for i, ok in enumerate(done) if not ok), len(done) - 1)
    chips: list[str] = []
    for i, label in enumerate(_STEP_LABELS):
        cls = "done" if done[i] else ("active" if i == active else "")
        chips.append(f'<span class="ba-step {cls}">{label}</span>')
    st.markdown(f'<div class="ba-steps">{"".join(chips)}</div>', unsafe_allow_html=True)


def render_board_assistant_page(client: BackendApiClient) -> None:
    """渲染板卡助手页面主体。"""
    # ── 页头 ──
    st.markdown(
        """
<div style="margin-bottom:1.25rem;">
  <h2 style="font-size:1.2rem;font-weight:700;color:#e2e8f0;margin:0 0 0.25rem;">
    🔌 板卡助手
  </h2>
  <p style="color:#64748b;font-size:0.85rem;margin:0;">
    识别开发板 → 同步官方资料 → 生成工程模板 → 烧录与运行校验
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    state = st.session_state
    _init_state(state)
    _render_step_bar(state)

    # ─────────────────────── 步骤 1：板卡识别 ───────────────────────
    with st.expander("① 板卡识别", expanded=True):
        col_model, col_opts = st.columns([3, 2])
        with col_model:
            user_model = st.text_input(
                "手动指定板卡型号（可选）",
                value=state.get("user_model", ""),
                placeholder="如 STM32F103C8T6、ESP32-S3…",
            )
        with col_opts:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            scan_ports = st.checkbox("扫描串口", value=True, key="detect_scan_ports")
            scan_usb = st.checkbox("扫描 USB", value=True, key="detect_scan_usb")

        if st.button("🔍 识别板卡", key="detect_board", type="primary"):
            with st.spinner("正在扫描设备…"):
                try:
                    data = client.detect_board(
                        {
                            "userProvidedModel": user_model or None,
                            "scanPorts": bool(scan_ports),
                            "scanUsb": bool(scan_usb),
                        }
                    )
                    state["detect_result"] = data
                    state["boardDetectState"] = "success"
                    state["detect_confirmed_request_id"] = ""
                    st.toast("✓ 板卡识别完成")
                except Exception as exc:
                    state["boardDetectState"] = "failed"
                    _show_error("板卡识别失败，请检查后端服务与设备连接。", exc)

        detect_result = state.get("detect_result") or {}
        if detect_result:
            _render_kv_grid(
                detect_result,
                [
                    ("板卡型号", "resolvedBoard.model"),
                    ("厂商", "resolvedBoard.vendor"),
                    ("置信度", "resolvedBoard.confidence"),
                    ("请求 ID", "requestId"),
                ],
            )
            _render_scan_result(detect_result)

            if detect_result.get("needConfirm"):
                st.warning("⚠ 识别置信度较低，请选择候选后执行二次识别确认。")
                candidates = detect_result.get("candidates", [])
                options = [c.get("model", "") for c in candidates if c.get("model")]
                selected = st.selectbox("候选板卡", options=options, key="manual_candidate_model") if options else ""
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("↻ 二次识别", key="identify_board", use_container_width=True):
                        try:
                            res = client.identify_board(
                                {
                                    "requestId": detect_result.get("requestId", ""),
                                    "userProvidedModel": user_model or None,
                                    "manualCandidateModel": selected or None,
                                }
                            )
                            state["detect_result"] = {
                                **detect_result,
                                "resolvedBoard": res.get("resolvedBoard"),
                                "candidates": res.get("candidates", []),
                                "needConfirm": res.get("needConfirm", False),
                                "matchSignals": res.get("matchSignals", {}),
                            }
                            if not res.get("needConfirm", False):
                                state["detect_confirmed_request_id"] = detect_result.get("requestId", "")
                            st.success(res.get("explain") or "✓ 二次识别完成")
                        except Exception as exc:
                            _show_error("二次识别失败，请稍后重试。", exc)
                with btn_col2:
                    if st.button("✓ 确认当前结果", key="confirm_detect_result", use_container_width=True):
                        state["detect_confirmed_request_id"] = detect_result.get("requestId", "")
                        st.success("✓ 已确认当前识别结果")
            else:
                state["detect_confirmed_request_id"] = detect_result.get("requestId", "")
                resolved = detect_result.get("resolvedBoard") or {}
                if resolved.get("model"):
                    st.success(f"✓ 已识别：**{resolved['model']}**")

    # ─────────────────────── 步骤 2：同步资料 ───────────────────────
    with st.expander("② 同步官方资料", expanded=False):
        force_refresh = st.checkbox("强制刷新缓存", value=False)
        if st.button("📥 同步资料", key="sync_kb", type="primary"):
            resolved = (state.get("detect_result") or {}).get("resolvedBoard") or {}
            detect_result = state.get("detect_result") or {}
            if detect_result.get("needConfirm") and state.get("detect_confirmed_request_id") != detect_result.get("requestId"):
                st.warning("⚠ 请先在「板卡识别」步骤确认低置信度结果。")
            elif not resolved.get("model"):
                st.warning("⚠ 请先完成板卡识别。")
            else:
                with st.spinner("正在同步官方资料…"):
                    try:
                        data = client.sync_knowledge(
                            {
                                "boardModel": resolved.get("model"),
                                "vendorHint": resolved.get("vendor"),
                                "forceRefresh": force_refresh,
                                "sourcePolicy": {"allowApi": True, "allowWeb": True, "allowPdfIndex": True},
                            }
                        )
                        state["knowledge_result"] = data
                        state["knowledgeSyncState"] = "success"
                        st.toast("✓ 资料同步完成")
                    except Exception as exc:
                        state["knowledgeSyncState"] = "failed"
                        _show_error("资料同步失败，请确认板卡型号与网络。", exc)

        if state.get("knowledge_result"):
            _render_kv_grid(
                state["knowledge_result"],
                [
                    ("资料 ID", "knowledgeId"),
                    ("条目数", "itemCount"),
                    ("来源", "source"),
                    ("更新时间", "updatedAt"),
                ],
            )
            st.success("✓ 资料已就绪")

    # ─────────────────────── 步骤 3：生成工程 ───────────────────────
    with st.expander("③ 生成工程模板", expanded=False):
        requirement_text = st.text_area(
            "需求描述",
            value=state.get("requirement_text", ""),
            placeholder="例如：每秒读取 DHT11 温湿度并通过 UART1 串口输出…",
            height=100,
        )
        fw_col, tc_col = st.columns(2)
        with fw_col:
            framework = st.selectbox("框架", options=["auto", "baremetal", "esp-idf"], index=0)
        with tc_col:
            toolchain = st.selectbox("工具链", options=["auto", "make", "cmake"], index=0)

        if st.button("⚙ 生成工程", key="generate_project", type="primary"):
            kb = state.get("knowledge_result") or {}
            resolved = (state.get("detect_result") or {}).get("resolvedBoard") or {}
            detect_result = state.get("detect_result") or {}
            if detect_result.get("needConfirm") and state.get("detect_confirmed_request_id") != detect_result.get("requestId"):
                st.warning("⚠ 请先在「板卡识别」步骤确认低置信度结果。")
            elif not kb.get("knowledgeId"):
                st.warning("⚠ 请先完成「同步官方资料」。")
            elif not requirement_text.strip():
                st.warning("⚠ 需求描述不能为空。")
            else:
                with st.spinner("正在生成工程…"):
                    try:
                        data = client.generate_project(
                            {
                                "boardModel": resolved.get("model", ""),
                                "knowledgeId": kb["knowledgeId"],
                                "requirementText": requirement_text,
                                "language": "c",
                                "frameworkPreference": "auto",
                                "framework": framework,
                                "toolchain": toolchain,
                                "templateOptions": {},
                            }
                        )
                        state["project_result"] = data
                        state["requirement_text"] = requirement_text
                        state["projectGenerationState"] = "success"
                        st.toast("✓ 工程生成完成")
                    except Exception as exc:
                        state["projectGenerationState"] = "failed"
                        _show_error("工程生成失败，请稍后重试。", exc)

        if state.get("project_result"):
            _render_kv_grid(
                state["project_result"],
                [
                    ("工程 ID", "projectId"),
                    ("框架", "framework"),
                    ("工具链", "toolchain"),
                    ("入口文件", "entryFile"),
                ],
            )
            st.success("✓ 工程已生成")

    # ─────────────────────── 步骤 4：烧录与校验 ───────────────────────
    with st.expander("④ 烧录与运行校验", expanded=False):
        st.markdown("**烧录配置**")
        dry_run = st.checkbox("仅演习（dry-run，不实际写入）", value=True)
        confirm = st.checkbox("我已确认风险，允许实际烧录")

        flash_col, plan_col = st.columns(2)
        with plan_col:
            if st.button("📋 生成烧录计划", key="plan_flash", use_container_width=True):
                project = state.get("project_result") or {}
                port_options = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or [""]
                if not project.get("projectId"):
                    st.warning("⚠ 请先生成工程。")
                else:
                    with st.spinner("生成烧录计划…"):
                        try:
                            plan_data = client.plan_flash(
                                project["projectId"],
                                {"preferredTool": None, "artifactPath": "build/firmware.bin",
                                 "port": port_options[0], "baudrate": 115200},
                            )
                            state["flash_plan"] = plan_data
                            st.success("✓ 烧录计划已生成")
                            _render_kv_grid(plan_data, [("计划 ID", "flashPlanId"), ("工具", "tool"), ("端口", "port")])
                        except Exception as exc:
                            _show_error("烧录计划生成失败。", exc)

        with flash_col:
            if st.button("🔥 执行烧录", key="flash_project", type="primary", use_container_width=True):
                project = state.get("project_result") or {}
                port_options = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or ["/dev/tty.usbmodem1101"]
                if not project.get("projectId"):
                    st.warning("⚠ 请先生成工程。")
                else:
                    with st.spinner("烧录中…"):
                        try:
                            flash_data = client.flash_project(
                                project["projectId"],
                                {
                                    "port": port_options[0],
                                    "programmer": "stlink",
                                    "eraseMode": "chip",
                                    "dryRun": dry_run,
                                    "userConfirmedRisk": confirm,
                                    "flashPlanId": (state.get("flash_plan") or {}).get("flashPlanId"),
                                },
                            )
                            state["flash_task"] = flash_data
                            state["flashTaskState"] = "success"
                            st.success("✓ 烧录任务已提交")
                            _render_kv_grid(flash_data, [("任务 ID", "taskId"), ("状态", "status"), ("端口", "port")])
                        except Exception as exc:
                            state["flashTaskState"] = "failed"
                            _show_error("烧录失败，请检查设备连接与配置。", exc)

        st.divider()
        st.markdown("**运行校验**")

        port_default = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or [""]
        rc_col1, rc_col2, rc_col3 = st.columns(3)
        with rc_col1:
            serial_port = st.text_input("串口端口", value=port_default[0], key="runcheck_port")
        with rc_col2:
            baudrate = st.number_input("波特率", min_value=300, max_value=2000000, value=115200, step=100)
        with rc_col3:
            assert_mode = st.selectbox("断言模式", options=["all", "any"], index=0)

        expect_keywords = st.text_input("期望关键字（逗号分隔）", value="heartbeat")

        if st.button("▶ 执行运行校验", key="run_check", type="primary"):
            project = state.get("project_result") or {}
            if not project.get("projectId"):
                st.warning("⚠ 请先生成工程。")
            elif not serial_port.strip():
                st.warning("⚠ 请填写串口端口。")
            else:
                with st.spinner("运行校验中…"):
                    try:
                        check_data = client.run_check(
                            project["projectId"],
                            {
                                "checkProfile": "serial_keyword_assert",
                                "timeoutSec": 20,
                                "serial_keyword_assert": True,
                                "serialConfig": {
                                    "port": serial_port,
                                    "baudrate": int(baudrate),
                                    "bytesize": 8,
                                    "parity": "N",
                                    "stopbits": 1,
                                    "writeTimeoutSec": 1.0,
                                },
                                "probeCommand": "status\\n",
                                "expectKeywords": [k.strip() for k in expect_keywords.split(",") if k.strip()],
                                "assertMode": assert_mode,
                            },
                        )
                        state["check_task"] = check_data
                        st.success("✓ 运行校验任务已创建")
                        _render_kv_grid(check_data, [("任务 ID", "taskId"), ("状态", "status"), ("校验项", "checkProfile")])
                    except Exception as exc:
                        _show_error("运行校验失败，请检查串口与设备状态。", exc)

        # 任务查询
        task_default = (state.get("flash_task") or {}).get("taskId", "")
        task_id = st.text_input("查询任务 ID", value=task_default, placeholder="输入任务 ID 查询状态")
        if st.button("🔎 查询任务", key="query_task") and task_id.strip():
            try:
                task = client.get_task(task_id.strip())
                _render_kv_grid(task, [("任务 ID", "taskId"), ("类型", "type"), ("状态", "status")])
                _raw_expander(task)
            except Exception as exc:
                _show_error("任务查询失败，请确认任务 ID。", exc)


def _init_state(state: st.session_state) -> None:
    """初始化板卡助手页面状态机默认值。"""
    defaults = {
        "boardDetectState": "idle",
        "knowledgeSyncState": "idle",
        "projectGenerationState": "idle",
        "flashTaskState": "idle",
        "detect_confirmed_request_id": "",
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


def _render_scan_result(detect_result: dict[str, object]) -> None:
    """渲染真实设备扫描明细（串口 / USB）。"""
    probe_info = detect_result.get("probeInfo") if isinstance(detect_result, dict) else None
    if not isinstance(probe_info, dict):
        return

    serial_ports = probe_info.get("serialPorts") or []
    serial_details = probe_info.get("serialPortDetails") or []
    usb_devices = probe_info.get("usbDevices") or []

    if not serial_ports and not usb_devices:
        return

    with st.expander("设备扫描明细", expanded=False):
        if serial_ports:
            st.markdown(f"**串口设备：** `{', '.join(str(p) for p in serial_ports)}`")
            if serial_details:
                st.dataframe(serial_details, use_container_width=True)
        else:
            st.markdown("**串口设备：** 未发现")

        if usb_devices:
            st.markdown("**USB 设备：**")
            st.dataframe(usb_devices, use_container_width=True)
        else:
            st.markdown("**USB 设备：** 未发现")
