# Ego-Exo Task-Relevance Filtering Pipeline

## Annotator Quick Start

If you only need to label data, read:

```text
docs/annotator_quickstart.zh-CN.md
```

A generated review pack contains:

```text
review_pack/ANNOTATOR_GUIDE.zh-CN.md
review_pack/annotation_review.csv
review_pack/index.html
review_pack/review_images/
```

Annotators only need to open `index.html`, fill the empty label columns in `annotation_review.csv`, and return the completed CSV.

中文说明: [README.zh-CN.md](README.zh-CN.md)

This repository builds task-relevant Ego-Exo data artifacts for coarse loco-manipulation FACT tokenizer training.

The goal is not to select visually pleasing videos. The goal is to convert broad Ego-Exo takes into reproducible training artifacts where:

- ego contains usable interaction or active-motion cues,
- exo contains body/global context,
- the take has enough temporal phase diversity,
- scene-only and take-ID shortcuts are reduced.

Large videos, NPZ files, contact sheets, checkpoints, and credentials must stay outside Git. Store them on the server and commit only code, configs, schemas, annotation CSVs, and audit summaries.

## Outputs

The pipeline is designed to produce:

```text
outputs/filtering_v0/take_relevance_scores.csv
outputs/filtering_v0/annotation_batch_001.csv
outputs/filtering_v0/annotation_batch_001_labeled.csv
outputs/filtering_v0/take_relevance_ranked.csv
outputs/filtering_v0/filtered_split_v0.json
outputs/filtering_v0/transition_selection_train.csv
outputs/filtering_v0/transition_selection_heldout.csv
outputs/filtering_v0/filtered_npz/train_by_take.npz
outputs/filtering_v0/filtered_npz/heldout_by_take.npz
outputs/filtering_v0/same_take_negative_index_train.npz
outputs/filtering_v0/audit_report.md
outputs/filtering_v0/phase_diagnostic_candidates.csv
```

The two most important artifacts for `fact-tokenizer` are:

```text
filtered_npz/train_by_take.npz
same_take_negative_index_train.npz
```

## Quick Start

Use the current FACT split as input:

```bash
BASE=data/fact_egoexo_sxh_handoff/splits/diverse_500takes_t0p5_s1_48t_seed123_80_20
OUT=outputs/filtering_v0

python tools/make_take_contact_sheets.py \
  --split $BASE/train_by_take.npz \
  --labels-jsonl $BASE/train_labels.jsonl \
  --out $OUT/contact_sheets_train \
  --num-frames 12

python tools/extract_relevance_features.py \
  --split $BASE/train_by_take.npz \
  --split-name train \
  --labels-jsonl $BASE/train_labels.jsonl \
  --contact-sheet-manifest $OUT/contact_sheets_train/contact_sheet_manifest.csv \
  --out $OUT/take_relevance_scores_train.csv

python tools/export_annotation_csv.py \
  --scores $OUT/take_relevance_scores_train.csv \
  --sample-size 300 \
  --out $OUT/annotation_batch_001.csv
```

After humans fill `annotation_batch_001_labeled.csv`:

```bash
python tools/train_relevance_ranker.py \
  --features $OUT/take_relevance_scores_train.csv \
  --labels $OUT/annotation_batch_001_labeled.csv \
  --out $OUT/relevance_ranker.pkl

python tools/apply_relevance_ranker.py \
  --features $OUT/take_relevance_scores_train.csv \
  --ranker $OUT/relevance_ranker.pkl \
  --out $OUT/take_relevance_ranked_train.csv
```

Build split and training artifacts:

```bash
python tools/build_filtered_split.py \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --policy configs/filter_policy_v0.yaml \
  --out $OUT/filtered_split_v0.json

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

python tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_train.csv \
  --heldout-selection $OUT/transition_selection_heldout.csv \
  --out-dir $OUT/filtered_npz

python tools/build_same_take_negative_index.py \
  --npz $OUT/filtered_npz/train_by_take.npz \
  --out $OUT/same_take_negative_index_train.npz
```

## filtering_v1 Human-Calibrated Flow

`filtering_v1` upgrades the v0 proxy filter with manual calibration labels. For the current 427-take split, export all takes for annotation:

Chinese workflow notes are available in [`docs/filtering_v1_workflow.zh-CN.md`](docs/filtering_v1_workflow.zh-CN.md).

The workflow has two gates:

1. Export the annotation CSV and stop for human labeling.
2. Only after `annotation_batch_v1_labeled.csv` exists, run validation, ranker training, split generation, and filtered NPZ generation.

Do not run the ranker or split commands before the labeled CSV is ready.

### Stage 1: Export the human annotation CSV

```bash
OUT=/data_all/intern02/egoexo-task-filter/outputs/filtering_v1_500takes_20260624
V0=/data_all/intern02/egoexo-task-filter/outputs/filtering_v0_500takes_20260624

python tools/export_annotation_csv.py \
  --scores $V0/take_relevance_scores_all.csv \
  --sample-size 500 \
  --strategy v1_full_if_small \
  --out $OUT/annotation_batch_v1_all.csv
```

