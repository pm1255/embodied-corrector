# Embodied-Corrector · verl + Qwen

根据用户提供的《Embodied-Corrector》论文实现：公共证据输入 → Judge/Cause SFT → 条件式 Sub/Fine SFT → NEPO → 检查点 → 独立评估 → 公开 EB-ALFRED 仿真调用。

实现直接使用 **verl v0.9.1 的 DataProto、GRPO advantage、clipped PPO loss**，上游源码固定在 `vendor/verl`。训练器为单卡 PyTorch/Hugging Face 实现，可通过 Ray 单卡任务执行；没有把它包装成已经验证的原生 RayPPOTrainer/FSDP 多卡训练。完整实验状态见工作区的 [report_summary.md](validation.md)。

## 快速开始

建议 Linux、Python 3.12、CUDA GPU，Qwen3-VL-2B-Instruct，24 GB 以上显存。实际显存需求取决于图片分辨率与序列长度。

```bash
bash scripts/setup.sh
export EC_MODEL=/path/to/Qwen3-VL-2B-Instruct
bash scripts/validate_gpu.sh
```

`validate_gpu.sh` 执行数值/数据检查、真实多模态对齐检查、两阶段 SFT、两步 NEPO、保存与重新加载评估。默认使用论文图片的四条教学示例，结果只用于验证代码流程。

语言模型也可运行文本夹具：

```bash
export EC_MODEL=/path/to/Qwen3-0.6B
bash scripts/smoke.sh
```

输入包含图片时会要求 VL 模型，不会静默删除图片。

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
"$EC_PYTHON" -m ec_verl.serve --model "$EC_MODEL" --corrector-model runs/qwen-smoke/checkpoints/nepo-0002 --device cuda
# 在另一个终端执行
"$EC_PYTHON" -m ec_verl.embodiedbench --repo /path/to/EmbodiedBench --endpoint http://127.0.0.1:18127/respond --corrector-endpoint http://127.0.0.1:18127/correct --output runs/eb-alfred --episodes 1 --max-steps 30 --display 1
```

基础 Qwen 充当规划器，训练后的检查点充当纠错器。这验证论文工作流的接口；不代表复现了论文中固定 GPT-5.5 规划器的执行结果。其他 EmbodiedBench 环境（Habitat、Navigation、Manipulation）没有在本实现中声称已适配。

## 代码位置

| 文件 | 用途 |
|---|---|
| `ec_verl/nepo.py` | 论文概率差、非对称熵门控、verl GRPO/PPO 调用 |
| `ec_verl/model.py` | Qwen/VL 推理、token 对齐、检查点 |
| `ec_verl/train.py` | SFT → NEPO → 评估 |
| `ec_verl/schema.py`、`prompts.py` | 数据验证与公共证据边界 |
| `ec_verl/reward.py` | 可替换字段奖励接口 |
| `ec_verl/evaluate.py` | 字段与领域指标 |
| `ec_verl/serve.py`、`embodiedbench.py` | 规划—执行—纠错闭环 |
| `method.md` | 算法约定与复现边界 |

本项目奖励使用显式字段/关键词规则，不是论文未公开的官方判分器。不要把夹具上的分数作为论文性能或真实机器人能力。

## 已验证的最小闭环（2026-10-24）

- Qwen3-VL-2B，单 H100，LoRA；18 项数值与接口检查通过。
- 两阶段 SFT 各 12 步，NEPO 2 步；154 个规划 token、非零特权信号、参数更新。
- 检查点重新加载后两条示例输出与原输出完全一致。
- 公开 EB-ALFRED base 第 0 个任务：11 次真实动作调用、10 次有效四字段纠错、环境正常结束。**任务失败，成功率 0/1**，不是论文成绩。

这证明代码和接口可执行，不证明少量示例训练后的模型具有可靠纠错能力。诊断示例仅 2 条训练 / 2 条评估，四字段联合命中也为 0。正式效果需要完整标注集和独立测试集。
