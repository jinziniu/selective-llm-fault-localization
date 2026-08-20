from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl  # noqa: E402


DEFAULT_KS = (1, 3, 5, 10)
RECALL_KS = (10, 20, 50, 100)
MAIN_RANK_DEPTH = 10


def rel(path: str) -> Path:
    return ROOT / path


def path_text(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: "NA" if row.get(field, "") is None else row.get(field, "")
                    for field in fieldnames
                }
            )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def default_manifest() -> dict[str, Any]:
    return {
        "created_by": "scripts/build_statistical_supplement.py",
        "date": "2026-06-10",
        "datasets": [
            {
                "name": "closure_61_100",
                "display_name": "Closure-61..100",
                "bugs": [
                    "data/defects4j/closure_heldout_61_80.jsonl",
                    "data/defects4j/closure_heldout_81_100.jsonl",
                ],
                "methods": [
                    {
                        "name": "retrieval_top50",
                        "display_name": "Retrieval",
                        "paths": [
                            "outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
                            "outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl",
                        ],
                        "role": "baseline",
                    },
                    {
                        "name": "selective_rerank",
                        "display_name": "Selective rerank",
                        "paths": [
                            "outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                            "outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl",
                        ],
                        "role": "main",
                    },
                ],
                "retrieval_methods": ["retrieval_top50"],
                "recall_variants": [
                    {
                        "name": "retrieval_top100",
                        "display_name": "Retrieval Top-100",
                        "paths": [
                            "outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top100.jsonl",
                            "outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top100.jsonl",
                        ],
                    }
                ],
                "selection": [
                    "outputs/closure_heldout_61_80_selector_closure_cost_control_v3.json",
                    "outputs/closure_heldout_81_100_selector_closure_cost_control_v3.json",
                ],
                "subset_baseline": "retrieval_top50",
                "subset_final": "selective_rerank",
                "comparisons": [
                    {
                        "name": "retrieval_vs_selective",
                        "baseline": "retrieval_top50",
                        "method": "selective_rerank",
                    }
                ],
            },
            {
                "name": "aboutwork_committed_60",
                "display_name": "AboutWork-60",
                "bugs": ["data/aboutwork/aboutwork_committed_60.jsonl"],
                "methods": [
                    {
                        "name": "bm25",
                        "display_name": "BM25",
                        "paths": ["outputs/aboutwork_committed_60_bm25_top50.jsonl"],
                        "role": "baseline",
                    },
                    {
                        "name": "one_shot",
                        "display_name": "Selective one-shot",
                        "paths": ["outputs/aboutwork_committed_60_bm25_plus_deepseek_selector_v3.jsonl"],
                        "role": "main",
                    },
                    {
                        "name": "agentic",
                        "display_name": "Agentic",
                        "paths": ["outputs/aboutwork_committed_60_bm25_plus_agentic_deepseek_selector_v3_s2.jsonl"],
                        "role": "rq3",
                    },
                    {
                        "name": "agentic_verifier",
                        "display_name": "Agentic+verifier",
                        "paths": ["outputs/aboutwork_committed_60_bm25_plus_agentic_verifier_deepseek_selector_v3_s2.jsonl"],
                        "role": "rq3",
                    },
                ],
                "retrieval_methods": ["bm25"],
                "recall_variants": [
                    {
                        "name": "bm25_top100",
                        "display_name": "BM25 Top-100",
                        "paths": ["outputs/aboutwork_committed_60_bm25_top100.jsonl"],
                    }
                ],
                "selection": ["outputs/aboutwork60_selector_v3.json"],
                "subset_baseline": "bm25",
                "subset_final": "one_shot",
                "comparisons": [
                    {"name": "bm25_vs_one_shot", "baseline": "bm25", "method": "one_shot"},
                    {"name": "one_shot_vs_agentic", "baseline": "one_shot", "method": "agentic"},
                    {
                        "name": "agentic_vs_verifier",
                        "baseline": "agentic",
                        "method": "agentic_verifier",
                    },
                ],
            },
            {
                "name": "easy_finance_clean63",
                "display_name": "Easy Finance clean63",
                "bugs": ["data/easy_finance/easy_finance_committed_clean63.jsonl"],
                "methods": [
                    {
                        "name": "bm25",
                        "display_name": "BM25",
                        "paths": ["outputs/easy_finance_committed_clean63_bm25_prod_top50.jsonl"],
                        "role": "baseline",
                    },
                    {
                        "name": "one_shot",
                        "display_name": "Selective one-shot",
                        "paths": [
                            "outputs/easy_finance_committed_clean63_bm25_prod_plus_deepseek_selector_v1_ui_evidence_v2.jsonl"
                        ],
                        "role": "main",
                    },
                ],
                "retrieval_methods": ["bm25"],
                "recall_variants": [
                    {
                        "name": "bm25_top100",
                        "display_name": "BM25 Top-100",
                        "paths": ["outputs/easy_finance_committed_clean63_bm25_prod_top100.jsonl"],
                    }
                ],
                "selection": ["outputs/easy_finance_clean63_prod_selector_v1.json"],
                "subset_baseline": "bm25",
                "subset_final": "one_shot",
                "comparisons": [
                    {"name": "bm25_vs_one_shot", "baseline": "bm25", "method": "one_shot"}
                ],
            },
            {
                "name": "easy_finance_strict62",
                "display_name": "Easy Finance strict62",
                "bugs": ["data/easy_finance/easy_finance_committed_strict62.jsonl"],
                "methods": [
                    {
                        "name": "bm25",
                        "display_name": "BM25",
                        "paths": ["outputs/easy_finance_committed_strict62_bm25_prod_top50.jsonl"],
                        "role": "baseline",
                    },
                    {
                        "name": "one_shot",
                        "display_name": "Selective one-shot",
                        "paths": [
                            "outputs/easy_finance_committed_strict62_bm25_prod_plus_deepseek_selector_v1_ui_evidence_v2.jsonl"
                        ],
                        "role": "main",
                    },
                    {
                        "name": "agentic",
                        "display_name": "Agentic",
                        "paths": [
                            "outputs/easy_finance_committed_strict62_bm25_prod_plus_agentic_deepseek_selector_v1_s2.jsonl"
                        ],
                        "role": "rq3",
                    },
                    {
                        "name": "agentic_verifier",
                        "display_name": "Agentic+verifier",
                        "paths": [
                            "outputs/easy_finance_committed_strict62_bm25_prod_plus_agentic_verifier_deepseek_selector_v1_s2.jsonl"
                        ],
                        "role": "rq3",
                    },
                ],
                "retrieval_methods": ["bm25"],
                "recall_variants": [
                    {
                        "name": "bm25_top100",
                        "display_name": "BM25 Top-100",
                        "paths": ["outputs/easy_finance_committed_strict62_bm25_prod_top100.jsonl"],
                    }
                ],
                "selection": ["outputs/easy_finance_strict62_prod_selector_v1.json"],
                "subset_baseline": "bm25",
                "subset_final": "one_shot",
                "comparisons": [
                    {"name": "one_shot_vs_agentic", "baseline": "one_shot", "method": "agentic"},
                    {
                        "name": "agentic_vs_verifier",
                        "baseline": "agentic",
                        "method": "agentic_verifier",
                    },
                ],
            },
            {
                "name": "rq5_defects4j_mini_10",
                "display_name": "Defects4J RQ3 diagnostic mini",
                "bugs": ["data/defects4j/rq5_defects4j_mini_10.jsonl"],
                "methods": [
                    {
                        "name": "baseline",
                        "display_name": "Retrieval",
                        "paths": ["outputs/rq5_defects4j_mini_10_baseline_top50.jsonl"],
                        "role": "baseline",
                    },
                    {
                        "name": "one_shot",
                        "display_name": "One-shot",
                        "paths": ["outputs/rq5_defects4j_mini_10_oneshot_deepseek.jsonl"],
                        "role": "rq3",
                    },
                    {
                        "name": "agentic",
                        "display_name": "Agentic",
                        "paths": ["outputs/rq5_defects4j_mini_10_agentic_deepseek.jsonl"],
                        "role": "rq3",
                    },
                    {
                        "name": "agentic_verifier",
                        "display_name": "Agentic+verifier",
                        "paths": ["outputs/rq5_defects4j_mini_10_agentic_verifier_deepseek.jsonl"],
                        "role": "rq3",
                    },
                ],
                "retrieval_methods": ["baseline"],
                "comparisons": [
                    {"name": "baseline_vs_one_shot", "baseline": "baseline", "method": "one_shot"},
                    {"name": "one_shot_vs_agentic", "baseline": "one_shot", "method": "agentic"},
                    {
                        "name": "agentic_vs_verifier",
                        "baseline": "agentic",
                        "method": "agentic_verifier",
                    },
                ],
            },
            {
                "name": "math_fresh_21_40",
                "display_name": "Math-21..40",
                "bugs": ["data/defects4j/math_fresh_21_40.jsonl"],
                "methods": [
                    {
                        "name": "retrieval_top50",
                        "display_name": "Retrieval",
                        "paths": ["outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl"],
                        "role": "baseline",
                    },
                    {
                        "name": "selective_rerank",
                        "display_name": "Selective rerank",
                        "paths": [
                            "outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl"
                        ],
                        "role": "main",
                    },
                ],
                "retrieval_methods": ["retrieval_top50"],
                "recall_variants": [
                    {
                        "name": "retrieval_top100",
                        "display_name": "Retrieval Top-100",
                        "paths": ["outputs/math_fresh_21_40_hybrid_focused_direct_top100.jsonl"],
                    }
                ],
                "selection": ["outputs/math_fresh_21_40_selector_generic_t102_h7_patterns.json"],
                "subset_baseline": "retrieval_top50",
                "subset_final": "selective_rerank",
                "comparisons": [
                    {
                        "name": "retrieval_vs_selective",
                        "baseline": "retrieval_top50",
                        "method": "selective_rerank",
                    }
                ],
            },
        ],
    }


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in manifest["datasets"]:
        for path in dataset.get("bugs", []):
            candidate = rel(path)
            rows.append({"dataset": dataset["name"], "kind": "bugs", "path": path, "exists": candidate.exists()})
        for method in dataset.get("methods", []):
            for path in method.get("paths", []):
                candidate = rel(path)
                rows.append(
                    {
                        "dataset": dataset["name"],
                        "kind": f"method:{method['name']}",
                        "path": path,
                        "exists": candidate.exists(),
                    }
                )
        for path in dataset.get("selection", []):
            candidate = rel(path)
            rows.append({"dataset": dataset["name"], "kind": "selection", "path": path, "exists": candidate.exists()})
    return rows


