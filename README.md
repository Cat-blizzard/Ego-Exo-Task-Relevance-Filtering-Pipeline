# Ego-Exo Task-Relevance Filtering Pipeline

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
