# Filtering v0 Report

## Inputs

- Source train NPZ:
- Source heldout NPZ:
- Labels:
- Policy:
- Commit:

## Take Counts

| split | FACT-main | loco-aux | discard |
| --- | ---: | ---: | ---: |
| train | | | |
| heldout | | | |

## Bucket Audit

Summarize sampled human audit accuracy by bucket.

| bucket | sampled | accepted | rejected | notes |
| --- | ---: | ---: | ---: | --- |
| FACT-main | | | | |
| loco-aux | | | | |
| discard | | | | |

## Known Biases

List task categories overrepresented or underrepresented after filtering.

## Artifacts

```text
filtered_split_v0.json
transition_selection_train.csv
transition_selection_heldout.csv
filtered_npz/train_by_take.npz
filtered_npz/heldout_by_take.npz
same_take_negative_index_train.npz
```

## Downstream Ablations

- unfiltered diverse set
- random same-size subset
- filtered FACT-main
- filtered FACT-main + loco-aux
- human-verified subset
