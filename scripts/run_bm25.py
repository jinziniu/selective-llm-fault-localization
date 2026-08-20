#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.bm25 import BM25Index
from fl_localizer.indexer import index_source_files
from fl_localizer.io_utils import read_jsonl, write_jsonl
from fl_localizer.text import extract_runtime_context


def build_query(record: dict[str, object]) -> str:
    bug_report = record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}
    parts = [
        str(bug_report.get("id", "")),
        str(bug_report.get("text", "")),
        str(record.get("test_failure", "")),
        " ".join(record.get("triggering_tests", [])),  # type: ignore[arg-type]
        extract_runtime_context(str(record.get("stack_trace", ""))),
    ]
    return "\n".join(part for part in parts if part)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run file-level BM25 fault localization.")
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--out", type=Path, required=True, help="Prediction JSONL output")
    parser.add_argument("--top-k", type=int, default=10, help="Number of files to rank")
    args = parser.parse_args()

    predictions: list[dict[str, object]] = []
    for record in read_jsonl(args.bugs):
        bug_id = record["bug_id"]
        repo_path = Path(record["repo_path"])
        source_dir = record["source_dir"]
        source_files = index_source_files(repo_path, source_dir)
        documents = [(source.file, source.document_text()) for source in source_files]
        index = BM25Index(documents)
        ranked = index.rank(build_query(record), top_k=args.top_k)
        predictions.append(
            {
                "bug_id": bug_id,
                "method": "bm25",
                "query_sources": [
                    "bug_report.id",
                    "bug_report.text",
                    "test_failure",
                    "triggering_tests",
                    "stack_trace",
                ],
                "indexed_files": len(source_files),
                "ranked_files": [
                    {"rank": item.rank, "file": item.file, "score": item.score}
                    for item in ranked
                ],
            }
        )
        print(f"[{bug_id}] indexed {len(source_files)} files, wrote top {len(ranked)}")

    write_jsonl(args.out, predictions)
    print(f"Wrote {len(predictions)} prediction(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
