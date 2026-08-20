#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from statistical_analysis_common import (
    compute_metric_distributions,
    compute_recall_curves,
    default_manifest,
    write_csv,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute retrieval Recall@K curves.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/statistical_supplement_2026_06_10"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = default_manifest()
    metrics = compute_metric_distributions(manifest)
    result = compute_recall_curves(manifest, metrics["evaluations"])
    write_json(args.out_dir / "recall_curves.json", result)
    write_csv(
        args.out_dir / "recall_curve_points.csv",
        result["rows"],
        [
            "dataset",
            "method",
            "n",
            "max_depth",
            "hits_at_10",
            "recall_at_10",
            "hits_at_20",
            "recall_at_20",
            "hits_at_50",
            "recall_at_50",
            "hits_at_100",
            "recall_at_100",
            "marginal_50_to_100",
        ],
    )
    write_csv(
        args.out_dir / "retrieval_misses_top50_vs_top100.csv",
        result["retrieval_misses"],
        [
            "dataset",
            "method",
            "bug_id",
            "rank_at_available_depth",
            "max_depth",
            "rank_at_100",
            "rescued_by_100",
            "ground_truth_files",
        ],
    )
    print(f"Wrote {len(result['rows'])} recall rows to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
