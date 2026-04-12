"""后端 API 行为测试。"""
from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from backend.infrastructure.device_scanner import DeviceProbeResult


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    """创建测试项目并返回项目 ID。"""
    response = client.post(
        "/api/v1/projects/generate",
        headers=auth_headers,
        json={
            "boardModel": "STM32F103C8T6-BluePill",
            "knowledgeId": "kb_test",
            "requirementText": "点亮 LED 并输出心跳",
            "language": "c",
            "frameworkPreference": "auto",
        },
    )
    assert response.status_code == 200
    return response.json()["projectId"]


def _fake_probe() -> DeviceProbeResult:
    """构造稳定的探针快照。"""
    return DeviceProbeResult(
        usb_vid="0483",
        usb_pid="3748",
        serial_ports=["/dev/tty.usbmodem1101"],
        serial_port_details=[
            {
                "device": "/dev/tty.usbmodem1101",
                "description": "STM32 USB CDC",
                "hwid": "USB VID:PID=0483:3748",
                "vid": 0x0483,
                "pid": 0x3748,
                "serialNumber": "ABC123",
                "location": "1-1",
                "manufacturer": "STMicroelectronics",
                "product": "STM32 Virtual COM Port",
                "interface": "CDC",
            }
        ],
        usb_devices=[
            {
                "vid": "0483",
                "pid": "3748",
                "manufacturer": "STMicroelectronics",
                "product": "STM32 STLink",
                "serialNumber": "ABC123",
                "location": "usb-1-1",
            }
        ],
    )


def test_reject_request_when_missing_auth_header(client: TestClient) -> None:
    """缺少鉴权头时应返回未授权。"""
    response = client.post("/api/v1/boards/detect", json={})
    assert response.status_code == 401
    assert response.json()["errorCode"] == "UNAUTHORIZED"


