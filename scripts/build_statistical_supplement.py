#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from statistical_analysis_common import run_all


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the full statistical supplement.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/statistical_supplement_2026_06_10"),
    )
    parser.add_argument(
        "--doc",
        type=Path,
        default=Path("docs/statistical_supplement_2026-06-10.md"),
    )
    args = parser.parse_args()

    result = run_all(args.out_dir, args.doc)
    print(
        "Wrote statistical supplement: "
        f"{len(result['metric_rows'])} metric rows, "
        f"{len(result['paired_rows'])} paired-test rows, "
        f"{len(result['recall_rows'])} recall rows, "
        f"{len(result['subset_rows'])} subset rows"
    )
    print(f"Document: {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
