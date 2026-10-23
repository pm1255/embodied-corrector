#!/usr/bin/env bash
set -euo pipefail
EC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v uv >/dev/null || { printf '%s\n' 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ first.'; exit 1; }
uv venv --python 3.12 "$EC_ROOT/.venv"
uv pip install --python "$EC_ROOT/.venv/bin/python" torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python "$EC_ROOT/.venv/bin/python" -r "$EC_ROOT/requirements-core.txt"
uv pip install --python "$EC_ROOT/.venv/bin/python" --no-deps -e "$EC_ROOT[test]"
uv pip install --python "$EC_ROOT/.venv/bin/python" --no-deps -e "$EC_ROOT/vendor/verl"
printf '%s\n' 'Environment installed. Run scripts/smoke.sh with EC_MODEL set to a Qwen model.'
