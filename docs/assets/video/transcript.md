# Embodied-Corrector · Video introduction

English narration and bilingual subtitles. Based on the supplied manuscript; no authors are listed.

Four case walkthroughs use selected paper observations. Their playback timing is illustrative, not original simulator timing. Figures 7–8 show paired executions; Figures 9–10 show observations from one continuous episode. Navigation, reachability and articulation animations are protocol illustrations. Quantitative results are paper-reported simulation results.

## 00:00:00 · The question

When physical execution fails, continuing the same plan can repeat the same mistake. Embodied Corrector learns to understand the cause and recover.

物理执行失败后，继续原计划可能重复同样的错误。Embodied-Corrector 学习理解原因并恢复执行。

## 00:00:09 · Motivation

A corrective brain needs physical causal understanding, awareness of its executor, and the ability to learn from interaction history.

纠错大脑需要理解物理因果、识别执行器能力，并利用交互历史调整决策。

## 00:00:16 · RynnBrain

We train RynnBrain-8B with evaluation-first supervised fine-tuning and NEPO. The resulting model is Embodied-Corrector.

我们以 RynnBrain-8B 为基础，通过评估优先的监督微调与 NEPO，训练得到 Embodied-Corrector。

## 00:00:25 · Structured correction

Judge assesses the outcome. Cause explains the failure. Sub selects the recovery subtask, and Fine provides executable guidance.

Judge 判断结果，Cause 解释原因，Sub 选择恢复子任务，Fine 给出可执行的细粒度指导。

## 00:00:34 · Controlled data

We branch successful trajectories and change one physical factor. Observable, recoverable failures provide aligned diagnosis and correction targets.

从成功轨迹创建分支，每次改变一个物理因素。可观察、可恢复的失败提供对齐的诊断与纠错目标。

## 00:00:43 · Evaluation-first SFT

Supervised training first teaches judgment and cause. Planning then learns from verified evaluations, connecting failure diagnosis with recovery.

监督训练先学习结果判断与原因分析，再在已验证评估条件下学习规划，将失败诊断与恢复连接起来。

## 00:00:52 · NEPO

NEPO compares the same planning tokens under generated and verified evaluations. It preserves positive guidance and entropy gates uncertain negative signals.

NEPO 在模型生成和已验证两种评估上下文下比较相同规划 token，保留正向指导，并以熵门控衰减不确定的负向信号。

## 00:01:02 · Case 01 · prerequisite

An empty gripper cannot place the carton. The corrector restores pickup, verifies attachment, and then resumes transport and placement.

空夹爪无法完成纸盒放置。纠错器恢复抓取步骤、验证物体附着，再继续搬运和放置。

## 00:01:10 · Case 02 · target

Plausible motions can still target the wrong object. Regrounding the bowls and the requested spatial relation restores the correct plan.

看似合理的动作也可能作用于错误对象。重新定位碗并核对目标空间关系，才能恢复正确计划。

## 00:01:18 · Case 03 · grasp pose

The avocado remains in the sink after repeated empty grasps. Observation conditioned alignment guides the frozen policy toward a stable grasp.

反复空抓后，牛油果仍留在水槽中。根据观察调整姿态，引导冻结策略形成稳定抓取。

## 00:01:27 · Case 04 · timing

Late closure leaves the onion behind. Coordinating approach and closure enables recovery while the low level policy remains frozen.

闭合过晚使洋葱仍留在水槽中。协调接近动作与闭合时机，在低层策略冻结的情况下实现恢复。

## 00:01:35 · Failure coverage

The intervention protocol also covers navigation, reachability, and articulation. Each recovery restores a physical condition needed for task progress.

干预协议还覆盖导航、可达性和关节开合。每次纠错都恢复任务继续推进所需的物理条件。

## 00:01:45 · Paper results

The paper reports a thirteen point nine percentage point gain with a fixed code backend, and six point one on unseen composite tasks with frozen pi zero point five.

论文报告：固定代码后端提升 13.9 个百分点；冻结 π₀.₅ 在未见组合任务上提升 6.1 个百分点。

## 00:01:55 · Takeaway

Observe the outcome. Diagnose the cause. Restore the condition. Then continue. Explore the method and recovery cases on our project page.

观察结果，诊断原因，恢复条件，再继续执行。更多方法细节与纠错案例见项目主页。

## Results context

- Fixed code backend: 55.0% → 68.9%, macro-average across ten conditions; base RynnBrain-8B corrective brain compared with RynnBrain-NEPO.
- Frozen π₀.₅: 1.2% → 7.3%, Composite-Unseen on RoboCasa365. Short atomic tasks can regress; this gain does not describe every task setting.
- NEPO: the same policy scores the same planning tokens under generated and verified evaluations; the probability-gap signal is combined with group-relative reward guidance.

Voice: macOS Samantha system voice. Diagrams and motion graphics created for this project; case imagery reproduced from the manuscript.
