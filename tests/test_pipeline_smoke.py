from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def run_tool(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def make_npz(path: Path, take_count: int = 2, per_take: int = 8) -> Path:
    rng = np.random.default_rng(123)
    n = take_count * per_take
    ego = rng.integers(0, 255, size=(n, 2, 16, 16, 3), dtype=np.uint8)
    exo = rng.integers(0, 255, size=(n, 2, 16, 16, 3), dtype=np.uint8)
    take_uid = np.asarray([f"take_{take}" for take in range(take_count) for _ in range(per_take)])
    timestamp = np.asarray([time for _ in range(take_count) for time in range(per_take)], dtype=np.float32)
    sample_id = np.asarray([f"{take_uid[i]}:{timestamp[i]:.3f}" for i in range(n)])
    np.savez_compressed(path, ego=ego, exo=exo, take_uid=take_uid, timestamp=timestamp, sample_id=sample_id)
    return path


def write_labels(path: Path, take_count: int = 2) -> Path:
    rows = []
    parents = ["Cooking", "Basketball"]
    for index in range(take_count):
        rows.append(
            {
                "take_uid": f"take_{index}",
                "take_name": f"dummy_{index}",
                "parent_task_name": parents[index % len(parents)],
                "task_name": f"task_{index}",
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return path


def test_extract_features_and_annotation_export(tmp_path: Path) -> None:
    npz = make_npz(tmp_path / "split.npz")
    labels = write_labels(tmp_path / "labels.jsonl")
    scores = tmp_path / "scores.csv"
    run_tool(
        tmp_path,
        "tools/extract_relevance_features.py",
        "--split",
        str(npz),
        "--split-name",
        "train",
        "--labels-jsonl",
        str(labels),
        "--out",
        str(scores),
    )
    with scores.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {"take_uid", "relevance_score", "auto_bucket"}.issubset(rows[0])

    annotation = tmp_path / "annotation.csv"
    run_tool(
        tmp_path,
        "tools/export_annotation_csv.py",
        "--scores",
        str(scores),
        "--sample-size",
        "2",
        "--out",
        str(annotation),
    )
    with annotation.open(newline="", encoding="utf-8") as handle:
        annotation_rows = list(csv.DictReader(handle))
    assert len(annotation_rows) == 2
    assert "usable_for" in annotation_rows[0]


def test_filtered_split_has_separate_train_heldout_takes(tmp_path: Path) -> None:
    ranked = tmp_path / "ranked.csv"
    with ranked.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "take_uid",
            "split",
            "parent_task_name",
            "task_name",
            "relevance_score",
            "interaction_score",
            "loco_score",
            "scene_only_score",
            "temporal_diversity_score",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "take_uid": "train_take",
                "split": "train",
                "parent_task_name": "Cooking",
                "task_name": "dummy",
                "relevance_score": 0.8,
                "interaction_score": 0.8,
                "loco_score": 0.2,
                "scene_only_score": 0.1,
                "temporal_diversity_score": 0.5,
            }
        )
        writer.writerow(
            {
                "take_uid": "heldout_take",
                "split": "heldout",
                "parent_task_name": "Bike Repair",
                "task_name": "dummy",
                "relevance_score": 0.8,
                "interaction_score": 0.8,
                "loco_score": 0.2,
                "scene_only_score": 0.1,
                "temporal_diversity_score": 0.5,
            }
        )
    out = tmp_path / "filtered.json"
    run_tool(
        tmp_path,
        "tools/build_filtered_split.py",
        "--ranked",
        str(ranked),
        "--policy",
        str(ROOT / "configs/filter_policy_v0.yaml"),
        "--out",
        str(out),
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    train_takes = {row["take_uid"] for bucket in payload["splits"]["train"].values() for row in bucket}
    heldout_takes = {row["take_uid"] for bucket in payload["splits"]["heldout"].values() for row in bucket}
    assert train_takes == {"train_take"}
    assert heldout_takes == {"heldout_take"}
    assert train_takes.isdisjoint(heldout_takes)


def test_same_take_negative_index_invariants(tmp_path: Path) -> None:
    npz = make_npz(tmp_path / "filtered.npz", take_count=2, per_take=8)
    out = tmp_path / "negative_index.npz"
    run_tool(
        tmp_path,
        "tools/build_same_take_negative_index.py",
        "--npz",
        str(npz),
        "--out",
        str(out),
        "--top-k",
        "3",
        "--min-gap",
        "2",
        "--max-gap",
        "5",
    )
    with np.load(npz, allow_pickle=False) as source, np.load(out, allow_pickle=False) as neg:
        take_uid = source["take_uid"].astype(str)
        timestamp = source["timestamp"]
        donors = neg["donor_index_topk"]
    valid = donors >= 0
    anchors = np.repeat(np.arange(donors.shape[0])[:, None], donors.shape[1], axis=1)
    assert valid.any()
    assert np.all(take_uid[anchors[valid]] == take_uid[donors[valid]])
    gap = np.abs(timestamp[anchors[valid]] - timestamp[donors[valid]])
    assert np.all((gap >= 2) & (gap <= 5))
