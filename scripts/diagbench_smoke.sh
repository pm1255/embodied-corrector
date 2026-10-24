#!/usr/bin/env bash
# One GPU: RynnBrain collection, then a separately selected vision judge.
set -euo pipefail
source "$(dirname "$0")/env.sh"
: "${DIAGBENCH_ROOT:?Set DIAGBENCH_ROOT to the extracted release}"
: "${RYNN_MODEL:?Set RYNN_MODEL to the local RynnBrain-8B checkpoint}"
: "${JUDGE_MODEL:?Set JUDGE_MODEL to an independent local Qwen3-VL vision judge}"
EC_RUN="${EC_RUN:-$EC_ROOT/runs/diagbench-rynnbrain-smoke}"
EC_PORT="${EC_PORT:-18419}"
EC_MAX_TOKENS="${EC_MAX_TOKENS:-512}"
mkdir -p "$EC_RUN"
server_pid=''
current_stage=data
status() { "$EC_PYTHON" -m ec_verl.diagbench.monitor --output "$EC_RUN" --stage "$1" --state "$2"; }
stop_server() {
  if [ -n "$server_pid" ]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
    server_pid=''
  fi
}
cleanup() {
  code=$?
  stop_server
  if [ "$code" -ne 0 ]; then status "$current_stage" failed || true; fi
}
trap cleanup EXIT
start_server() {
  "$EC_PYTHON" -m ec_verl.diagbench.serve_transformers --model-path "$1" \
    --served-model-name "$2" --port "$EC_PORT" --metadata-output "$EC_RUN/$2-environment.json" \
    > "$EC_RUN/$2-server.log" 2>&1 &
  server_pid=$!
  for ((attempt=0; attempt<120; attempt++)); do
    if ! kill -0 "$server_pid" 2>/dev/null; then cat "$EC_RUN/$2-server.log"; return 1; fi
    if curl --noproxy '*' -fsS "http://127.0.0.1:$EC_PORT/v1/models" > "$EC_RUN/$2-service.json" 2>/dev/null; then return 0; fi
    sleep 5
  done
  echo 'Model service did not become ready within 10 minutes' >&2
  return 1
}
# Refuse to reuse another service on the selected port.
"$EC_PYTHON" -c 'import socket,sys; s=socket.socket(); s.bind(("127.0.0.1",int(sys.argv[1]))); s.close()' "$EC_PORT"
status data running
"$EC_PYTHON" -m ec_verl.diagbench.validate --root "$DIAGBENCH_ROOT" --hash --report "$EC_RUN/validation.json"
status data complete
current_stage=model
status model running
start_server "$RYNN_MODEL" rynnbrain
status model complete
current_stage=collect
"$EC_PYTHON" -m ec_verl.diagbench.evaluate collect --root "$DIAGBENCH_ROOT" --output "$EC_RUN" \
  --smoke --resume --workers 1 --max-tokens "$EC_MAX_TOKENS" --model rynnbrain \
  --api "http://127.0.0.1:$EC_PORT/v1/chat/completions"
stop_server
current_stage=judge
status judge running
start_server "$JUDGE_MODEL" vision-judge
"$EC_PYTHON" -m ec_verl.diagbench.evaluate judge --root "$DIAGBENCH_ROOT" --output "$EC_RUN" \
  --smoke --resume --workers 1 --max-tokens "$EC_MAX_TOKENS" --judge-max-tokens 512 --model vision-judge \
  --api "http://127.0.0.1:$EC_PORT/v1/chat/completions"
stop_server
current_stage=aggregate
"$EC_PYTHON" -m ec_verl.diagbench.evaluate aggregate --root "$DIAGBENCH_ROOT" --output "$EC_RUN" --smoke
