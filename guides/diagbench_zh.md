# DiagBench 使用说明

已将 ModelScope 发布包的测评流程接入 `ec_verl.diagbench`。单步 4,000 条、轨迹 240 条，共引用 8,289 个视频；完整评测展开为 11,612 次预测。

## 下载与校验

需要 Python 3.10+、curl、ffmpeg、ffprobe。

```bash
python -m pip install -r requirements-diagbench.txt
python -m ec_verl.diagbench.download --output data/diagbench
export DIAGBENCH_ROOT="$PWD/data/diagbench/EmbodiedDiag-Bench-small-20261024"
python -m ec_verl.diagbench.validate --root "$DIAGBENCH_ROOT" --hash --report runs/diagbench-validation.json
```

下载器固定发布版本，支持断点下载，校验压缩包 SHA-256 后解压。原始视频、标注、媒体修复记录和原始脚本保留在本地数据目录；大文件不加入 Git。

## 用 RynnBrain 运行

先按仓库安装指南准备 GPU 环境，并下载完整的 **RynnBrain-8B 原始权重**（`Alibaba-DAMO-Academy/RynnBrain-8B` / `DAMO_Academy/RynnBrain-8B`）。配置 RynnBrain 和独立视觉裁判：

```bash
export RYNN_MODEL=/models/RynnBrain-8B
export JUDGE_MODEL=/models/vision-judge
export EC_RUN="$PWD/runs/diagbench-rynnbrain"
bash scripts/diagbench_smoke.sh
```

脚本依次完成完整性校验、RynnBrain 推理、视觉判分和汇总，并保存模型身份、预测、判分、预算、校验和阶段日志。裁判若输出非法枚举，会按评判标准追加格式纠正请求；每次原始回答都会保留。

## 全量评测

以下命令假定 RynnBrain 与视觉裁判的兼容 API 已启动；密钥由 `BENCH_API_KEY` 环境变量提供：

```bash
python -m ec_verl.diagbench.evaluate collect --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18409/v1/chat/completions \
  --model rynnbrain --workers 1 --max-tokens 2048
python -m ec_verl.diagbench.evaluate judge --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full --api http://127.0.0.1:18410/v1/chat/completions \
  --model vision-judge --workers 1 --judge-max-tokens 512
python -m ec_verl.diagbench.evaluate aggregate --root "$DIAGBENCH_ROOT" \
  --output runs/diagbench-full
```

每个阶段都会记录等待、运行、完成或失败状态，以及预测、判分、错误和最终指标。中断后使用相同参数加 `--resume` 继续；改变预算或裁判时使用新的输出目录。

## 监控与协议

```bash
python -m tensorboard.main --logdir runs --host 127.0.0.1 --port 6006 --load_fast=false
```

打开 <http://127.0.0.1:6006> 查看数据、模型、推理、判分、汇总的状态和指标。Judge 判断成败；Cause 只统计参考答案失败的单步样本；Sub 判断动作类型；Fine 同时要求动作和目标正确。轨迹使用参考历史，只统计 planner 的动作类型，不能解释为闭环机器人执行成功率。

更多协议说明见[英文指南](diagbench.md)。
