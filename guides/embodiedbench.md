# 公开 EmbodiedBench / EB-ALFRED

上游代码固定为 `9be4e980e9cd6bcb38373cd4aab7c32724bdd401`（master，2026-10-23 获取）。任务仓库固定为 `af55cc721725ed058830fd7a8aee66c1f69efbaa`。较新的上游已经修正部分 find 导航与指令问题，论文没有指明使用哪个提交；版本差异必须记录。

## 环境

官方推荐安装流程见上游 README；`scripts/setup_embodiedbench.sh` 固定上述版本。AI2-THOR 2.1.0 使用 201909061227 Linux 程序，其 SHA256 为：

```
cc61de810ddb8d681e9f6a7e342dd2d2c8454db413dd681de6bc85d2b2f70459
```

官方程序下载地址：[AI2-THOR Linux build](https://s3-us-west-2.amazonaws.com/ai2-thor/builds/thor-201909061227-Linux64.zip)。解压并确保可执行权限后，可通过 `--thor-executable /path/to/thor-201909061227-Linux64` 指定，避免运行时再次下载。

需要 X11/OpenGL 显示服务。官方 `startx.py` 使用 NVIDIA Xorg；已具备 Mesa 的系统也可尝试 `Xvfb :1 -screen 0 1024x768x24 +extension GLX`。这是真实 Unity 渲染，运行是否可行需按机器验证。上游绘图依赖 `/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf`；缺少字体时应安装 Ubuntu 字体，不能把字体错误误判为模型错误。

## 推理与评估

`/respond` 保持官方 `CustomModel.respond(prompt, obs_path)` 的 multipart 接口；`/correct` 另接收仅含 task、previous_subtask、history、observation 的 JSON 文本和当前图片。

基本回路：

1. 环境 reset，取得真实任务指令、图片与可用动作。
2. 基础 Qwen 根据公开证据输出 JSON action_id。
3. EBAlfEnv 执行动作，返回下一张图像与公开反馈。
4. 训练后的 corrector 输出 Judge/Cause/Sub/Fine。
5. 下一步规划读取前次纠错，直到 done 或步数限制。

没有把 task_success、object_states 或内部 simulator metadata 传给模型。只在结果统计中读取 task_success。每个 episode 清空历史和纠错，不跨任务读取记忆。

默认 30 次决策，环境也可能提前结束。结果同时记录环境 done、adapter 步数上限、实际执行动作数和成功率，不能把脚本完成等同于任务成功。输出目录中含 `episode-*/step-*.png`、`trace.json`、`result.json`、`metrics.json` 和 TensorBoard。

测试可以只下载 base 第 0 个任务的注释文件：

```
pick_clean_then_place_in_recep-Ladle-None-DiningTable-4/trial_T20190909_164840_568811/pp/ann_2.json
```

放入官方仓库的 `embodiedbench/envs/eb_alfred/data/json_2.1.0/`。仅此文件时只能运行 `--episodes 1 --subset base`；不能报告完整 benchmark 成绩。

## 本次 Linux 运行的兼容设置

实际环境为 Python 3.12、AI2-THOR 2.1.0。Werkzeug 3.1 会使此旧版 Unity 通信中断；验证使用 Flask 2.0.3 / Werkzeug 2.0.3。容器默认加载 NVIDIA EGL 时 Xvfb 崩溃，已通过仅为本进程选择 Mesa 解决：

```bash
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json
export __GLX_VENDOR_LIBRARY_NAME=mesa
export LIBGL_ALWAYS_SOFTWARE=1
```

这些设置仅影响图像渲染；Qwen 仍在 CUDA GPU 上推理。`validate_embodiedbench.sh` 已包含这些设置，并在退出时清理自己创建的显示与推理进程。上游环境的物理逻辑、任务判断和动作实现没有修改。

纠错服务还接受模型生成的等价四字段 JSON，并转换成统一的逐行格式。缺失、重复或多余字段不会被悄悄补齐。原始响应存入 `correction_raw`，`valid_structured_corrections` 单独统计格式有效次数；格式有效不表示诊断正确。纠错器的历史只包含实际动作与公开反馈，避免把先前模型的推测当成执行证据。训练仍使用严格逐行格式，以保持 NEPO token 边界一致。
