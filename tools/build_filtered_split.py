#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FACT-main/loco-aux/discard split JSON from ranked relevance rows.")
    parser.add_argument("--ranked", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def get_probability(row: pd.Series, candidates: list[str], fallback: str) -> float:
    for column in candidates:
        if column in row and pd.notna(row[column]):
            return float(row[column])
    return float(row.get(fallback, 0.0))


def main() -> None:
    args = parse_args()
    ranked = pd.read_csv(args.ranked)
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    fact_policy = policy["fact_main"]
    loco_policy = policy["loco_aux"]
    output = {
        "version": policy.get("version", "filtering_v0"),
        "policy": policy,
        "splits": {"train": {"fact_main": [], "loco_aux": [], "discard": []}, "heldout": {"fact_main": [], "loco_aux": [], "discard": []}},
    }
    for _, row in ranked.iterrows():
        split = str(row.get("split", "train"))
        if split not in output["splits"]:
            split = "train"
        interaction_prob = get_probability(
            row,
            ["prob_a_interaction_rich", "prob_interaction_rich", "prob_tokenizer_main"],
            "interaction_score",
        )
        loco_prob = get_probability(row, ["prob_b_loco_body", "prob_loco_body", "prob_loco_aux"], "loco_score")
        scene = float(row.get("scene_only_score", 0.0))
        temporal = float(row.get("temporal_diversity_score", 0.0))
        item = {
            "take_uid": str(row["take_uid"]),
            "parent_task_name": str(row.get("parent_task_name", "")),
            "task_name": str(row.get("task_name", "")),
            "relevance_score": float(row.get("relevance_score", 0.0)),
            "interaction_prob": interaction_prob,
            "loco_prob": loco_prob,
            "scene_only_score": scene,
            "temporal_diversity_score": temporal,
        }
        if (
            interaction_prob >= float(fact_policy["min_interaction_prob"])
            and temporal >= float(fact_policy["min_temporal_diversity"])
            and scene <= float(fact_policy["max_scene_only"])
        ):
            output["splits"][split]["fact_main"].append(item)
        elif loco_prob >= float(loco_policy["min_loco_prob"]) and scene <= float(loco_policy["max_scene_only"]):
            output["splits"][split]["loco_aux"].append(item)
        else:
            output["splits"][split]["discard"].append(item)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    for split, buckets in output["splits"].items():
        print(split, {bucket: len(items) for bucket, items in buckets.items()})
    print(f"Saved filtered split to {args.out}")


if __name__ == "__main__":
    main()
