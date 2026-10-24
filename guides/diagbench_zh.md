# DiagBench 使用说明

已将 ModelScope 发布包的测评流程接入 `ec_verl.diagbench`。单步 4,000 条、
轨迹 240 条，共引用 8,289 个视频；全量展开为 11,612 次预测。
默认快速试跑覆盖 12 个分层单步样本和 16 个轨迹轮次，共 28 次预测。

## 下载与校验

需要 Python 3.10+、curl、ffmpeg、ffprobe。

```bash
python -m pip install -r requirements-diagbench.txt
python -m ec_verl.diagbench.download --output data/diagbench
export DIAGBENCH_ROOT="$PWD/data/diagbench/EmbodiedDiag-Bench-small-20261024"
python -m ec_verl.diagbench.validate --root "$DIAGBENCH_ROOT" --hash --report runs/diagbench-validation.json
```

下载器固定发布版本，支持断点下载，校验压缩包 SHA-256 后解压。
原始视频、标注、媒体修复记录和原始脚本都保留在本地数据目录；大文件不加入 Git。

## 用 RynnBrain 试跑

先按仓库安装指南准备 GPU 环境，并下载完整的 **RynnBrain-8B 原始权重**
（`Alibaba-DAMO-Academy/RynnBrain-8B` / `DAMO_Academy/RynnBrain-8B`）。
选择独立的视觉裁判，设置：

```bash
export RYNN_MODEL=/models/RynnBrain-8B
export JUDGE_MODEL=/models/Qwen3-VL-32B-Instruct
export EC_RUN="$PWD/runs/diagbench-rynnbrain-smoke"
bash scripts/diagbench_smoke.sh
```

脚本依次进行完整性校验、RynnBrain 推理、释放模型、加载视觉裁判、判分和汇总，
只需同时运行一个模型。默认生成预算 512 tokens；截断回答保留并明确标记。
裁判若输出非法枚举，会在相同评判标准下最多追加两次格式纠正请求；
保留每次原始回答，无法纠正则拒绝汇总，不把解释文本猜成分数。
已有结果不会被直接覆盖；续跑核对数据、模型、接口、预算和预测文件。

如果只为验证连通性使用较小的 Qwen 视觉裁判，应明确记录具体型号。
此类分数不能与论文、发布包内 Qwen3.8-27B 裁判结果或完整基准成绩比较。
本次试跑不使用评测样本训练模型。

## 监控与结果

```bash
python -m tensorboard.main --logdir runs --host 127.0.0.1 --port 6006 --load_fast=false
```

打开 <http://127.0.0.1:6006> 查看数据、模型、推理、判分、汇总的等待和完成状态，
以及完成率、错误数和最终指标。每次调用评估入口都会自动记录。
原始回答见 `predictions.jsonl`，判分见 `judged.jsonl`，汇总见 `summary.json`。

保留官方抽帧、提示词和统计口径：Judge 判断成败；Cause 只统计参考答案失败的
单步样本；Sub 判断动作类型；Fine 同时要求动作和目标正确。轨迹使用参考历史，
只统计 planner 的动作类型，不能解释为闭环机器人执行成功率。
发布版恢复了 523 段视频并修正轨迹角色识别，不能直接当作历史论文版本。

完整评测和已有 API 服务的分阶段命令见 [英文详细指南](diagbench.md)。
