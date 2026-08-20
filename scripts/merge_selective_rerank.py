#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl, write_jsonl


def load_selected_bug_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = payload.get("selected_bug_ids", [])
    if not isinstance(selected, list):
        raise ValueError(f"{path} does not contain a selected_bug_ids list")
    return {str(bug_id) for bug_id in selected}


def truncate_record(record: dict[str, Any], top_output: int) -> dict[str, Any]:
    updated = dict(record)
    ranked_files = updated.get("ranked_files", [])
    if isinstance(ranked_files, list):
        updated["ranked_files"] = ranked_files[:top_output]
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge baseline predictions with rerank predictions for selected bug ids."
    )
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline prediction JSONL")
    parser.add_argument("--rerank", type=Path, required=True, help="Rerank prediction JSONL")
    parser.add_argument("--selection", type=Path, required=True, help="Selection report JSON")
    parser.add_argument("--out", type=Path, required=True, help="Merged prediction JSONL")
    parser.add_argument("--top-output", type=int, default=10)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Use baseline records when a selected bug id is missing from the rerank file",
    )
    args = parser.parse_args()

    selected_bug_ids = load_selected_bug_ids(args.selection)
    rerank_by_bug = {record["bug_id"]: record for record in read_jsonl(args.rerank)}
    missing = sorted(bug_id for bug_id in selected_bug_ids if bug_id not in rerank_by_bug)
    if missing and not args.allow_missing:
        raise ValueError(
            "Selected bug ids missing from rerank file: " + ", ".join(missing)
        )

    merged: list[dict[str, Any]] = []
    rerank_used = 0
    for baseline_record in read_jsonl(args.baseline):
        bug_id = str(baseline_record["bug_id"])
        if bug_id in selected_bug_ids and bug_id in rerank_by_bug:
            merged.append(truncate_record(rerank_by_bug[bug_id], args.top_output))
            rerank_used += 1
        else:
            record = truncate_record(baseline_record, args.top_output)
            record["method"] = str(record.get("method", "baseline")) + "+selective-no-llm"
            merged.append(record)

    write_jsonl(args.out, merged)
    print(
        f"Wrote {len(merged)} records to {args.out}; "
        f"selected={len(selected_bug_ids)}, rerank_used={rerank_used}, missing={len(missing)}"
    )
    if missing:
        print("Missing selected bug ids: " + ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
