#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl
from statistical_analysis_common import (
    compute_metric_distributions,
    compute_paired_tests,
    compute_recall_curves,
    compute_selector_subsets,
)


OUTPUT_DIR = ROOT / "outputs" / "compress_frozen_1_40_analysis_2026_08_11"
REPORT_PATH = ROOT / "docs" / "compress_frozen_1_40_validation_report_2026-08-11.md"


def relative(path: str) -> Path:
    return ROOT / path


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(fmt(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> int:
    paths = {
        "bugs": "data/defects4j/compress_frozen_1_40.jsonl",
        "baseline_top10": "outputs/compress_frozen_1_40_hybrid_focused_direct_top10_eval_boundary.jsonl",
        "baseline_top50": "outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl",
        "baseline_top100": "outputs/compress_frozen_1_40_hybrid_focused_direct_top100.jsonl",
        "selection": "outputs/compress_frozen_1_40_selector_generic_t102_h7_patterns.json",
        "rerank_complete": "outputs/compress_frozen_1_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_complete.jsonl",
        "merged": "outputs/compress_frozen_1_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl",
        "usage": "outputs/compress_frozen_1_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_usage.json",
        "protocol": "docs/frozen_protocol_2026-08-11_compress_1_40.md",
    }
    missing = [name for name, path in paths.items() if not relative(path).exists()]
    if missing:
        raise FileNotFoundError("Missing inputs: " + ", ".join(missing))

    manifest = {
        "generated_at": "2026-08-11",
        "datasets": [
            {
                "name": "compress_frozen_1_40",
                "display_name": "Compress 1--40",
                "bugs": [paths["bugs"]],
                "methods": [
                    {
                        "name": "retrieval_top10",
                        "display_name": "Retrieval",
                        "paths": [paths["baseline_top10"]],
                        "role": "baseline",
                    },
                    {
                        "name": "selective_rerank",
                        "display_name": "Selective rerank",
                        "paths": [paths["merged"]],
                        "role": "main",
                    },
                ],
                "retrieval_methods": ["retrieval_top10"],
                "recall_variants": [
                    {
                        "name": "retrieval_top100",
                        "display_name": "Retrieval Top-100",
                        "paths": [paths["baseline_top100"]],
                    }
                ],
                "selection": [paths["selection"]],
                "subset_baseline": "retrieval_top10",
                "subset_final": "selective_rerank",
                "comparisons": [
                    {
                        "name": "retrieval_vs_selective",
                        "baseline": "retrieval_top10",
                        "method": "selective_rerank",
                    }
                ],
            }
        ],
    }

    metrics = compute_metric_distributions(manifest)
    paired = compute_paired_tests(manifest, metrics["evaluations"])
    recall_manifest = json.loads(json.dumps(manifest))
    recall_manifest["datasets"][0]["retrieval_methods"] = ["retrieval_top10"]
    # Recall uses the full Top-50 retrieval as the base and Top-100 as sensitivity.
    recall_manifest["datasets"][0]["methods"].append(
        {
            "name": "retrieval_top50",
            "display_name": "Retrieval Top-50",
            "paths": [paths["baseline_top50"]],
            "role": "recall",
        }
    )
    recall_manifest["datasets"][0]["retrieval_methods"] = ["retrieval_top50"]
    recall = compute_recall_curves(recall_manifest, metrics["evaluations"])
    subsets = compute_selector_subsets(manifest, metrics["evaluations"])

    selection = json.loads(relative(paths["selection"]).read_text(encoding="utf-8"))
    usage = json.loads(relative(paths["usage"]).read_text(encoding="utf-8"))
    rerank_records = read_jsonl(relative(paths["rerank_complete"]))
    output_validity = {
        "records": len(rerank_records),
        "invalid_files": sum(len(row.get("invalid_files", [])) for row in rerank_records),
        "duplicate_files": sum(len(row.get("duplicate_files", [])) for row in rerank_records),
        "fallback_added": sum(int(row.get("fallback_added_count", 0)) for row in rerank_records),
        "models": sorted({str(row.get("model", "")) for row in rerank_records}),
    }

    metric_rows = metrics["rows"]
    paired_rows = paired["rows"]
    recall_rows = recall["rows"]
    subset_rows = subsets["rows"]
    false_negatives = subsets["selector_false_negatives"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "analysis_manifest.json", manifest)
    write_json(OUTPUT_DIR / "metric_distributions.json", {"rows": metric_rows})
    write_json(OUTPUT_DIR / "paired_tests.json", paired)
    write_json(OUTPUT_DIR / "recall_curves.json", recall)
    write_json(OUTPUT_DIR / "selector_subset_metrics.json", subsets)
    write_json(OUTPUT_DIR / "usage.json", usage)
    write_json(OUTPUT_DIR / "output_validity.json", output_validity)
    write_csv(OUTPUT_DIR / "metric_distributions.csv", metric_rows)
    write_csv(OUTPUT_DIR / "paired_tests.csv", paired_rows)
    write_csv(OUTPUT_DIR / "recall_curves.csv", recall_rows)
    write_csv(OUTPUT_DIR / "selector_subset_metrics.csv", subset_rows)
    write_csv(OUTPUT_DIR / "selector_false_negatives.csv", false_negatives)

    checksum_rows = [
        {"artifact": path, "sha256": sha256(relative(path))}
        for path in paths.values()
    ]
    write_json(OUTPUT_DIR / "artifact_checksums.json", {"rows": checksum_rows})
    write_csv(OUTPUT_DIR / "artifact_checksums.csv", checksum_rows)

    baseline = next(row for row in metric_rows if row["method"] == "retrieval_top10")
    final = next(row for row in metric_rows if row["method"] == "selective_rerank")
    wilcoxon = next(row for row in paired_rows if row["test"] == "wilcoxon_rr")
    top1_test = next(row for row in paired_rows if row["test"] == "mcnemar_top_1")

    report_sections = [
        "# Compress 1--40 Frozen Cross-Project Validation",
        "Date: 2026-08-11",
        "",
        "## Protocol Boundary",
        "",
        "Compress was not used in prior pilot, selector, prompt, evidence-rule, or error-analysis development. The generic pipeline was frozen before dataset construction. All 40 active bugs were built successfully. The first API batch completed Compress-2 and then encountered a read timeout on Compress-5; the remaining five preselected records were rerun with only the network timeout increased to 300 seconds, as recorded in the frozen protocol.",
        "",
        "## Main Result",
        "",
        table(
            ["Method", "N", "Calls", "Top-1", "Top-3", "Top-5", "Top-10", "MRR@10"],
            [
                ["Retrieval", baseline["n"], 0, baseline["top_1_accuracy"], baseline["top_3_accuracy"], baseline["top_5_accuracy"], baseline["top_10_accuracy"], baseline["mrr"]],
                ["Selective rerank", final["n"], selection["summary"]["selected"], final["top_1_accuracy"], final["top_3_accuracy"], final["top_5_accuracy"], final["top_10_accuracy"], final["mrr"]],
            ],
        ),
        "",
        f"Selective reranking changes one record: Compress-2 moves from rank 3 to rank 1. The other five selected records remain at rank 1. Top-1 increases from {baseline['top_1_hits']}/40 to {final['top_1_hits']}/40 and MRR@10 increases by {final['mrr'] - baseline['mrr']:.4f}; Top-3, Top-5, and Top-10 remain unchanged.",
        "",
        "## Selector and Candidate Diagnostics",
        "",
        table(
            ["Selected", "Fraction", "Top-5 failures selected", "Top-10 failures selected"],
            [[selection["summary"]["selected"], selection["summary"]["selected_fraction"], "0/2", "0/1"]],
        ),
        "",
        "The sole Top-10 retrieval failure is Compress-35 (retrieval rank 28), which remains unselected. Recall@50 and Recall@100 are both 1.0000, so this is a selector miss rather than a candidate-retrieval miss.",
        "",
        "## Cost and Output Validity",
        "",
        table(
            ["Requests", "Tokens", "Seconds", "Tokens/request", "Seconds/request", "Invalid", "Duplicates", "Fallback added"],
            [[usage["records"], usage["total_tokens"], usage["total_duration_seconds"], usage["avg_total_tokens"], usage["avg_duration_seconds"], output_validity["invalid_files"], output_validity["duplicate_files"], output_validity["fallback_added"]]],
        ),
        "",
        "## Paired Statistical Description",
        "",
        table(
            ["Comparison", "+RR", "-RR", "0RR", "Mean dRR@10", "Wilcoxon p", "Top-1 b/c", "McNemar p"],
            [["Retrieval vs selective", wilcoxon["n_positive_delta"], wilcoxon["n_negative_delta"], wilcoxon["n_zero_delta"], wilcoxon["mean_delta_rr"], wilcoxon["p_value"], f"{top1_test['b_baseline_miss_method_hit']}/{top1_test['c_baseline_hit_method_miss']}", top1_test["p_value"]]],
        ),
        "",
        "The tests are descriptive: only one record changes, so the slice does not provide inferential evidence of a stable improvement despite the positive aggregate direction.",
        "",
        "## Interpretation",
        "",
        "This fully unseen project strengthens the external-validity evidence for running the pipeline without project-specific tuning, but it also narrows the claim. Retrieval is already very strong on Compress, selective reranking produces only a small Top-1/MRR@10 improvement, and the generic selector misses the hard retrieval cases. The result therefore supports feasibility of the routing pipeline across another Defects4J project, not broad or statistically established cross-project superiority.",
    ]
    REPORT_PATH.write_text("\n".join(report_sections) + "\n", encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH}")
    print(f"Wrote analysis artifacts: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
