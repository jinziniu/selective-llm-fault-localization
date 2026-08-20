#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.evaluation import evaluate_file_level
from fl_localizer.io_utils import read_jsonl


def parse_ks(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("--ks must include at least one integer")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate file-level localization predictions.")
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--pred", type=Path, required=True, help="Prediction JSONL input")
    parser.add_argument("--per-bug", action="store_true", help="Print per-bug results")
    parser.add_argument("--ks", default="1,3,5", help="Comma-separated Top-k values")
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    result = evaluate_file_level(read_jsonl(args.bugs), read_jsonl(args.pred), ks=parse_ks(args.ks))
    payload = result if args.per_bug else result["summary"]
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
