# 实现与论文对应

## 两阶段 SFT

1. 固定公共任务、历史、观察与图片，训练 Judge/Cause。
2. 使用相同部署提示；将已验证 Judge/Cause 加入 assistant 前缀，只在 Sub/Fine 计算监督损失。

部署提示不含 target、rubric、隐藏模拟器状态。规划 SFT 的特权前缀和 NEPO teacher 前缀只用于训练。论文未给出两个 SFT 部分是否必须使用独立训练时段；这里采用顺序执行的可检查实现。

## NEPO

同一旧策略采样组内答案 y；在更新前计算：

- `p_t`：采样 token 在生成评估前缀下的概率。
- `q_t`：同一个 token 在已验证评估前缀下的概率。
- `h_t`：student 在该位置的完整词表熵，单位为 nat。
- `s_t = q_t − p_t`。
- `g_t = sigmoid((kappa − h_t) / beta)`。
- `delta_t = max(s_t, 0) + g_t * min(s_t, 0)`。
- 规划 token：`A_t = A_GRPO + coefficient * delta_t`；评估 token：`A_t = A_GRPO`。

old、teacher、entropy 与 advantage 都停止梯度。两种上下文保留同一图片与公开证据；teacher 替换评估前缀，复用采样规划 token ID，不能重新分词。每组至少两个答案；按同一输入分组。padding 不参与优势与 loss，真实 EOS 保留。检测不到完整字段边界的答案仅保留组相对奖励；若整个运行无规划 token 或 NEPO 信号为零，验证运行失败。

PPO loss 由上游 verl 原函数计算。每批只做一次更新，因此本默认配置初始 importance ratio 为 1；裁剪接口保留，用于后续加入多个 PPO epoch。没有额外 KL 正则。默认 κ=1、β=.5、λ=1、clip=.2 是明确的工程默认值。

## verl 连接范围

`DataProto` 承载 response_mask、old_log_probs、teacher_log_probs、old_entropy、planning_mask、token_level_rewards 与 uid。GRPO 与 PPO 都执行 vendored verl 的代码，并非本地重写。`embodied_nepo` 注册器符合 `(advantages, returns)` 张量接口，但原生 verl trainer 还需要增加 teacher forward 与这些额外字段，单独在 YAML 填 estimator 名称不能完成 NEPO。

`ray_train.py` 只为单卡训练提供 Ray 资源边界，不声称实现了 FSDP、vLLM rollout、多机或异步 rollout。需要扩展时，应在更新前冻结 rollout policy，并让同一 actor 对 teacher 前缀打分；不能用已更新参数或参考模型代替论文的同一策略。

## 复现边界

PDF 没有随附完整训练集、官方判分器、模型检查点与全部超参数。论文示例和合成语言夹具都标记为 smoke，不能进入 formal 模式。公开 EB-ALFRED 测试使用真实环境，但 Qwen 规划器替代了论文固定规划器，因此不是表格结果复现。
