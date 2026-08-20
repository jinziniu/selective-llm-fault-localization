#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl, write_jsonl


def complete_record(
    record: dict[str, Any],
    bm25_record: dict[str, Any],
    *,
    top_output: int,
) -> dict[str, Any]:
    candidate_files = [item["file"] for item in bm25_record["ranked_files"]]
    candidate_file_set = set(candidate_files)
    completed: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_files: list[str] = []
    duplicate_files: list[str] = []

    original_ranked = record.get("ranked_files", [])
    if not isinstance(original_ranked, list):
        original_ranked = []

    for item in original_ranked:
        if not isinstance(item, dict) or "file" not in item:
            continue
        file_path = str(item["file"])
        if file_path not in candidate_file_set:
            invalid_files.append(file_path)
            continue
        if file_path in seen:
            duplicate_files.append(file_path)
            continue
        seen.add(file_path)
        completed.append(
            {
                "rank": len(completed) + 1,
                "file": file_path,
                "confidence": item.get("confidence"),
                "reason": str(item.get("reason", "")),
                "source": item.get("source", "llm"),
            }
        )
        if len(completed) >= top_output:
            break

    fallback_added: list[str] = []
    for file_path in candidate_files:
        if len(completed) >= top_output:
            break
        if file_path in seen:
            continue
        seen.add(file_path)
        fallback_added.append(file_path)
        completed.append(
            {
                "rank": len(completed) + 1,
                "file": file_path,
                "confidence": None,
                "reason": "Fallback candidate appended in original BM25 order because the model did not return enough valid files.",
                "source": "bm25-fallback",
            }
        )

    updated = dict(record)
    updated["candidate_count"] = len(candidate_files)
    updated["requested_output_count"] = top_output
    updated["llm_returned_count"] = len(original_ranked)
    updated["valid_llm_count"] = len([item for item in completed if item["source"] == "llm"])
    updated["fallback_added_count"] = len(fallback_added)
    updated["fallback_added_files"] = fallback_added
    updated["invalid_files"] = invalid_files
    updated["duplicate_files"] = duplicate_files
    updated["ranked_files"] = completed
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete rerank outputs with BM25 fallback files.")
    parser.add_argument("--rerank", type=Path, required=True)
    parser.add_argument("--bm25", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top-output", type=int, default=10)
    args = parser.parse_args()

    bm25_by_bug = {record["bug_id"]: record for record in read_jsonl(args.bm25)}
    records = [
        complete_record(record, bm25_by_bug[record["bug_id"]], top_output=args.top_output)
        for record in read_jsonl(args.rerank)
    ]
    write_jsonl(args.out, records)
    print(f"Wrote {len(records)} completed record(s) to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
