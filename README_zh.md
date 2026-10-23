<div align="center">
  <img src="docs/assets/branding/logo.svg" alt="Embodied-Corrector" width="640">

# Embodied-Corrector

**Learning from Feedback for Physical Failure Understanding and Correction**

[English](README.md) · **中文**

[项目主页](https://pm1255.github.io/embodied-corrector/) · [论文 PDF](docs/assets/paper.pdf) · [验证记录](guides/validation.md) · [训练说明](guides/training_zh.md)

</div>

通过公开执行证据学习物理失败诊断与可执行纠错，统一输出 **Judge → Cause → Sub → Fine**。本仓库包含论文网页、evaluation-first SFT、基于 verl 的 NEPO 训练，以及公开 EmbodiedBench / EB-ALFRED 仿真闭环。

**当前已验证单卡 Qwen 训练和真实仿真流程。** 训练使用 verl 的 DataProto、GRPO advantage 与 PPO loss；尚未实现原生分布式 RayPPOTrainer/FSDP。此次小样本运行没有复现论文表格效果。

## 更新

- **2026-10-24**：发布网页、代码和验证记录；18 项数值与接口检查通过，完成 Qwen3-VL-2B 训练、重新加载和真实 EB-ALFRED 仿真验证。

## 方法

<p align="center"><img src="docs/assets/figures/training.webp" alt="SFT 与 NEPO" width="960"></p>

1. **评估优先 SFT**：先训练 Judge/Cause，再基于已验证评估前缀训练 Sub/Fine。
2. **同策略双上下文打分**：同一未更新策略，在生成评估和已验证评估前缀下，对相同规划 token 计算概率。
3. **NEPO**：使用 `q − p` 概率差，对高熵位置的负信号进行衰减，再叠加到 GRPO 优势。
4. **执行闭环**：规划器选择动作，真实环境执行，纠错器读取反馈并向下一次规划提供四字段纠错。

图片和公开证据在两条训练分支中保持一致。部署输入不包含训练标注或隐藏模拟器状态。详细公式与实现范围见 [方法说明](guides/method.md)。

## 安装和训练

建议 Linux、Python 3.12、CUDA GPU。先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)，再执行：

```bash
git clone https://github.com/pm1255/embodied-corrector.git
cd embodied-corrector
bash scripts/setup.sh
export EC_MODEL=/path/to/Qwen3-VL-2B-Instruct
bash scripts/validate_gpu.sh
```

模型目录需包含完整 Qwen 权重、tokenizer 和 processor。上述脚本执行多模态对齐检查、两阶段 SFT、NEPO、检查点保存和重新加载评估。

自己的数据需先按原始轨迹划分，避免同源泄漏：

```bash
source scripts/env.sh
"$EC_PYTHON" -m ec_verl.data split --input /data/all.jsonl --output /data/split
bash scripts/train.sh \
  --model "$EC_MODEL" \
  --train /data/split/train.jsonl --eval /data/split/eval.jsonl \
  --output runs/my-run --device cuda --dtype bfloat16 --lora \
  --scope formal --sft-steps 1000 --nepo-steps 500 --group-size 4
```

步数和 κ/β/λ 默认值是工程示例，不能视为论文披露的参数。完整说明见 [训练指南](guides/training_zh.md) 和 [数据格式](guides/data.md)。

## 真实 EmbodiedBench 验证

按照 [环境说明](guides/embodiedbench.md) 准备官方仓库、数据和 AI2-THOR：

```bash
export EC_EB_ROOT=/path/to/EmbodiedBench
export EC_THOR_EXECUTABLE=/path/to/thor-201909061227-Linux64
export EC_CORRECTOR="$PWD/runs/qwen-vl-smoke/checkpoints/nepo-0002"
bash scripts/validate_embodiedbench.sh
```

基础 Qwen 充当规划器，训练后的检查点充当纠错器。模型只读取公开图像与执行反馈，环境 `task_success` 决定最终成功标志。实际动作、拒绝反馈、原始纠错和逐步图片都会保存。其他 EmbodiedBench 后端尚未适配。

## 已完成的验证

| 范围 | 结果 |
|---|---|
| 代码检查 | 18 项通过 |
| SFT | 两阶段各 12 步 |
| NEPO | 2 步，154 个规划 token，非零信号和参数更新 |
| 保存与重新加载 | 两条评估输出完全一致 |
| 诊断教学示例 | 格式 2/2，四字段联合命中 **0/2** |
| 真实 EB-ALFRED | 11 次动作调用、10 次格式有效纠错，环境正常结束 |
| 仿真任务成功 | **0/1** |

这些结果证明代码路径可执行。动作调用包含环境拒绝的动作；格式有效不代表内容正确。正式效果需要完整标注数据、官方或经验证的判分器及独立评估。详细记录见 [验证报告](guides/validation.md)。

## 监控

```bash
source scripts/env.sh
"$EC_PYTHON" -m tensorboard.main --logdir "$EC_ROOT/runs" --port 6006 --bind_all --load_fast=false
```

打开 `http://localhost:6006`，可查看 SFT/NEPO loss、奖励、熵、概率差信号、梯度、检查点和评估进度。正式运行与 smoke 验证分开记录。

## 数据和代码范围

包含四条由论文图示整理的教学数据；未发布完整训练集、官方 EmbodiedDiag-Bench、预训练权重或正式模型检查点。训练器是单卡实现，目前不支持优化器断点续训。详细目录见 [英文 README](README.md#repository-structure)。

论文作者暂不展示。第三方源码与论文材料保留原有权利，见 [第三方说明](THIRD_PARTY_NOTICES.md)。
