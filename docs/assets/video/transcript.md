# Embodied-Corrector · Video introduction

English narration and captions. Robot motion is decoded from continuous simulator recordings at 1× speed. The demonstrations use a GPT proxy and simulator-state-assisted control and are separate from the trained-model evaluation.

## 00:00:00 · Recover, don’t just continue.

When physical execution fails, continuing the same plan can repeat the same mistake. Embodied Corrector learns to understand the cause and recover.

## 00:00:08 · Understand why. Decide how.

A corrective brain needs physical causal understanding, awareness of its executor, and the ability to learn from interaction history.

## 00:00:16 · Built on RynnBrain-8B.

We train RynnBrain-8B with evaluation-first supervised fine-tuning and NEPO. The resulting model is Embodied-Corrector.

## 00:00:24 · Assess first. Then plan.

Judge assesses the outcome. Cause explains the failure. Sub selects the recovery subtask, and Fine provides executable guidance.

## 00:00:33 · One change. A learnable cause.

We branch successful trajectories and change one physical factor. Observable, recoverable failures provide aligned diagnosis and correction targets.

## 00:00:42 · Learn evaluation before planning.

Supervised training first teaches judgment and cause. Planning then learns from verified evaluations, connecting failure diagnosis with recovery.

## 00:00:52 · Bridge training and deployment.

NEPO compares the same planning tokens under generated and verified evaluations. It preserves positive guidance and entropy gates uncertain negative signals.

## 00:01:01 · Continuous simulation: grasp before placement.

This continuous simulator recording illustrates the interface with a GPT proxy and a state assisted controller. It is separate from the trained model evaluation.

## 00:01:11 · Continuous simulation: identify the target.

The instruction asks for the other bowl. The proxy revises the target and grasp. The full episode and official outcome are available in the gallery.

## 00:01:19 · Continuous simulation: open the drawer.

The drawer must open before insertion. This is a continuous segment from the same simulated episode, with no reset between corrective actions.

## 00:01:28 · Continuous simulation: preserve failures.

In the kitchen task, grasping remains difficult. We retain incomplete episodes and report the simulator outcome, rather than treating attempted recovery as success.

## 00:01:38 · Seven factors. One correction interface.

The paper studies seven physical failure categories. The website also provides continuous demonstration episodes, with controller identity and official outcomes recorded separately.

## 00:01:49 · Better recovery with fixed executors.

The paper reports a thirteen point nine percentage point gain with a fixed code backend, and six point one on unseen composite tasks with frozen pi zero point five.

## 00:01:59 · Feedback becomes a recovery plan.

Observe the outcome. Diagnose the cause. Restore the condition. Then continue. Explore the method and recovery cases on our project page.
