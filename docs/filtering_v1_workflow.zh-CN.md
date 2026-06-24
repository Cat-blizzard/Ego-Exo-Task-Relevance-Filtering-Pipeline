# filtering_v1 人工校准流程

`filtering_v1` 的目标是把 `filtering_v0` 的自动 proxy 粗筛，升级成经过人工校准的 task-relevant split。第一版仍然从 FACT 已经准备好的 NPZ 出发，不直接处理 Ego-Exo4D 原始视频。

当前最重要的暂停点：

```text
先生成 annotation_batch_v1_all.csv
然后人工填写并另存为 annotation_batch_v1_labeled.csv
在 labeled.csv 完成之前，不要继续跑 ranker、split、NPZ 生成或 FACT 训练
```

## 产物目标

本轮固定输出到：

```text
/data_all/intern02/egoexo-task-filter/outputs/filtering_v1_500takes_20260624
```

核心产物包括：

- `annotation_batch_v1_all.csv`：给人工填写的全量标注表。
- `annotation_batch_v1_labeled.csv`：人工完成后的标注表。
- `relevance_ranker_usable_for.pkl`：用 `usable_for` 训练出来的主 ranker。
- `take_relevance_ranked_all.csv`：带 `prob_tokenizer_main`、`prob_loco_aux`、`prob_discard` 等概率的 take 表。
- `filtered_split_v1.json`：最终三桶 split，保持 `fact_main`、`loco_aux`、`discard`。
- `audit_report_v1.md`：v0 自动桶和人工标签的校准报告。
- `transition_selection_fact_main_*.csv`：只用 `fact_main` 的 transition 选择。
- `transition_selection_fact_main_plus_loco25_*.csv`：`fact_main + capped loco_aux` 的 transition 选择。

## 1. 导出人工标注表

当前只有 427 个 take，所以 `--strategy v1_full_if_small` 会直接导出全量。未来扩到更多数据时，超过 `--sample-size` 后会按桶、任务类别和分数边界做分层抽样。

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

人工基于 contact sheet 填写这几个字段：

- `take_relevance`
- `ego_hand_visibility`
- `exo_body_visibility`
- `object_interaction`
- `phase_diversity`
- `usable_for`
- `notes`

人工完成后，把文件保存为：

```text
$OUT/annotation_batch_v1_labeled.csv
```

## 2. 校验人工标注

```bash
$PY tools/validate_annotations.py \
  --annotations $OUT/annotation_batch_v1_labeled.csv
```

校验会检查：

- 枚举值是否合法。
- 必填字段是否为空。
- `take_uid` 是否重复。
- 是否存在明显矛盾标签，例如 `D_scene_only` 却标成 `tokenizer_main`。

这一步不过，不要继续训练 ranker。

## 3. 训练并应用 usable_for ranker

主标签用 `usable_for`，不要用 `take_relevance` 直接决定最终 split。

```bash
$PY tools/train_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --labels $OUT/annotation_batch_v1_labeled.csv \
  --label-column usable_for \
  --out $OUT/relevance_ranker_usable_for.pkl

$PY tools/apply_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --ranker $OUT/relevance_ranker_usable_for.pkl \
  --out $OUT/take_relevance_ranked_all.csv
```

应用后需要重点看这些列：

- `prob_tokenizer_main`
- `prob_loco_aux`
- `prob_discard`
- `prob_diagnostic_candidate`

## 4. 生成 filtering_v1 split 和校准报告

```bash
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

先看 `audit_report_v1.md`，不要只看数量。重点检查：

- v1 `fact_main` 里有多少人工标成 `tokenizer_main`。
- v1 `loco_aux` 里有多少人工标成 `loco_aux`。
- `discard` 里是否误丢了大量 `tokenizer_main`。
- 每个 parent task 的保留率是否合理。

## 5. 生成 transition selection

只用 `fact_main`：

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
```

`fact_main + capped loco_aux`，其中 `loco_aux` 每个 take 只取少量 transition，避免 body/loco 数据淹没 manipulation token：

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
```

## 6. 生成 FACT 可直接使用的 filtered NPZ

`fact_main`：

```bash
$PY tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main
```

`fact_main_plus_loco25`：

```bash
$PY tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_plus_loco25_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_plus_loco25_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main_plus_loco25
```

生成后 FACT 侧使用的路径是：

```text
$OUT/filtered_npz/fact_main/train_by_take.npz
$OUT/filtered_npz/fact_main/heldout_by_take.npz
$OUT/filtered_npz/fact_main_plus_loco25/train_by_take.npz
$OUT/filtered_npz/fact_main_plus_loco25/heldout_by_take.npz
```

## 7. 进入 FACT 训练前的检查

人工 QA 最低要求：

- `fact_main` 抽检 50 个，至少 80% 应该适合 `tokenizer_main`。
- `loco_aux` 抽检 30 个，至少 70% 应该适合 loco/body。
- `fact_main` 中明显 scene-only 或 bad-ego 的误保留不超过 15%。

如果达不到，先修标注、ranker 或 `configs/filter_policy_v1.yaml`，不要进入 FACT 训练。

## 8. FACT 侧复测策略

第一轮只用 `fact_main`：

```text
v6b@90000 -> filtering_v1 fact_main @92000
```

继续使用固定 filtered heldout 口径，追踪：

- ego same
- ego random-take
- ego random-code
- used codes
- take NMI

只有当 `filtering_v1 fact_main` 不弱于 `filtering_v0 filtered-v6b`，才继续跑到 `95000`，再做 `fact_main_plus_loco25` ablation。
