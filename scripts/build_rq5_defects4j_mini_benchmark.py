#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl, write_jsonl


@dataclass(frozen=True)
class MiniCase:
    bug_id: str
    bug_file: Path
    pred_file: Path
    category: str
    rationale: str


CASES: tuple[MiniCase, ...] = (
    MiniCase(
        bug_id="Math-12",
        bug_file=Path("data/defects4j/math_pilot_20.jsonl"),
        pred_file=Path("outputs/math_pilot_20_hybrid_focused_direct_top50.jsonl"),
        category="state-reset evidence",
        rationale="Candidate-present case where the true file needs clone/reseed/reset evidence.",
    ),
    MiniCase(
        bug_id="Math-14",
        bug_file=Path("data/defects4j/math_pilot_20.jsonl"),
        pred_file=Path("outputs/math_pilot_20_hybrid_focused_direct_top50.jsonl"),
        category="matrix/allocation evidence",
        rationale="Candidate/evidence case affected by direct candidate inclusion.",
    ),
    MiniCase(
        bug_id="Closure-4",
        bug_file=Path("data/defects4j/closure_pilot_20.jsonl"),
        pred_file=Path("outputs/closure_pilot_20_hybrid_focused_passchain_direct_top50.jsonl"),
        category="type-cycle evidence",
        rationale="Candidate-present case where snippet scoring must expose type-cycle handling.",
    ),
    MiniCase(
        bug_id="Closure-13",
        bug_file=Path("data/defects4j/closure_pilot_20.jsonl"),
        pred_file=Path("outputs/closure_pilot_20_hybrid_focused_passchain_direct_top50.jsonl"),
        category="pass-chain retrieval boundary",
        rationale="True file is available only after pass-chain retrieval broadens the candidate pool.",
    ),
    MiniCase(
        bug_id="Closure-65",
        bug_file=Path("data/defects4j/closure_heldout_61_80.jsonl"),
        pred_file=Path("outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl"),
        category="code-output evidence gap",
        rationale="Held-out selector did not rerank a code-generation failure.",
    ),
    MiniCase(
        bug_id="Closure-67",
        bug_file=Path("data/defects4j/closure_heldout_61_80.jsonl"),
        pred_file=Path("outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl"),
        category="selector false negative",
        rationale="Semantic pass-family mismatch missed by the cost-control selector.",
    ),
    MiniCase(
        bug_id="Closure-75",
        bug_file=Path("data/defects4j/closure_heldout_61_80.jsonl"),
        pred_file=Path("outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl"),
        category="utility-file ambiguity",
        rationale="Diagnostic case around ambiguous utility-file localization.",
    ),
    MiniCase(
        bug_id="Closure-98",
        bug_file=Path("data/defects4j/closure_heldout_81_100.jsonl"),
        pred_file=Path("outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl"),
        category="retrieval boundary negative",
        rationale="Top-50 retrieval boundary case included to test failure behavior.",
    ),
    MiniCase(
        bug_id="Mockito-26",
        bug_file=Path("data/defects4j/mockito_fresh_21_30.jsonl"),
        pred_file=Path("outputs/mockito_fresh_21_30_hybrid_focused_direct_top50.jsonl"),
        category="mockito primitive/default-value pattern",
        rationale="Mockito pattern generalization case not selected by the previous gate.",
    ),
    MiniCase(
        bug_id="Mockito-28",
        bug_file=Path("data/defects4j/mockito_fresh_21_30.jsonl"),
        pred_file=Path("outputs/mockito_fresh_21_30_hybrid_focused_direct_top50.jsonl"),
        category="mockito injection/ancestor pattern",
        rationale="Mockito injection matching case not selected by the previous gate.",
    ),
)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_by_bug_id(path: Path) -> dict[str, dict[str, Any]]:
    resolved = resolve(path)
    return {str(record["bug_id"]): record for record in read_jsonl(resolved)}


def best_ground_truth_rank(
    bug_record: dict[str, Any],
    pred_record: dict[str, Any],
) -> int | None:
    gt_files = set(bug_record.get("ground_truth", {}).get("files", []))
    ranks: list[int] = []
    for index, candidate in enumerate(pred_record.get("ranked_files", []), start=1):
        if candidate.get("file") in gt_files:
            ranks.append(int(candidate.get("rank", index)))
    return min(ranks) if ranks else None


def build_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    bug_cache: dict[Path, dict[str, dict[str, Any]]] = {}
    pred_cache: dict[Path, dict[str, dict[str, Any]]] = {}

    bug_records: list[dict[str, Any]] = []
    pred_records: list[dict[str, Any]] = []
    manifest_cases: list[dict[str, Any]] = []

    for case in CASES:
        bug_cache.setdefault(case.bug_file, load_by_bug_id(case.bug_file))
        pred_cache.setdefault(case.pred_file, load_by_bug_id(case.pred_file))

        try:
            bug_record = bug_cache[case.bug_file][case.bug_id]
        except KeyError as exc:
            raise KeyError(f"{case.bug_id} missing from {case.bug_file}") from exc

        try:
            pred_record = pred_cache[case.pred_file][case.bug_id]
        except KeyError as exc:
            raise KeyError(f"{case.bug_id} missing from {case.pred_file}") from exc

        rank = best_ground_truth_rank(bug_record, pred_record)
        bug_records.append(bug_record)
        pred_records.append(pred_record)
        manifest_cases.append(
            {
                "bug_id": case.bug_id,
                "bug_file": str(case.bug_file),
                "pred_file": str(case.pred_file),
                "category": case.category,
                "rationale": case.rationale,
                "ground_truth_files": bug_record.get("ground_truth", {}).get("files", []),
                "baseline_best_gt_rank": rank,
                "baseline_gt_in_top50": rank is not None and rank <= 50,
            }
        )

    manifest = {
        "benchmark": "rq5_defects4j_mini_10",
        "date": "2026-06-03",
        "interpretation": "diagnostic mini-benchmark for RQ5, not a main held-out split",
        "num_cases": len(CASES),
        "cases": manifest_cases,
    }
    return bug_records, pred_records, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the frozen RQ5 Defects4J diagnostic mini-benchmark."
    )
    parser.add_argument(
        "--out-bugs",
        type=Path,
        default=ROOT / "data/defects4j/rq5_defects4j_mini_10.jsonl",
        help="Output bug JSONL path.",
    )
    parser.add_argument(
        "--out-pred",
        type=Path,
        default=ROOT / "outputs/rq5_defects4j_mini_10_baseline_top50.jsonl",
        help="Output baseline prediction JSONL path.",
    )
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=ROOT / "outputs/rq5_defects4j_mini_10_manifest.json",
        help="Output manifest JSON path.",
    )
    args = parser.parse_args()

    bug_records, pred_records, manifest = build_records()

    write_jsonl(args.out_bugs, bug_records)
    write_jsonl(args.out_pred, pred_records)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {len(bug_records)} bugs to {args.out_bugs}")
    print(f"wrote {len(pred_records)} predictions to {args.out_pred}")
    print(f"wrote manifest to {args.manifest_out}")
    for case in manifest["cases"]:
        print(
            f"{case['bug_id']}: baseline_gt_rank={case['baseline_best_gt_rank']} "
            f"category={case['category']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
