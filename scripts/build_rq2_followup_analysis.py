#!/usr/bin/env python3
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import statistics
import subprocess
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fl_localizer.io_utils import read_jsonl  # noqa: E402
from statistical_analysis_common import (  # noqa: E402
    DEFAULT_KS,
    MAIN_RANK_DEPTH,
    by_bug,
    evaluate_method,
    first_correct_rank,
    load_bug_records,
    load_json,
    load_prediction_records,
    load_selected_bug_ids,
    rel,
    summarize_per_bug,
    write_csv,
    write_json,
)


OUT_DIR = ROOT / "outputs" / "rq2_followup_2026_06_26"
DOC_PATH = ROOT / "docs" / "rq2_followup_diagnostics_2026-06-26.md"


def dataset_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "closure_61_100",
            "display_name": "Closure-61..100",
            "bugs": [
                "data/defects4j/closure_heldout_61_80.jsonl",
                "data/defects4j/closure_heldout_81_100.jsonl",
            ],
            "baseline": [
                "outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
                "outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
            ],
            "selective_final": [
                "outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                "outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
            ],
            "selective_rerank": [
                "outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                "outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
            ],
            "selection": [
                "outputs/closure_heldout_61_80_selector_closure_cost_control_v3.json",
                "outputs/closure_heldout_81_100_selector_closure_cost_control_v3.json",
            ],
            "full_rerank": [
                "outputs/rq2_followup_2026_06_26/closure_61_80_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl",
                "outputs/rq2_followup_2026_06_26/closure_81_100_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl",
            ],
        },
        {
            "name": "math_fresh_21_40",
            "display_name": "Math-21..40",
            "bugs": ["data/defects4j/math_fresh_21_40.jsonl"],
            "baseline": ["outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl"],
            "selective_final": [
                "outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl"
            ],
            "selective_rerank": [
                "outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl"
            ],
            "selection": ["outputs/math_fresh_21_40_selector_generic_t102_h7_patterns.json"],
            "full_rerank": [
                "outputs/rq2_followup_2026_06_26/math_21_40_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl"
            ],
        },
        {
            "name": "aboutwork_committed_60",
            "display_name": "AboutWork-60",
            "bugs": ["data/aboutwork/aboutwork_committed_60.jsonl"],
            "baseline": ["outputs/aboutwork_committed_60_bm25_top50.jsonl"],
            "selective_final": ["outputs/aboutwork_committed_60_bm25_plus_deepseek_selector_v3.jsonl"],
            "selective_rerank": ["outputs/aboutwork_committed_60_rerank_deepseek_selector_v3.jsonl"],
            "selection": ["outputs/aboutwork60_selector_v3.json"],
            "full_rerank": [
                "outputs/rq2_followup_2026_06_26/aboutwork_60_full_rerank_all_deepseek_selector_v3_legacy_evidence_top50.jsonl"
            ],
            "notes": "AboutWork full rerank uses the 2026-06-08 selector_v3 evidence configuration: retrieval evidence enabled, triggering-test context disabled, max_snippet_lines=18.",
        },
        {
            "name": "easy_finance_clean63",
            "display_name": "Easy Finance clean63",
            "bugs": ["data/easy_finance/easy_finance_committed_clean63.jsonl"],
            "baseline": ["outputs/easy_finance_committed_clean63_bm25_prod_top50.jsonl"],
            "selective_final": [
                "outputs/easy_finance_committed_clean63_bm25_prod_plus_deepseek_selector_v1_ui_evidence_v2.jsonl"
            ],
            "selective_rerank": [
                "outputs/easy_finance_committed_clean63_rerank_deepseek_prod_selector_v1_ui_evidence_v2.jsonl"
            ],
            "selection": ["outputs/easy_finance_clean63_prod_selector_v1.json"],
        },
        {
            "name": "mockito_fresh_21_30",
            "display_name": "Mockito-21..30",
            "bugs": ["data/defects4j/mockito_fresh_21_30.jsonl"],
            "baseline": ["outputs/mockito_fresh_21_30_hybrid_focused_direct_top50.jsonl"],
            "selection": ["outputs/mockito_fresh_21_30_tight_selector.json"],
        },
        {
            "name": "mockito_fresh_31_38",
            "display_name": "Mockito-31..38",
            "bugs": ["data/defects4j/mockito_fresh_31_38.jsonl"],
            "baseline": ["outputs/mockito_fresh_31_38_hybrid_focused_direct_top50.jsonl"],
            "selective_final": [
                "outputs/mockito_fresh_31_38_merged_deepseek_cost_control_v2_s6_ctx12000_top50.jsonl"
            ],
            "selective_rerank": [
                "outputs/mockito_fresh_31_38_rerank_deepseek_cost_control_v2_s6_ctx12000_top50.jsonl"
            ],
            "selection": ["outputs/mockito_fresh_31_38_tight_cost_control_v2_selector.json"],
        },
    ]