def method_by_name(dataset: dict[str, Any], name: str) -> dict[str, Any]:
    for method in dataset["methods"]:
        if method["name"] == name:
            return method
    raise KeyError(f"{dataset['name']} does not define method {name}")


def load_bug_records(paths: list[str]) -> dict[str, dict[str, Any]]:
    bugs: dict[str, dict[str, Any]] = {}
    for path in paths:
        for record in read_jsonl(rel(path)):
            bug_id = str(record["bug_id"])
            if bug_id in bugs:
                raise ValueError(f"Duplicate bug_id in bug inputs: {bug_id}")
            bugs[bug_id] = record
    return bugs


def load_prediction_records(paths: list[str]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for path in paths:
        for record in read_jsonl(rel(path)):
            bug_id = str(record["bug_id"])
            if bug_id in predictions:
                raise ValueError(f"Duplicate bug_id in prediction inputs: {bug_id}")
            predictions[bug_id] = record
    return predictions


def first_correct_rank(ranked_files: list[dict[str, Any]], ground_truth_files: set[str]) -> int | None:
    for index, item in enumerate(ranked_files, start=1):
        file_path = str(item.get("file", ""))
        if file_path in ground_truth_files:
            return index
    return None


def evaluate_method(
    dataset: dict[str, Any],
    method: dict[str, Any],
    *,
    rank_depth: int | None = None,
) -> dict[str, Any]:
    bugs = load_bug_records(dataset["bugs"])
    predictions = load_prediction_records(method["paths"])
    per_bug: list[dict[str, Any]] = []
    missing_predictions = sorted(set(bugs) - set(predictions))
    extra_predictions = sorted(set(predictions) - set(bugs))
    for bug_id, bug in bugs.items():
        prediction = predictions.get(bug_id)
        if prediction is None:
            continue
        ground_truth_files = set(str(path) for path in bug["ground_truth"]["files"])
        ranked_files = prediction.get("ranked_files", [])
        if not isinstance(ranked_files, list):
            ranked_files = []
        if rank_depth is not None:
            ranked_files = ranked_files[:rank_depth]
        rank = first_correct_rank(ranked_files, ground_truth_files)
        max_depth = len(ranked_files)
        per_bug.append(
            {
                "bug_id": bug_id,
                "correct_rank": rank,
                "rr": 0.0 if rank is None else 1.0 / rank,
                "max_depth": max_depth,
                "ground_truth_files": sorted(ground_truth_files),
            }
        )
    return {
        "dataset": dataset["name"],
        "dataset_display_name": dataset.get("display_name", dataset["name"]),
        "method": method["name"],
        "method_display_name": method.get("display_name", method["name"]),
        "role": method.get("role", ""),
        "paths": method["paths"],
        "per_bug": per_bug,
        "missing_predictions": missing_predictions,
        "extra_predictions": extra_predictions,
    }


def quantile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def iqr(values: list[float]) -> float | None:
    ordered = sorted(values)
    q1 = quantile(ordered, 0.25)
    q3 = quantile(ordered, 0.75)
    if q1 is None or q3 is None:
        return None
    return q3 - q1


def sample_sd(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def summarize_per_bug(per_bug: list[dict[str, Any]], *, ks: tuple[int, ...] = DEFAULT_KS) -> dict[str, Any]:
    n = len(per_bug)
    max_depth = max((int(row["max_depth"]) for row in per_bug), default=0)
    cap = max_depth + 1
    rr_values = [float(row["rr"]) for row in per_bug]
    capped_ranks = [
        float(row["correct_rank"] if row["correct_rank"] is not None else cap)
        for row in per_bug
    ]
    summary: dict[str, Any] = {
        "n": n,
        "max_depth": max_depth,
        "miss_count": sum(1 for row in per_bug if row["correct_rank"] is None),
        "mrr": sum(rr_values) / n if n else 0.0,
        "median_rr": statistics.median(rr_values) if rr_values else 0.0,
        "sd_rr": sample_sd(rr_values),
        "iqr_rr": iqr(rr_values) or 0.0,
        "median_capped_rank": statistics.median(capped_ranks) if capped_ranks else 0.0,
        "iqr_capped_rank": iqr(capped_ranks) or 0.0,
        "miss_cap": cap,
    }
    for k in ks:
        hits = sum(1 for row in per_bug if row["correct_rank"] is not None and row["correct_rank"] <= k)
        summary[f"top_{k}_hits"] = hits
        summary[f"top_{k}_accuracy"] = hits / n if n else 0.0
    return summary


def compute_metric_distributions(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    evaluations: dict[str, dict[str, Any]] = {}
    for dataset in manifest["datasets"]:
        dataset_evals: dict[str, Any] = {}
        for method in dataset["methods"]:
            evaluated = evaluate_method(dataset, method, rank_depth=MAIN_RANK_DEPTH)
            summary = summarize_per_bug(evaluated["per_bug"], ks=(1, 3, 5, 10, 50, 100))
            dataset_evals[method["name"]] = evaluated
            row = {
                "dataset": dataset["name"],
                "dataset_display_name": dataset.get("display_name", dataset["name"]),
                "method": method["name"],
                "method_display_name": method.get("display_name", method["name"]),
                "role": method.get("role", ""),
                **summary,
                "missing_predictions": len(evaluated["missing_predictions"]),
                "extra_predictions": len(evaluated["extra_predictions"]),
            }
            rows.append(row)
        evaluations[dataset["name"]] = dataset_evals
    return {"rows": rows, "evaluations": evaluations}


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    threshold = min(b, c)
    prob = sum(math.comb(n, i) for i in range(threshold + 1)) / (2**n)
    return min(1.0, 2.0 * prob)


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        avg = (index + 1 + end) / 2.0
        for original_index, _ in indexed[index:end]:
            ranks[original_index] = avg
        index = end
    return ranks


def wilcoxon_signed_rank(baseline_rr: list[float], method_rr: list[float]) -> dict[str, Any]:
    diffs = [method - baseline for baseline, method in zip(baseline_rr, method_rr) if method != baseline]
    if not diffs:
        return {
            "method": "none_all_zero_deltas",
            "n_nonzero": 0,
            "w_statistic": 0.0,
            "p_two_sided": 1.0,
        }

    try:
        from scipy.stats import wilcoxon  # type: ignore

        result = wilcoxon(method_rr, baseline_rr, zero_method="wilcox", alternative="two-sided")
        return {
            "method": "scipy_wilcoxon",
            "n_nonzero": len(diffs),
            "w_statistic": float(result.statistic),
            "p_two_sided": float(result.pvalue),
        }
    except Exception:
        pass

    abs_diffs = [abs(diff) for diff in diffs]
    ranks = average_ranks(abs_diffs)
    w_positive = sum(rank for rank, diff in zip(ranks, diffs) if diff > 0)
    w_negative = sum(rank for rank, diff in zip(ranks, diffs) if diff < 0)
    w_statistic = min(w_positive, w_negative)
    n = len(diffs)
    mean = n * (n + 1) / 4.0
    variance = n * (n + 1) * (2 * n + 1) / 24.0
    if variance <= 0:
        p_value = 1.0
    else:
        z = (w_statistic - mean) / math.sqrt(variance)
        p_value = 2.0 * (0.5 * math.erfc(abs(z) / math.sqrt(2.0)))
    return {
        "method": "normal_approx_no_tie_correction",
        "n_nonzero": n,
        "w_positive": w_positive,
        "w_negative": w_negative,
        "w_statistic": w_statistic,
        "p_two_sided": min(1.0, p_value),
    }


def by_bug(per_bug: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["bug_id"]): row for row in per_bug}


def compute_paired_tests(manifest: dict[str, Any], evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for dataset in manifest["datasets"]:
        dataset_name = dataset["name"]
        for comparison in dataset.get("comparisons", []):
            baseline_eval = by_bug(evaluations[dataset_name][comparison["baseline"]]["per_bug"])
            method_eval = by_bug(evaluations[dataset_name][comparison["method"]]["per_bug"])
            bug_ids = sorted(set(baseline_eval) & set(method_eval))
            baseline_rr = [float(baseline_eval[bug_id]["rr"]) for bug_id in bug_ids]
            method_rr = [float(method_eval[bug_id]["rr"]) for bug_id in bug_ids]
            wilcoxon = wilcoxon_signed_rank(baseline_rr, method_rr)
            rows.append(
                {
                    "dataset": dataset_name,
                    "dataset_display_name": dataset.get("display_name", dataset_name),
                    "comparison": comparison["name"],
                    "test": "wilcoxon_rr",
                    "n": len(bug_ids),
                    "p_value": wilcoxon["p_two_sided"],
                    "w_statistic": wilcoxon.get("w_statistic"),
                    "wilcoxon_method": wilcoxon.get("method"),
                    "mean_delta_rr": statistics.mean(
                        [method - base for base, method in zip(baseline_rr, method_rr)]
                    )
                    if bug_ids
                    else 0.0,
                    "median_delta_rr": statistics.median(
                        [method - base for base, method in zip(baseline_rr, method_rr)]
                    )
                    if bug_ids
                    else 0.0,
                    "n_positive_delta": sum(1 for base, method in zip(baseline_rr, method_rr) if method > base),
                    "n_negative_delta": sum(1 for base, method in zip(baseline_rr, method_rr) if method < base),
                    "n_zero_delta": sum(1 for base, method in zip(baseline_rr, method_rr) if method == base),
                }
            )
            for k in DEFAULT_KS:
                b = 0
                c = 0
                for bug_id in bug_ids:
                    baseline_hit = (
                        baseline_eval[bug_id]["correct_rank"] is not None
                        and int(baseline_eval[bug_id]["correct_rank"]) <= k
                    )
                    method_hit = (
                        method_eval[bug_id]["correct_rank"] is not None
                        and int(method_eval[bug_id]["correct_rank"]) <= k
                    )
                    if not baseline_hit and method_hit:
                        b += 1
                    elif baseline_hit and not method_hit:
                        c += 1
                rows.append(
                    {
                        "dataset": dataset_name,
                        "dataset_display_name": dataset.get("display_name", dataset_name),
                        "comparison": comparison["name"],
                        "test": f"mcnemar_top_{k}",
                        "n": len(bug_ids),
                        "b_baseline_miss_method_hit": b,
                        "c_baseline_hit_method_miss": c,
                        "discordant": b + c,
                        "p_value": mcnemar_exact(b, c),
                    }
                )
    return {"rows": rows}


def load_selected_bug_ids(paths: list[str]) -> set[str]:
    selected: set[str] = set()
    for path in paths:
        payload = load_json(rel(path))
        raw_ids = payload.get("selected_bug_ids", [])
        if not isinstance(raw_ids, list):
            raise ValueError(f"{path} does not contain selected_bug_ids")
        selected.update(str(bug_id) for bug_id in raw_ids)
    return selected


def compute_selector_subsets(manifest: dict[str, Any], evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []
    for dataset in manifest["datasets"]:
        selection_paths = dataset.get("selection", [])
        if not selection_paths:
            continue
        selected = load_selected_bug_ids(selection_paths)
        baseline_name = dataset.get("subset_baseline")
        final_name = dataset.get("subset_final")
        if not baseline_name or not final_name:
            continue
        baseline_eval = by_bug(evaluations[dataset["name"]][baseline_name]["per_bug"])
        final_eval = by_bug(evaluations[dataset["name"]][final_name]["per_bug"])
        all_bug_ids = sorted(set(baseline_eval) & set(final_eval))
        for subset_name, subset_ids in [
            ("selected", sorted(selected & set(all_bug_ids))),
            ("unselected", sorted(set(all_bug_ids) - selected)),
        ]:
            baseline_subset = [baseline_eval[bug_id] for bug_id in subset_ids]
            final_subset = [final_eval[bug_id] for bug_id in subset_ids]
            baseline_summary = summarize_per_bug(baseline_subset, ks=DEFAULT_KS)
            final_summary = summarize_per_bug(final_subset, ks=DEFAULT_KS)
            rows.append(
                {
                    "dataset": dataset["name"],
                    "dataset_display_name": dataset.get("display_name", dataset["name"]),
                    "subset": subset_name,
                    "n": len(subset_ids),
                    "baseline_method": baseline_name,
                    "final_method": final_name,
                    "baseline_top_1": baseline_summary["top_1_accuracy"],
                    "baseline_top_3": baseline_summary["top_3_accuracy"],
                    "baseline_top_5": baseline_summary["top_5_accuracy"],
                    "baseline_top_10": baseline_summary["top_10_accuracy"],
                    "baseline_mrr": baseline_summary["mrr"],
                    "final_top_1": final_summary["top_1_accuracy"],
                    "final_top_3": final_summary["top_3_accuracy"],
                    "final_top_5": final_summary["top_5_accuracy"],
                    "final_top_10": final_summary["top_10_accuracy"],
                    "final_mrr": final_summary["mrr"],
                }
            )
        for bug_id in sorted(set(all_bug_ids) - selected):
            final_rank = final_eval[bug_id]["correct_rank"]
            if final_rank is None or int(final_rank) > 10:
                false_negatives.append(
                    {
                        "dataset": dataset["name"],
                        "bug_id": bug_id,
                        "baseline_rank": baseline_eval[bug_id]["correct_rank"],
                        "final_rank": final_rank,
                        "ground_truth_files": ";".join(baseline_eval[bug_id]["ground_truth_files"]),
                    }
                )
    return {"rows": rows, "selector_false_negatives": false_negatives}


def compute_recall_curves(manifest: dict[str, Any], evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for dataset in manifest["datasets"]:
        dataset_name = dataset["name"]
        recall_variants = dataset.get("recall_variants")
        if recall_variants and dataset.get("retrieval_methods"):
            base_method_name = dataset["retrieval_methods"][0]
            base_eval = evaluate_method(dataset, method_by_name(dataset, base_method_name))
            base_by_bug = by_bug(base_eval["per_bug"])
            for variant in recall_variants:
                top100_eval = evaluate_method(
                    dataset,
                    {
                        "name": variant["name"],
                        "display_name": variant.get("display_name", variant["name"]),
                        "paths": variant["paths"],
                        "role": "recall",
                    },
                )
                top100_by_bug = by_bug(top100_eval["per_bug"])
                bug_ids = sorted(set(base_by_bug) & set(top100_by_bug))
                n = len(bug_ids)
                row: dict[str, Any] = {
                    "dataset": dataset_name,
                    "dataset_display_name": dataset.get("display_name", dataset_name),
                    "method": variant["name"],
                    "method_display_name": variant.get("display_name", variant["name"]),
                    "n": n,
                    "max_depth": 100,
                    "base_method": base_method_name,
                    "top100_method": variant["name"],
                }
                for k in (10, 20, 50):
                    hits = sum(
                        1
                        for bug_id in bug_ids
                        if base_by_bug[bug_id]["correct_rank"] is not None
                        and int(base_by_bug[bug_id]["correct_rank"]) <= k
                    )
                    row[f"hits_at_{k}"] = hits
                    row[f"recall_at_{k}"] = hits / n if n else 0.0
                hits_100 = sum(
                    1
                    for bug_id in bug_ids
                    if top100_by_bug[bug_id]["correct_rank"] is not None
                    and int(top100_by_bug[bug_id]["correct_rank"]) <= 100
                )
                row["hits_at_100"] = hits_100
                row["recall_at_100"] = hits_100 / n if n else 0.0
                row["marginal_50_to_100"] = row["recall_at_100"] - row["recall_at_50"]
                rows.append(row)
                for bug_id in bug_ids:
                    base_rank = base_by_bug[bug_id]["correct_rank"]
                    if base_rank is None or int(base_rank) > 50:
                        rank_100 = top100_by_bug[bug_id]["correct_rank"]
                        misses.append(
                            {
                                "dataset": dataset_name,
                                "method": variant["name"],
                                "bug_id": bug_id,
                                "rank_at_available_depth": base_rank,
                                "max_depth": top100_by_bug[bug_id]["max_depth"],
                                "rank_at_100": rank_100
                                if rank_100 is not None and int(rank_100) <= 100
                                else None,
                                "rescued_by_100": bool(rank_100 is not None and int(rank_100) <= 100),
                                "ground_truth_files": ";".join(base_by_bug[bug_id]["ground_truth_files"]),
                            }
                        )
            continue

        for method_name in dataset.get("retrieval_methods", []):
            evaluated = evaluations[dataset_name][method_name]
            per_bug = evaluated["per_bug"]
            n = len(per_bug)
            row: dict[str, Any] = {
                "dataset": dataset_name,
                "dataset_display_name": dataset.get("display_name", dataset_name),
                "method": evaluated["method"],
                "method_display_name": evaluated.get("method_display_name", evaluated["method"]),
                "n": n,
                "max_depth": max((int(item["max_depth"]) for item in per_bug), default=0),
            }
            for k in RECALL_KS:
                if row["max_depth"] < k:
                    row[f"recall_at_{k}"] = None
                else:
                    hits = sum(
                        1
                        for item in per_bug
                        if item["correct_rank"] is not None and int(item["correct_rank"]) <= k
                    )
                    row[f"recall_at_{k}"] = hits / n if n else 0.0
                    row[f"hits_at_{k}"] = hits
            if row.get("recall_at_50") is not None and row.get("recall_at_100") is not None:
                row["marginal_50_to_100"] = row["recall_at_100"] - row["recall_at_50"]
            rows.append(row)
            for item in per_bug:
                rank = item["correct_rank"]
                if rank is None or int(rank) > 50:
                    misses.append(
                        {
                            "dataset": dataset_name,
                            "method": evaluated["method"],
                            "bug_id": item["bug_id"],
                            "rank_at_available_depth": rank,
                            "max_depth": item["max_depth"],
                            "rank_at_100": rank if rank is not None and int(rank) <= 100 else None,
                            "rescued_by_100": bool(rank is not None and 50 < int(rank) <= 100),
                            "ground_truth_files": ";".join(item["ground_truth_files"]),
                        }
                    )
    return {"rows": rows, "retrieval_misses": misses}


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(item) for item in row) + " |")
    return "\n".join(lines)


def build_markdown(
    metric_rows: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    recall_rows: list[dict[str, Any]],
    subset_rows: list[dict[str, Any]],
    false_negatives: list[dict[str, Any]],
) -> str:
    main_metric_rows = [
        [
            row["dataset_display_name"],
            row["method_display_name"],
            row["n"],
            f"{row['top_1_hits']}/{row['n']}",
            f"{row['top_3_hits']}/{row['n']}",
            f"{row['top_5_hits']}/{row['n']}",
            f"{row['top_10_hits']}/{row['n']}",
            row["mrr"],
            row["median_rr"],
            row["sd_rr"],
        ]
        for row in metric_rows
    ]
    mcnemar_rows = [
        [
            row["dataset_display_name"],
            row["comparison"],
            row["test"],
            row.get("b_baseline_miss_method_hit", ""),
            row.get("c_baseline_hit_method_miss", ""),
            row["p_value"],
        ]
        for row in paired_rows
        if str(row["test"]).startswith("mcnemar")
    ]
    wilcoxon_rows = [
        [
            row["dataset_display_name"],
            row["comparison"],
            row["n"],
            row.get("w_statistic"),
            row["p_value"],
            row.get("mean_delta_rr"),
            row.get("median_delta_rr"),
            row.get("n_positive_delta"),
            row.get("n_negative_delta"),
            row.get("n_zero_delta"),
        ]
        for row in paired_rows
        if row["test"] == "wilcoxon_rr"
    ]
    recall_table_rows = [
        [
            row["dataset_display_name"],
            row.get("method_display_name", row["method"]),
            row["n"],
            row.get("recall_at_10"),
            row.get("recall_at_20"),
            row.get("recall_at_50"),
            row.get("recall_at_100"),
            row.get("marginal_50_to_100"),
        ]
        for row in recall_rows
    ]
    subset_table_rows = [
        [
            row["dataset_display_name"],
            row["subset"],
            row["n"],
            row["baseline_top_5"],
            row["final_top_5"],
            row["baseline_mrr"],
            row["final_mrr"],
        ]
        for row in subset_rows
    ]
    false_negative_rows = [
        [
            row["dataset"],
            row["bug_id"],
            row["baseline_rank"],
            row["final_rank"],
            row["ground_truth_files"],
        ]
        for row in false_negatives[:30]
    ]

    return "\n\n".join(
        [
            "# Statistical Supplement",
            "Date: 2026-06-10",
            "This supplement reports raw counts, dispersion statistics, paired tests, Recall@K, and selected vs unselected subset metrics computed from existing experiment outputs. P-values are descriptive because the paired samples are modest.",
            "## Metric Distributions",
            markdown_table(
                ["Dataset", "Method", "N", "Top-1", "Top-3", "Top-5", "Top-10", "MRR@10", "Median RR@10", "SD(RR@10)"],
                main_metric_rows,
            ),
            "## McNemar Exact Tests",
            markdown_table(["Dataset", "Comparison", "Metric", "b", "c", "p"], mcnemar_rows),
            "## Wilcoxon Signed-Rank Tests",
            markdown_table(
                [
                    "Dataset",
                    "Comparison",
                    "N",
                    "W",
                    "p",
                    "Mean dRR@10",
                    "Median dRR@10",
                    "+",
                    "-",
                    "0",
                ],
                wilcoxon_rows,
            ),
            "## Recall@K Curves",
            markdown_table(
                ["Dataset", "Method", "N", "R@10", "R@20", "R@50", "R@100", "R@100 - R@50"],
                recall_table_rows,
            ),
            "## Selected Vs Unselected",
            markdown_table(
                ["Dataset", "Subset", "N", "Baseline Top-5", "Final Top-5", "Baseline MRR@10", "Final MRR@10"],
                subset_table_rows,
            ),
            "## Selector False Negatives",
            markdown_table(["Dataset", "Bug", "Baseline Rank", "Final Rank", "Ground Truth"], false_negative_rows),
            "## Interpretation Notes",
            "- `b` in McNemar is the count of bugs missed by baseline but hit by the compared method.",
            "- `c` is the count of bugs hit by baseline but missed by the compared method.",
            "- `RR@10` is reciprocal rank at depth 10, with 0 for misses outside the Top-10 output boundary.",
            "- `R@100` is `NA` until retrieval-only Top-100 outputs are generated for that dataset.",
            "- Selected and unselected subsets are not random treatment/control groups; they describe selector behavior and fallback behavior.",
        ]
    ) + "\n"


def run_all(output_dir: Path, docs_path: Path) -> dict[str, Any]:
    manifest = default_manifest()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "analysis_manifest.json", manifest)
    inventory_rows = validate_manifest(manifest)
    write_json(output_dir / "input_inventory.json", {"rows": inventory_rows})
    missing = [row for row in inventory_rows if not row["exists"]]
    if missing:
        write_json(output_dir / "missing_inputs.json", {"rows": missing})
        raise FileNotFoundError(f"Missing {len(missing)} manifest input(s); see {output_dir / 'missing_inputs.json'}")

    metrics = compute_metric_distributions(manifest)
    metric_rows = metrics["rows"]
    evaluations = metrics["evaluations"]
    paired = compute_paired_tests(manifest, evaluations)
    recall = compute_recall_curves(manifest, evaluations)
    subsets = compute_selector_subsets(manifest, evaluations)

    write_json(output_dir / "metric_distributions.json", {"rows": metric_rows})
    write_json(output_dir / "paired_tests.json", paired)
    write_json(output_dir / "recall_curves.json", recall)
    write_json(output_dir / "selector_subset_metrics.json", subsets)

    write_csv(
        output_dir / "metric_distributions.csv",
        metric_rows,
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
    write_csv(
        output_dir / "paired_tests.csv",
        paired["rows"],
        [
            "dataset",
            "comparison",
            "test",
            "n",
            "b_baseline_miss_method_hit",
            "c_baseline_hit_method_miss",
            "discordant",
            "p_value",
            "w_statistic",
            "mean_delta_rr",
            "median_delta_rr",
            "n_positive_delta",
            "n_negative_delta",
            "n_zero_delta",
            "wilcoxon_method",
        ],
    )
    write_csv(
        output_dir / "recall_curve_points.csv",
        recall["rows"],
        [
            "dataset",
            "method",
            "n",
            "max_depth",
            "hits_at_10",
            "recall_at_10",
            "hits_at_20",
            "recall_at_20",
            "hits_at_50",
            "recall_at_50",
            "hits_at_100",
            "recall_at_100",
            "marginal_50_to_100",
        ],
    )
    write_csv(
        output_dir / "retrieval_misses_top50_vs_top100.csv",
        recall["retrieval_misses"],
        ["dataset", "method", "bug_id", "rank_at_available_depth", "max_depth", "rank_at_100", "rescued_by_100", "ground_truth_files"],
    )
    write_csv(
        output_dir / "selector_subset_metrics.csv",
        subsets["rows"],
        [
            "dataset",
            "subset",
            "n",
            "baseline_top_1",
            "baseline_top_3",
            "baseline_top_5",
            "baseline_top_10",
            "baseline_mrr",
            "final_top_1",
            "final_top_3",
            "final_top_5",
            "final_top_10",
            "final_mrr",
        ],
    )
    write_csv(
        output_dir / "selector_false_negatives.csv",
        subsets["selector_false_negatives"],
        ["dataset", "bug_id", "baseline_rank", "final_rank", "ground_truth_files"],
    )

    markdown = build_markdown(
        metric_rows,
        paired["rows"],
        recall["rows"],
        subsets["rows"],
        subsets["selector_false_negatives"],
    )
    (output_dir / "statistical_supplement_tables.md").write_text(markdown, encoding="utf-8")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(markdown, encoding="utf-8")
    return {
        "manifest": manifest,
        "metric_rows": metric_rows,
        "paired_rows": paired["rows"],
        "recall_rows": recall["rows"],
        "subset_rows": subsets["rows"],
        "false_negatives": subsets["selector_false_negatives"],
    }
