# Embodied-Corrector · Video introduction

English narration with Chinese subtitles. Robot motion is decoded from continuous simulator MP4 recordings; no paper-frame sequence is used to simulate motion. The gallery demonstrations use a GPT proxy and an analytical controller with privileged simulator localization. They are separate from trained-model, manuscript-reported quantitative results. All excerpts play at 1×.

## 00:00 · Recover, don’t just continue.

When physical execution fails, continuing the same plan can repeat the same mistake. Embodied Corrector learns to understand the cause and recover.

物理执行失败后，继续原计划可能重复同样的错误。Embodied-Corrector 学习理解原因并恢复执行。

## 00:08 · Understand why. Decide how.

A corrective brain needs physical causal understanding, awareness of its executor, and the ability to learn from interaction history.

纠错大脑需要理解物理因果、识别执行器能力，并利用交互历史调整决策。

## 00:16 · Built on RynnBrain-8B.

We train RynnBrain-8B with evaluation-first supervised fine-tuning and NEPO. The resulting model is Embodied-Corrector.

我们以 RynnBrain-8B 为基础，通过评估优先的监督微调与 NEPO，训练得到 Embodied-Corrector。

## 00:24 · Assess first. Then plan.

Judge assesses the outcome. Cause explains the failure. Sub selects the recovery subtask, and Fine provides executable guidance.

Judge 判断结果，Cause 解释原因，Sub 选择恢复子任务，Fine 给出可执行的细粒度指导。

## 00:33 · One change. A learnable cause.

We branch successful trajectories and change one physical factor. Observable, recoverable failures provide aligned diagnosis and correction targets.

从成功轨迹创建分支，每次改变一个物理因素。可观察、可恢复的失败提供对齐的诊断与纠错目标。

## 00:42 · Learn evaluation before planning.

Supervised training first teaches judgment and cause. Planning then learns from verified evaluations, connecting failure diagnosis with recovery.

监督训练先学习结果判断与原因分析，再在已验证评估条件下学习规划，将失败诊断与恢复连接起来。

## 00:52 · Bridge training and deployment.

NEPO compares the same planning tokens under generated and verified evaluations. It preserves positive guidance and entropy gates uncertain negative signals.

NEPO 在模型生成和已验证两种评估上下文下比较相同规划 token，保留正向指导，并以熵门控衰减不确定的负向信号。

## 01:01 · Continuous simulation: grasp before placement.

This continuous simulator recording illustrates the interface with a GPT proxy and a state assisted controller. It is separate from the trained model evaluation.

连续仿真展示 GPT 代理与状态辅助控制器的交互，独立于训练模型评测。

## 01:11 · Continuous simulation: identify the target.

The instruction asks for the other bowl. The proxy revises the target and grasp. The full episode and official outcome are available in the gallery.

根据空间关系重新选择目标并调整抓取。完整回合及官方判定见案例库。

## 01:19 · Continuous simulation: open the drawer.

The drawer must open before insertion. This is a continuous segment from the same simulated episode, with no reset between corrective actions.

放置前先打开抽屉。片段来自同一连续仿真回合，纠错动作之间不重置环境。

## 01:28 · Continuous simulation: preserve failures.

In the kitchen task, grasping remains difficult. We retain incomplete episodes and report the simulator outcome, rather than treating attempted recovery as success.

厨房任务中仍有抓取困难。保留未完成回合，并按仿真官方条件报告结果。

## 01:38 · Seven factors. One correction interface.

The paper studies seven physical failure categories. The website also provides continuous demonstration episodes, with controller identity and official outcomes recorded separately.

论文研究七类物理失败。网页另提供连续演示回合，明确记录控制器身份与官方结果。

## 01:49 · Better recovery with fixed executors.

The paper reports a thirteen point nine percentage point gain with a fixed code backend, and six point one on unseen composite tasks with frozen pi zero point five.

论文报告：固定代码后端提升 13.9 个百分点；冻结 π₀.₅ 在未见组合任务上提升 6.1 个百分点。

## 01:59 · Feedback becomes a recovery plan.

Observe the outcome. Diagnose the cause. Restore the condition. Then continue. Explore the method and recovery cases on our project page.

观察结果，诊断原因，恢复条件，再继续执行。更多方法细节与纠错案例见项目主页。
