#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
: "${EC_MODEL:?Set EC_MODEL to a local Qwen VL checkpoint}"
EC_RUN="${EC_RUN:-$EC_ROOT/runs/qwen-vl-smoke}"
mkdir -p "$EC_RUN"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
"$EC_PYTHON" -m pytest "$EC_ROOT/tests" -q --junitxml="$EC_RUN/tests.xml"
"$EC_PYTHON" -m ec_verl.integration_check --model "$EC_MODEL" --data "$EC_ROOT/data/paper_examples/train.jsonl" --output "$EC_RUN/model_checks.json"
"$EC_PYTHON" -m ec_verl.train --model "$EC_MODEL" --train "$EC_ROOT/data/paper_examples/train.jsonl" --eval "$EC_ROOT/data/paper_examples/eval.jsonl" --output "$EC_RUN" --device cuda --dtype bfloat16 --lora --sft-steps "${EC_SFT_STEPS:-12}" --nepo-steps 2 --group-size 2 --max-new-tokens 192 --scope smoke
"$EC_PYTHON" -m ec_verl.evaluate --model "$EC_RUN/checkpoints/nepo-0002" --data "$EC_ROOT/data/paper_examples/eval.jsonl" --output "$EC_RUN/reloaded-evaluation" --device cuda --dtype bfloat16 --max-new-tokens 192