Humans should inspect the contact sheets and fill these columns:

```text
take_relevance
ego_hand_visibility
exo_body_visibility
object_interaction
phase_diversity
usable_for
notes
```

Save the completed file as:

```text
$OUT/annotation_batch_v1_labeled.csv
```

For easier local annotation, build a review pack with friendly image names:

```bash
python tools/build_annotation_review_pack.py \
  --annotations $OUT/annotation_batch_v1_labeled.csv \
  --out-dir $OUT/review_pack \
  --copy-images
```

On a local Windows copy, map server paths to the downloaded folder:

```powershell
$env:PYTHONPATH="D:\Ego-Exo-Task-Relevance-Filtering-Pipeline"
python D:\Ego-Exo-Task-Relevance-Filtering-Pipeline\tools\build_annotation_review_pack.py `
  --annotations D:\egoexo_v1_annotation\annotation_batch_v1_labeled.csv `
  --out-dir D:\egoexo_v1_annotation\review_pack `
  --path-prefix-from /data_all/intern02/egoexo-task-filter/outputs/filtering_v0_500takes_20260624 `
  --path-prefix-to D:/egoexo_v1_annotation `
  --copy-images
```

Annotators can then use `review_pack/annotation_review.csv` together with `review_pack/index.html` and `review_pack/review_images/`.

### Stage 2: Validate labels and train the usable_for ranker

Run this only after `annotation_batch_v1_labeled.csv` exists:

```bash
python tools/validate_annotations.py \
  --annotations $OUT/annotation_batch_v1_labeled.csv

python tools/train_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --labels $OUT/annotation_batch_v1_labeled.csv \
  --label-column usable_for \
  --out $OUT/relevance_ranker_usable_for.pkl

python tools/apply_relevance_ranker.py \
  --features $V0/take_relevance_scores_all.csv \
  --ranker $OUT/relevance_ranker_usable_for.pkl \
  --out $OUT/take_relevance_ranked_all.csv

python tools/build_filtered_split.py \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --policy configs/filter_policy_v1.yaml \
  --out $OUT/filtered_split_v1.json

python tools/summarize_annotation_calibration.py \
  --scores $V0/take_relevance_scores_all.csv \
  --ranked $OUT/take_relevance_ranked_all.csv \
  --annotations $OUT/annotation_batch_v1_labeled.csv \
  --filtered-split $OUT/filtered_split_v1.json \
  --out $OUT/audit_report_v1.md
```

### Stage 3: Build transition selections and filtered NPZ files

Run this only after `audit_report_v1.md` looks acceptable:

```bash
BASE=/data_all/intern02/fact-tokenizer/data/fact_egoexo_sxh_handoff/splits/diverse_500takes_t0p5_s1_48t_seed123_80_20

python tools/build_transition_selection.py \
  --npz $BASE/train_by_take.npz \
  --split-name train \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main \
  --out $OUT/transition_selection_fact_main_train.csv

python tools/build_transition_selection.py \
  --npz $BASE/heldout_by_take.npz \
  --split-name heldout \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main \
  --out $OUT/transition_selection_fact_main_heldout.csv

python tools/build_transition_selection.py \
  --npz $BASE/train_by_take.npz \
  --split-name train \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main loco_aux \
  --bucket-num-transitions loco_aux=12 \
  --out $OUT/transition_selection_fact_main_plus_loco25_train.csv

python tools/build_transition_selection.py \
  --npz $BASE/heldout_by_take.npz \
  --split-name heldout \
  --filtered-split $OUT/filtered_split_v1.json \
  --include-buckets fact_main loco_aux \
  --bucket-num-transitions loco_aux=12 \
  --out $OUT/transition_selection_fact_main_plus_loco25_heldout.csv

python tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main

python tools/build_filtered_npz.py \
  --train-npz $BASE/train_by_take.npz \
  --heldout-npz $BASE/heldout_by_take.npz \
  --train-selection $OUT/transition_selection_fact_main_plus_loco25_train.csv \
  --heldout-selection $OUT/transition_selection_fact_main_plus_loco25_heldout.csv \
  --out-dir $OUT/filtered_npz/fact_main_plus_loco25
```

## Bucket Definitions

- `A_interaction_rich`: ego has hand/object or manipulation cues, exo has body/global context, phases include reach/contact/carry/place or related interaction.
- `B_loco_body`: body motion, approach, turn, reposition, or alignment is visible; hand-object interaction is weak.
- `C_active_view_only`: ego mainly contains head/camera motion or active looking with weak action semantics.
- `D_scene_only`: scene, wall, field, floor, or static background dominates; no clear action phase.
- `E_fine_dexterous`: fine manipulation exists, but it is not the main coarse loco-manipulation target yet.
- `F_bad_or_unclear`: sync, occlusion, visibility, or semantic ambiguity makes the take unreliable.

## Validation

Run:

```bash
python -m pytest
```

Tests cover schema-level behavior, take leakage, and same-take negative index invariants on synthetic data.
