#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
: "${EC_MODEL:?Set EC_MODEL to a Qwen model directory or Hugging Face model ID}"
EC_RUN="${EC_RUN:-$EC_ROOT/runs/qwen-smoke}"
"$EC_PYTHON" -m ec_verl.data fixture --output "$EC_ROOT/data/generated"
"$EC_PYTHON" -m pytest "$EC_ROOT/tests" -q
"$EC_PYTHON" -m ec_verl.train --model "$EC_MODEL" --train "$EC_ROOT/data/generated/train.jsonl" --eval "$EC_ROOT/data/generated/eval.jsonl" --output "$EC_RUN" --lora --sft-steps 8 --nepo-steps 2 --group-size 2 --max-new-tokens 160 --device "${EC_DEVICE:-cuda}" --dtype "${EC_DTYPE:-bfloat16}" --scope smoke
