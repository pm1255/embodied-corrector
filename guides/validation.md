# Code execution guide

This guide describes how to run the repository with **RynnBrain-8B**. Paper-reported results remain documented in the project page and manuscript; this file only covers commands and runtime inputs.

## Environment

Use Linux, Python 3.12, a CUDA GPU, and the pinned dependencies:

```bash
bash scripts/setup.sh
source scripts/env.sh
export EC_MODEL=/models/RynnBrain-8B
```

The checkpoint directory must include the model weights, tokenizer, and processor files expected by the serving adapter.

## Training

Split and validate data by source trajectory, then run evaluation-first SFT followed by NEPO:

```bash
"$EC_PYTHON" -m ec_verl.data split --input /data/all.jsonl --output /data/split
"$EC_PYTHON" -m ec_verl.data validate \
  --train /data/split/train.jsonl --eval /data/split/eval.jsonl
bash scripts/train.sh \
  --model "$EC_MODEL" \
  --train /data/split/train.jsonl --eval /data/split/eval.jsonl \
  --output runs/rynnbrain --device cuda --dtype bfloat16 --lora \
  --scope formal --sft-steps 1000 --nepo-steps 500 --group-size 4 \
  --kappa 1 --beta .5 --opd-coef 1
```

The run directory stores checkpoints, metrics, rollouts, and stage status. See [the data guide](data.md) for the record schema and split rules.

## EmbodiedBench

After preparing the pinned EmbodiedBench repository, task data, AI2-THOR build, and display dependencies, start the RynnBrain service:

```bash
export EC_EB_ROOT=/path/to/EmbodiedBench
export EC_THOR_EXECUTABLE=/path/to/thor-201909061227-Linux64
"$EC_PYTHON" -m ec_verl.serve \
  --model "$EC_MODEL" \
  --corrector-model runs/rynnbrain/checkpoints/nepo-0002 \
  --device cuda
```

In another terminal, run the environment adapter:

```bash
"$EC_PYTHON" -m ec_verl.embodiedbench \
  --repo "$EC_EB_ROOT" \
  --endpoint http://127.0.0.1:18127/respond \
  --corrector-endpoint http://127.0.0.1:18127/correct \
  --output runs/eb-alfred --episodes 1 --max-steps 30 --display 1
```

The adapter records observations, actions, feedback, structured corrections, and environment metrics. The environment's own `task_success` predicate supplies the final task result.

## DiagBench

Download and validate the released data, configure a RynnBrain endpoint and a compatible vision-judge endpoint, then run the three stages:

```bash
python -m ec_verl.diagbench.download --output data/diagbench
export DIAGBENCH_ROOT="$PWD/data/diagbench/EmbodiedDiag-Bench-small-20261024"
python -m ec_verl.diagbench.validate --root "$DIAGBENCH_ROOT" --hash --report runs/diagbench-validation.json

python -m ec_verl.diagbench.evaluate collect --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18409/v1/chat/completions \
  --model rynnbrain --workers 1 --max-tokens 2048
python -m ec_verl.diagbench.evaluate judge --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18410/v1/chat/completions \
  --model vision-judge --workers 1 --judge-max-tokens 512
python -m ec_verl.diagbench.evaluate aggregate --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full
```

Each stage writes its status, predictions, judgments, metrics, and logs under the selected output directory. Add `--resume` with the same settings to continue an interrupted stage.

## Monitoring

```bash
python -m tensorboard.main --logdir runs --host 127.0.0.1 --port 6006 --load_fast=false
```

Open <http://127.0.0.1:6006> to inspect training and evaluation progress.
