# Embodied-Corrector · 训练与评估说明

项目模型基于 **RynnBrain-8B**，通过评估优先 SFT 和 NEPO 训练。本文档直接说明 RynnBrain 的代码运行流程。

根据《Embodied-Corrector》论文实现：公共证据输入 → Judge/Cause SFT → 条件式 Sub/Fine SFT → NEPO → 检查点 → 独立评估 → 公开 EB-ALFRED 仿真调用。

实现直接使用 **verl v0.9.1 的 DataProto、GRPO advantage、clipped PPO loss**，上游源码固定在 `vendor/verl`。训练器为单卡 PyTorch/Hugging Face 实现，可通过 Ray 单卡任务执行；没有把它包装成已经验证的原生 RayPPOTrainer/FSDP 多卡训练。完整代码流程检查记录见 [验证详情](validation.md)。

## 快速开始

建议 Linux、Python 3.12、CUDA GPU 和 RynnBrain-8B，实际显存需求取决于图片分辨率与序列长度。

```bash
bash scripts/setup.sh
export EC_MODEL=/models/RynnBrain-8B
bash scripts/validate_gpu.sh
```

`validate_gpu.sh` 执行数值/数据检查、多模态对齐检查、两阶段 SFT、NEPO、检查点保存和评估。

输入包含图片时使用 RynnBrain 的视觉处理器，不会静默删除图片。

## 使用自己的数据

每行一个 JSON 对象，字段见 `data.md`。先按原始轨迹划分，之后才能生成扰动分支。不同划分中出现相同 `source_trajectory` 会直接报错。

```bash
source scripts/env.sh
"$EC_PYTHON" -m ec_verl.data split --input /data/all.jsonl --output /data/split
"$EC_PYTHON" -m ec_verl.data validate --train /data/split/train.jsonl --eval /data/split/eval.jsonl
bash scripts/train.sh --model "$EC_MODEL" --train /data/split/train.jsonl --eval /data/split/eval.jsonl --output runs/my-run --lora --dtype bfloat16 --device cuda --scope formal --sft-steps 1000 --nepo-steps 500 --group-size 4 --kappa 1 --beta .5 --opd-coef 1
```

这些步数与 NEPO 门控参数是示例配置，**不是论文披露的超参数**。生产训练需要先用独立验证集选择参数。当前入口按阶段保存，不支持优化器断点续训；从 LoRA 检查点传入 `--model` 可开启一个新的训练运行，不等价于恢复原优化器状态。

## 监控

```bash
source scripts/env.sh
"$EC_PYTHON" -m tensorboard.main --logdir "$EC_ROOT/runs" --port 6006 --bind_all --load_fast=false
```

页面：[TensorBoard](http://127.0.0.1:6006/#scalars)。显示阶段等待/运行/完成/失败、SFT loss、NEPO loss/reward/entropy/gap、梯度、检查点路径、评估完成率。`smoke` 与 `formal` 分开记录。`runs/<name>/status.json`、`metrics.jsonl` 与 `rollouts.jsonl` 同步落盘。

## EmbodiedBench

两个评估入口含义不同：

- `ec_verl.evaluate`：论文的 Judge/Cause/Sub/Fine 字段诊断接口。官方 EmbodiedDiag-Bench 尚未随 PDF 提供；随附数据仅为教学示例。
- `ec_verl.embodiedbench`：公开 EmbodiedBench 的真实 **EB-ALFRED** 环境。读取真实图像与动作反馈，以环境 `task_success` 计分，保留逐步图片和轨迹。

```bash
# 安装官方环境、任务数据及显示服务，见 embodiedbench.md
source scripts/env.sh
"$EC_PYTHON" -m ec_verl.serve --model "$EC_MODEL" --corrector-model runs/rynnbrain/checkpoints/nepo-0002 --device cuda
# 在另一个终端执行
"$EC_PYTHON" -m ec_verl.embodiedbench --repo /path/to/EmbodiedBench --endpoint http://127.0.0.1:18127/respond --corrector-endpoint http://127.0.0.1:18127/correct --output runs/eb-alfred --episodes 1 --max-steps 30 --display 1
```

RynnBrain 充当规划器，训练后的检查点充当纠错器。其他 EmbodiedBench 环境（Habitat、Navigation、Manipulation）没有在本实现中声称已适配。

## 代码位置

| 文件 | 用途 |
|---|---|
| `ec_verl/nepo.py` | 论文概率差、非对称熵门控、verl GRPO/PPO 调用 |
| `ec_verl/model.py` | RynnBrain 视觉语言推理、token 对齐、检查点 |
| `ec_verl/train.py` | SFT → NEPO → 评估 |
| `ec_verl/schema.py`、`prompts.py` | 数据验证与公共证据边界 |
| `ec_verl/reward.py` | 可替换字段奖励接口 |
| `ec_verl/evaluate.py` | 字段与领域指标 |
| `ec_verl/serve.py`、`embodiedbench.py` | 规划—执行—纠错闭环 |
| `method.md` | 算法约定与复现边界 |

本项目奖励使用显式字段/关键词规则，不是论文未公开的官方判分器。不要把夹具上的分数作为论文性能或真实机器人能力。

代码运行参数和入口见 [验证详情](validation.md)。
