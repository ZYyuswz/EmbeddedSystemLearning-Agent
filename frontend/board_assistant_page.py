"""板卡助手页面。"""
from __future__ import annotations

import streamlit as st

from frontend.api_client import BackendApiClient


def render_board_assistant_page(client: BackendApiClient) -> None:
    """渲染板卡助手页面。"""
    st.subheader("板卡助手")
    st.caption("流程：识别板卡 -> 同步资料 -> 生成工程 -> 烧录/运行校验")

    state = st.session_state
    _init_state(state)

    with st.expander("1) 板卡识别", expanded=True):
        user_model = st.text_input("可选：手动输入板卡型号", value=state.get("user_model", ""))
        scan_ports = st.checkbox("扫描串口设备", value=True, key="detect_scan_ports")
        scan_usb = st.checkbox("扫描 USB 设备", value=True, key="detect_scan_usb")
        if st.button("识别板卡", key="detect_board"):
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
            except Exception as exc:
                state["boardDetectState"] = "failed"
                st.error(f"识别失败: {exc}")

        detect_result = state.get("detect_result") or {}
        if detect_result:
            st.json(detect_result)
            _render_scan_result(detect_result)
            if detect_result.get("needConfirm"):
                st.warning("识别置信度较低，请选择候选后执行二次识别确认。")
                candidates = detect_result.get("candidates", [])
                options = [candidate.get("model", "") for candidate in candidates if candidate.get("model")]
                selected = st.selectbox("手工候选", options=options, key="manual_candidate_model") if options else ""
                if st.button("执行二次识别", key="identify_board"):
                    try:
                        identify_result = client.identify_board(
                            {
                                "requestId": detect_result.get("requestId", ""),
                                "userProvidedModel": user_model or None,
                                "manualCandidateModel": selected or None,
                            }
                        )
                        state["detect_result"] = {
                            **detect_result,
                            **{
                                "resolvedBoard": identify_result.get("resolvedBoard"),
                                "candidates": identify_result.get("candidates", []),
                                "needConfirm": identify_result.get("needConfirm", False),
                                "matchSignals": identify_result.get("matchSignals", {}),
                            },
                        }
                        if not identify_result.get("needConfirm", False):
                            state["detect_confirmed_request_id"] = detect_result.get("requestId", "")
                        st.success(identify_result.get("explain") or "二次识别完成")
                    except Exception as exc:
                        st.error(f"二次识别失败: {exc}")
                if st.button("确认使用当前候选", key="confirm_detect_result"):
                    state["detect_confirmed_request_id"] = detect_result.get("requestId", "")
                    st.success("已确认当前识别结果")
            else:
                state["detect_confirmed_request_id"] = detect_result.get("requestId", "")

    with st.expander("2) 同步官方资料", expanded=True):
        force_refresh = st.checkbox("强制刷新资料", value=False)
        if st.button("同步资料", key="sync_kb"):
            resolved = (state.get("detect_result") or {}).get("resolvedBoard") or {}
            detect_result = state.get("detect_result") or {}
            if detect_result.get("needConfirm") and state.get("detect_confirmed_request_id") != detect_result.get("requestId"):
                st.warning("请先在“板卡识别”步骤确认低置信度结果")
            else:
                board_model = resolved.get("model")
                vendor = resolved.get("vendor")
                if not board_model:
                    st.warning("请先完成板卡识别")
                else:
                    try:
                        data = client.sync_knowledge(
                            {
                                "boardModel": board_model,
                                "vendorHint": vendor,
                                "forceRefresh": force_refresh,
                                "sourcePolicy": {"allowApi": True, "allowWeb": True, "allowPdfIndex": True},
                            }
                        )
                        state["knowledge_result"] = data
                        state["knowledgeSyncState"] = "success"
                    except Exception as exc:
                        state["knowledgeSyncState"] = "failed"
                        st.error(f"同步失败: {exc}")

        if state.get("knowledge_result"):
            st.json(state["knowledge_result"])

    with st.expander("3) 生成工程", expanded=True):
        requirement_text = st.text_area("需求描述", value=state.get("requirement_text", ""), placeholder="例如：每秒读取温湿度并通过串口输出")
        framework = st.selectbox("框架", options=["auto", "baremetal", "esp-idf"], index=0)
        toolchain = st.selectbox("工具链", options=["auto", "make", "cmake"], index=0)
        if st.button("生成工程", key="generate_project"):
            kb = state.get("knowledge_result") or {}
            resolved = (state.get("detect_result") or {}).get("resolvedBoard") or {}
            detect_result = state.get("detect_result") or {}
            if detect_result.get("needConfirm") and state.get("detect_confirmed_request_id") != detect_result.get("requestId"):
                st.warning("请先在“板卡识别”步骤确认低置信度结果")
            else:
                if not kb.get("knowledgeId"):
                    st.warning("请先同步官方资料")
                elif not requirement_text.strip():
                    st.warning("需求不能为空")
                else:
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
                        state["projectGenerationState"] = "success"
                    except Exception as exc:
                        state["projectGenerationState"] = "failed"
                        st.error(f"生成失败: {exc}")

        if state.get("project_result"):
            st.json(state["project_result"])

    with st.expander("4) 烧录与运行校验", expanded=True):
        dry_run = st.checkbox("仅 dry-run", value=True)
        confirm = st.checkbox("我确认烧录风险")
        if st.button("生成烧录计划", key="plan_flash"):
            project = state.get("project_result") or {}
            port_options = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or [""]
            if not project.get("projectId"):
                st.warning("请先生成工程")
            else:
                try:
                    plan_data = client.plan_flash(
                        project["projectId"],
                        {"preferredTool": None, "artifactPath": "build/firmware.bin", "port": port_options[0], "baudrate": 115200},
                    )
                    state["flash_plan"] = plan_data
                    st.success("烧录计划已生成")
                    st.json(plan_data)
                except Exception as exc:
                    st.error(f"生成烧录计划失败: {exc}")

        if st.button("执行烧录", key="flash_project"):
            project = state.get("project_result") or {}
            port_options = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or ["/dev/tty.usbmodem1101"]
            if not project.get("projectId"):
                st.warning("请先生成工程")
            else:
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
                    st.success("烧录任务完成")
                    st.json(flash_data)
                except Exception as exc:
                    state["flashTaskState"] = "failed"
                    st.error(f"烧录失败: {exc}")

        port_default = ((state.get("detect_result") or {}).get("probeInfo") or {}).get("serialPorts") or [""]
        serial_port = st.text_input("串口端口", value=port_default[0], key="runcheck_port")
        baudrate = st.number_input("波特率", min_value=300, max_value=2000000, value=115200, step=100)
        expect_keywords = st.text_input("期望关键字（逗号分隔）", value="heartbeat")
        assert_mode = st.selectbox("断言模式", options=["all", "any"], index=0)
        probe_command = st.text_input("探测命令（可选）", value="status\\n")

        if st.button("执行运行校验", key="run_check"):
            project = state.get("project_result") or {}
            if not project.get("projectId"):
                st.warning("请先生成工程")
            elif not serial_port.strip():
                st.warning("请填写串口端口")
            else:
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
                            "probeCommand": probe_command,
                            "expectKeywords": [item.strip() for item in expect_keywords.split(",") if item.strip()],
                            "assertMode": assert_mode,
                        },
                    )
                    state["check_task"] = check_data
                    st.success("运行校验任务已创建")
                    st.json(check_data)
                except Exception as exc:
                    st.error(f"运行校验失败: {exc}")

        task_id = st.text_input("查询任务 ID", value=(state.get("flash_task") or {}).get("taskId", ""))
        if st.button("查询任务详情", key="query_task") and task_id.strip():
            try:
                task = client.get_task(task_id.strip())
                st.json(task)
            except Exception as exc:
                st.error(f"查询失败: {exc}")


def _init_state(state: st.session_state) -> None:
    """初始化页面状态机。"""
    defaults = {
        "boardDetectState": "idle",
        "knowledgeSyncState": "idle",
        "projectGenerationState": "idle",
        "flashTaskState": "idle",
        "evaluationState": "idle",
        "detect_confirmed_request_id": "",
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value


def _render_scan_result(detect_result: dict[str, object]) -> None:
    """渲染真实设备扫描结果。"""
    probe_info = detect_result.get("probeInfo") if isinstance(detect_result, dict) else None
    if not isinstance(probe_info, dict):
        return

    serial_ports = probe_info.get("serialPorts") or []
    serial_details = probe_info.get("serialPortDetails") or []
    usb_devices = probe_info.get("usbDevices") or []

    with st.container(border=True):
        st.markdown("**真实设备扫描结果**")
        if serial_ports:
            st.write("串口设备：", ", ".join(str(item) for item in serial_ports))
        else:
            st.write("串口设备：未发现")

        if serial_details:
            st.caption("串口枚举明细")
            st.dataframe(serial_details, use_container_width=True)

        if usb_devices:
            st.caption("USB 枚举明细")
            st.dataframe(usb_devices, use_container_width=True)
        else:
            st.write("USB 设备：未发现")
