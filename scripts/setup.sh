#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${ASTRA_DATA_DIR:-${HOME}/.astra/data}"
LOG_DIR="${DATA_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG_PATH="${LOG_DIR}/setup-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "${LOG_PATH}") 2>&1

command -v python3 >/dev/null || { echo "Python 3.10-3.13 is required."; exit 1; }
python3 -c 'import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)' || { echo "Python 3.10-3.13 is required."; exit 1; }
command -v node >/dev/null || { echo "Node.js 22 or newer is required."; exit 1; }
command -v npm >/dev/null || { echo "npm is required."; exit 1; }
NODE_MAJOR="$(node --version | sed 's/^v//' | cut -d. -f1)"
[[ "${NODE_MAJOR}" -ge 22 ]] || { echo "Node.js 22 or newer is required."; exit 1; }

if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then python3 -m venv "${ROOT}/.venv"; fi
"${ROOT}/.venv/bin/python" -m pip install --disable-pip-version-check --requirement "${ROOT}/backend/requirements.lock" --editable "${ROOT}/backend"
(cd "${ROOT}/frontend" && npm ci)
"${ROOT}/.venv/bin/python" "${ROOT}/scripts/initialize.py"

if command -v ollama >/dev/null; then
  ollama pull "${ASTRA_OLLAMA_MODEL:-qwen3:8b}"
else
  echo "Ollama is not installed. ASTRA setup completed in offline mode."
  echo "Install it from https://ollama.com/download and rerun this script to enable the local assistant."
fi

"${ROOT}/.venv/bin/python" "${ROOT}/scripts/diagnose.py"
echo "ASTRA setup completed. Launch with ./launch_astra.sh"
echo "Setup log: ${LOG_PATH}"
