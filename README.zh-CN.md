# Ego-Exo Task-Relevance Filtering Pipeline 中文说明

这个仓库用于构建 **适合 coarse loco-manipulation FACT tokenizer 训练的数据筛选管线**。

它的目标不是筛“画面好看”的视频，而是把泛 Ego-Exo4D 数据筛成对 FACT action token 有用的数据：

- ego 视角里有可预测的交互线索或主动运动线索；
- exo 视角里能补充身体 / 全局空间关系；
- 同一个 take 内有足够动作阶段变化；
- 尽量减少 scene shortcut、take shortcut、纯背景运动对 tokenizer 的污染。

## 当前能力边界

当前 v0 版本可以完成：

```text
已有 FACT NPZ / labels
    -> 生成 take contact sheet
    -> 提取 relevance proxy features
    -> 导出人工标注 CSV
    -> 训练 / 应用轻量 relevance ranker
    -> 生成 FACT-main / loco-aux / discard filtered split
    -> 做 take 内 transition selection
    -> 生成 filtered train_by_take.npz / heldout_by_take.npz
    -> 生成 same_take_negative_index.npz
    -> 生成 audit report / phase diagnostic candidates
```

它目前还不能独立完成：

```text
Ego-Exo4D 原始视频
    -> camera 选择
    -> 时间同步 / frame aligned 读取
    -> transition 采样
    -> resize
    -> 生成初始 FACT NPZ
```

也就是说，当前仓库负责 **初始 FACT NPZ 之后的数据筛选与重建**。  
从 Ego-Exo4D 原始视频到初始 FACT NPZ 的前处理阶段，暂时仍依赖 `fact-tokenizer` 侧已有脚本，后续可以迁移或封装到本仓库。

## 不要提交到 GitHub 的内容

不要提交：

```text
Ego-Exo4D 原始视频
大 NPZ 数据
contact sheet 图片
checkpoint
AWS key / 服务器密码 / 数据集凭证
```

这些大文件应该放在服务器，例如：

```text
/data_all/intern02/egoexo-task-filter/outputs/filtering_v0/
```

GitHub 只提交：

```text
代码
配置
schema
小型测试数据
人工标注 CSV
summary / audit report
artifact manifest
```

## 仓库结构

```text
configs/
  filter_policy_v0.yaml

docs/
  annotation_protocol.md
  filtering_v0_report_template.md

schemas/
  filtered_split.schema.json
  same_take_negative_index.schema.json
  take_relevance_scores.schema.json

tools/
  make_take_contact_sheets.py
  extract_relevance_features.py
  export_annotation_csv.py
  train_relevance_ranker.py
  apply_relevance_ranker.py
  build_filtered_split.py
  build_transition_selection.py
  build_filtered_npz.py
  build_same_take_negative_index.py
  audit_filtered_split.py
  build_phase_diagnostic_set.py

tests/
  test_pipeline_smoke.py
```

## 输入格式

当前工具默认输入已经是 FACT 风格 NPZ：

```text
train_by_take.npz:
  ego          # [N, 2, H, W, 3] 或兼容布局
  exo          # [N, 2, H, W, 3] 或兼容布局
  sample_id    # [N]
  take_uid     # [N]
  timestamp    # [N]

train_labels.jsonl / heldout_labels.jsonl:
  take_uid
  parent_task_name
  task_name
  take_name
  ...
```

## 最小运行流程

假设已有 split：

```bash
BASE=data/fact_egoexo_sxh_handoff/splits/diverse_500takes_t0p5_s1_48t_seed123_80_20
OUT=outputs/filtering_v0
```

### 1. 生成 take contact sheet

```bash
python tools/make_take_contact_sheets.py \
  --split $BASE/train_by_take.npz \
  --labels-jsonl $BASE/train_labels.jsonl \
  --out $OUT/contact_sheets_train \
  --num-frames 12
```

每个 take 会生成一张图，供人工快速判断这个 take 是否有交互 / loco / scene-only 问题。

### 2. 提取自动粗筛特征

