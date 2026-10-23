# RoboCasa365 / LIBERO-PRO 连续仿真案例

两套仿真环境均已实际执行。2026-10-24 共完成 **9 次独立尝试，3 次官方任务成功、6 次未完成**；主页新增 6 类完整连续视频。LIBERO-PRO 的三个目标任务均有成功尝试，RoboCasa365 的三个组合任务尚未完成。RoboCasa 的执行可达性、抓取稳定性仍限制使用，当前适合作为局部恢复与失败分析案例；后续应先改善执行器，再开展固定协议评估。

本组经授权用 **GPT 代理模拟 RynnBrain 的 Judge → Cause → Sub → Fine 输出格式**。实际执行器为使用仿真对象位置的解析 OSC 控制器，交互调试也参考了状态诊断。它不是训练后的 RynnBrain，不是冻结 π₀.₅，也不复现论文表格。以下数字是调试记录的计数，不是基准成功率。

[观看六类完整案例](https://pm1255.github.io/embodied-corrector/#simulations) · [六案例选段视频](../docs/assets/simulations/highlights.mp4) · [全部动作与原始四字段记录](../docs/assets/simulations/execution-records.zip) · [机器可读汇总](../docs/assets/simulations/attempts.json)

## 每次尝试

| 回合 ID | 困难因素 / 任务 | 物理控制步数 | 官方最终判定 | 观察与恢复结果 |
| --- | --- | ---: | --- | --- |
| libero-articulation-r1 | TaskPerturbator：抽屉内目标替换为奶油奶酪；开口不足 | 1422 | 完成 | 从约 3.8 cm 继续拉开到约 16 cm；初次空抓后转动夹爪，放入顶层抽屉 |
| libero-relational | TaskPerturbator：between → not between | 890 | 未完成 | 选对目标后停在盘缘；后续尝试推动了盘子，未满足目标中心条件 |
| libero-relational-r2 | 同一关系取反任务，独立重试 | 746 | 完成 | 改抓碗沿，补偿物体与夹爪中心偏移后放到盘上 |
| libero-multiobject-r1 | SwapPerturbator：目标与干扰物换位；双目标入篮 | 1407 | 未完成 | 黄油入篮；奶油奶酪运输掉落，未能稳定重新抓起 |
| libero-multiobject-r2 | 同一双目标任务，独立重试 | 1349 | 完成 | 两个目标分别使用合适的夹爪朝向与高度，均进入篮子 |
| robocasa-salsa | ColorfulSalsa：四种食材上砧板 | 2528 | 未完成 | 牛油果局部恢复成功；番茄运输不稳定，其余条件未全部满足 |
| robocasa-clearing | ClearCuttingBoard：移走非蔬菜，再放入两种蔬菜 | 2113 | 未完成 | 倾斜接近曾带起肉块，放置后仍在砧板前缘；蔬菜未全部上板 |
| robocasa-sorting | SizeSorting：按尺寸堆叠杯子 | 816 | 未完成 | 小杯抓取受到固定基座可达范围与台沿限制 |
| robocasa-sorting-r2 | 同一堆叠任务，加入基座移动的独立重试 | 448 | 未完成 | 期望平移 32 cm，实际位移约 2.5 cm，未达到目标，也未完成抓取 |

零步初始化错误和环境探测不计入这 9 次尝试。LIBERO-PRO 共 5 次、成功 3 次；RoboCasa365 共 4 次、成功 0 次。案例经过选择，执行器在调试过程中修改过速度、夹爪朝向、放置补偿和移动接口，因此不能据此比较算法优劣。`-r1`、`-r2` 是独立回合，不是同一轨迹的续段。

## 输出与物理证据

- 每次纠错先读取当前执行结果，再由 GPT 会话写入四字段及动作命令，随后执行；记录没有事后改写为成功叙事。GPT 的局部判断可能有误，最终结果以环境 `_check_success()` 为准。
- `Judge` 可能描述当前子步骤，不能等同于完整任务成功；`Cause` 定位原因，`Sub` 指定恢复子任务，`Fine` 给出执行与验证步骤。
- 夹爪、物体和抽屉的运动均由 `env.step` 推进；回合内不通过对象位置赋值、瞬移或 reset 制造恢复。初始受控失败与纠错段保持同一连续状态。
- 首段预先指定的受控扰动没有纠错大脑输出，视频明确标为“尚未调用纠错大脑”。完整视频不省略中间物理步骤，原始录像为 10 fps，控制为 20 Hz，展示以 2× 播放；六案例合辑明确标为选段。
- 四字段在其动作区间展示；官方最终结果在片尾展示，避免提前向观众显示尚未发生的结果。原文、每步动作、环境反馈与状态诊断均保留在记录包中。
- 没有运行训练后的 RynnBrain 或冻结 VLA，也没有执行全任务集、多随机种子或统计显著性评估。RoboCasa 画面存在机械臂遮挡，视频保留原始机位；未使用未验证的换视角重放。

## 环境与来源

本次在 Linux 服务器、无 GPU 条件下使用 MuJoCo + Mesa EGL 实际渲染和执行。任务环境 seed 为 7；RoboCasa 使用 layout 1、style 1、目标对象 split，`objaverse` / `lightwheel` 对象库。LIBERO 扰动配置与 BDDL 保存在 [任务目录](../scripts/simulations/tasks/)；双目标位置交换扰动 seed 为 17，任务替换 seed 见 [清单](../scripts/simulations/task_manifest.json)。

| 项目 | 固定版本 |
| --- | --- |
| [RoboCasa365](https://github.com/robocasa/robocasa) | `2ce1aecdd76e29b52d32fdb160436c5a3e230b07` |
| [robosuite（RoboCasa 环境）](https://github.com/ARISE-Initiative/robosuite) | `5ce6643f3092639d08f7b0f90ed1c6a84f50552c` |
| [LIBERO-PRO](https://github.com/Zxy-MLlab/LIBERO-PRO) | `eafdb809426b13153aa1e4c42d6601844217dfec` |
| LIBERO Python 环境 | robosuite 1.4.1 / MuJoCo 3.2.3 / NumPy 1.x |
| RoboCasa Python 环境 | MuJoCo 3.3.1 / NumPy 2.2.5 / SciPy 1.15.3 |

完整依赖快照见 [LIBERO](../scripts/simulations/requirements-libero-resolved.txt) / [RoboCasa](../scripts/simulations/requirements-robocasa-resolved.txt)。源码与第三方资产遵循各自许可，不在本仓库重新打包。

RoboCasa 资产：`textures`、`fixtures_lightwheel`、`objects_lightwheel`、`objaverse`。官方 Box 域名不可达时，本次采用 Hugging Face 数据集镜像，逐文件核对 SHA-256 后解压。来源和哈希见 [资产清单](../scripts/simulations/assets.json)。本任务没有使用 `aigen_objs`。

## 启动新的交互回合

以下脚本整理自本次运行环境。两个后端的实际回合已执行；新机器的安装仍取决于系统 EGL 库、网络和资产可用性。安装脚本不会把已有 vendor 的未提交修改覆盖掉。

```bash
bash scripts/simulations/setup.sh
# RoboCasa 另需按其官方说明下载上述资产到 vendor/robocasa/robocasa/models/assets。

# 一个终端持续运行环境；每次独立尝试使用新目录。
bash scripts/simulations/start.sh libero_pro \
  scripts/simulations/tasks/libero-articulation.bddl \
  runs/simulations/drawer-new --horizon 3000

# RoboCasa 示例（单独终端）
bash scripts/simulations/start.sh robocasa365 \
  ColorfulSalsa runs/simulations/salsa-new --horizon 6000
```

环境会保存 `frames/initial.png`，并在 `status.json` 标记 `waiting_for_gpt`。这不是已经连接 GPT API 的自动评估程序：本次由当前 GPT 会话读取图像、反馈与诊断，逐次生成命令。新运行同样需要外部模型或操作者提供下一条命令，等待超过 30 分钟会终止。

先查看当前画面，再填写 `next_command.json`。例如抓取命令的结构如下；四字段必须来自当前回合观察，不能直接当作所有状态通用的正确答案：

```json
{
  "brain": {
    "Judge": "failure",
    "Cause": "填写当前观察到的失败原因",
    "Sub": "填写下一项恢复子任务",
    "Fine": "填写执行细节和验证条件"
  },
  "action": "pick",
  "object": "cream_cheese_1",
  "yaw_degrees": 90,
  "offset": [0, 0, 0]
}
```

```bash
.venv-libero/bin/python scripts/simulations/submit_command.py \
  --run runs/simulations/drawer-new --command next_command.json
```

提交器先写临时文件再原子改名，避免环境读取半份 JSON。执行后查看 `frames/NNN-after.png` 和 `events.json`，再决定下一步；以 `action: "finish"` 和准确的最终四字段结束回合，落盘 `result.json`、`actions.json` 和 `raw.mp4`。动作接口还包括 `place`、`move`、`gripper`、`pull_drawer`、`wait`；`base_shift` 仅适用于 RoboCasa，当前案例未验证其能达到期望位移。

发布的执行器包含最新移动接口；早期失败尝试使用了更早的执行器参数。完整历史动作已保留，不能只用最新高层控制器重放旧命令就宣称逐帧复现。

## TensorBoard

所有新回合自动写入独立 TensorBoard 日志，包括实际物理步数、四字段记录数、官方判定和结束状态。汇总读取器独立读取日志，不修改仿真计算。

```bash
.venv-libero/bin/python scripts/simulations/aggregate_monitor.py --logdir runs/simulations
# 另一个终端
.venv-libero/bin/python -m tensorboard.main \
  --logdir runs/simulations --port 16027 --host 127.0.0.1 --load_fast=false
```

打开 `http://127.0.0.1:16027/#scalars`。`overview` 分别显示两个后端完成数、成功数与物理步数；单回合显示命令、脑输出和官方结果。`evaluation/progress` 在执行期间表示物理步数 / 预算，结束时为 1；不等于任务成功率。本组没有训练阶段，所以不生成训练 loss。

## 记录包结构

`execution-records.zip` 包含全部 9 次尝试的：

- `manifest.json`：任务、seed、模型与执行器身份、相机、控制频率。
- `commands/`：执行前写入的原始四字段和动作。
- `events.json`：命令边界、反馈、执行后的官方判定和明确标记的仿真状态诊断。
- `actions.json`：每个物理步的动作、reward 和 done。
- `result.json`：最终判定、步数、结束原因。
- `sources/`：任务 BDDL、扰动与固定源码版本。

网页的单案例 JSON 为阅读方便省略了状态诊断，完整值仍在记录包内。原始视频保留于实验输出，SHA-256 列在 `attempts.json`；网页提供经过统一版式制作的六类完整连续视频。

## 文件核对

已核对 11,719 个连续物理控制步、全部 9 次尝试的命令与四字段一致性，以及记录包与原文件一致性。6 段完整视频和 1 段合辑均完整解码通过。[程序核对报告](../docs/assets/simulations/validation.json)。
