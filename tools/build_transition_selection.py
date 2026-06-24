#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.common import group_indices_by_take, load_npz_metadata, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select motion-aware transitions inside filtered takes.")
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--split-name", choices=["train", "heldout"], required=True)
    parser.add_argument("--filtered-split", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--num-transitions", type=int, default=48)
    parser.add_argument("--include-buckets", nargs="+", default=["fact_main", "loco_aux"])
    parser.add_argument("--view-keys", nargs=2, default=["ego", "exo"])
    return parser.parse_args()


def motion_scores(video: np.ndarray) -> np.ndarray:
    values = video.astype(np.float32)
    if values.max(initial=0.0) > 1.5:
        values = values / 255.0
    if values.shape[-1] in (1, 3):
        delta = values[:, -1] - values[:, 0]
    else:
        delta = values[:, -1].transpose(0, 2, 3, 1) - values[:, 0].transpose(0, 2, 3, 1)
    return np.abs(delta).mean(axis=tuple(range(1, delta.ndim))).astype(np.float32)


def selected_takes(filtered_split: dict, split_name: str, include_buckets: list[str]) -> dict[str, str]:
    takes: dict[str, str] = {}
    split = filtered_split["splits"][split_name]
    for bucket in include_buckets:
        for row in split.get(bucket, []):
            takes[str(row["take_uid"])] = bucket
    return takes


def select_rows(indices: list[int], score: np.ndarray, timestamps: np.ndarray, count: int) -> list[int]:
    if len(indices) <= count:
        return list(indices)
    ordered = sorted(indices, key=lambda idx: float(timestamps[idx]))
    bins = np.array_split(np.asarray(ordered, dtype=np.int64), count)
    selected = []
    for values in bins:
        best = int(values[np.argmax(score[values])])
        selected.append(best)
    return sorted(set(selected), key=lambda idx: float(timestamps[idx]))


def main() -> None:
    args = parse_args()
    metadata = load_npz_metadata(args.npz)
    filtered_split = json.loads(args.filtered_split.read_text(encoding="utf-8"))
    take_bucket = selected_takes(filtered_split, args.split_name, args.include_buckets)
    grouped = group_indices_by_take(metadata["take_uid"])
    with np.load(args.npz, allow_pickle=False) as data:
        score = sum(motion_scores(np.asarray(data[view_key])) for view_key in args.view_keys) / len(args.view_keys)
    rows = []
    for take_uid, indices in sorted(grouped.items()):
        if take_uid not in take_bucket:
            continue
        selected = set(select_rows(indices, score, metadata["timestamp"], args.num_transitions))
        for idx in indices:
            is_selected = idx in selected
            rows.append(
                {
                    "split": args.split_name,
                    "bucket": take_bucket[take_uid],
                    "take_uid": take_uid,
                    "row_index": idx,
                    "sample_id": str(metadata["sample_id"][idx]),
                    "timestamp": float(metadata["timestamp"][idx]),
                    "selected": int(is_selected),
                    "selection_reason": "motion_aware_temporal_coverage" if is_selected else "",
                    "motion_score": float(score[idx]),
                }
            )
    fieldnames = ["split", "bucket", "take_uid", "row_index", "sample_id", "timestamp", "selected", "selection_reason", "motion_score"]
    write_csv(args.out, rows, fieldnames=fieldnames)
    print(f"Saved {len(rows)} transition rows to {args.out}")


if __name__ == "__main__":
    main()
