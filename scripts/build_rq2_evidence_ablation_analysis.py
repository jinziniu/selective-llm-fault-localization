#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.evaluation import evaluate_file_level
from fl_localizer.io_utils import read_jsonl, write_jsonl


OUT_DIR = ROOT / "outputs" / "rq2_evidence_ablation_2026_07_20"
DOC_PATH = ROOT / "docs" / "rq2_evidence_ablation_2026-07-20.md"

SPLITS = [
    {
        "name": "closure_61_80",
        "bugs": ROOT / "data" / "defects4j" / "closure_heldout_61_80.jsonl",
        "baseline": ROOT
        / "outputs"
        / "closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
        "selection": ROOT / "outputs" / "closure_heldout_61_80_selector_closure_cost_control_v3.json",
    },
    {
        "name": "closure_81_100",
        "bugs": ROOT / "data" / "defects4j" / "closure_heldout_81_100.jsonl",
        "baseline": ROOT
        / "outputs"
        / "closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
        "selection": ROOT / "outputs" / "closure_heldout_81_100_selector_closure_cost_control_v3.json",
    },
]

VARIANTS = [
    {
        "name": "metadata_only",
        "label": "Metadata only",
        "detail": "Candidate paths, ranks/scores, packages, class names, and method names; no retrieval reasons, no source snippets, no triggering-test source context.",
        "rerank": {
            "closure_61_80": OUT_DIR / "closure_61_80_metadata_only_deepseek.jsonl",
            "closure_81_100": OUT_DIR / "closure_81_100_metadata_only_deepseek.jsonl",
        },
    },
    {
        "name": "metadata_retrieval",
        "label": "Metadata + retrieval reasons",
        "detail": "Metadata-only candidate package plus retrieval evidence fields and deterministic retrieval reasons; no source snippets or triggering-test source context.",
        "rerank": {
            "closure_61_80": OUT_DIR / "closure_61_80_metadata_retrieval_deepseek.jsonl",
            "closure_81_100": OUT_DIR / "closure_81_100_metadata_retrieval_deepseek.jsonl",
        },
    },
    {
        "name": "full_evidence",
        "label": "Full evidence package",
        "detail": "Current thesis evidence package: retrieval evidence, selected source snippets, and triggering-test source context.",
        "rerank": {
            "closure_61_80": OUT_DIR / "closure_61_80_full_evidence_deepseek.jsonl",
            "closure_81_100": OUT_DIR / "closure_81_100_full_evidence_deepseek.jsonl",
        },
    },
]


