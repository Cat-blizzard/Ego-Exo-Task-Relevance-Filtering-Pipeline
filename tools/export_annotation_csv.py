#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

from tools.common import read_csv, write_csv


ANNOTATION_COLUMNS = [
    "take_relevance",
    "ego_hand_visibility",
    "exo_body_visibility",
    "object_interaction",
    "phase_diversity",
    "usable_for",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a stratified take annotation CSV from relevance scores.")
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.scores)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("auto_bucket", "F_uncertain")].append(row)
    rng = random.Random(args.seed)
    selected: list[dict[str, str]] = []
    buckets = sorted(grouped)
    per_bucket = max(1, args.sample_size // max(1, len(buckets)))
    for bucket in buckets:
        values = grouped[bucket]
        rng.shuffle(values)
        selected.extend(values[:per_bucket])
    if len(selected) < args.sample_size:
        remaining = [row for row in rows if row not in selected]
        rng.shuffle(remaining)
        selected.extend(remaining[: args.sample_size - len(selected)])
    selected = selected[: args.sample_size]
    output = []
    for row in selected:
        output.append(
            {
                "take_uid": row.get("take_uid", ""),
                "contact_sheet_path": row.get("contact_sheet_path", ""),
                "auto_bucket": row.get("auto_bucket", ""),
                "relevance_score": row.get("relevance_score", ""),
                "parent_task_name": row.get("parent_task_name", ""),
                "task_name": row.get("task_name", ""),
                **{column: "" for column in ANNOTATION_COLUMNS},
            }
        )
    write_csv(args.out, output)
    print(f"Saved {len(output)} annotation rows to {args.out}")


if __name__ == "__main__":
    main()
