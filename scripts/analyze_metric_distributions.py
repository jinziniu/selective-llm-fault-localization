#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from statistical_analysis_common import (
    compute_metric_distributions,
    default_manifest,
    write_csv,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute raw counts and rank distribution metrics.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/statistical_supplement_2026_06_10"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = compute_metric_distributions(default_manifest())
    rows = result["rows"]
    write_json(args.out_dir / "metric_distributions.json", {"rows": rows})
    write_csv(
        args.out_dir / "metric_distributions.csv",
        rows,
        [
            "dataset",
            "method",
            "role",
            "n",
            "top_1_hits",
            "top_3_hits",
            "top_5_hits",
            "top_10_hits",
            "mrr",
            "median_rr",
            "sd_rr",
            "median_capped_rank",
            "miss_count",
            "max_depth",
        ],
    )
    print(f"Wrote {len(rows)} metric rows to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
