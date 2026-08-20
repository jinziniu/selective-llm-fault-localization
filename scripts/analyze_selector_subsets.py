#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from statistical_analysis_common import (
    compute_metric_distributions,
    compute_selector_subsets,
    default_manifest,
    write_csv,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze selected and unselected selector subsets.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/statistical_supplement_2026_06_10"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = default_manifest()
    metrics = compute_metric_distributions(manifest)
    result = compute_selector_subsets(manifest, metrics["evaluations"])
    write_json(args.out_dir / "selector_subset_metrics.json", result)
    write_csv(
        args.out_dir / "selector_subset_metrics.csv",
        result["rows"],
        [
            "dataset",
            "subset",
            "n",
            "baseline_top_1",
            "baseline_top_3",
            "baseline_top_5",
            "baseline_top_10",
            "baseline_mrr",
            "final_top_1",
            "final_top_3",
            "final_top_5",
            "final_top_10",
            "final_mrr",
        ],
    )
    write_csv(
        args.out_dir / "selector_false_negatives.csv",
        result["selector_false_negatives"],
        ["dataset", "bug_id", "baseline_rank", "final_rank", "ground_truth_files"],
    )
    print(f"Wrote {len(result['rows'])} selector subset rows to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
