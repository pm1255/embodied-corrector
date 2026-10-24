# 连续仿真案例与来源

> 当前主页已改为 [12 段成功纠错精选](selected_recoveries.md)。本文保留此前 50 段实验档案及其真实结果，不代表当前展示列表。


**主页已提供 20 个 LIBERO-PRO 回合和 30 个 RoboCasa365 回合，全部来自独立连续仿真录像，封面为对应视频第一帧。** 视频与动作日志可以用于展示执行过程和分析失败。

**用途限制：这些是演示，不是训练后 Embodied-Corrector 的成绩。** 其中 6 个为原有 GPT 代理交互案例，44 个为明确标注的脚本控制回合，均使用仿真状态定位。脚本的反馈记录不是模型生成的 Judge/Cause/Sub/Fine。未完成任务均如实保留；不同种子不当作不同任务。

[在线案例库](https://pm1255.github.io/embodied-corrector/#simulations) · [完整执行日志包](../docs/assets/simulations/execution-records.zip) · [视频与动作核验](../docs/assets/simulations/gallery-validation.json) · [原有 9 次交互尝试的历史记录](simulation_history_20261024.md)

## 展示范围

| 环境 | 展示回合 | GPT 交互 | 脚本控制 | 官方完成 | 官方未完成 |
| --- | ---: | ---: | ---: | ---: | ---: |
| LIBERO-PRO | 20 | 3 | 17 | 9 | 11 |
| RoboCasa365 | 30 | 3 | 27 | 0 | 30 |

以上是展示记录计数，不是抽样估计的基准成功率。原有 3 个未选入网页的调试尝试仍保存在历史记录及日志包中，共归档 53 个完成录制的回合。

新增 LIBERO-PRO 回合覆盖 6 个基础任务，使用官方 SwapPerturbator 改变目标与干扰物/设施位置；种子为 11、23、37，最后一个任务为 11、23。新增 RoboCasa365 回合覆盖 9 个官方任务，每个种子为 11、23、37。厨房风格为 1；BowlAndCup 使用带餐桌的布局 2，其他任务使用布局 1。初始化失败日志单独保留，不计入完成录像。PortionFruitBowl 在当前资产组合中反复无法初始化，最终使用官方 DessertAssembly 任务替换其三个回合。完整任务指令见每个视频的 JSON，不将局部动作完成误报为完整任务成功。

## 连续性与封面核验

所有运动均由 `env.step` 推进，回合内不通过 reset、对象位置赋值或瞬移制造结果。控制为 20 Hz，原始视频为 10 fps。新增 44 段直接封装完整原始视频，以 1× 播放；原有 6 段保持包含四字段面板的完整 2× 视频。介绍视频中的片段为实际连续录像的连续裁剪，以 1× 播放。

逐个检查了 50 段视频解码、动作步数连续性、事件起止衔接、官方结果与日志一致性、不同录像 SHA-256 和首帧封面像素一致性。动作日志与视频帧数对应；没有使用少量论文图片模拟机械臂运动。

## 逐回合目录

| 回合 | 任务 | 种子 | 执行方式 | 控制步数 | 官方结果 |
| --- | --- | ---: | --- | ---: | --- |
| [libero-articulation-r1](../docs/assets/simulations/libero-articulation-r1.json) | 先打开，再放入 | 7 | GPT 代理交互 | 1422 | 完成 |
| [libero-relational-r2](../docs/assets/simulations/libero-relational-r2.json) | 读懂“不在两者之间” | 7 | GPT 代理交互 | 746 | 完成 |
| [libero-multiobject-r2](../docs/assets/simulations/libero-multiobject-r2.json) | 两个目标，一个都不能少 | 7 | GPT 代理交互 | 1349 | 完成 |
| [robocasa-salsa](../docs/assets/simulations/robocasa-salsa.json) | 四种食材，逐一完成 | 7 | GPT 代理交互 | 2528 | 未完成 |
| [robocasa-clearing](../docs/assets/simulations/robocasa-clearing.json) | 先清空，再布置 | 7 | GPT 代理交互 | 2113 | 未完成 |
| [robocasa-sorting-r2](../docs/assets/simulations/robocasa-sorting-r2.json) | 从大到小，稳定堆叠 | 7 | GPT 代理交互 | 448 | 未完成 |
| [libero-gallery-01-s11](../docs/assets/simulations/libero-gallery-01-s11.json) | 碗放入盘中 | 11 | 脚本控制 | 394 | 完成 |
| [libero-gallery-01-s23](../docs/assets/simulations/libero-gallery-01-s23.json) | 碗放入盘中 | 23 | 脚本控制 | 370 | 完成 |
| [libero-gallery-01-s37](../docs/assets/simulations/libero-gallery-01-s37.json) | 碗放入盘中 | 37 | 脚本控制 | 391 | 完成 |
| [libero-gallery-02-s11](../docs/assets/simulations/libero-gallery-02-s11.json) | 碗移到炉台 | 11 | 脚本控制 | 449 | 未完成 |
| [libero-gallery-02-s23](../docs/assets/simulations/libero-gallery-02-s23.json) | 碗移到炉台 | 23 | 脚本控制 | 374 | 未完成 |
| [libero-gallery-02-s37](../docs/assets/simulations/libero-gallery-02-s37.json) | 碗移到炉台 | 37 | 脚本控制 | 414 | 未完成 |
| [libero-gallery-03-s11](../docs/assets/simulations/libero-gallery-03-s11.json) | 奶酪放入碗中 | 11 | 脚本控制 | 518 | 完成 |
| [libero-gallery-03-s23](../docs/assets/simulations/libero-gallery-03-s23.json) | 奶酪放入碗中 | 23 | 脚本控制 | 449 | 完成 |
| [libero-gallery-03-s37](../docs/assets/simulations/libero-gallery-03-s37.json) | 奶酪放入碗中 | 37 | 脚本控制 | 491 | 完成 |
| [libero-gallery-04-s11](../docs/assets/simulations/libero-gallery-04-s11.json) | 酒瓶移到置物架 | 11 | 脚本控制 | 486 | 未完成 |
| [libero-gallery-04-s23](../docs/assets/simulations/libero-gallery-04-s23.json) | 酒瓶移到置物架 | 23 | 脚本控制 | 453 | 未完成 |
| [libero-gallery-04-s37](../docs/assets/simulations/libero-gallery-04-s37.json) | 酒瓶移到置物架 | 37 | 脚本控制 | 494 | 未完成 |
| [libero-gallery-05-s11](../docs/assets/simulations/libero-gallery-05-s11.json) | 酒瓶移到柜顶 | 11 | 脚本控制 | 501 | 未完成 |
| [libero-gallery-05-s23](../docs/assets/simulations/libero-gallery-05-s23.json) | 酒瓶移到柜顶 | 23 | 脚本控制 | 480 | 未完成 |
| [libero-gallery-05-s37](../docs/assets/simulations/libero-gallery-05-s37.json) | 酒瓶移到柜顶 | 37 | 脚本控制 | 512 | 未完成 |
| [libero-gallery-06-s11](../docs/assets/simulations/libero-gallery-06-s11.json) | 碗移到柜顶 | 11 | 脚本控制 | 528 | 未完成 |
| [libero-gallery-06-s23](../docs/assets/simulations/libero-gallery-06-s23.json) | 碗移到柜顶 | 23 | 脚本控制 | 499 | 未完成 |
| [robocasa-gallery-01-s11](../docs/assets/simulations/robocasa-gallery-01-s11.json) | 蔬菜分盘摆放 | 11 | 脚本控制 | 1142 | 未完成 |
| [robocasa-gallery-01-s23](../docs/assets/simulations/robocasa-gallery-01-s23.json) | 蔬菜分盘摆放 | 23 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-01-s37](../docs/assets/simulations/robocasa-gallery-01-s37.json) | 蔬菜分盘摆放 | 37 | 脚本控制 | 983 | 未完成 |
| [robocasa-gallery-02-s11](../docs/assets/simulations/robocasa-gallery-02-s11.json) | 水槽蔬菜移到砧板 | 11 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-02-s23](../docs/assets/simulations/robocasa-gallery-02-s23.json) | 水槽蔬菜移到砧板 | 23 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-02-s37](../docs/assets/simulations/robocasa-gallery-02-s37.json) | 水槽蔬菜移到砧板 | 37 | 脚本控制 | 1256 | 未完成 |
| [robocasa-gallery-03-s11](../docs/assets/simulations/robocasa-gallery-03-s11.json) | 多食材移到砧板 | 11 | 脚本控制 | 1461 | 未完成 |
| [robocasa-gallery-03-s23](../docs/assets/simulations/robocasa-gallery-03-s23.json) | 多食材移到砧板 | 23 | 脚本控制 | 1984 | 未完成 |
| [robocasa-gallery-03-s37](../docs/assets/simulations/robocasa-gallery-03-s37.json) | 多食材移到砧板 | 37 | 脚本控制 | 1984 | 未完成 |
| [robocasa-gallery-04-s11](../docs/assets/simulations/robocasa-gallery-04-s11.json) | 清理并布置砧板 | 11 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-04-s23](../docs/assets/simulations/robocasa-gallery-04-s23.json) | 清理并布置砧板 | 23 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-04-s37](../docs/assets/simulations/robocasa-gallery-04-s37.json) | 清理并布置砧板 | 37 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-05-s11](../docs/assets/simulations/robocasa-gallery-05-s11.json) | 容器按大小堆叠 | 11 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-05-s23](../docs/assets/simulations/robocasa-gallery-05-s23.json) | 容器按大小堆叠 | 23 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-05-s37](../docs/assets/simulations/robocasa-gallery-05-s37.json) | 容器按大小堆叠 | 37 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-06-s11](../docs/assets/simulations/robocasa-gallery-06-s11.json) | 杯子放入碗中 | 11 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-06-s23](../docs/assets/simulations/robocasa-gallery-06-s23.json) | 杯子放入碗中 | 23 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-06-s37](../docs/assets/simulations/robocasa-gallery-06-s37.json) | 杯子放入碗中 | 37 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-07-s11](../docs/assets/simulations/robocasa-gallery-07-s11.json) | 甜点与容器摆上托盘 | 11 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-07-s23](../docs/assets/simulations/robocasa-gallery-07-s23.json) | 甜点与容器摆上托盘 | 23 | 脚本控制 | 1231 | 未完成 |
| [robocasa-gallery-07-s37](../docs/assets/simulations/robocasa-gallery-07-s37.json) | 甜点与容器摆上托盘 | 37 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-08-s11](../docs/assets/simulations/robocasa-gallery-08-s11.json) | 肉类移入容器 | 11 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-08-s23](../docs/assets/simulations/robocasa-gallery-08-s23.json) | 肉类移入容器 | 23 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-08-s37](../docs/assets/simulations/robocasa-gallery-08-s37.json) | 肉类移入容器 | 37 | 脚本控制 | 688 | 未完成 |
| [robocasa-gallery-09-s11](../docs/assets/simulations/robocasa-gallery-09-s11.json) | 冰箱水果移到砧板 | 11 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-09-s23](../docs/assets/simulations/robocasa-gallery-09-s23.json) | 冰箱水果移到砧板 | 23 | 脚本控制 | 1336 | 未完成 |
| [robocasa-gallery-09-s37](../docs/assets/simulations/robocasa-gallery-09-s37.json) | 冰箱水果移到砧板 | 37 | 脚本控制 | 1336 | 未完成 |

## 复现新增脚本回合

先按原有仿真安装说明准备 LIBERO-PRO / RoboCasa365、资产及各自虚拟环境，在仓库根目录运行：

```bash
.venv-libero/bin/python scripts/simulations/prepare_gallery.py
.venv-libero/bin/python scripts/simulations/run_gallery.py
```

控制脚本拒绝覆盖已有回合；默认四个 CPU 进程，每个回合最多 2,600 个物理步骤并有独立超时。失败后的抓取调整来自确定性反馈规则，未调用学习模型。TensorBoard 日志写入 `runs/gallery-overview/tensorboard`，每个回合同时保存独立日志。
