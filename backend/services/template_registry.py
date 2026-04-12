"""工程模板注册与渲染服务。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.repositories.sqlite_repo import SQLiteRepo


@dataclass(frozen=True)
class TemplateResolved:
    """模板解析结果。"""

    template_id: str
    board_family: str
    framework: str
    toolchain: str


_TEMPLATE_FILES = {
    "stm32f1-stdc-make-v1": {
        "src/main.c": (
            "/* 自动生成示例工程 */\n"
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    // 需求摘要: __REQ__\n"
            "    while (1) {\n"
            "        printf(\"heartbeat\\n\");\n"
            "        break;\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "Makefile": (
            "APP=firmware\n"
            "all:\n\t@echo \"构建 $$(APP)\"\n"
            "flash:\n\t@echo \"模拟烧录\"\n"
        ),
        "scripts/check_serial.py": (
            "import argparse\n"
            "import time\n\n"
            "parser = argparse.ArgumentParser(description='串口检查')\n"
            "parser.add_argument('--timeout', type=int, default=15)\n"
            "args = parser.parse_args()\n"
            "time.sleep(0.1)\n"
            "print(f'串口收到 20 条数据，超时阈值 {{args.timeout}}s')\n"
        ),
    },
    "esp32-idf-cmake-v1": {
        "main/main.c": (
            "#include <stdio.h>\n\n"
            "void app_main(void) {\n"
            "    // 需求摘要: __REQ__\n"
            "    printf(\"heartbeat\\n\");\n"
            "}\n"
        ),
        "CMakeLists.txt": "cmake_minimum_required(VERSION 3.5)\nproject(generated_esp32)\n",
        "scripts/check_serial.py": (
            "import argparse\n"
            "import time\n\n"
            "parser = argparse.ArgumentParser(description='串口检查')\n"
            "parser.add_argument('--timeout', type=int, default=15)\n"
            "args = parser.parse_args()\n"
            "time.sleep(0.1)\n"
            "print(f'串口收到 20 条数据，超时阈值 {{args.timeout}}s')\n"
        ),
    },
}


def resolve_template(repo: SQLiteRepo, board_model: str, framework: str, toolchain: str) -> TemplateResolved | None:
    """按板卡、框架、工具链解析模板。"""
    board_family = _to_board_family(board_model)
    eff_framework = framework if framework != "auto" else _default_framework(board_family)
    eff_toolchain = toolchain if toolchain != "auto" else _default_toolchain(board_family)

    row = repo.find_template(board_family, eff_framework, eff_toolchain)
    if not row:
        return None
    return TemplateResolved(
        template_id=row["templateId"],
        board_family=board_family,
        framework=eff_framework,
        toolchain=eff_toolchain,
    )


def render_project_files(template: TemplateResolved, context: dict[str, Any]) -> dict[str, str]:
    """根据模板与上下文渲染文件。"""
    raw_files = _TEMPLATE_FILES.get(template.template_id, {})
    requirement_text = str(context.get("requirementText", "")).strip() or "未提供"
    rendered: dict[str, str] = {}
    for path, content in raw_files.items():
        rendered[path] = content.replace("__REQ__", requirement_text)
    return rendered


def _to_board_family(board_model: str) -> str:
    """将板卡型号映射为模板族。"""
    lowered = board_model.lower()
    if "esp32" in lowered:
        return "esp32"
    if "stm32" in lowered or "bluepill" in lowered:
        return "stm32f1"
    return "generic"


def _default_framework(board_family: str) -> str:
    """返回默认框架。"""
    if board_family == "esp32":
        return "esp-idf"
    return "baremetal"


def _default_toolchain(board_family: str) -> str:
    """返回默认工具链。"""
    if board_family == "esp32":
        return "cmake"
    return "make"
