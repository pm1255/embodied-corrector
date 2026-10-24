<div align="center">

# Embodied-Corrector

**Learning from Feedback for Physical Failure Understanding and Correction**

[![Code](https://img.shields.io/badge/Code-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/pm1255/embodied-corrector)
[![Project Page](https://img.shields.io/badge/Project_Page-5969EC?style=for-the-badge&logo=googlechrome&logoColor=white)](https://pm1255.github.io/embodied-corrector/)

**English** · [Chinese](README_zh.md)

</div>

## Overview

The [latest introduction and 12 recovery videos](https://pm1255.github.io/embodied-corrector/?v=visible-failure-12#video) are on the project page. Native attachments below are from the previous recording revision.

https://github.com/user-attachments/assets/a89f5368-ed4c-44c3-905a-4011c73f6d9b

Research overview with English narration and subtitles. Robot motion comes from continuous simulator recordings.

## Selected successful recoveries

[Watch the updated 12-episode gallery](https://pm1255.github.io/embodied-corrector/?v=visible-failure-12#simulations): all six RoboCasa videos now combine wrong-way navigation and manipulation.

The updated project gallery shows the initial action without a premature Judge/Cause label, followed by an observed failure, the **Judge → Cause → Sub → Fine** output, corrective actions, and a verified successful ending. Titles use the original task instructions; all video text is English. Videos retain every action frame at **native 20 fps and 1× speed**, with a three-second final result hold. Each recovery rejoins a newly collected, verified successful reference trajectory after a controlled perturbation.

### Open the top layer of the drawer and put the cream cheese inside

**LIBERO-PRO.** Restore handle contact, open the top drawer, and place the cream cheese inside. **Final environment result: success.**

https://github.com/user-attachments/assets/943e6c8b-d766-4894-96d0-f1cc69fdd9ec

### Put both the cream cheese box and the butter in the basket

**LIBERO-PRO.** Correct the grasp height and put both required objects in the basket. **Final environment result: success.**

https://github.com/user-attachments/assets/02a661f5-b2cf-48b2-9925-1acb15dbcd65

### Place the garlic and the mushroom on separate cutting boards.

**RoboCasa365, previous recording.** Correct a missed grasp and place the two vegetables on separate cutting boards. **Final environment result: success.**

https://github.com/user-attachments/assets/e5711720-0fca-4182-a5aa-a25259f95a6c

These demonstrations use a **GPT proxy with simulator-state-assisted analytical control**. They illustrate the correction workflow and are separate from trained Embodied-Corrector / RynnBrain evaluation results.

The [project gallery](https://pm1255.github.io/embodied-corrector/?v=visible-failure-12#simulations) contains **12 selected successful recovery episodes: 6 LIBERO-PRO and 6 RoboCasa365**, with navigation and manipulation combined in all six RoboCasa episodes, using the same video layout and visible brain output. They cover task and seed variations; they are not 12 distinct tasks or an estimate of benchmark success rate. See [episode provenance and verification](guides/selected_recoveries.md).

## Abstract

Reliable embodied execution requires physical causal understanding, adaptation to the executor’s capabilities, and revision from interaction feedback. **Embodied-Corrector**, trained from **RynnBrain-8B**, connects observed failures with diagnosis and executable recovery through **Judge → Cause → Sub → Fine**. We construct controlled failure–recovery branches from successful trajectories, changing one physical factor at a time. **Evaluation-first SFT** learns assessment before planning; **NEPO** combines group-relative rewards with entropy-gated token-level guidance across generated and verified evaluation contexts. At inference time, the model uses public observations and within-episode history without parameter updates. The manuscript reports improvements in failure reasoning, planning transfer, and recovery with fixed execution backends, including **55.0% → 68.9%** macro-average success with a fixed code backend and **1.2% → 7.3%** on RoboCasa365 Composite-Unseen with frozen π₀.₅.

## Motivation

Multimodal models can understand instructions, perceive scenes, and generate plans. Physical execution, however, is jointly constrained by the embodiment, controller, and environment. When an action produces an unexpected outcome, continuing the original plan can repeat the same failure. We ask: **how can an embodied brain understand why execution failed and turn interaction feedback into a recovery that its current executor can realize?**

We identify three complementary capabilities:

- **Physical causal understanding and failure localization:** trace execution to the action, physical relation, or unmet prerequisite that first invalidated progress—for example, distinguish mistimed grasping from an unsuitable contact pose or an omitted earlier step.
- **Execution-capability identification and adaptation:** adapt the content and granularity of recovery instructions to the current state and executor, producing subtasks a fixed controller or frozen VLA can carry out.
- **Learning from interaction experience:** use previous actions, observations, and correction outcomes as evidence for the next decision, adapting through context without updating model parameters at inference time.

<p align="center"><img src="docs/assets/figures/diagnosis.webp" alt="Physical failure diagnosis and cause-level feedback" width="960"></p>

## Method

We introduce **Embodied-Corrector**, trained from **RynnBrain-8B** with evaluation-first SFT and NEPO, which turns physical execution feedback into failure diagnosis and executable recovery. Its structured reasoning follows **Judge → Cause → Sub → Fine**: assess the execution outcome, identify the failure cause, select a recovery subtask, and provide fine-grained action guidance. Recovery planning is thus grounded in an assessment of what actually happened.

<p align="center"><img src="docs/assets/figures/training.webp" alt="Evaluation-first SFT and NEPO training framework" width="960"></p>

1. **Controlled failure–recovery data.** Branch successful trajectories at subtask boundaries and intervene on one physical factor to connect actions, observable consequences, causes, and recoveries. Retain observable, recoverable failures and split source trajectories before generating perturbations.
2. **Evaluation-first supervised fine-tuning.** Learn outcome judgment and cause analysis (Judge/Cause), then learn recovery planning (Sub/Fine) conditioned on verified evaluations, connecting diagnosis with planning.
3. **NEPO policy optimization.** Address the mismatch between verified evaluations used during training and model-generated evaluations at deployment. The same policy scores identical planning tokens under the two evaluation contexts. Noise-Aware Entropy-Gated Policy Optimization (**NEPO**) combines group-relative rewards with token probability differences, preserves positive guidance, and uses entropy gating to attenuate uncertain negative signals.
4. **Closed-loop correction from interaction history.** Observe outcomes, diagnose failures, and revise subsequent plans while keeping the execution backend fixed. Within-episode actions and feedback inform the next decision without parameter updates at inference time.

Verified evaluations are used only during training. At deployment, the model generates all four fields from observable execution evidence. See the [method guide](guides/method.md) for equations and their correspondence to the implementation.

## Experiments

The paper evaluates the corrective brain from **failure diagnosis → planning transfer → closed-loop recovery**. All results below are reported in the manuscript and measured in simulation.

| Setting | Comparison | Baseline | Embodied-Corrector | Gain | Source |
| --- | --- | ---: | ---: | ---: | --- |
| Fixed code backend | RynnBrain-8B → RynnBrain-NEPO; macro-average across 10 conditions | 55.0% | 68.9% | +13.9 pp | Table 3 |
| Frozen π₀.₅ | RoboCasa365 Composite-Unseen; add corrective brain | 1.2% | 7.3% | +6.1 pp | Figure 4 |
| Planning transfer | EB-ALFRED Base; RynnBrain-8B → RynnBrain-NEPO | 30% | 78% | +48 pp | Table 2 |
| Failure judgment | EmbodiedDiag-Bench Navigation; Judge | 23.6% | 79.6% | +56.0 pp | Table 1 |
| Cause diagnosis | EmbodiedDiag-Bench Navigation; Cause | 13.6% | 58.2% | +44.6 pp | Table 1 |

The code-backend comparison fixes the GPT-5.5 planner, analytic robot functions, perception, and execution budget; its macro-average covers four OmniBehavior and six LIBERO-PRO conditions. The frozen-VLA gain is specific to **Composite-Unseen**; Atomic-Seen can regress when unnecessary instruction changes are introduced. Planning transfer uses identical observation/action interfaces and step limits, without an explicit failure prompt or corrective Harness. These paper results are distinct from the runnable Qwen software example below.

[Explore all four evaluation settings and full result tables →](https://pm1255.github.io/embodied-corrector/#results)

<p align="center"><img src="docs/assets/figures/dynamics.webp" alt="NEPO post-training loss, answer reward and token entropy" width="960"></p>

## Citation

If you find this work useful for your research, please cite Embodied-Corrector. The formal paper BibTeX will be added when its citation metadata is released. For now, the following entry cites the project page.

```bibtex
@misc{embodiedcorrector2026,
  title        = {Embodied-Corrector},
  year         = {2026},
  howpublished = {Project page},
  url          = {https://pm1255.github.io/embodied-corrector/}
}
```

[Download the project citation](docs/citation.bib)

## Installation

Linux, Python 3.12 and a CUDA GPU are recommended. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/pm1255/embodied-corrector.git
cd embodied-corrector
bash scripts/setup.sh
```

The repository vendors **verl v0.9.1** at a fixed commit. PyTorch is installed separately from the CUDA 12.8 wheel index; other core versions are pinned in [requirements-core.txt](requirements-core.txt). The exact environment used for validation is documented separately in [guides/validation.md](guides/validation.md).

## Training

The paper model follows **RynnBrain-8B → evaluation-first SFT → NEPO → Embodied-Corrector**. The runnable Qwen example below checks the software pipeline; the paper model and paper-reported results are based on RynnBrain.

### Qwen pipeline example

Prepare a local copy of [`Qwen/Qwen3-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct), including model weights, tokenizer and processor files:

```bash
export EC_MODEL=/path/to/Qwen3-VL-2B-Instruct
bash scripts/validate_gpu.sh
```

This runs numerical checks, a real multimodal alignment check, two SFT stages, two NEPO updates, checkpoint saving, evaluation, and checkpoint reload evaluation. Four illustrative paper-derived examples are included solely for this software validation.

For your own dataset:

```bash
source scripts/env.sh
"$EC_PYTHON" -m ec_verl.data split --input /data/all.jsonl --output /data/split
"$EC_PYTHON" -m ec_verl.data validate \
  --train /data/split/train.jsonl --eval /data/split/eval.jsonl

bash scripts/train.sh \
  --model "$EC_MODEL" \
  --train /data/split/train.jsonl --eval /data/split/eval.jsonl \
  --output runs/my-run --device cuda --dtype bfloat16 --lora \
  --scope formal --sft-steps 1000 --nepo-steps 500 --group-size 4 \
  --kappa 1 --beta .5 --opd-coef 1
```

These hyperparameters are engineering examples, not values disclosed by the paper. Split by original source trajectory before constructing perturbation branches. Image inputs require a vision-language model. See [data schema](guides/data.md) and [training guide in Chinese](guides/training_zh.md).

## EmbodiedBench evaluation

<p align="center"><img src="docs/assets/figures/harness.webp" alt="Planning, execution and correction workflow" width="960"></p>

The adapter executes the official **EBAlfEnv**. In this pipeline example, a base Qwen model acts as planner, and the trained LoRA checkpoint acts as corrector. Only public observations, actions and feedback enter model prompts; task success is measured using the environment's own predicate.

After preparing the pinned EmbodiedBench repository, task data, AI2-THOR build and display dependencies described in [the environment guide](guides/embodiedbench.md):

```bash
export EC_EB_ROOT=/path/to/EmbodiedBench
export EC_THOR_EXECUTABLE=/path/to/thor-201909061227-Linux64
export EC_CORRECTOR="$PWD/runs/qwen-vl-smoke/checkpoints/nepo-0002"
bash scripts/validate_embodiedbench.sh
```

The default run evaluates one base-subset simulation task with a 30-decision budget. Per-step images, actions, raw and normalized corrections, environment feedback and final metrics are saved. The script closes its inference and display processes on exit.

This Qwen planner verifies the interface; it differs from the fixed planner in the manuscript. Habitat, Navigation and Manipulation backends are not implemented here.

## DiagBench evaluation

The released EmbodiedDiag-Bench small dataset and its collect → visual judge → aggregate protocol are integrated. **RynnBrain-8B has completed a 28-prediction smoke run**, including independent visual judging and aggregation. The full **11,612-prediction evaluation is supported but has not been run**.

The smoke run used a 512-token budget (6 truncated answers) and a Qwen3-VL-2B-Instruct judge for pipeline verification. Formal comparisons require a larger generation budget and a fixed, comparable judge configuration. Pinned downloads, integrity checks, safe resume and TensorBoard are included. See the [evaluation guide](guides/diagbench.md) and [run record](validation/diagbench-smoke-20261024.json).

## Monitoring

```bash
source scripts/env.sh
"$EC_PYTHON" -m tensorboard.main \
  --logdir "$EC_ROOT/runs" --port 6006 --bind_all --load_fast=false
```

Open `http://localhost:6006`. Logs include stage waiting/running/completed/failed states, SFT loss, NEPO reward/entropy/probability gap, gradients, checkpoints and evaluation progress. Smoke and formal curves are separated.

## Repository structure

```text
.
├── ec_verl/          # SFT, NEPO, inference and benchmark adapters
├── scripts/          # Setup, training and validation entry points
├── configs/          # Documented smoke-run settings
├── data/             # Four labeled teaching examples
├── tests/            # Numerical, leakage and interface checks
├── guides/           # Method, data, environment and validation notes
├── validation/       # Small machine-readable verification records
├── docs/             # Author-free project page for GitHub Pages
└── vendor/verl/      # Pinned upstream verl source and license
```

## Acknowledgements and rights

The paper model is based on [RynnBrain](https://github.com/alibaba-damo-academy/RynnBrain). The implementation uses [verl](https://github.com/verl-project/verl), [Transformers](https://github.com/huggingface/transformers), [PEFT](https://github.com/huggingface/peft), [Qwen](https://github.com/QwenLM/Qwen3-VL), [EmbodiedBench](https://github.com/EmbodiedBench/EmbodiedBench) and [AI2-THOR](https://github.com/allenai/ai2thor). Repository presentation takes inspiration from [VLA-Corrector](https://github.com/ZJU-OmniAI/vla-corrector).

Third-party code retains its original license. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The manuscript and its figures retain their respective rights.