```bash
python tools/extract_relevance_features.py \
  --split $BASE/train_by_take.npz \
  --split-name train \
  --labels-jsonl $BASE/train_labels.jsonl \
  --contact-sheet-manifest $OUT/contact_sheets_train/contact_sheet_manifest.csv \
  --out $OUT/take_relevance_scores_train.csv
```

当前 v0 使用的是便宜 proxy：

```text
metadata prior
ego motion score
exo body motion score
object motion proxy
temporal diversity score
scene-only proxy
```

注意：v0 还没有真正接入 hand detector、object detector 或 VLM。

### 3. 导出人工标注 CSV

```bash
python tools/export_annotation_csv.py \
  --scores $OUT/take_relevance_scores_train.csv \
  --sample-size 300 \
  --out $OUT/annotation_batch_001.csv
```

人工填写后保存为：

```text
outputs/filtering_v0/annotation_batch_001_labeled.csv
```

### 4. 训练轻量 relevance ranker

```bash
python tools/train_relevance_ranker.py \
  --features $OUT/take_relevance_scores_train.csv \
  --labels $OUT/annotation_batch_001_labeled.csv \
  --out $OUT/relevance_ranker.pkl
```

### 5. 应用 ranker

```bash
python tools/apply_relevance_ranker.py \
  --features $OUT/take_relevance_scores_train.csv \
  --ranker $OUT/relevance_ranker.pkl \
  --out $OUT/take_relevance_ranked_train.csv
```

实际使用时，需要把 train / heldout 的 ranked CSV 合并成：

```text
take_relevance_ranked_all.csv
```

### 6. 生成 filtered split

```bash
python tools/build_filtered_split.py \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --policy configs/filter_policy_v0.yaml \
  --out $OUT/filtered_split_v0.json
```

输出会分成：

```text
FACT-main
loco-aux
discard
```

### 7. 选择 take 内 transition

```bash
python tools/build_transition_selection.py \
  --npz $BASE/train_by_take.npz \
  --split-name train \
  --filtered-split $OUT/filtered_split_v0.json \
  --out $OUT/transition_selection_train.csv

python tools/build_transition_selection.py \
  --npz $BASE/heldout_by_take.npz \
  --split-name heldout \
  --filtered-split $OUT/filtered_split_v0.json \
  --out $OUT/transition_selection_heldout.csv
```

### 8. 生成 filtered NPZ

```bash
python tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_train.csv \
  --heldout-selection $OUT/transition_selection_heldout.csv \
  --out-dir $OUT/filtered_npz
```

### 9. 生成 same-take hard negative index

```bash
python tools/build_same_take_negative_index.py \
  --npz $OUT/filtered_npz/train_by_take.npz \
  --out $OUT/same_take_negative_index_train.npz
```

这个文件可以交给 `fact-tokenizer` 训练脚本，作为 v6e/v6f 的 same-take hard negative index。

## filtering_v1 当前推荐流程

`filtering_v1` 和 v0 最大区别是：**先人工校准，再训练 ranker，再生成 split**。不要拿 v0 的自动分数直接继续调阈值。

当前流程分成三个阶段。

### 阶段 1：导出人工标注表，然后暂停

服务器上使用：

```bash
cd /data_all/intern02/Ego-Exo-Task-Relevance-Filtering-Pipeline

PY=/home/intern02/miniconda3/envs/egoexo_fact/bin/python
V0=/data_all/intern02/egoexo-task-filter/outputs/filtering_v0_500takes_20260624
OUT=/data_all/intern02/egoexo-task-filter/outputs/filtering_v1_500takes_20260624
mkdir -p "$OUT"

$PY tools/export_annotation_csv.py \
  --scores $V0/take_relevance_scores_all.csv \
  --sample-size 500 \
  --strategy v1_full_if_small \
  --out $OUT/annotation_batch_v1_all.csv
```

这一步会导出当前 427 个 take。导出后先不要继续跑 ranker，也不要生成 split。下一步是人工看 contact sheet，并填写：

