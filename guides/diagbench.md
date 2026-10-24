# EmbodiedDiag-Bench integration

[中文说明](diagbench_zh.md)

This adapter preserves the released **small-portable-v1-question-roles** protocol:
4,000 single-step examples, 240 fixed-history trajectories and 8,289 referenced
videos. Full evaluation expands into 11,612 predictions; the deterministic smoke
selection has 12 steps and 16 trajectory turns (28 predictions).

## Install and download

Python 3.10+, `curl`, `ffmpeg` and `ffprobe` are required. For a lightweight client
without a GPU or the training stack:

```bash
python -m pip install -r requirements-diagbench.txt
python -m ec_verl.diagbench.download --output data/diagbench
export DIAGBENCH_ROOT="$PWD/data/diagbench/EmbodiedDiag-Bench-small-20261024"
python -m ec_verl.diagbench.validate --root "$DIAGBENCH_ROOT" --hash --report runs/diagbench-validation.json
```

The downloader pins ModelScope revision
`93a7e12e7e89459c16269d2ffc8416ab0e1be338`, resumes interrupted transfers, checks
all 5,170,502,918 archive bytes against SHA-256, and rejects unsafe ZIP paths.
The extracted package includes the upstream scripts, media manifest, repair
provenance and historical smoke results. Large videos/weights are ignored by Git.
The checked-in [provenance record](../validation/diagbench-upstream.json) identifies
the original scripts; `ec_verl/diagbench` contains the maintained integration.

## Local RynnBrain-8B smoke run

Prepare the full original `Alibaba-DAMO-Academy/RynnBrain-8B` checkpoint, not the
RynnBrain 1.1 series or Qwen's base weights. ModelScope offers it as
`DAMO_Academy/RynnBrain-8B`. The released model architecture is Qwen3-VL.
Install the repository's core GPU environment (`scripts/setup.sh`) first.
Provide a separate **vision-language** judge checkpoint:

```bash
export RYNN_MODEL=/models/RynnBrain-8B
export JUDGE_MODEL=/models/Qwen3-VL-32B-Instruct
export EC_RUN="$PWD/runs/diagbench-rynnbrain-smoke"
bash scripts/diagbench_smoke.sh
```

The script validates the data, starts RynnBrain, collects 28 greedy predictions,
releases that server, starts the selected judge on the same GPU, scores all
predictions and aggregates. It saves environment/model identities, predictions,
judgments, token budgets, truncations, checksums and stage logs. It manages only
its own server processes. The smoke generation budget is 512 tokens and must be
recorded when comparing runs. The original package's smoke budget was 256.

A smaller Qwen3-VL judge can check the pipeline when a 32B checkpoint is unavailable,
but its scores are **not comparable to the paper or the upstream release**.
An end-to-end smoke run is not full-benchmark validation or paper reproduction.
The runner does not train on evaluation examples.

## Existing API servers and full evaluation

Each stage can run separately using any compatible image-capable
`/v1/chat/completions` endpoint. Keep API credentials in `BENCH_API_KEY`.

```bash
python -m ec_verl.diagbench.evaluate collect --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18409/v1/chat/completions \
  --model rynnbrain --workers 1 --max-tokens 2048
python -m ec_verl.diagbench.evaluate judge --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18410/v1/chat/completions \
  --model vision-judge --workers 1 --judge-max-tokens 512
python -m ec_verl.diagbench.evaluate aggregate --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full
```

Add `--smoke` to **every stage** for the small selection. Add `--resume` with the
same settings after a failed/interrupted stage. Existing output is never silently
overwritten. Resume checks model, endpoint, data/media hashes, token budgets,
selection, media overrides and, for scoring, the prediction file hash.

## Monitoring

```bash
python -m tensorboard.main --logdir runs --host 127.0.0.1 --port 6006 --load_fast=false
```

Open <http://127.0.0.1:6006>. Every evaluation invocation writes TensorBoard events,
`status.json` and `metrics.jsonl`: data/model/collect/judge/aggregate waiting,
running, complete or failed; prediction/scoring completion and errors; and final
metrics. Smoke and formal runs have separate event directories. No training loss
is fabricated. If a process is forcibly killed, the scheduler exit status/log
must also be consulted; a stale running status is not proof of completion.

## Protocol and changes

- Videos replace `<video>` in position, retaining system messages and text history.
  Step: up to 6 frames/video. Trajectory: 5 fps sampling, up to 16 frames/video,
  latest 3 videos, width 448. Sampling and prompts retain upstream behavior.
- Current reference answers are held out of collection prompts. Trajectory
  histories contain dataset reference turns; this is offline teacher-history
  evaluation, not an interactive rollout or physical robot success rate.
- Roles follow each question, not whether a reference answer mentions success or
  failure. This preserves the release's fix for 252 misclassified trajectory turns.
- Judge measures outcome judgment. Cause uses failure-reference steps only.
  Sub measures action category; Fine requires action and target correctness.
  Trajectory success requires every planner action category correct; mean progress
  is the planner action-category correct fraction, not longest correct prefix.
- 523 video clips in this release were restored from original RGB recordings.
  Camera/rendering can differ from historical simulator replay; scores cannot be
  equated to old media versions.
- Integration changes: package imports/CLI entries, pinned download + SHA verification,
  TensorBoard, safe resumability, duplicate/missing/tampered-record and judge-enum
  checks, service provenance, one-GPU orchestration and regression tests.
  Existing upstream reference judgments aggregate identically with this adapter.

`ec_verl.evaluate` remains the separate four-field illustrative rubric evaluator;
DiagBench uses the released visual-judge protocol and its original schema.

Malformed judge enums receive at most two format-only follow-ups under the original criteria. Every raw response is retained in `judge_attempts`; prose is never coerced into a score. Exhausted repairs remain explicit errors and prevent complete aggregation.