def file_exists(paths: list[str]) -> bool:
    return all(rel(path).exists() for path in paths)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv_local(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "NA" if row.get(field) is None else row.get(field, "") for field in fields})


def method_summary(spec: dict[str, Any], name: str, paths: list[str]) -> dict[str, Any]:
    evaluated = evaluate_method(
        {"name": spec["name"], "display_name": spec["display_name"], "bugs": spec["bugs"]},
        {"name": name, "display_name": name, "paths": paths},
        rank_depth=MAIN_RANK_DEPTH,
    )
    return {"evaluation": evaluated, "summary": summarize_per_bug(evaluated["per_bug"], ks=DEFAULT_KS)}


def usage_summary(paths: list[str]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in paths:
        if not rel(path).exists():
            continue
        records.extend(read_jsonl(rel(path)))
    total_tokens = 0
    total_runtime = 0.0
    invalid_json_count = 0
    for record in records:
        usage = record.get("token_usage")
        if isinstance(usage, dict):
            total_tokens += int(usage.get("total_tokens") or 0)
        total_runtime += float(record.get("llm_duration_seconds") or 0.0)
        if record.get("parse_error") or record.get("invalid_json"):
            invalid_json_count += 1
    calls = len(records)
    return {
        "llm_calls": calls,
        "tokens": total_tokens,
        "avg_tokens_per_case": total_tokens / calls if calls else 0.0,
        "runtime_seconds": total_runtime,
        "avg_runtime_per_case": total_runtime / calls if calls else 0.0,
        "invalid_json_count": invalid_json_count,
    }


def metric_value(summary: dict[str, Any], metric: str) -> float:
    if metric in {"MRR", "MRR@10"}:
        return float(summary["mrr"])
    k = metric.replace("Top-", "")
    return float(summary[f"top_{k}_accuracy"])


def build_table_a(specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_a1: list[dict[str, Any]] = []
    table_a2: list[dict[str, Any]] = []
    metrics = ["Top-1", "Top-3", "Top-5", "Top-10", "MRR@10"]
    for spec in specs:
        if not file_exists(spec["baseline"]) or not file_exists(spec.get("selective_final", [])):
            continue
        full_paths = spec.get("full_rerank", [])
        if not full_paths or not file_exists(full_paths):
            continue

        retrieval = method_summary(spec, "retrieval", spec["baseline"])
        selective = method_summary(spec, "selective", spec["selective_final"])
        full = method_summary(spec, "full_rerank", full_paths)
        selective_usage = usage_summary(spec.get("selective_rerank", []))
        full_usage = usage_summary(full_paths)
        n = int(retrieval["summary"]["n"])
        rows = [
            ("Retrieval only", retrieval, {"llm_calls": 0, "tokens": 0, "avg_tokens_per_case": 0.0, "runtime_seconds": 0.0, "avg_runtime_per_case": 0.0}, 0.0),
            ("Full one-shot rerank-all", full, full_usage, 1.0),
            (
                "Selective one-shot rerank",
                selective,
                selective_usage,
                selective_usage["llm_calls"] / n if n else 0.0,
            ),
        ]
        for setting, evaluated, usage, selected_fraction in rows:
            summary = evaluated["summary"]
            table_a1.append(
                {
                    "dataset": spec["display_name"],
                    "setting": setting,
                    "n": n,
                    "llm_calls": usage["llm_calls"],
                    "selected_fraction": selected_fraction,
                    "tokens": usage["tokens"],
                    "avg_tokens_per_case": usage["avg_tokens_per_case"],
                    "runtime_seconds": usage["runtime_seconds"],
                    "avg_runtime_per_case": usage["avg_runtime_per_case"],
                    "top_1": summary["top_1_accuracy"],
                    "top_3": summary["top_3_accuracy"],
                    "top_5": summary["top_5_accuracy"],
                    "top_10": summary["top_10_accuracy"],
                    "mrr": summary["mrr"],
                }
            )
        for metric in metrics:
            retrieval_value = metric_value(retrieval["summary"], metric)
            full_value = metric_value(full["summary"], metric)
            selective_value = metric_value(selective["summary"], metric)
            full_gain = full_value - retrieval_value
            selective_gain = selective_value - retrieval_value
            table_a2.append(
                {
                    "dataset": spec["display_name"],
                    "metric": metric,
                    "retrieval": retrieval_value,
                    "full_rerank": full_value,
                    "selective_rerank": selective_value,
                    "full_gain_over_retrieval": full_gain,
                    "selective_gain_over_retrieval": selective_gain,
                    "selective_retention_of_full_gain": selective_gain / full_gain if full_gain > 0 else None,
                    "call_saving_vs_full": 1.0 - (selective_usage["llm_calls"] / full_usage["llm_calls"]) if full_usage["llm_calls"] else None,
                    "token_saving_vs_full": 1.0 - (selective_usage["tokens"] / full_usage["tokens"]) if full_usage["tokens"] else None,
                    "runtime_saving_vs_full": 1.0 - (selective_usage["runtime_seconds"] / full_usage["runtime_seconds"]) if full_usage["runtime_seconds"] else None,
                }
            )
    return table_a1, table_a2


def build_table_b(specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []
    for spec in specs:
        if not file_exists(spec["bugs"]) or not file_exists(spec["baseline"]) or not file_exists(spec.get("selection", [])):
            continue
        selected = load_selected_bug_ids(spec["selection"])
        baseline = method_summary(spec, "baseline", spec["baseline"])
        baseline_by_bug = by_bug(baseline["evaluation"]["per_bug"])
        bug_ids = sorted(baseline_by_bug)
        baseline_failures: dict[int, list[str]] = {}
        selected_failures: dict[int, list[str]] = {}
        for k in (1, 5, 10):
            failures = [
                bug_id
                for bug_id in bug_ids
                if baseline_by_bug[bug_id]["correct_rank"] is None
                or int(baseline_by_bug[bug_id]["correct_rank"]) > k
            ]
            baseline_failures[k] = failures
            selected_failures[k] = [bug_id for bug_id in failures if bug_id in selected]
        coverage_rows.append(
            {
                "dataset": spec["display_name"],
                "n": len(bug_ids),
                "total_selected": len(selected & set(bug_ids)),
                "selected_fraction": len(selected & set(bug_ids)) / len(bug_ids) if bug_ids else 0.0,
                "baseline_top_1_failures": len(baseline_failures[1]),
                "baseline_top_5_failures": len(baseline_failures[5]),
                "baseline_top_10_failures": len(baseline_failures[10]),
                "selected_among_top_5_failures": len(selected_failures[5]),
                "selected_among_top_10_failures": len(selected_failures[10]),
                "selector_recall_on_top_5_failures": len(selected_failures[5]) / len(baseline_failures[5]) if baseline_failures[5] else None,
                "selector_recall_on_top_10_failures": len(selected_failures[10]) / len(baseline_failures[10]) if baseline_failures[10] else None,
                "unselected_top_5_failures_remaining": len(set(baseline_failures[5]) - selected),
                "unselected_top_10_failures_remaining": len(set(baseline_failures[10]) - selected),
            }
        )

        if not spec.get("selective_final") or not file_exists(spec["selective_final"]):
            continue
        final = method_summary(spec, "final", spec["selective_final"])
        final_by_bug = by_bug(final["evaluation"]["per_bug"])
        selected_ids = sorted(selected & set(baseline_by_bug) & set(final_by_bug))
        deltas: list[float] = []
        improved = degraded = unchanged = 0
        top5_improved = top5_degraded = top10_improved = top10_degraded = 0
        notes: list[str] = []
        for bug_id in selected_ids:
            base_rr = float(baseline_by_bug[bug_id]["rr"])
            final_rr = float(final_by_bug[bug_id]["rr"])
            delta = final_rr - base_rr
            deltas.append(delta)
            if delta > 0:
                improved += 1
            elif delta < 0:
                degraded += 1
                notes.append(f"{bug_id}:RR {base_rr:.4f}->{final_rr:.4f}")
            else:
                unchanged += 1
            for k, improved_counter, degraded_counter in [
                (5, "top5", "top5"),
                (10, "top10", "top10"),
            ]:
                base_hit = baseline_by_bug[bug_id]["correct_rank"] is not None and int(baseline_by_bug[bug_id]["correct_rank"]) <= k
                final_hit = final_by_bug[bug_id]["correct_rank"] is not None and int(final_by_bug[bug_id]["correct_rank"]) <= k
                if not base_hit and final_hit:
                    if k == 5:
                        top5_improved += 1
                    else:
                        top10_improved += 1
                elif base_hit and not final_hit:
                    if k == 5:
                        top5_degraded += 1
                    else:
                        top10_degraded += 1
        effect_rows.append(
            {
                "dataset": spec["display_name"],
                "selected_n": len(selected_ids),
                "improved_cases": improved,
                "degraded_cases": degraded,
                "unchanged_cases": unchanged,
                "mean_drr": statistics.mean(deltas) if deltas else 0.0,
                "positive_rr_changes": improved,
                "negative_rr_changes": degraded,
                "zero_rr_changes": unchanged,
                "top_5_improved_cases": top5_improved,
                "top_5_degraded_cases": top5_degraded,
                "top_10_improved_cases": top10_improved,
                "top_10_degraded_cases": top10_degraded,
                "notes": "; ".join(notes[:8]),
            }
        )
    return coverage_rows, effect_rows


def variance_specs() -> list[dict[str, Any]]:
    return [
        {
            "run_id": "original",
            "paths": [
                "outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                "outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
            ],
            "rerank_paths": [
                "outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                "outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
            ],
            "notes": "original reported run",
        },
        *[
            {
                "run_id": f"run{i}",
                "paths": [
                    f"outputs/rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_merged.jsonl",
                    f"outputs/rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_merged.jsonl",
                ],
                "rerank_paths": [
                    f"outputs/rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_deepseek.jsonl",
                    f"outputs/rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_deepseek.jsonl",
                ],
                "notes": "follow-up repeated run",
            }
            for i in range(1, 6)
        ],
    ]


def build_variance_tables() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    spec = {
        "name": "closure_61_100",
        "display_name": "Closure-61..100",
        "bugs": [
            "data/defects4j/closure_heldout_61_80.jsonl",
            "data/defects4j/closure_heldout_81_100.jsonl",
        ],
    }
    per_run: list[dict[str, Any]] = []
    for run in variance_specs():
        if not file_exists(run["paths"]):
            continue
        evaluated = method_summary(spec, run["run_id"], run["paths"])
        summary = evaluated["summary"]
        usage = usage_summary(run["rerank_paths"])
        per_run.append(
            {
                "run_id": run["run_id"],
                "llm_calls": usage["llm_calls"],
                "tokens": usage["tokens"],
                "runtime": usage["runtime_seconds"],
                "top_1": summary["top_1_accuracy"],
                "top_3": summary["top_3_accuracy"],
                "top_5": summary["top_5_accuracy"],
                "top_10": summary["top_10_accuracy"],
                "mrr": summary["mrr"],
                "invalid_json_count": usage["invalid_json_count"],
                "notes": run["notes"],
            }
        )
    followup_runs = [row for row in per_run if row["run_id"] != "original"]
    source = followup_runs if followup_runs else per_run
    aggregate: list[dict[str, Any]] = []
    if source:
        row: dict[str, Any] = {
            "dataset": "Closure-61..100",
            "setting": "Selective rerank repeated runs" if followup_runs else "Selective rerank original only",
            "runs": len(source),
        }
        for metric in ("top_1", "top_3", "top_5", "top_10", "mrr"):
            values = [float(item[metric]) for item in source]
            row[f"{metric}_mean"] = statistics.mean(values)
            row[f"{metric}_sd"] = statistics.stdev(values) if len(values) > 1 else 0.0
            row[f"{metric}_min"] = min(values)
            row[f"{metric}_max"] = max(values)
        for metric in ("invalid_json_count", "tokens", "runtime"):
            values = [float(item[metric]) for item in source]
            row[f"{metric}_mean"] = statistics.mean(values)
        aggregate.append(row)
    return aggregate, per_run


def build_checksums() -> list[dict[str, Any]]:
    roots = [
        ROOT / "outputs" / "rq2_followup_2026_06_26",
        ROOT / "outputs" / "prompts_rq2_followup_2026_06_26",
    ]
    rows: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return rows


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable:not_a_git_repository"


def aggregate_sha256(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for raw_path in sorted(paths):
        path = rel(raw_path)
        if not path.exists():
            continue
        files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file()) if path.is_dir() else [path]
        for file_path in files:
            digest.update(str(file_path.relative_to(ROOT)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(sha256(file_path).encode("ascii"))
            digest.update(b"\0")
    return digest.hexdigest()


def artifact_times(paths: list[str], runtime_seconds: float) -> tuple[str, str]:
    mtimes = [rel(path).stat().st_mtime for path in paths if rel(path).exists()]
    if not mtimes:
        return "NA", "NA"
    completed = datetime.fromtimestamp(max(mtimes), tz=timezone.utc)
    started = completed - timedelta(seconds=runtime_seconds)
    return started.isoformat(), completed.isoformat()


def run_manifest_rows() -> list[dict[str, Any]]:
    git_hash = git_commit_hash()

    def row(
        *,
        run_id: str,
        dataset: str,
        setting: str,
        command_line: str,
        output_paths: list[str],
        prompt_dirs: list[str],
        config: str,
        access_date: str = "2026-06-26",
        notes: str = "",
    ) -> dict[str, Any]:
        usage = usage_summary(output_paths)
        started_at, completed_at = artifact_times(output_paths, usage["runtime_seconds"])
        return {
            "run_id": run_id,
            "dataset": dataset,
            "setting": setting,
            "model_alias": "deepseek-v4-flash",
            "provider": "deepseek",
            "access_date": access_date,
            "temperature": 0.0,
            "response_format": "json_object",
            "config": config,
            "git_commit_hash": git_hash,
            "command_line": command_line,
            "output_paths": ";".join(output_paths),
            "prompt_dirs": ";".join(prompt_dirs),
            "started_at_utc": started_at,
            "completed_at_utc": completed_at,
            "llm_calls": usage["llm_calls"],
            "tokens": usage["tokens"],
            "runtime_seconds": usage["runtime_seconds"],
            "invalid_json_count": usage["invalid_json_count"],
            "evidence_package_checksum": aggregate_sha256(prompt_dirs),
            "output_checksum": aggregate_sha256(output_paths),
            "notes": notes,
        }

    common = (
        "--provider deepseek --model deepseek-v4-flash --top-candidates 50 "
        "--top-output 10 --include-retrieval-evidence"
    )
    current = "top50/top10, max_snippet_lines=12, retrieval evidence, triggering-test context up to 12000 chars"
    aboutwork_legacy = (
        "top50/top10, max_snippet_lines=18, retrieval evidence, no triggering-test context; "
        "matches the 2026-06-08 AboutWork selector_v3 selective run"
    )
    rows = [
        row(
            run_id="closure_full_61_80",
            dataset="Closure-61..80",
            setting="full one-shot rerank-all",
            command_line=(
                "python3 scripts/run_llm_rerank.py --bugs data/defects4j/closure_heldout_61_80.jsonl "
                "--bm25 outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl "
                "--out outputs/rq2_followup_2026_06_26/closure_61_80_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl "
                f"{common} --max-snippet-lines 12 --include-test-context --max-test-context-chars 12000 "
                "--prompt-dir outputs/prompts_rq2_followup_2026_06_26/closure_61_80_full_rerank_all_s12_ctx12000_top50"
            ),
            output_paths=[
                "outputs/rq2_followup_2026_06_26/closure_61_80_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_rq2_followup_2026_06_26/closure_61_80_full_rerank_all_s12_ctx12000_top50"
            ],
            config=current,
        ),
        row(
            run_id="closure_full_81_100",
            dataset="Closure-81..100",
            setting="full one-shot rerank-all",
            command_line=(
                "python3 scripts/run_llm_rerank.py --bugs data/defects4j/closure_heldout_81_100.jsonl "
                "--bm25 outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl "
                "--out outputs/rq2_followup_2026_06_26/closure_81_100_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl "
                f"{common} --max-snippet-lines 12 --include-test-context --max-test-context-chars 12000 "
                "--prompt-dir outputs/prompts_rq2_followup_2026_06_26/closure_81_100_full_rerank_all_s12_ctx12000_top50"
            ),
            output_paths=[
                "outputs/rq2_followup_2026_06_26/closure_81_100_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_rq2_followup_2026_06_26/closure_81_100_full_rerank_all_s12_ctx12000_top50"
            ],
            config=current,
        ),
        row(
            run_id="math_full_21_40",
            dataset="Math-21..40",
            setting="full one-shot rerank-all",
            command_line=(
                "python3 scripts/run_llm_rerank.py --bugs data/defects4j/math_fresh_21_40.jsonl "
                "--bm25 outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl "
                "--out outputs/rq2_followup_2026_06_26/math_21_40_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl "
                f"{common} --max-snippet-lines 12 --include-test-context --max-test-context-chars 12000 "
                "--prompt-dir outputs/prompts_rq2_followup_2026_06_26/math_21_40_full_rerank_all_s12_ctx12000_top50"
            ),
            output_paths=[
                "outputs/rq2_followup_2026_06_26/math_21_40_full_rerank_all_deepseek_s12_ctx12000_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_rq2_followup_2026_06_26/math_21_40_full_rerank_all_s12_ctx12000_top50"
            ],
            config=current,
        ),
        row(
            run_id="aboutwork_full_60",
            dataset="AboutWork-60",
            setting="full one-shot rerank-all",
            command_line=(
                "python3 scripts/run_llm_rerank.py --bugs data/aboutwork/aboutwork_committed_60.jsonl "
                "--bm25 outputs/aboutwork_committed_60_bm25_top50.jsonl "
                "--out outputs/rq2_followup_2026_06_26/aboutwork_60_full_rerank_all_deepseek_selector_v3_legacy_evidence_top50.jsonl "
                f"{common} --max-snippet-lines 18 "
                "--prompt-dir outputs/prompts_rq2_followup_2026_06_26/aboutwork_60_full_rerank_all_selector_v3_legacy_evidence_top50"
            ),
            output_paths=[
                "outputs/rq2_followup_2026_06_26/aboutwork_60_full_rerank_all_deepseek_selector_v3_legacy_evidence_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_rq2_followup_2026_06_26/aboutwork_60_full_rerank_all_selector_v3_legacy_evidence_top50"
            ],
            config=aboutwork_legacy,
            notes="Case-study diagnostic only; this preserves exact comparability with the existing AboutWork selective run.",
        ),
        row(
            run_id="closure_original_selective_61_80",
            dataset="Closure-61..80",
            setting="original selective one-shot rerank",
            command_line="recorded historical run; see docs/worklog.md and output prompt_path fields",
            output_paths=[
                "outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_closure_heldout_61_80_cost_control_v3_s12_ctx12000_top50"
            ],
            config=current,
            access_date="2026-06-02",
            notes="Original main selective run retained as main result.",
        ),
        row(
            run_id="closure_original_selective_81_100",
            dataset="Closure-81..100",
            setting="original selective one-shot rerank",
            command_line="recorded historical run; see docs/worklog.md and output prompt_path fields",
            output_paths=[
                "outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl"
            ],
            prompt_dirs=[
                "outputs/prompts_closure_heldout_81_100_cost_control_v3_s12_ctx12000_top50"
            ],
            config=current,
            access_date="2026-06-02",
            notes="Original main selective run retained as main result.",
        ),
    ]

    for i in range(1, 6):
        rows.append(
            row(
                run_id=f"closure_selective_variance_run{i}_61_80",
                dataset="Closure-61..80",
                setting="selective rerank repeated run",
                command_line=(
                    "python3 scripts/run_llm_rerank.py --bugs data/defects4j/closure_heldout_61_80.jsonl "
                    "--bm25 outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl "
                    f"--out outputs/rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_deepseek.jsonl "
                    f"{common} --max-snippet-lines 12 --bug-ids Closure-64,Closure-69,Closure-70,Closure-72,Closure-76,Closure-77 "
                    "--include-test-context --max-test-context-chars 12000 "
                    f"--prompt-dir outputs/prompts_rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_deepseek_s12_ctx12000_top50"
                ),
                output_paths=[
                    f"outputs/rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_deepseek.jsonl"
                ],
                prompt_dirs=[
                    f"outputs/prompts_rq2_followup_2026_06_26/closure_61_80_selective_variance_run{i}_deepseek_s12_ctx12000_top50"
                ],
                config=current,
                notes="Selector was not rerun; selected bug ids are from the frozen selector JSON.",
            )
        )
        rows.append(
            row(
                run_id=f"closure_selective_variance_run{i}_81_100",
                dataset="Closure-81..100",
                setting="selective rerank repeated run",
                command_line=(
                    "python3 scripts/run_llm_rerank.py --bugs data/defects4j/closure_heldout_81_100.jsonl "
                    "--bm25 outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl "
                    f"--out outputs/rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_deepseek.jsonl "
                    f"{common} --max-snippet-lines 12 --bug-ids Closure-82,Closure-83,Closure-91,Closure-95,Closure-100 "
                    "--include-test-context --max-test-context-chars 12000 "
                    f"--prompt-dir outputs/prompts_rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_deepseek_s12_ctx12000_top50"
                ),
                output_paths=[
                    f"outputs/rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_deepseek.jsonl"
                ],
                prompt_dirs=[
                    f"outputs/prompts_rq2_followup_2026_06_26/closure_81_100_selective_variance_run{i}_deepseek_s12_ctx12000_top50"
                ],
                config=current,
                notes="Selector was not rerun; selected bug ids are from the frozen selector JSON.",
            )
        )
    return rows


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


FIELD_LABELS = {
    "mrr": "mrr@10",
    "mrr_mean": "mrr@10_mean",
    "mrr_sd": "mrr@10_sd",
    "mrr_min": "mrr@10_min",
    "mrr_max": "mrr@10_max",
    "mean_drr": "mean_drr@10",
}


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_Not available yet._\n"
    lines = [
        "| " + " | ".join(FIELD_LABELS.get(field, field) for field in fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(field)) for field in fields) + " |")
    return "\n".join(lines) + "\n"


def write_report(
    table_a1: list[dict[str, Any]],
    table_a2: list[dict[str, Any]],
    table_b1: list[dict[str, Any]],
    table_b2: list[dict[str, Any]],
    table_c1: list[dict[str, Any]],
    table_c2: list[dict[str, Any]],
) -> None:
    content = [
        "# RQ2 Follow-up Diagnostics",
        "",
        "Date: 2026-06-26",
        "",
        "These experiments are diagnostic follow-ups for RQ2. They do not change the final three-RQ thesis structure, the frozen held-out protocol, selector rules, retrieval scoring, prompt template, candidate pool size, or evaluation scripts.",
        "",
        "## A1 Retrieval vs Full Rerank vs Selective Rerank",
        "",
        markdown_table(
            table_a1,
            [
                "dataset",
                "setting",
                "n",
                "llm_calls",
                "selected_fraction",
                "tokens",
                "avg_tokens_per_case",
                "runtime_seconds",
                "avg_runtime_per_case",
                "top_1",
                "top_3",
                "top_5",
                "top_10",
                "mrr",
            ],
        ),
        "## A2 Accuracy Retention and Cost Savings",
        "",
        markdown_table(
            table_a2,
            [
                "dataset",
                "metric",
                "retrieval",
                "full_rerank",
                "selective_rerank",
                "full_gain_over_retrieval",
                "selective_gain_over_retrieval",
                "selective_retention_of_full_gain",
                "call_saving_vs_full",
                "token_saving_vs_full",
                "runtime_saving_vs_full",
            ],
        ),
        "## B1 Selector Hard-case Coverage",
        "",
        markdown_table(
            table_b1,
            [
                "dataset",
                "n",
                "total_selected",
                "selected_fraction",
                "baseline_top_1_failures",
                "baseline_top_5_failures",
                "baseline_top_10_failures",
                "selected_among_top_5_failures",
                "selected_among_top_10_failures",
                "selector_recall_on_top_5_failures",
                "selector_recall_on_top_10_failures",
                "unselected_top_5_failures_remaining",
                "unselected_top_10_failures_remaining",
            ],
        ),
        "## B2 Selected-case Effect and Degradation",
        "",
        markdown_table(
            table_b2,
            [
                "dataset",
                "selected_n",
                "improved_cases",
                "degraded_cases",
                "unchanged_cases",
                "mean_drr",
                "positive_rr_changes",
                "negative_rr_changes",
                "zero_rr_changes",
                "top_5_improved_cases",
                "top_5_degraded_cases",
                "top_10_improved_cases",
                "top_10_degraded_cases",
                "notes",
            ],
        ),
        "## C1 Aggregate Variance",
        "",
        markdown_table(
            table_c1,
            [
                "dataset",
                "setting",
                "runs",
                "top_1_mean",
                "top_1_sd",
                "top_1_min",
                "top_1_max",
                "top_3_mean",
                "top_3_sd",
                "top_3_min",
                "top_3_max",
                "top_5_mean",
                "top_5_sd",
                "top_5_min",
                "top_5_max",
                "top_10_mean",
                "top_10_sd",
                "top_10_min",
                "top_10_max",
                "mrr_mean",
                "mrr_sd",
                "mrr_min",
                "mrr_max",
                "invalid_json_count_mean",
                "tokens_mean",
                "runtime_mean",
            ],
        ),
        "## C2 Per-run Results",
        "",
        markdown_table(
            table_c2,
            [
                "run_id",
                "llm_calls",
                "tokens",
                "runtime",
                "top_1",
                "top_3",
                "top_5",
                "top_10",
                "mrr",
                "invalid_json_count",
                "notes",
            ],
        ),
        "## Artifacts",
        "",
        "```text",
        "outputs/rq2_followup_2026_06_26/",
        "outputs/prompts_rq2_followup_2026_06_26/",
        "outputs/rq2_followup_2026_06_26/run_manifest.csv",
        "outputs/rq2_followup_2026_06_26/run_manifest.json",
        "```",
        "",
    ]
    DOC_PATH.write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = dataset_specs()
    table_a1, table_a2 = build_table_a(specs)
    table_b1, table_b2 = build_table_b(specs)
    table_c1, table_c2 = build_variance_tables()
    run_manifest = run_manifest_rows()
    checksums = build_checksums()

    write_json(OUT_DIR / "table_a1_retrieval_full_selective.json", table_a1)
    write_json(OUT_DIR / "table_a2_retention_cost_savings.json", table_a2)
    write_json(OUT_DIR / "table_b1_selector_hard_case_coverage.json", table_b1)
    write_json(OUT_DIR / "table_b2_selected_case_effect_degradation.json", table_b2)
    write_json(OUT_DIR / "table_c1_variance_aggregate.json", table_c1)
    write_json(OUT_DIR / "table_c2_variance_per_run.json", table_c2)
    write_json(OUT_DIR / "run_manifest.json", run_manifest)
    write_json(OUT_DIR / "artifact_checksums.json", checksums)

    write_csv_local(
        OUT_DIR / "table_a1_retrieval_full_selective.csv",
        table_a1,
        [
            "dataset",
            "setting",
            "n",
            "llm_calls",
            "selected_fraction",
            "tokens",
            "avg_tokens_per_case",
            "runtime_seconds",
            "avg_runtime_per_case",
            "top_1",
            "top_3",
            "top_5",
            "top_10",
            "mrr",
        ],
    )
    write_csv_local(
        OUT_DIR / "table_a2_retention_cost_savings.csv",
        table_a2,
        [
            "dataset",
            "metric",
            "retrieval",
            "full_rerank",
            "selective_rerank",
            "full_gain_over_retrieval",
            "selective_gain_over_retrieval",
            "selective_retention_of_full_gain",
            "call_saving_vs_full",
            "token_saving_vs_full",
            "runtime_saving_vs_full",
        ],
    )
    write_csv_local(
        OUT_DIR / "table_b1_selector_hard_case_coverage.csv",
        table_b1,
        [
            "dataset",
            "n",
            "total_selected",
            "selected_fraction",
            "baseline_top_1_failures",
            "baseline_top_5_failures",
            "baseline_top_10_failures",
            "selected_among_top_5_failures",
            "selected_among_top_10_failures",
            "selector_recall_on_top_5_failures",
            "selector_recall_on_top_10_failures",
            "unselected_top_5_failures_remaining",
            "unselected_top_10_failures_remaining",
        ],
    )
    write_csv_local(
        OUT_DIR / "table_b2_selected_case_effect_degradation.csv",
        table_b2,
        [
            "dataset",
            "selected_n",
            "improved_cases",
            "degraded_cases",
            "unchanged_cases",
            "mean_drr",
            "positive_rr_changes",
            "negative_rr_changes",
            "zero_rr_changes",
            "top_5_improved_cases",
            "top_5_degraded_cases",
            "top_10_improved_cases",
            "top_10_degraded_cases",
            "notes",
        ],
    )
    write_csv_local(
        OUT_DIR / "table_c1_variance_aggregate.csv",
        table_c1,
        [
            "dataset",
            "setting",
            "runs",
            "top_1_mean",
            "top_1_sd",
            "top_1_min",
            "top_1_max",
            "top_3_mean",
            "top_3_sd",
            "top_3_min",
            "top_3_max",
            "top_5_mean",
            "top_5_sd",
            "top_5_min",
            "top_5_max",
            "top_10_mean",
            "top_10_sd",
            "top_10_min",
            "top_10_max",
            "mrr_mean",
            "mrr_sd",
            "mrr_min",
            "mrr_max",
            "invalid_json_count_mean",
            "tokens_mean",
            "runtime_mean",
        ],
    )
    write_csv_local(
        OUT_DIR / "table_c2_variance_per_run.csv",
        table_c2,
        [
            "run_id",
            "llm_calls",
            "tokens",
            "runtime",
            "top_1",
            "top_3",
            "top_5",
            "top_10",
            "mrr",
            "invalid_json_count",
            "notes",
        ],
    )
    write_csv_local(
        OUT_DIR / "run_manifest.csv",
        run_manifest,
        [
            "run_id",
            "dataset",
            "setting",
            "model_alias",
            "provider",
            "access_date",
            "temperature",
            "response_format",
            "config",
            "git_commit_hash",
            "command_line",
            "output_paths",
            "prompt_dirs",
            "started_at_utc",
            "completed_at_utc",
            "llm_calls",
            "tokens",
            "runtime_seconds",
            "invalid_json_count",
            "evidence_package_checksum",
            "output_checksum",
            "notes",
        ],
    )
    write_csv_local(OUT_DIR / "artifact_checksums.csv", checksums, ["path", "bytes", "sha256"])
    write_report(table_a1, table_a2, table_b1, table_b2, table_c1, table_c2)
    print(f"Wrote RQ2 follow-up diagnostics to {OUT_DIR}")
    print(f"Wrote report to {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
