#!/usr/bin/env bash
set -euo pipefail
EC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$EC_ROOT:$EC_ROOT/vendor/verl${PYTHONPATH:+:$PYTHONPATH}"
export TOKENIZERS_PARALLELISM=false
export VERL_USE_EXTERNAL_PLUGINS=none
export NO_PROXY="localhost,127.0.0.1${NO_PROXY:+,$NO_PROXY}"
EC_PYTHON="${EC_PYTHON:-$EC_ROOT/.venv/bin/python}"
