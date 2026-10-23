#!/usr/bin/env bash
set -euo pipefail
EC_SIM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$EC_SIM_ROOT"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
if [[ -f /usr/share/glvnd/egl_vendor.d/50_mesa.json ]]; then
  export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json
fi
export LIBERO_CONFIG_PATH="$EC_SIM_ROOT/libero-config"
export PYTHONPATH="$EC_SIM_ROOT/vendor/LIBERO-PRO${PYTHONPATH:+:$PYTHONPATH}"
EC_SIM_BACKEND="${1:?Usage: start.sh libero_pro|robocasa365 TASK OUTPUT [extra harness arguments]}"
EC_SIM_TASK="${2:?Task required}"
EC_SIM_OUTPUT="${3:?New output directory required}"
shift 3
if [[ -e "$EC_SIM_OUTPUT/manifest.json" ]]; then
  printf '%s\n' 'Use a new output directory for every independent episode.' >&2
  exit 1
fi
case "$EC_SIM_BACKEND" in
  libero_pro) EC_SIM_PYTHON=.venv-libero/bin/python ;;
  robocasa365) EC_SIM_PYTHON=.venv-robocasa/bin/python ;;
  *) exit 2 ;;
esac
exec "$EC_SIM_PYTHON" scripts/simulations/interactive_harness.py --backend "$EC_SIM_BACKEND" --task "$EC_SIM_TASK" --output "$EC_SIM_OUTPUT" "$@"
