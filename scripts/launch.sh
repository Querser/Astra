#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${ASTRA_DATA_DIR:-${HOME}/.astra/data}"
LOG_DIR="${DATA_ROOT}/logs"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
mkdir -p "${LOG_DIR}"
PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do kill "${pid}" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

if [[ ! -x "${ROOT}/.venv/bin/python" || ! -d "${ROOT}/frontend/node_modules" ]]; then
  "${ROOT}/scripts/setup.sh"
fi

MODEL="${ASTRA_OLLAMA_MODEL:-qwen3:8b}"
AI_READY=0
if command -v ollama >/dev/null; then
  if ! curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ollama serve >"${LOG_DIR}/ollama-${RUN_ID}.log" 2>&1 &
    PIDS+=("$!")
    for _ in {1..40}; do curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break; sleep 0.5; done
  fi
  if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags | grep -Fq "\"${MODEL}\""; then AI_READY=1; fi
fi
export ASTRA_CHAT_MODEL_ENABLED="${AI_READY}"
[[ "${AI_READY}" == "1" ]] || echo "The local AI model is offline. Profiles and forecasts remain available."

if ! curl -fsS --max-time 2 http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
  (cd "${ROOT}/backend" && "${ROOT}/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log) >"${LOG_DIR}/backend-${RUN_ID}.log" 2>&1 &
  PIDS+=("$!")
fi
for _ in {1..120}; do curl -fsS --max-time 2 http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS --max-time 2 http://127.0.0.1:8000/api/v1/health >/dev/null || { echo "Backend failed. Check ${LOG_DIR}."; exit 1; }

if ! curl -fsS --max-time 2 http://127.0.0.1:5173/ >/dev/null 2>&1; then
  (cd "${ROOT}/frontend" && npm run dev) >"${LOG_DIR}/frontend-${RUN_ID}.log" 2>&1 &
  PIDS+=("$!")
fi
for _ in {1..120}; do curl -fsS --max-time 2 http://127.0.0.1:5173/ >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS --max-time 2 http://127.0.0.1:5173/ >/dev/null || { echo "Frontend failed. Check ${LOG_DIR}."; exit 1; }

if command -v open >/dev/null; then open http://127.0.0.1:5173/; elif command -v xdg-open >/dev/null; then xdg-open http://127.0.0.1:5173/; fi
echo "ASTRA is ready at http://127.0.0.1:5173/. Press Ctrl+C to stop."
wait
