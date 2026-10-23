#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
: "${EC_MODEL:?Set EC_MODEL to the planner Qwen VL checkpoint}"
: "${EC_EB_ROOT:?Set EC_EB_ROOT to the pinned official repository}"
: "${EC_THOR_EXECUTABLE:?Set EC_THOR_EXECUTABLE to the official Unity executable}"
: "${EC_CORRECTOR:?Set EC_CORRECTOR to the trained corrector checkpoint}"
EC_EB_RUN="${EC_EB_RUN:-$EC_ROOT/runs/eb-alfred-smoke}"
EC_DISPLAY="${EC_DISPLAY:-27}"
mkdir -p "$EC_EB_RUN"
if [ ! -f /usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf ] && [ -n "${EC_EB_FONT:-}" ]; then
  mkdir -p /usr/share/fonts/truetype/ubuntu
  cp "$EC_EB_FONT" /usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf
fi
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# Keep software rendering independent of the CUDA device used for Qwen.
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json
export __GLX_VENDOR_LIBRARY_NAME=mesa LIBGL_ALWAYS_SOFTWARE=1
# Each validation owns its display and inference process; both are closed on exit.
Xvfb ":$EC_DISPLAY" -screen 0 1024x768x24 +extension GLX > "$EC_EB_RUN/display.log" 2>&1 &
EC_DISPLAY_PID=$!
"$EC_PYTHON" -m ec_verl.serve --model "$EC_MODEL" --corrector-model "$EC_CORRECTOR" --device cuda > "$EC_EB_RUN/server.log" 2>&1 &
EC_SERVER_PID=$!
trap 'kill "$EC_SERVER_PID" "$EC_DISPLAY_PID" 2>/dev/null || true' EXIT
"$EC_PYTHON" - <<'PY'
import time,requests
for _ in range(120):
 try:
  r=requests.get('http://127.0.0.1:18127/health',timeout=2);r.raise_for_status();print(r.json());break
 except requests.RequestException:time.sleep(1)
else:raise RuntimeError('Qwen inference server was not ready after 120 seconds')
PY
"$EC_PYTHON" -m ec_verl.embodiedbench --repo "$EC_EB_ROOT" --thor-executable "$EC_THOR_EXECUTABLE" --endpoint http://127.0.0.1:18127/respond --corrector-endpoint http://127.0.0.1:18127/correct --output "$EC_EB_RUN" --episodes 1 --max-steps "${EC_EB_STEPS:-30}" --display "$EC_DISPLAY"
