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

backend_pid=""
frontend_pid=""

# 检查端口是否已被占用。
is_port_in_use() {
  local port="$1"
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
  local timeout_sec="${4:-20}"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    if "${PYTHON_BIN}" - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.5)
code = sock.connect_ex((host, port))
sock.close()
sys.exit(0 if code == 0 else 1)
PY
    then
      echo "${service_name} 已就绪: http://${host}:${port}"
      return 0
    fi

    if (( "$(date +%s)" - start_ts > timeout_sec )); then
      echo "等待 ${service_name} 超时，请查看日志排查。"
      return 1
    fi
    sleep 1
  done
}

# 退出时清理本脚本拉起的后台进程。
cleanup() {
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ ! -f "config/secrets.env" ]]; then
  cp "config/secrets.example.env" "config/secrets.env"
  echo "已创建 config/secrets.env，请按需填写 DASHSCOPE_API_KEY / DEEPSEEK_API_KEY。"
fi

if ! "${PYTHON_BIN}" -c "import fastapi,streamlit,uvicorn,httpx,numpy,sklearn" >/dev/null 2>&1; then
  echo "检测到依赖未安装，开始执行 pip install -r requirements.txt ..."
  "${PYTHON_BIN}" -m pip install -r requirements.txt
fi

if is_port_in_use "${BACKEND_PORT}"; then
  echo "后端端口 ${BACKEND_PORT} 已被占用，请先释放端口后重试。"
  exit 1
fi

if is_port_in_use "${FRONTEND_PORT}"; then
  echo "前端端口 ${FRONTEND_PORT} 已被占用，请先释放端口后重试。"
  exit 1
fi

echo "启动后端服务 ..."
"${PYTHON_BIN}" -m uvicorn backend.main:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --app-dir "${ROOT_DIR}" \
  >"${ROOT_DIR}/tmp_data/backend.log" 2>&1 &
backend_pid="$!"

wait_for_port "${BACKEND_HOST}" "${BACKEND_PORT}" "后端服务"

echo "启动前端服务 ..."
"${PYTHON_BIN}" -m streamlit run "${ROOT_DIR}/login.py" \
  --server.address "${FRONTEND_HOST}" \
  --server.port "${FRONTEND_PORT}" \
  >"${ROOT_DIR}/tmp_data/frontend.log" 2>&1 &
frontend_pid="$!"

wait_for_port "${FRONTEND_HOST}" "${FRONTEND_PORT}" "前端服务"

echo
echo "项目已启动："
echo "- 前端: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "- 后端: http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "- API 文档: http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo
echo "日志文件："
echo "- ${ROOT_DIR}/tmp_data/backend.log"
echo "- ${ROOT_DIR}/tmp_data/frontend.log"
echo
echo "按 Ctrl+C 停止服务。"

wait
