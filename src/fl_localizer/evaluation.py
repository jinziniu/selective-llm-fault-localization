from __future__ import annotations

from typing import Any


def first_correct_rank(ranked_files: list[str], ground_truth_files: set[str]) -> int | None:
    for rank, file_path in enumerate(ranked_files, start=1):
        if file_path in ground_truth_files:
            return rank
    return None


def evaluate_file_level(
    bug_records: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, Any]:
    bugs_by_id = {record["bug_id"]: record for record in bug_records}
    per_bug: list[dict[str, Any]] = []

    for prediction in predictions:
        bug_id = prediction["bug_id"]
        bug = bugs_by_id[bug_id]
        ground_truth_files = set(bug["ground_truth"]["files"])
        ranked_files = [item["file"] for item in prediction["ranked_files"]]
        correct_rank = first_correct_rank(ranked_files, ground_truth_files)
        result = {
            "bug_id": bug_id,
            "correct_rank": correct_rank,
            "mrr": 0.0 if correct_rank is None else 1.0 / correct_rank,
        }
        for k in ks:
            result[f"top_{k}"] = correct_rank is not None and correct_rank <= k
        per_bug.append(result)

    total = len(per_bug)
    summary: dict[str, Any] = {"bugs": total}
    for k in ks:
        summary[f"top_{k}_accuracy"] = (
            sum(1 for result in per_bug if result[f"top_{k}"]) / total if total else 0.0
        )
    summary["mrr"] = sum(result["mrr"] for result in per_bug) / total if total else 0.0
    return {"summary": summary, "per_bug": per_bug}