```text
take_relevance
ego_hand_visibility
exo_body_visibility
object_interaction
phase_diversity
usable_for
notes
```

人工填完后保存成：

```text
/data_all/intern02/egoexo-task-filter/outputs/filtering_v1_500takes_20260624/annotation_batch_v1_labeled.csv
```

### 阶段 2：标注完成后，校验并训练 ranker

只有当 `annotation_batch_v1_labeled.csv` 已经存在时，才运行下面命令：

```bash
$PY tools/validate_annotations.py \
  --annotations $OUT/annotation_batch_v1_labeled.csv

$PY tools/train_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --labels $OUT/annotation_batch_v1_labeled.csv \
  --label-column usable_for \
  --out $OUT/relevance_ranker_usable_for.pkl

$PY tools/apply_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --ranker $OUT/relevance_ranker_usable_for.pkl \
  --out $OUT/take_relevance_ranked_all.csv

$PY tools/build_filtered_split.py \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --policy configs/filter_policy_v1.yaml \
  --out $OUT/filtered_split_v1.json

$PY tools/summarize_annotation_calibration.py \
  --scores $V0/take_relevance_scores_all.csv \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --annotations $OUT/annotation_batch_v1_labeled.csv \
  --filtered-split $OUT/filtered_split_v1.json \
  --out $OUT/audit_report_v1.md
```

先看 `audit_report_v1.md`。如果 `fact_main` 里混入太多 scene-only / bad ego，或者 `discard` 误丢了很多 `tokenizer_main`，先修标注或 policy，不进入 FACT 训练。

### 阶段 3：报告通过后，生成 FACT 可用 NPZ

只用 `fact_main` 的第一版：

```bash
BASE=/data_all/intern02/fact-tokenizer/data/fact_egoexo_sxh_handoff/splits/diverse_500takes_t0p5_s1_48t_seed123_80_20

$PY tools/build_transition_selection.py \
  --npz $BASE/train_by_take.npz \
  --split-name train \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main \
  --out $OUT/transition_selection_fact_main_train.csv

$PY tools/build_transition_selection.py \
  --npz $BASE/heldout_by_take.npz \
  --split-name heldout \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main \
  --out $OUT/transition_selection_fact_main_heldout.csv

$PY tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main
```

`fact_main + capped loco_aux` 是第二个 ablation，不要一开始就用它替代主线：

```bash
$PY tools/build_transition_selection.py \
  --npz $BASE/train_by_take.npz \
  --split-name train \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main loco_aux \
  --bucket-num-transitions loco_aux=12 \
  --out $OUT/transition_selection_fact_main_plus_loco25_train.csv

$PY tools/build_transition_selection.py \
  --npz $BASE/heldout_by_take.npz \
  --split-name heldout \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main loco_aux \
  --bucket-num-transitions loco_aux=12 \
  --out $OUT/transition_selection_fact_main_plus_loco25_heldout.csv

$PY tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_plus_loco25_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_plus_loco25_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main_plus_loco25
```

### 当前状态

如果你是在当前服务器环境继续做，`annotation_batch_v1_all.csv` 已经可以直接生成或重新生成。现在真正需要人工完成的是：

```text
annotation_batch_v1_all.csv
    -> 人工填写
    -> annotation_batch_v1_labeled.csv
```

在这个文件完成之前，v1 后续命令都只是准备好，暂时不用跑。

### 可选：生成更适合人工看的 review pack

原始 contact sheet 文件名是 UUID，例如：

```text
4abc4d07-a180-4713-b507-69c2fe7f2db8.jpg
```

这对人工标注不友好。可以生成一份 review pack，把图片复制成顺序编号和任务名，例如：

```text
0001_heldout_Basketball_Basketball_Drills_Reverse_Layup_32d54e67.jpg
0002_heldout_Basketball_Basketball_Drills_Reverse_Layup_3fce7d86.jpg
```

如果已经把 CSV 和 contact sheets 下载到本地 `D:\egoexo_v1_annotation`，在本地 PowerShell 运行：

