# 数据格式

JSONL 示例（图片路径相对 JSONL 所在目录）：

```json
{"id":"episode-1-step-3","source_trajectory":"original-episode-1","domain":"operation","task":"Put the cup in the basket.","previous_subtask":"Pick up the cup.","observation":"The gripper is empty and the cup remains on the counter.","history":[{"action":"grasp cup","feedback":"No attachment visible."}],"images":["images/step3.png"],"target":{"Judge":"failure","Cause":"The grasp missed the cup.","Sub":"Grasp the cup again.","Fine":"Open the gripper; align; descend; close; verify attachment."},"rubric":{},"provenance":"user_supplied"}
```

`domain` 是 navigation 或 operation；Judge 是 success 或 failure。Cause/Sub/Fine 必须为非空字符串。评分规则见 reward.py，可按字段提供关键词 alternatives，默认使用规范化精确匹配。正式数据应由执行证据验证标注质量。

训练与评估先按 `source_trajectory` 划分，扰动分支保留原始轨迹 ID。重复 ID、同源轨迹泄漏与不存在的图片都会报错。图片路径导出后为绝对路径；迁移到另一机器时需要同步图片并重新导出。

`ec_verl.data parquet` 提供 verl 兼容记录导出；extra_info 的 verified_prefix 仅供训练 teacher 使用，不能拼接到部署输入。SFT 主入口直接读取 JSONL。
