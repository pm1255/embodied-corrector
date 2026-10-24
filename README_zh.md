<div align="center">

# Embodied-Corrector

**Learning from Feedback for Physical Failure Understanding and Correction**

[![Code](https://img.shields.io/badge/Code-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/pm1255/embodied-corrector)
[![Project Page](https://img.shields.io/badge/Project_Page-5969EC?style=for-the-badge&logo=googlechrome&logoColor=white)](https://pm1255.github.io/embodied-corrector/)

[English](README.md) · **中文**

</div>

## 项目介绍

https://github.com/user-attachments/assets/d41e20cd-94c3-4598-b413-608e2d1d3d80

英文配音、中文字幕，介绍研究动机与方法。机械臂运动来自连续仿真录像。

## 连续仿真案例

### LIBERO-PRO · 抽屉放置

拉开顶层抽屉，在一次抓取失败后调整夹持方向，将奶油奶酪放入抽屉。**官方任务判定：完成。** 完整回合以 2 倍速播放，并展示诊断与动作说明。

https://github.com/user-attachments/assets/8c6f4297-f74d-459e-87ec-ab9f6eb27e0e

### RoboCasa365 · Colorful Salsa

尝试将四种食材放到砧板上。**官方任务判定：未完成。** 完整回合以 2 倍速播放，保留未成功的尝试。

https://github.com/user-attachments/assets/ec48e161-533e-44c1-86d1-64503f6fc8d0

以上两个案例使用 GPT 代理与仿真状态辅助定位的解析控制器，展示交互流程，不代表训练后的 Embodied-Corrector 或 RynnBrain 测评成绩。

[项目案例库](https://pm1255.github.io/embodied-corrector/#simulations) 包含 **20 个 LIBERO-PRO 和 30 个 RoboCasa365 回合**：6 个 GPT 代理演示和 44 个明确标注的脚本控制回合。每个回合保留任务、种子、动作、反馈和官方结果，详见[执行记录与来源说明](guides/simulation_report_zh.md)。

## 摘要

可靠的具身执行需要理解物理失败的原因、适应执行器能力，并根据交互反馈修订后续决策。我们提出基于 **RynnBrain-8B** 训练的 **Embodied-Corrector**，通过 **Judge → Cause → Sub → Fine** 将执行观察、失败诊断与可执行恢复联系起来。我们从成功轨迹构建可控的失败—恢复分支，每次只改变一个物理因素；采用**评估优先 SFT**，先学习判断与原因，再学习恢复规划；通过 **NEPO** 将组相对奖励与两种评估上下文之间的 token 级指导结合，并用熵门控抑制不确定的负向信号。部署时，模型只使用公开观察和当前回合历史，不更新参数。论文在失败推理、规划迁移和固定执行后端的恢复任务上进行评估：固定代码后端的宏平均成功率由 **55.0% 提升至 68.9%**，冻结 π₀.₅ 在 RoboCasa365 未见组合任务上的成功率由 **1.2% 提升至 7.3%**。

## 研究动机

多模态模型已经能够理解任务、感知场景并生成计划，但物理执行会受到机器人形态、控制器能力和环境状态的共同约束。动作的实际结果可能偏离预期，继续沿用原有计划就可能重复失败。我们的核心问题是：**如何让具身大脑理解执行为什么失败，并从交互反馈中形成当前执行器能够完成的恢复方案？**

这需要三种相互补充的能力：

- **物理因果理解与失败定位**：沿执行过程找到最先破坏任务进展的动作、物理关系或缺失前提，例如区分抓取时机错误、接触姿态不当和前置步骤遗漏。
- **执行能力识别与适应**：根据当前状态和执行器能力调整指令内容与粒度，将恢复目标转化为固定控制器或冻结 VLA 可以执行的子任务。
- **从交互经验中学习**：把历史动作、观察和纠错结果作为下一步决策的证据，在推理时通过上下文修正行为，无需更新模型参数。

<p align="center"><img src="docs/assets/figures/diagnosis.webp" alt="物理失败诊断与因果反馈" width="960"></p>

## 方法

我们提出基于 **RynnBrain-8B** 训练的 **Embodied-Corrector**，将物理执行反馈转化为原因诊断与可执行恢复。模型按照 **Judge → Cause → Sub → Fine** 依次判断执行结果、定位失败原因、选择恢复子任务并生成细粒度动作指导，使恢复计划建立在对执行过程的评估之上。

<p align="center"><img src="docs/assets/figures/training.webp" alt="评估优先 SFT 与 NEPO 训练框架" width="960"></p>

1. **可控失败—恢复数据构建**：从成功轨迹的子任务边界出发，对单个物理因素施加干预，建立动作、可观察后果、失败原因与恢复方案之间的对应关系。保留可观察、可恢复的失败，并在生成扰动前按源轨迹划分训练与评估数据。
2. **评估优先的监督微调**：先学习执行结果与失败原因（Judge/Cause），再学习在已验证评估条件下生成恢复计划（Sub/Fine），将诊断与规划联系起来。
3. **NEPO 策略优化**：针对训练时使用已验证评估、部署时依赖模型自身评估的差异，用同一策略在两种评估上下文下对相同规划 token 打分。Noise-Aware Entropy-Gated Policy Optimization（NEPO）将组相对奖励与 token 概率差信号结合，保留正向指导，并用熵门控衰减不确定位置的负向信号。
4. **基于交互历史的闭环纠错**：在固定执行后端上观察结果、诊断原因并修订后续计划。模型通过当前回合的历史动作和反馈调整决策，执行后端保持固定，推理过程中不更新参数。

已验证评估仅用于训练；部署时模型从可观察执行证据生成完整的四字段响应。算法与代码对应关系见 [方法说明](guides/method.md)。

## 实验

论文从**失败诊断 → 规划迁移 → 闭环恢复**评估纠错大脑。下表为论文报告的仿真结果。

| 评估设置 | 比较条件 | 基线 | Embodied-Corrector | 提升 | 论文出处 |
| --- | --- | ---: | ---: | ---: | --- |
| 固定代码后端 | RynnBrain-8B → RynnBrain-NEPO；10 种条件宏平均 | 55.0% | 68.9% | +13.9 个百分点 | 表 3 |
| 冻结 π₀.₅ | RoboCasa365 Composite-Unseen；加入纠错大脑 | 1.2% | 7.3% | +6.1 个百分点 | 图 4 |
| 规划迁移 | EB-ALFRED Base；RynnBrain-8B → RynnBrain-NEPO | 30% | 78% | +48 个百分点 | 表 2 |
| 失败判断 | EmbodiedDiag-Bench 导航；Judge | 23.6% | 79.6% | +56.0 个百分点 | 表 1 |
| 原因诊断 | EmbodiedDiag-Bench 导航；Cause | 13.6% | 58.2% | +44.6 个百分点 | 表 1 |

固定代码后端比较中，GPT-5.5 规划器、机器人解析函数、感知模块与执行预算保持一致，宏平均覆盖 4 个 OmniBehavior 和 6 个 LIBERO-PRO 条件。冻结 VLA 的提升对应**未见组合任务**；在短原子任务中，不必要的指令改写也可能使成功率下降。规划迁移使用相同观察、动作接口和步数限制，不提供显式失败提示或纠错 Harness。上述论文结果与下方 Qwen 工程流程示例分别对应不同用途。

[查看四类评估、完整结果表及实验协议 →](https://pm1255.github.io/embodied-corrector/#results)

<p align="center"><img src="docs/assets/figures/dynamics.webp" alt="NEPO 的训练损失、答案奖励和 token 熵" width="960"></p>

## 引用

如果这项工作对你的研究有帮助，欢迎引用 Embodied-Corrector。正式论文的 BibTeX 将在引用信息公开后补充；目前可使用以下条目引用项目主页。

```bibtex
@misc{embodiedcorrector2026,
  title        = {Embodied-Corrector},
  year         = {2026},
  howpublished = {Project page},
  url          = {https://pm1255.github.io/embodied-corrector/}
}
```

[下载项目引用条目](docs/citation.bib)

## 安装和训练

论文模型的训练路线为 **RynnBrain-8B → 评估优先 SFT → NEPO → Embodied-Corrector**。下列 Qwen3-VL 命令是便于运行的代码流程示例；论文模型及主页中的论文结果均基于 RynnBrain。

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

## EmbodiedBench 评估

按照 [环境说明](guides/embodiedbench.md) 准备官方仓库、数据和 AI2-THOR：

```bash
export EC_EB_ROOT=/path/to/EmbodiedBench
export EC_THOR_EXECUTABLE=/path/to/thor-201909061227-Linux64
export EC_CORRECTOR="$PWD/runs/qwen-vl-smoke/checkpoints/nepo-0002"
bash scripts/validate_embodiedbench.sh
```

此代码流程示例中，基础 Qwen 充当规划器，训练后的检查点充当纠错器。模型只读取公开图像与执行反馈，环境 `task_success` 决定最终成功标志。实际动作、拒绝反馈、原始纠错和逐步图片都会保存。其他 EmbodiedBench 后端尚未适配。

## DiagBench 测评

已接入 ModelScope 发布的 EmbodiedDiag-Bench small 数据与“模型推理 → 视觉裁判 → 指标汇总”流程。**真实 RynnBrain-8B 已完成 28 条预测、独立视觉裁判判分和汇总；支持 11,612 条全量预测，但全量尚未运行。**

试跑采用 512-token 预算，其中 6 条回答截断；裁判使用 Qwen3-VL-2B-Instruct 验证流程。正式比较前应提高生成预算、统一裁判配置。代码已提供固定版本下载、完整性校验、安全续跑和 TensorBoard，详见[中文运行指南](guides/diagbench_zh.md)与[试跑记录](validation/diagbench-smoke-20261024.json)。

## 监控

```bash
source scripts/env.sh
"$EC_PYTHON" -m tensorboard.main --logdir "$EC_ROOT/runs" --port 6006 --bind_all --load_fast=false
```

打开 `http://localhost:6006`，可查看 SFT/NEPO loss、奖励、熵、概率差信号、梯度、检查点和评估进度。正式运行与 smoke 验证分开记录。

第三方源码与论文材料保留原有权利，见 [第三方说明](THIRD_PARTY_NOTICES.md)。
