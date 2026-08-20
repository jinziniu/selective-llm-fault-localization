#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl


def usage_int(record: dict[str, Any], key: str) -> int:
    usage = record.get("token_usage", {})
    if not isinstance(usage, dict):
        return 0
    value = usage.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    durations = [float(record.get("llm_duration_seconds") or 0.0) for record in records]
    prompt_tokens = [usage_int(record, "prompt_tokens") for record in records]
    completion_tokens = [usage_int(record, "completion_tokens") for record in records]
    total_tokens = [usage_int(record, "total_tokens") for record in records]
    cache_hit_tokens = [usage_int(record, "prompt_cache_hit_tokens") for record in records]
    cache_miss_tokens = [usage_int(record, "prompt_cache_miss_tokens") for record in records]

    def average(values: list[int] | list[float]) -> float:
        return sum(values) / total if total else 0.0

    return {
        "records": total,
        "total_duration_seconds": round(sum(durations), 3),
        "avg_duration_seconds": round(average(durations), 3),
        "total_prompt_tokens": sum(prompt_tokens),
        "avg_prompt_tokens": round(average(prompt_tokens), 2),
        "total_completion_tokens": sum(completion_tokens),
        "avg_completion_tokens": round(average(completion_tokens), 2),
        "total_tokens": sum(total_tokens),
        "avg_total_tokens": round(average(total_tokens), 2),
        "total_prompt_cache_hit_tokens": sum(cache_hit_tokens),
        "total_prompt_cache_miss_tokens": sum(cache_miss_tokens),
        "avg_prompt_cache_hit_tokens": round(average(cache_hit_tokens), 2),
        "avg_prompt_cache_miss_tokens": round(average(cache_miss_tokens), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize LLM usage metadata from rerank JSONL.")
    parser.add_argument("--pred", type=Path, required=True, help="Rerank prediction JSONL")
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    summary = summarize(read_jsonl(args.pred))
    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
