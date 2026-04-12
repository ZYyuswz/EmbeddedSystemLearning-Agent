#!/usr/bin/env bash

set -euo pipefail

# 计算仓库根目录，确保从任意位置执行脚本都能工作。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-8502}"

PID_DIR="${ROOT_DIR}/tmp_data"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"
BACKEND_LOG="${PID_DIR}/backend.log"
FRONTEND_LOG="${PID_DIR}/frontend.log"

mkdir -p "${PID_DIR}"

# 判断端口是否已被监听。
is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  "${PYTHON_BIN}" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.2)
code = sock.connect_ex(("127.0.0.1", port))
sock.close()
sys.exit(0 if code == 0 else 1)
PY
}

# 等待端口监听成功。
wait_for_port() {
  local host="$1"
  local port="$2"
  local service_name="$3"
  local timeout_sec="${4:-25}"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    if "${PYTHON_BIN}" - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.4)
code = sock.connect_ex((host, port))
sock.close()
sys.exit(0 if code == 0 else 1)
PY
    then
      echo "${service_name} 已就绪: http://${host}:${port}"
      return 0
    fi

    if (( "$(date +%s)" - start_ts > timeout_sec )); then
      echo "等待 ${service_name} 启动超时，请检查日志:"
      echo "- ${BACKEND_LOG}"
      echo "- ${FRONTEND_LOG}"
      return 1
    fi
    sleep 1
  done
}

# 清理无效 PID 文件，避免误判。
clean_stale_pid() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
    rm -f "${pid_file}"
  fi
}

clean_stale_pid "${BACKEND_PID_FILE}"
clean_stale_pid "${FRONTEND_PID_FILE}"

if [[ -f "${BACKEND_PID_FILE}" ]] || [[ -f "${FRONTEND_PID_FILE}" ]]; then
  echo "检测到服务可能已在运行，请先执行 scripts/stop_project.sh。"
  exit 1
fi

if [[ ! -f "config/secrets.env" ]]; then
  cp "config/secrets.example.env" "config/secrets.env"
  echo "已创建 config/secrets.env，请按需填写 DASHSCOPE_API_KEY / DEEPSEEK_API_KEY。"
fi

if ! "${PYTHON_BIN}" -c "import fastapi,streamlit,uvicorn,httpx,numpy,sklearn" >/dev/null 2>&1; then
  echo "检测到依赖未安装，开始执行 pip install -r requirements.txt ..."
  "${PYTHON_BIN}" -m pip install -r requirements.txt
fi

if is_port_in_use "${BACKEND_PORT}"; then
  echo "后端端口 ${BACKEND_PORT} 已被占用，请先释放端口。"
  exit 1
fi

if is_port_in_use "${FRONTEND_PORT}"; then
  echo "前端端口 ${FRONTEND_PORT} 已被占用，请先释放端口。"
  exit 1
fi

echo "启动后端服务 ..."
"${PYTHON_BIN}" -m uvicorn backend.main:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --app-dir "${ROOT_DIR}" \
  >"${BACKEND_LOG}" 2>&1 &
backend_pid="$!"
echo "${backend_pid}" > "${BACKEND_PID_FILE}"

wait_for_port "${BACKEND_HOST}" "${BACKEND_PORT}" "后端服务"

echo "启动前端服务 ..."
"${PYTHON_BIN}" -m streamlit run "${ROOT_DIR}/login.py" \
  --server.address "${FRONTEND_HOST}" \
  --server.port "${FRONTEND_PORT}" \
  >"${FRONTEND_LOG}" 2>&1 &
frontend_pid="$!"
echo "${frontend_pid}" > "${FRONTEND_PID_FILE}"

wait_for_port "${FRONTEND_HOST}" "${FRONTEND_PORT}" "前端服务"

echo
echo "项目已启动："
echo "- 前端: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "- 后端: http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "- API 文档: http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo
echo "PID 文件："
echo "- ${BACKEND_PID_FILE}"
echo "- ${FRONTEND_PID_FILE}"
echo
echo "停止服务请执行: ./scripts/stop_project.sh"
