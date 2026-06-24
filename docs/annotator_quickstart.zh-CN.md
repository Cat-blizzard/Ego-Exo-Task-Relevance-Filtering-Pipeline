# Ego-Exo v1 数据标注快速说明

这份说明给数据标注员使用。你不需要理解 FACT tokenizer 或训练代码，只需要看图并给每一行打标签。

## 你要打开什么

标注包通常长这样：

```text
review_pack/
  annotation_review.csv
  index.html
  review_images/
```

请打开：

```text
annotation_review.csv
index.html
```

`index.html` 用来看图；`annotation_review.csv` 用来填写标签。每一行对应一张 contact sheet 图片。

## 你只需要填写哪些列

只填写这些列：

```text
ego_hand_visibility
exo_body_visibility
object_interaction
phase_diversity
take_relevance
usable_for
notes
```

不要改这些列：

```text
review_id
review_image
review_image_path
contact_sheet_path
take_uid
parent_task_name
task_name
relevance_score
auto_bucket
```

## 数字列怎么填

`ego_hand_visibility`：

```text
0 = ego 里看不到手/腕/前臂
1 = 看到一点手/腕/前臂，但不稳定或不清楚
2 = 清楚看到手/腕/前臂或操作区域
```

`exo_body_visibility`：

```text
0 = exo 里看不到人或身体
1 = 看到部分身体
2 = 清楚看到身体动作
```

`object_interaction`：

```text
0 = 没有物体交互
1 = 有弱交互或不确定
2 = 明确有手-物体 / 身体-物体交互
```

`phase_diversity`：

```text
0 = 没有明显动作阶段变化
1 = 有一点阶段变化
2 = 明确有 approach / reach / contact / carry / place / release 等阶段变化
```

## 类别列怎么填

`take_relevance` 只填下面 6 个之一：

```text
A_interaction_rich
B_loco_body
C_active_view_only
D_scene_only
E_fine_dexterous
F_bad_or_unclear
```

`usable_for` 只填下面 4 个之一：

```text
tokenizer_main
loco_aux
discard
diagnostic_candidate
```

## 最快判断规则

看到明显手、物体、拿放、接触、搬运、修理、做饭、工具使用：

```text
take_relevance = A_interaction_rich
usable_for = tokenizer_main
```

看到走动、转身、靠近、站位、身体移动，但手物交互不明显：

```text
take_relevance = B_loco_body
usable_for = loco_aux
```

主要是看场景、球场、墙、地面、桌面角落、头动，没明确动作：

```text
take_relevance = C_active_view_only 或 D_scene_only
usable_for = discard
```

有很细的手部动作，但不是 coarse loco-manipulation 主目标：

```text
take_relevance = E_fine_dexterous
usable_for = diagnostic_candidate
```

看不清、遮挡严重、同步奇怪、判断不了：

```text
take_relevance = F_bad_or_unclear
usable_for = diagnostic_candidate 或 discard
```

## 示例

好样本：

```text
ego_hand_visibility = 2
exo_body_visibility = 2
object_interaction = 2
phase_diversity = 2
take_relevance = A_interaction_rich
usable_for = tokenizer_main
notes = clear hand-object interaction
```

身体运动辅助样本：

```text
ego_hand_visibility = 0
exo_body_visibility = 2
object_interaction = 0
phase_diversity = 1
take_relevance = B_loco_body
usable_for = loco_aux
notes = body movement only
```

丢弃样本：

```text
ego_hand_visibility = 0
exo_body_visibility = 0
object_interaction = 0
phase_diversity = 0
take_relevance = D_scene_only
usable_for = discard
notes = scene only
```

## 标注原则

- 不需要逐帧精修，按 contact sheet 做快速判断。
- 如果 10 秒内判断不了，优先标 `diagnostic_candidate` 或 `discard`。
- 不要为了保留数据而勉强标 `tokenizer_main`。
- `tokenizer_main` 应该尽量留给真正有交互、动作阶段、手物或身体物体关系的样本。
- `loco_aux` 是辅助数据，不要把纯场景或纯头动放进去。

## 完成后交付什么

交付填好的：

```text
annotation_review.csv
```

项目负责人会再做校验、训练 ranker、生成最终训练数据。
