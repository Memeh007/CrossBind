#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "ddOS — Drug Discovery Operating System"
echo "==================================="

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [[ -z "${VINA_BIN:-}" ]]; then
  if [[ -x bin/vina ]]; then export VINA_BIN="$(pwd)/bin/vina"; fi
fi

PORT="${CROSSBIND_PORT:-8787}"
echo "Starting on http://127.0.0.1:${PORT}"
exec python -m uvicorn crossbind.app:app --host 127.0.0.1 --port "${PORT}"