```powershell
$env:PYTHONPATH="D:\Ego-Exo-Task-Relevance-Filtering-Pipeline"

python D:\Ego-Exo-Task-Relevance-Filtering-Pipeline\tools\build_annotation_review_pack.py `
  --annotations D:\egoexo_v1_annotation\annotation_batch_v1_labeled.csv `
  --out-dir D:\egoexo_v1_annotation\review_pack `
  --path-prefix-from /data_all/intern02/egoexo-task-filter/outputs/filtering_v0_500takes_20260624 `
  --path-prefix-to D:/egoexo_v1_annotation `
  --copy-images
```

生成后给标注同学使用：

```text
D:\egoexo_v1_annotation\review_pack\annotation_review.csv
D:\egoexo_v1_annotation\review_pack\index.html
D:\egoexo_v1_annotation\review_pack\review_images\
```

标注时直接填 `annotation_review.csv` 里的空列即可。`review_id` 和 `review_image` 只是辅助列，不影响后续校验和 ranker 训练。

## 人工标注类别

`take_relevance`：

```text
A_interaction_rich
B_loco_body
C_active_view_only
D_scene_only
E_fine_dexterous
F_bad_or_unclear
```

含义：

```text
A_interaction_rich:
  ego 有手/物体/交互线索，exo 有身体/全局关系，存在 reach/contact/carry/place 等阶段。

B_loco_body:
  有明显走动、转身、站位、靠近、身体对齐等，但手物交互弱。

C_active_view_only:
  主要是 ego 转头、看场景、视角变化，动作阶段弱。

D_scene_only:
  只有场景、墙、地面、球场、桌面角落等，无明确动作/交互。

E_fine_dexterous:
  有很细的手部操作，但当前 coarse tokenizer 第一版不主攻。

F_bad_or_unclear:
  同步、遮挡、画质、语义都不可靠。
```

其他字段：

```text
ego_hand_visibility: 0 none / 1 partial / 2 clear
exo_body_visibility: 0 none / 1 partial / 2 clear
object_interaction: 0 none / 1 weak / 2 clear
phase_diversity: 0 none / 1 weak / 2 clear
usable_for: tokenizer_main / loco_aux / discard / diagnostic_candidate
```

## 与 fact-tokenizer 的分工

推荐分工：

```text
fact-tokenizer:
  原始 Ego-Exo4D -> 初始 FACT NPZ
  训练 v6b/v6e/v6f
  checkpoint sweep / probe / report

本仓库:
  初始 FACT NPZ -> task-relevant filtered NPZ
  人工标注校准
  filtered split
  transition selection
  same-take negative index
  audit report
```

后续如果希望数据负责人完全独立，本仓库还需要补：

```text
tools/build_egoexo_manifest.py
tools/extract_aligned_transitions.py
tools/build_fact_npz_from_egoexo.py
tools/split_npz_by_take.py
```

补完后才能从 Ego-Exo4D 原始视频一路生成 FACT 训练数据。

## 最重要的两个交付物

第一阶段最关键的是：

```text
filtered_npz/train_by_take.npz
same_take_negative_index_train.npz
```

前者解决“训练数据太杂”，后者解决“同一个 take 内缺少真正 hard negative”。

## 验证

运行：

```bash
python -m pytest
```

当前测试覆盖：

```text
feature extraction smoke
annotation CSV export
filtered split train/heldout 不串 take
same-take negative index 不跨 take，且时间间隔满足约束
```

## 当前 v0 的局限

当前 v0 是为了快速闭环，不是最终筛选器：

- hand visibility 还不是检测模型输出；
- object visibility 目前只是 motion/object proxy；
- scene-only score 仍是 heuristic；
- ranker 需要人工标注 CSV 校准后才有意义；
- 还不能直接从 Ego-Exo4D 原视频生成初始 FACT NPZ。

下一步建议先在当前 500-take split 上跑通完整闭环。如果 filtered subset 能明显改善 same-take delta、take leakage、phase purity，再扩展到更大规模 Ego-Exo4D。