def load_selected(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = payload.get("selected_bug_ids", [])
    if not isinstance(selected, list):
        raise ValueError(f"{path} does not contain selected_bug_ids")
    return {str(item) for item in selected}


def truncate_record(record: dict[str, Any], top_output: int = 10) -> dict[str, Any]:
    updated = dict(record)
    ranked = updated.get("ranked_files", [])
    if isinstance(ranked, list):
        updated["ranked_files"] = ranked[:top_output]
    return updated


def merge_split(
    *,
    baseline_path: Path,
    rerank_path: Path,
    selection_path: Path,
) -> list[dict[str, Any]]:
    selected = load_selected(selection_path)
    rerank_by_bug = {str(row["bug_id"]): row for row in read_jsonl(rerank_path)}
    missing = selected - set(rerank_by_bug)
    if missing:
        raise ValueError(f"{rerank_path} is missing selected bug ids: {sorted(missing)}")

    merged: list[dict[str, Any]] = []
    for baseline in read_jsonl(baseline_path):
        bug_id = str(baseline["bug_id"])
        if bug_id in selected:
            merged.append(truncate_record(rerank_by_bug[bug_id]))
        else:
            record = truncate_record(baseline)
            record["method"] = str(record.get("method", "baseline")) + "+selective-no-llm"
            merged.append(record)
    return merged


def usage_summary(paths: list[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(read_jsonl(path))
    total_tokens = sum(int(row.get("token_usage", {}).get("total_tokens", 0)) for row in rows)
    prompt_tokens = sum(int(row.get("token_usage", {}).get("prompt_tokens", 0)) for row in rows)
    completion_tokens = sum(
        int(row.get("token_usage", {}).get("completion_tokens", 0)) for row in rows
    )
    duration = sum(float(row.get("llm_duration_seconds", 0.0)) for row in rows)
    return {
        "model_requests": len(rows),
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "duration_seconds": round(duration, 3),
        "tokens_per_selected_case": round(total_tokens / len(rows), 1) if rows else 0.0,
        "seconds_per_selected_case": round(duration / len(rows), 1) if rows else 0.0,
    }


def rank_map(evaluation: dict[str, Any]) -> dict[str, int | None]:
    return {row["bug_id"]: row["correct_rank"] for row in evaluation["per_bug"]}


def rr_at_10(rank: int | None) -> float:
    if rank is None or rank > 10:
        return 0.0
    return 1.0 / rank


def format_metric(value: float) -> str:
    return f"{value:.4f}"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bug_records: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for split in SPLITS:
        bug_records.extend(read_jsonl(split["bugs"]))
        baseline_records.extend(truncate_record(row) for row in read_jsonl(split["baseline"]))
        selected_ids.update(load_selected(split["selection"]))

    combined_bugs = OUT_DIR / "closure_61_100_selected_ablation_bugs.jsonl"
    combined_baseline = OUT_DIR / "closure_61_100_retrieval_top10_baseline.jsonl"
    write_jsonl(combined_bugs, bug_records)
    write_jsonl(combined_baseline, baseline_records)

    baseline_eval = evaluate_file_level(bug_records, baseline_records, ks=(1, 3, 5, 10))
    baseline_eval_path = OUT_DIR / "closure_61_100_retrieval_top10_baseline_eval.json"
    baseline_eval_path.write_text(json.dumps(baseline_eval, indent=2, sort_keys=True) + "\n")

    selected_bug_records = [row for row in bug_records if str(row["bug_id"]) in selected_ids]
    selected_baseline_records = [
        row for row in baseline_records if str(row["bug_id"]) in selected_ids
    ]
    selected_baseline_eval = evaluate_file_level(
        selected_bug_records, selected_baseline_records, ks=(1, 3, 5, 10)
    )
    baseline_ranks = rank_map(baseline_eval)
    selected_baseline_ranks = rank_map(selected_baseline_eval)

    aggregate_rows: list[dict[str, Any]] = [
        {
            "variant": "retrieval_baseline",
            "label": "Retrieval baseline",
            "scope": "all_38",
            "n": baseline_eval["summary"]["bugs"],
            "model_requests": 0,
            "total_tokens": 0,
            "duration_seconds": 0.0,
            "top_1": format_metric(baseline_eval["summary"]["top_1_accuracy"]),
            "top_3": format_metric(baseline_eval["summary"]["top_3_accuracy"]),
            "top_5": format_metric(baseline_eval["summary"]["top_5_accuracy"]),
            "top_10": format_metric(baseline_eval["summary"]["top_10_accuracy"]),
            "mrr_at_10": format_metric(baseline_eval["summary"]["mrr"]),
        },
        {
            "variant": "retrieval_baseline",
            "label": "Retrieval baseline",
            "scope": "selected_11",
            "n": selected_baseline_eval["summary"]["bugs"],
            "model_requests": 0,
            "total_tokens": 0,
            "duration_seconds": 0.0,
            "top_1": format_metric(selected_baseline_eval["summary"]["top_1_accuracy"]),
            "top_3": format_metric(selected_baseline_eval["summary"]["top_3_accuracy"]),
            "top_5": format_metric(selected_baseline_eval["summary"]["top_5_accuracy"]),
            "top_10": format_metric(selected_baseline_eval["summary"]["top_10_accuracy"]),
            "mrr_at_10": format_metric(selected_baseline_eval["summary"]["mrr"]),
        },
    ]
    usage_rows: list[dict[str, Any]] = []
    selected_rank_rows: list[dict[str, Any]] = []
    variant_summaries: dict[str, Any] = {
        "selected_bug_ids": sorted(selected_ids),
        "baseline": {
            "all_38": baseline_eval["summary"],
            "selected_11": selected_baseline_eval["summary"],
        },
        "variants": {},
    }
    artifact_paths = [combined_bugs, combined_baseline, baseline_eval_path]

    selected_rank_by_variant: dict[str, dict[str, int | None]] = {}
    for variant in VARIANTS:
        merged: list[dict[str, Any]] = []
        rerank_paths: list[Path] = []
        for split in SPLITS:
            rerank_path = variant["rerank"][split["name"]]
            rerank_paths.append(rerank_path)
            merged.extend(
                merge_split(
                    baseline_path=split["baseline"],
                    rerank_path=rerank_path,
                    selection_path=split["selection"],
                )
            )

        merged_path = OUT_DIR / f"closure_61_100_{variant['name']}_merged.jsonl"
        eval_path = OUT_DIR / f"closure_61_100_{variant['name']}_merged_eval.json"
        selected_eval_path = OUT_DIR / f"closure_61_100_{variant['name']}_selected_eval.json"
        write_jsonl(merged_path, merged)
        evaluation = evaluate_file_level(bug_records, merged, ks=(1, 3, 5, 10))
        eval_path.write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n")

        selected_records = [row for row in merged if str(row["bug_id"]) in selected_ids]
        selected_eval = evaluate_file_level(selected_bug_records, selected_records, ks=(1, 3, 5, 10))
        selected_eval_path.write_text(json.dumps(selected_eval, indent=2, sort_keys=True) + "\n")

        usage = usage_summary(rerank_paths)
        usage_row = {"variant": variant["name"], "label": variant["label"], **usage}
        usage_rows.append(usage_row)
        aggregate_rows.append(
            {
                "variant": variant["name"],
                "label": variant["label"],
                "scope": "all_38",
                "n": evaluation["summary"]["bugs"],
                "model_requests": usage["model_requests"],
                "total_tokens": usage["total_tokens"],
                "duration_seconds": usage["duration_seconds"],
                "top_1": format_metric(evaluation["summary"]["top_1_accuracy"]),
                "top_3": format_metric(evaluation["summary"]["top_3_accuracy"]),
                "top_5": format_metric(evaluation["summary"]["top_5_accuracy"]),
                "top_10": format_metric(evaluation["summary"]["top_10_accuracy"]),
                "mrr_at_10": format_metric(evaluation["summary"]["mrr"]),
            }
        )
        aggregate_rows.append(
            {
                "variant": variant["name"],
                "label": variant["label"],
                "scope": "selected_11",
                "n": selected_eval["summary"]["bugs"],
                "model_requests": usage["model_requests"],
                "total_tokens": usage["total_tokens"],
                "duration_seconds": usage["duration_seconds"],
                "top_1": format_metric(selected_eval["summary"]["top_1_accuracy"]),
                "top_3": format_metric(selected_eval["summary"]["top_3_accuracy"]),
                "top_5": format_metric(selected_eval["summary"]["top_5_accuracy"]),
                "top_10": format_metric(selected_eval["summary"]["top_10_accuracy"]),
                "mrr_at_10": format_metric(selected_eval["summary"]["mrr"]),
            }
        )

        selected_rank_by_variant[variant["name"]] = rank_map(selected_eval)
        variant_summaries["variants"][variant["name"]] = {
            "label": variant["label"],
            "detail": variant["detail"],
            "all_38": evaluation["summary"],
            "selected_11": selected_eval["summary"],
            "usage": usage,
            "rerank_paths": [str(path.relative_to(ROOT)) for path in rerank_paths],
            "merged_path": str(merged_path.relative_to(ROOT)),
            "eval_path": str(eval_path.relative_to(ROOT)),
            "selected_eval_path": str(selected_eval_path.relative_to(ROOT)),
        }
        artifact_paths.extend([merged_path, eval_path, selected_eval_path, *rerank_paths])

    for bug_id in sorted(selected_ids):
        row: dict[str, Any] = {
            "bug_id": bug_id,
            "baseline_rank": selected_baseline_ranks.get(bug_id),
            "baseline_rr_at_10": format_metric(rr_at_10(selected_baseline_ranks.get(bug_id))),
        }
        for variant in VARIANTS:
            rank = selected_rank_by_variant[variant["name"]].get(bug_id)
            base_rank = selected_baseline_ranks.get(bug_id)
            row[f"{variant['name']}_rank"] = rank
            row[f"{variant['name']}_rr_at_10"] = format_metric(rr_at_10(rank))
            row[f"{variant['name']}_delta_rr_at_10"] = format_metric(
                rr_at_10(rank) - rr_at_10(base_rank)
            )
        selected_rank_rows.append(row)

    aggregate_csv = OUT_DIR / "evidence_ablation_summary.csv"
    usage_csv = OUT_DIR / "evidence_ablation_usage.csv"
    ranks_csv = OUT_DIR / "evidence_ablation_selected_case_ranks.csv"
    summary_json = OUT_DIR / "evidence_ablation_summary.json"
    checksums_csv = OUT_DIR / "evidence_ablation_artifact_checksums.csv"
    write_csv(aggregate_csv, aggregate_rows)
    write_csv(usage_csv, usage_rows)
    write_csv(ranks_csv, selected_rank_rows)
    summary_json.write_text(json.dumps(variant_summaries, indent=2, sort_keys=True) + "\n")
    artifact_paths.extend([aggregate_csv, usage_csv, ranks_csv, summary_json])

    checksum_rows = [
        {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifact_paths
        if path.exists()
    ]
    write_csv(checksums_csv, checksum_rows)

    lines = [
        "# RQ2 Evidence-Quality Ablation (2026-07-20)",
        "",
        "This report analyzes a small controlled evidence-package ablation on the 11 Closure selected cases from the frozen `61..100` held-out aggregate. The retrieval candidate pool, selected bug IDs, model alias, Top-10 evaluation boundary, and selector are held fixed. Only the candidate evidence shown to the one-shot reranker changes.",
        "",
        "## Configurations",
        "",
    ]
    for variant in VARIANTS:
        lines.append(f"- **{variant['label']}**: {variant['detail']}")
    lines.extend(
        [
            "",
            "## Aggregate Metrics",
            "",
            "| Variant | Scope | N | Requests | Tokens | Seconds | Top-1 | Top-3 | Top-5 | Top-10 | MRR@10 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in aggregate_rows:
        lines.append(
            "| {label} | {scope} | {n} | {model_requests} | {total_tokens} | {duration_seconds} | {top_1} | {top_3} | {top_5} | {top_10} | {mrr_at_10} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Selected-Case Rank Changes",
            "",
            f"Per-bug selected-case ranks are saved in `{ranks_csv.relative_to(ROOT)}`. These rows compare each evidence configuration against the retrieval rank for the same selected bug.",
            "",
            "## Interpretation Boundary",
            "",
            "This is a small selected-case ablation, not a dataset-wide evidence-quality experiment. It supports a more concrete RQ2 statement about candidate evidence on Closure selected cases, but it should not be generalized to all datasets or all evidence designs.",
            "",
            "## Artifacts",
            "",
            f"- Summary CSV: `{aggregate_csv.relative_to(ROOT)}`",
            f"- Usage CSV: `{usage_csv.relative_to(ROOT)}`",
            f"- Selected-case ranks CSV: `{ranks_csv.relative_to(ROOT)}`",
            f"- Summary JSON: `{summary_json.relative_to(ROOT)}`",
            f"- Checksums CSV: `{checksums_csv.relative_to(ROOT)}`",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {summary_json.relative_to(ROOT)}")
    print(f"Wrote {DOC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
