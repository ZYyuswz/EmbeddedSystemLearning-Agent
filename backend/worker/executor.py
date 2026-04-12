"""任务命令执行器。"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class ExecResult:
    """命令执行结果。"""

    ok: bool
    stdout: str
    stderr: str
    returncode: int


def run_command(command: str, timeout_sec: int, cwd: str | None = None) -> ExecResult:
    """执行命令并返回标准化结果。"""
    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout_sec,
        check=False,
    )
    return ExecResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        returncode=proc.returncode,
    )
