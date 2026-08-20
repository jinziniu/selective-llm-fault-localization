# Closure Frozen Held-Out 61..100 Aggregate Summary

Date: 2026-06-02

This document aggregates the two frozen Closure held-out runs:

```text
Closure-61..80: 19 records, Closure-63 skipped
Closure-81..100: 19 records, Closure-93 skipped
Total: 38 records
```

The aggregate uses only already reported frozen results. No selector, prompt, snippet, retrieval, or rerank rule was changed for this summary.

## Aggregate Result

| Dataset | Setting | Bugs | LLM Calls | Top-1 | Top-3 | Top-5 | Top-10 | MRR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Closure-61..100 held-out | frozen retrieval baseline | 38 | 0 | 0.3947 | 0.5263 | 0.6053 | 0.7105 | 0.5080 |
| Closure-61..100 held-out | frozen cost-control v3 + DeepSeek | 38 | 11 | 0.5526 | 0.7105 | 0.7632 | 0.8421 | 0.6513 |

Improvement over frozen retrieval:

```text
Top-1:  +0.1579
Top-3:  +0.1842
Top-5:  +0.1579
Top-10: +0.1316
MRR:    +0.1434
```

Token/runtime cost:

```text
selected: 11 / 38
selected_fraction: 0.2895
total_tokens: 408568
avg_total_tokens_per_selected_case: 37142.55
total_duration_seconds: 178.838
avg_duration_seconds_per_selected_case: 16.258
```

## Selector Coverage

Baseline Top-5 failures:

```text
count: 15
selected: 6
selected fraction over Top-5 failures: 0.4000
selected ids:
Closure-70, Closure-72, Closure-76, Closure-77, Closure-91, Closure-100
```

Baseline Top-10 failures:

```text
count: 11
selected: 5
selected fraction over Top-10 failures: 0.4545
selected ids:
Closure-70, Closure-72, Closure-76, Closure-91, Closure-100
```

Retrieval Top-50 misses:

```text
Closure-98
```

## Interpretation

The aggregate strengthens the held-out conclusion:

- Selective rerank improves Top-1, Top-3, Top-5, Top-10, and MRR across both frozen Closure slices.
- The selected cases are consistently useful for rerank; selected-case Top-3 is 1.0000 across both slices.
- The dominant remaining problem is selector recall: the selector covers only 6/15 baseline Top-5 failures in the aggregate.
- Candidate recall is mostly strong but not perfect; `Closure-98` is outside the retrieval Top-50 pool and cannot be recovered by rerank.

## Mockito Held-Out Availability

Mockito cannot currently provide a new held-out slice in this Defects4J checkout:

```text
active Mockito bugs: 1..38
already used:
  Mockito-1..20 pilot
  Mockito-21..30 fresh attempt
  Mockito-31..38 fresh validation
unused active Mockito bugs after 38: none
```

Therefore, Mockito should be reported as pilot plus fresh validation, not as a separate frozen held-out benchmark.

## Source Artifacts

```text
docs/frozen_protocol_2026-06-01.md
docs/frozen_protocol_2026-06-02_closure_81_100.md
docs/closure_heldout_61_80_validation_report.md
docs/closure_heldout_81_100_validation_report.md
outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50_eval.json
outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50_eval.json
outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
```
