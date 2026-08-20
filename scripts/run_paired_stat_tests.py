#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from statistical_analysis_common import (
    compute_metric_distributions,
    compute_paired_tests,
    default_manifest,
    write_csv,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paired McNemar and Wilcoxon tests.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/statistical_supplement_2026_06_10"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = default_manifest()
    metrics = compute_metric_distributions(manifest)
    result = compute_paired_tests(manifest, metrics["evaluations"])
    rows = result["rows"]
    write_json(args.out_dir / "paired_tests.json", result)
    write_csv(
        args.out_dir / "paired_tests.csv",
        rows,
        [
            "dataset",
            "comparison",
            "test",
            "n",
            "b_baseline_miss_method_hit",
            "c_baseline_hit_method_miss",
            "discordant",
            "p_value",
            "w_statistic",
            "mean_delta_rr",
            "median_delta_rr",
            "n_positive_delta",
            "n_negative_delta",
            "n_zero_delta",
            "wilcoxon_method",
        ],
    )
    print(f"Wrote {len(rows)} paired-test rows to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
