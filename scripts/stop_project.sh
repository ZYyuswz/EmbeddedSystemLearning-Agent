#!/usr/bin/env bash

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8502}"

# 按端口停止监听进程，优先使用 lsof，缺失时回退到 fuser。
stop_by_port() {
  local port="$1"
  local service_name="$2"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "${port}"/tcp 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true)"
  fi

  if [[ -z "${pids}" ]]; then
    echo "${service_name} 未运行（端口 ${port} 未监听）。"
    return 0
  fi

  echo "正在停止 ${service_name}（端口 ${port}，PID: ${pids//$'\n'/, }）..."
  # 先尝试优雅停止。
  while IFS= read -r pid; do
    [[ -n "${pid}" ]] || continue
    kill -TERM "${pid}" 2>/dev/null || true
  done <<< "${pids}"

  sleep 1

  local remain=""
  if command -v lsof >/dev/null 2>&1; then
    remain="$(lsof -tiTCP:"${port}" -sTCP:LISTEN || true)"
  elif command -v fuser >/dev/null 2>&1; then
    remain="$(fuser "${port}"/tcp 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true)"
  fi

  if [[ -n "${remain}" ]]; then
    echo "${service_name} 仍在运行，执行强制停止..."
    while IFS= read -r pid; do
      [[ -n "${pid}" ]] || continue
      kill -KILL "${pid}" 2>/dev/null || true
    done <<< "${remain}"
  fi

  echo "${service_name} 已停止。"
}

stop_by_port "${FRONTEND_PORT}" "前端服务"
stop_by_port "${BACKEND_PORT}" "后端服务"

echo "停止完成。"