def test_detect_board_returns_resolved_candidate(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """板卡识别接口应返回主候选与探针信息。"""
    monkeypatch.setenv("BOARD_DETECT_CONFIDENCE", "0.4")
    monkeypatch.setattr(
        "backend.services.board_detection_service.collect_probe_info",
        lambda scan_usb, scan_ports: _fake_probe() if (scan_usb or scan_ports) else DeviceProbeResult("", "", [], [], []),
    )
    response = client.post(
        "/api/v1/boards/detect",
        headers=auth_headers,
        json={"userProvidedModel": "esp32-devkitc", "scanPorts": False, "scanUsb": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolvedBoard"]["model"] == "ESP32-DevKitC"
    assert payload["needConfirm"] is False
    assert payload["probeInfo"]["usbVid"] == ""
    assert payload["matchSignals"]["userInput"] > 0


def test_detect_board_returns_need_confirm_when_confidence_below_threshold(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """识别置信度低于阈值时应返回需要确认标记。"""
    monkeypatch.setenv("BOARD_DETECT_CONFIDENCE", "0.95")
    monkeypatch.setattr(
        "backend.services.board_detection_service.collect_probe_info",
        lambda scan_usb, scan_ports: _fake_probe() if (scan_usb or scan_ports) else DeviceProbeResult("", "", [], [], []),
    )
    response = client.post(
        "/api/v1/boards/detect",
        headers=auth_headers,
        json={"userProvidedModel": "custom-board-x", "scanPorts": False, "scanUsb": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolvedBoard"]["confidence"] == 0.55
    assert payload["needConfirm"] is True


def test_detect_board_returns_empty_when_no_probe_and_no_input(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """无扫描结果且无用户输入时应返回空设备错误。"""
    monkeypatch.setattr(
        "backend.services.board_detection_service.collect_probe_info",
        lambda *_: DeviceProbeResult("", "", [], [], []),
    )
    response = client.post(
        "/api/v1/boards/detect",
        headers=auth_headers,
        json={"scanPorts": False, "scanUsb": False},
    )
    assert response.status_code == 404
    assert response.json()["errorCode"] == "BOARD_DETECT_EMPTY"


def test_identify_board_resolves_manual_candidate(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """二次识别接口应支持人工候选确认。"""
    monkeypatch.setattr("backend.services.board_detection_service.collect_probe_info", lambda *_: _fake_probe())
    detect_response = client.post(
        "/api/v1/boards/detect",
        headers=auth_headers,
        json={"userProvidedModel": "unknown-abc", "scanPorts": True, "scanUsb": True},
    )
    assert detect_response.status_code == 200
    request_id = detect_response.json()["requestId"]

    identify_response = client.post(
        "/api/v1/boards/identify",
        headers=auth_headers,
        json={
            "requestId": request_id,
            "userProvidedModel": "stm32",
            "manualCandidateModel": "STM32F103C8T6-BluePill",
        },
    )
    assert identify_response.status_code == 200
    payload = identify_response.json()
    assert payload["resolvedBoard"]["model"] == "STM32F103C8T6-BluePill"
    assert payload["matchSignals"]["manualCandidate"] > 0


def test_identify_board_returns_not_found_for_unknown_request_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """二次识别请求 ID 不存在时应返回未找到。"""
    response = client.post(
        "/api/v1/boards/identify",
        headers=auth_headers,
        json={
            "requestId": "req_missing",
            "userProvidedModel": "stm32",
            "manualCandidateModel": "STM32F103C8T6-BluePill",
        },
    )
    assert response.status_code == 404
    assert response.json()["errorCode"] == "NOT_FOUND"


def test_sync_knowledge_returns_not_found_for_unknown_board(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """未知板卡同步资料时应返回来源不存在错误。"""
    response = client.post(
        "/api/v1/boards/knowledge/sync",
        headers=auth_headers,
        json={"boardModel": "UNKNOWN-BOARD"},
    )
    assert response.status_code == 404
    assert response.json()["errorCode"] == "OFFICIAL_SOURCE_NOT_FOUND"


def test_sync_knowledge_returns_cache_hit_after_first_request(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """资料同步第二次请求应命中缓存。"""
    first = client.post(
        "/api/v1/boards/knowledge/sync",
        headers=auth_headers,
        json={"boardModel": "STM32F103C8T6-BluePill", "forceRefresh": False},
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["cache"]["cacheHit"] is False

    second = client.post(
        "/api/v1/boards/knowledge/sync",
        headers=auth_headers,
        json={"boardModel": "STM32F103C8T6-BluePill", "forceRefresh": False},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["cache"]["cacheHit"] is True

    force_refresh = client.post(
        "/api/v1/boards/knowledge/sync",
        headers=auth_headers,
        json={"boardModel": "STM32F103C8T6-BluePill", "forceRefresh": True},
    )
    assert force_refresh.status_code == 200
    assert force_refresh.json()["cache"]["cacheHit"] is False


def test_generate_project_rejects_blank_requirement(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """空需求文本应被拒绝。"""
    response = client.post(
        "/api/v1/projects/generate",
        headers=auth_headers,
        json={
            "boardModel": "STM32F103C8T6-BluePill",
            "knowledgeId": "kb_test",
            "requirementText": "   ",
            "language": "c",
            "frameworkPreference": "auto",
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "GEN_REQUIREMENT_INVALID"


def test_generate_project_returns_template_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """工程生成响应应返回模板信息与文件清单。"""
    response = client.post(
        "/api/v1/projects/generate",
        headers=auth_headers,
        json={
            "boardModel": "STM32F103C8T6-BluePill",
            "knowledgeId": "kb_test",
            "requirementText": "点亮 LED",
            "framework": "baremetal",
            "toolchain": "make",
            "templateOptions": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["templateId"] == "stm32f1-stdc-make-v1"
    assert "src/main.c" in payload["generatedFiles"]
    assert "build/firmware.bin" in payload["generatedFiles"]


def test_flash_requires_user_confirmation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """烧录接口在未确认风险时应拒绝执行。"""
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project_id}/flash",
        headers=auth_headers,
        json={
            "port": "/dev/tty.usbmodem1101",
            "programmer": "stlink",
            "eraseMode": "chip",
            "dryRun": False,
            "userConfirmedRisk": False,
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "FLASH_CONFIRMATION_REQUIRED"


def test_flash_success_and_task_detail_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """烧录成功后可查询到成功任务详情。"""
    project_id = _create_project(client, auth_headers)
    flash_response = client.post(
        f"/api/v1/projects/{project_id}/flash",
        headers=auth_headers,
        json={
            "port": "/dev/tty.usbmodem1101",
            "programmer": "stlink",
            "eraseMode": "chip",
            "dryRun": True,
            "userConfirmedRisk": True,
        },
    )
    assert flash_response.status_code == 200
    task_id = flash_response.json()["taskId"]

    detail_response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "success"
    assert "开始执行烧录" in detail_payload["logs"]


def test_flash_plan_route_returns_missing_artifact_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """烧录计划在产物缺失时应返回对应错误码。"""
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project_id}/flash/plan",
        headers=auth_headers,
        json={"artifactPath": "build/not_exists.bin"},
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "FLASH_PLAN_ARTIFACT_MISSING"


def test_flash_plan_then_flash_success(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """先生成烧录计划再执行烧录应成功。"""
    project_id = _create_project(client, auth_headers)
    plan_response = client.post(
        f"/api/v1/projects/{project_id}/flash/plan",
        headers=auth_headers,
        json={"port": "/dev/tty.usbmodem1101", "preferredTool": "stlink"},
    )
    assert plan_response.status_code == 200
    flash_plan_id = plan_response.json()["flashPlanId"]

    flash_response = client.post(
        f"/api/v1/projects/{project_id}/flash",
        headers=auth_headers,
        json={
            "port": "/dev/tty.usbmodem1101",
            "programmer": "stlink",
            "eraseMode": "chip",
            "dryRun": True,
            "userConfirmedRisk": True,
            "flashPlanId": flash_plan_id,
        },
    )
    assert flash_response.status_code == 200


def test_run_check_invalid_profile_returns_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """运行校验接口在档位非法时应返回错误。"""
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project_id}/run-check",
        headers=auth_headers,
        json={
            "checkProfile": "unsupported_profile",
            "timeoutSec": 5,
            "serialConfig": {
                "port": "/dev/tty.usbmodem1101",
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "writeTimeoutSec": 1.0,
            },
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "RUN_CHECK_PROFILE_INVALID"


def test_run_check_returns_keyword_missing(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """运行校验未命中关键字时应返回业务错误。"""
    project_id = _create_project(client, auth_headers)

    class FakeSerial:
        """模拟串口读取但不包含目标关键字。"""

        def __init__(self, *args, **kwargs):
            self._lines = [b"boot ok\\n", b"system ready\\n"]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def reset_input_buffer(self):
            return None

        def reset_output_buffer(self):
            return None

        def write(self, _: bytes):
            return 1

        def flush(self):
            return None

        def readline(self):
            if self._lines:
                return self._lines.pop(0)
            return b""

    monkeypatch.setattr("backend.services.run_check_service.serial.Serial", FakeSerial)
    response = client.post(
        f"/api/v1/projects/{project_id}/run-check",
        headers=auth_headers,
        json={
            "checkProfile": "serial_keyword_assert",
            "timeoutSec": 2,
            "serialConfig": {
                "port": "/dev/tty.usbmodem1101",
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "writeTimeoutSec": 1.0,
            },
            "probeCommand": "status\\n",
            "expectKeywords": ["heartbeat"],
            "assertMode": "all",
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "RUN_CHECK_KEYWORD_MISSING"


def test_run_check_success_and_task_detail_contains_artifacts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """运行校验成功后，任务应包含 transcript 与匹配关键字。"""
    project_id = _create_project(client, auth_headers)

    class FakeSerial:
        """模拟可命中关键字的串口。"""

        def __init__(self, *args, **kwargs):
            self._lines = [b"boot ok\\n", b"heartbeat alive\\n"]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def reset_input_buffer(self):
            return None

        def reset_output_buffer(self):
            return None

        def write(self, _: bytes):
            return 1

        def flush(self):
            return None

        def readline(self):
            if self._lines:
                return self._lines.pop(0)
            return b""

    monkeypatch.setattr("backend.services.run_check_service.serial.Serial", FakeSerial)
    response = client.post(
        f"/api/v1/projects/{project_id}/run-check",
        headers=auth_headers,
        json={
            "checkProfile": "serial_keyword_assert",
            "timeoutSec": 2,
            "serialConfig": {
                "port": "/dev/tty.usbmodem1101",
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "writeTimeoutSec": 1.0,
            },
            "probeCommand": "status\\n",
            "expectKeywords": ["heartbeat"],
            "assertMode": "all",
        },
    )
    assert response.status_code == 200
    task_id = response.json()["taskId"]

    detail_response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["status"] == "success"
    assert payload["artifacts"]["report"] == "串口关键字校验通过"
    assert payload["artifacts"]["matchedKeywords"] == ["heartbeat"]
    transcript_path = Path(payload["artifacts"]["serialTranscriptPath"])
    assert transcript_path.exists()


def test_run_check_returns_timeout_when_serial_has_no_output(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """串口超时未返回数据时应返回超时错误码。"""
    project_id = _create_project(client, auth_headers)

    class FakeSerial:
        """模拟串口持续无输出。"""

        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def reset_input_buffer(self):
            return None

        def reset_output_buffer(self):
            return None

        def write(self, _: bytes):
            return 1

        def flush(self):
            return None

        def readline(self):
            return b""

    monkeypatch.setattr("backend.services.run_check_service.serial.Serial", FakeSerial)
    response = client.post(
        f"/api/v1/projects/{project_id}/run-check",
        headers=auth_headers,
        json={
            "checkProfile": "serial_keyword_assert",
            "timeoutSec": 1,
            "serialConfig": {
                "port": "/dev/tty.usbmodem1101",
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "writeTimeoutSec": 1.0,
            },
            "probeCommand": "status\\n",
            "expectKeywords": ["heartbeat"],
            "assertMode": "all",
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "RUN_CHECK_TIMEOUT"


def test_run_check_returns_port_open_failed_when_serial_open_raises(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """串口初始化失败时应映射端口打开错误。"""
    project_id = _create_project(client, auth_headers)

    def _raise_serial_exception(*args, **kwargs):
        raise Exception("open failed")

    import backend.services.run_check_service as run_check_module

    monkeypatch.setattr(run_check_module.serial, "SerialException", Exception)
    monkeypatch.setattr(run_check_module.serial, "Serial", _raise_serial_exception)
    response = client.post(
        f"/api/v1/projects/{project_id}/run-check",
        headers=auth_headers,
        json={
            "checkProfile": "serial_keyword_assert",
            "timeoutSec": 1,
            "serialConfig": {
                "port": "/dev/tty.usbmodem1101",
                "baudrate": 115200,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "writeTimeoutSec": 1.0,
            },
            "probeCommand": "",
            "expectKeywords": [],
            "assertMode": "all",
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "RUN_CHECK_PORT_OPEN_FAILED"


def test_task_detail_returns_not_found_for_unknown_task(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """查询不存在任务应返回 NOT_FOUND。"""
    response = client.get("/api/v1/tasks/task_not_exists", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["errorCode"] == "NOT_FOUND"


def test_eval_run_rejects_blank_scenario_name(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """评估任务场景名为空时应返回错误。"""
    response = client.post(
        "/api/v1/evaluations/prototype/run",
        headers=auth_headers,
        json={
            "projectId": "prj_123",
            "boardPlatform": "other",
            "scenarioName": "  ",
            "acceptanceChecklist": ["可生成代码"],
        },
    )
    assert response.status_code == 422
    assert response.json()["errorCode"] == "EVAL_SCENARIO_INVALID"


def test_eval_report_generated_without_improvement_list(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """关闭改进建议开关时，报告应返回空建议列表。"""
    run_response = client.post(
        "/api/v1/evaluations/prototype/run",
        headers=auth_headers,
        json={
            "projectId": "prj_123",
            "boardPlatform": "other",
            "scenarioName": "demo",
            "acceptanceChecklist": ["可生成代码"],
        },
    )
    assert run_response.status_code == 200
    evaluation_task_id = run_response.json()["evaluationTaskId"]

    response = client.post(
        "/api/v1/evaluations/reports/generate",
        headers=auth_headers,
        json={"evaluationTaskId": evaluation_task_id, "includeImprovementProposal": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["feasibility"] in {"high", "medium", "low"}
    assert payload["improvements"] == []


def test_eval_report_returns_not_found_when_task_missing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """评估任务不存在时应拒绝生成报告。"""
    response = client.post(
        "/api/v1/evaluations/reports/generate",
        headers=auth_headers,
        json={"evaluationTaskId": "eval_missing", "includeImprovementProposal": False},
    )
    assert response.status_code == 404
    assert response.json()["errorCode"] == "NOT_FOUND"
