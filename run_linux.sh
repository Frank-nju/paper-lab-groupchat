#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="$(command -v python3 || command -v python)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "未找到 Python 3，请先安装 Python 3.10+。" >&2
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

if [[ "$#" -eq 0 ]]; then
  exec .venv/bin/python main.py --interactive
else
  exec .venv/bin/python main.py "$@"
fi
