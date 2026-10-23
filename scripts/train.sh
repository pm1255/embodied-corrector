#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
exec "$EC_PYTHON" -m ec_verl.train "$@"
