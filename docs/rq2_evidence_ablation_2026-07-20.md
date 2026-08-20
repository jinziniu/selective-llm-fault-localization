# RQ2 Evidence-Quality Ablation (2026-07-20)

This report analyzes a small controlled evidence-package ablation on the 11 Closure selected cases from the frozen `61..100` held-out aggregate. The retrieval candidate pool, selected bug IDs, model alias, Top-10 evaluation boundary, and selector are held fixed. Only the candidate evidence shown to the one-shot reranker changes.

## Configurations

- **Metadata only**: Candidate paths, ranks/scores, packages, class names, and method names; no retrieval reasons, no source snippets, no triggering-test source context.
- **Metadata + retrieval reasons**: Metadata-only candidate package plus retrieval evidence fields and deterministic retrieval reasons; no source snippets or triggering-test source context.
- **Full evidence package**: Current thesis evidence package: retrieval evidence, selected source snippets, and triggering-test source context.

## Aggregate Metrics

| Variant | Scope | N | Requests | Tokens | Seconds | Top-1 | Top-3 | Top-5 | Top-10 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Retrieval baseline | all_38 | 38 | 0 | 0 | 0.0 | 0.3947 | 0.5263 | 0.6053 | 0.7105 | 0.4945 |
| Retrieval baseline | selected_11 | 11 | 0 | 0 | 0.0 | 0.1818 | 0.3636 | 0.4545 | 0.5455 | 0.3068 |
| Metadata only | all_38 | 38 | 11 | 201075 | 140.615 | 0.4737 | 0.7105 | 0.7632 | 0.8421 | 0.6031 |
| Metadata only | selected_11 | 11 | 11 | 201075 | 140.615 | 0.4545 | 1.0000 | 1.0000 | 1.0000 | 0.6818 |
| Metadata + retrieval reasons | all_38 | 38 | 11 | 290136 | 180.06 | 0.5263 | 0.6842 | 0.7632 | 0.8421 | 0.6215 |
| Metadata + retrieval reasons | selected_11 | 11 | 11 | 290136 | 180.06 | 0.6364 | 0.9091 | 1.0000 | 1.0000 | 0.7455 |
| Full evidence package | all_38 | 38 | 11 | 409285 | 201.042 | 0.5000 | 0.6842 | 0.7632 | 0.8421 | 0.6127 |
| Full evidence package | selected_11 | 11 | 11 | 409285 | 201.042 | 0.5455 | 0.9091 | 1.0000 | 1.0000 | 0.7152 |

## Selected-Case Rank Changes

Per-bug selected-case ranks are saved in `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_selected_case_ranks.csv`. These rows compare each evidence configuration against the retrieval rank for the same selected bug.

## Interpretation Boundary

This is a small selected-case ablation, not a dataset-wide evidence-quality experiment. It supports a more concrete RQ2 statement about candidate evidence on Closure selected cases, but it should not be generalized to all datasets or all evidence designs.

## Artifacts

- Summary CSV: `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_summary.csv`
- Usage CSV: `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_usage.csv`
- Selected-case ranks CSV: `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_selected_case_ranks.csv`
- Summary JSON: `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_summary.json`
- Checksums CSV: `outputs/rq2_evidence_ablation_2026_07_20/evidence_ablation_artifact_checksums.csv`
