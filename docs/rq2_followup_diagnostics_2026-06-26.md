# RQ2 Follow-up Diagnostics

Date: 2026-06-26

These experiments are diagnostic follow-ups for RQ2. They do not change the final three-RQ thesis structure, the frozen held-out protocol, selector rules, retrieval scoring, prompt template, candidate pool size, or evaluation scripts.

## A1 Retrieval vs Full Rerank vs Selective Rerank

| dataset | setting | n | llm_calls | selected_fraction | tokens | avg_tokens_per_case | runtime_seconds | avg_runtime_per_case | top_1 | top_3 | top_5 | top_10 | mrr@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closure-61..100 | Retrieval only | 38 | 0 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.3947 | 0.5263 | 0.6053 | 0.7105 | 0.4945 |
| Closure-61..100 | Full one-shot rerank-all | 38 | 38 | 1.0000 | 1420902 | 37392.1579 | 706.7100 | 18.5976 | 0.7368 | 0.9211 | 0.9737 | 0.9737 | 0.8219 |
| Closure-61..100 | Selective one-shot rerank | 38 | 11 | 0.2895 | 408568 | 37142.5455 | 178.8380 | 16.2580 | 0.5526 | 0.7105 | 0.7632 | 0.8421 | 0.6513 |
| Math-21..40 | Retrieval only | 20 | 0 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.7000 | 0.9500 | 0.9500 | 0.9500 | 0.8167 |
| Math-21..40 | Full one-shot rerank-all | 20 | 20 | 1.0000 | 652313 | 32615.6500 | 395.4240 | 19.7712 | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 0.9500 |
| Math-21..40 | Selective one-shot rerank | 20 | 3 | 0.1500 | 106016 | 35338.6667 | 48.8620 | 16.2873 | 0.8000 | 1.0000 | 1.0000 | 1.0000 | 0.8917 |
| AboutWork-60 | Retrieval only | 60 | 0 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.5667 | 0.8333 | 0.9167 | 0.9333 | 0.6977 |
| AboutWork-60 | Full one-shot rerank-all | 60 | 60 | 1.0000 | 1867359 | 31122.6500 | 1151.8420 | 19.1974 | 0.8833 | 0.9833 | 1.0000 | 1.0000 | 0.9264 |
| AboutWork-60 | Selective one-shot rerank | 60 | 16 | 0.2667 | 519530 | 32470.6250 | 336.0340 | 21.0021 | 0.7000 | 0.9500 | 0.9667 | 0.9667 | 0.8117 |

## A2 Accuracy Retention and Cost Savings

| dataset | metric | retrieval | full_rerank | selective_rerank | full_gain_over_retrieval | selective_gain_over_retrieval | selective_retention_of_full_gain | call_saving_vs_full | token_saving_vs_full | runtime_saving_vs_full |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closure-61..100 | Top-1 | 0.3947 | 0.7368 | 0.5526 | 0.3421 | 0.1579 | 0.4615 | 0.7105 | 0.7125 | 0.7469 |
| Closure-61..100 | Top-3 | 0.5263 | 0.9211 | 0.7105 | 0.3947 | 0.1842 | 0.4667 | 0.7105 | 0.7125 | 0.7469 |
| Closure-61..100 | Top-5 | 0.6053 | 0.9737 | 0.7632 | 0.3684 | 0.1579 | 0.4286 | 0.7105 | 0.7125 | 0.7469 |
| Closure-61..100 | Top-10 | 0.7105 | 0.9737 | 0.8421 | 0.2632 | 0.1316 | 0.5000 | 0.7105 | 0.7125 | 0.7469 |
| Closure-61..100 | MRR@10 | 0.4945 | 0.8219 | 0.6513 | 0.3274 | 0.1568 | 0.4789 | 0.7105 | 0.7125 | 0.7469 |
| Math-21..40 | Top-1 | 0.7000 | 0.9000 | 0.8000 | 0.2000 | 0.1000 | 0.5000 | 0.8500 | 0.8375 | 0.8764 |
| Math-21..40 | Top-3 | 0.9500 | 1.0000 | 1.0000 | 0.0500 | 0.0500 | 1.0000 | 0.8500 | 0.8375 | 0.8764 |
| Math-21..40 | Top-5 | 0.9500 | 1.0000 | 1.0000 | 0.0500 | 0.0500 | 1.0000 | 0.8500 | 0.8375 | 0.8764 |
| Math-21..40 | Top-10 | 0.9500 | 1.0000 | 1.0000 | 0.0500 | 0.0500 | 1.0000 | 0.8500 | 0.8375 | 0.8764 |
| Math-21..40 | MRR@10 | 0.8167 | 0.9500 | 0.8917 | 0.1333 | 0.0750 | 0.5625 | 0.8500 | 0.8375 | 0.8764 |
| AboutWork-60 | Top-1 | 0.5667 | 0.8833 | 0.7000 | 0.3167 | 0.1333 | 0.4211 | 0.7333 | 0.7218 | 0.7083 |
| AboutWork-60 | Top-3 | 0.8333 | 0.9833 | 0.9500 | 0.1500 | 0.1167 | 0.7778 | 0.7333 | 0.7218 | 0.7083 |
| AboutWork-60 | Top-5 | 0.9167 | 1.0000 | 0.9667 | 0.0833 | 0.0500 | 0.6000 | 0.7333 | 0.7218 | 0.7083 |
| AboutWork-60 | Top-10 | 0.9333 | 1.0000 | 0.9667 | 0.0667 | 0.0333 | 0.5000 | 0.7333 | 0.7218 | 0.7083 |
| AboutWork-60 | MRR@10 | 0.6977 | 0.9264 | 0.8117 | 0.2287 | 0.1140 | 0.4984 | 0.7333 | 0.7218 | 0.7083 |

## B1 Selector Hard-case Coverage

| dataset | n | total_selected | selected_fraction | baseline_top_1_failures | baseline_top_5_failures | baseline_top_10_failures | selected_among_top_5_failures | selected_among_top_10_failures | selector_recall_on_top_5_failures | selector_recall_on_top_10_failures | unselected_top_5_failures_remaining | unselected_top_10_failures_remaining |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closure-61..100 | 38 | 11 | 0.2895 | 23 | 15 | 11 | 6 | 5 | 0.4000 | 0.4545 | 9 | 6 |
| Math-21..40 | 20 | 3 | 0.1500 | 6 | 1 | 1 | 1 | 1 | 1.0000 | 1.0000 | 0 | 0 |
| AboutWork-60 | 60 | 16 | 0.2667 | 26 | 5 | 4 | 3 | 2 | 0.6000 | 0.5000 | 2 | 2 |
| Easy Finance clean63 | 63 | 10 | 0.1587 | 38 | 9 | 8 | 9 | 8 | 1.0000 | 1.0000 | 0 | 0 |
| Mockito-21..30 | 9 | 4 | 0.4444 | 5 | 4 | 3 | 2 | 2 | 0.5000 | 0.6667 | 2 | 1 |
| Mockito-31..38 | 8 | 4 | 0.5000 | 7 | 2 | 1 | 2 | 1 | 1.0000 | 1.0000 | 0 | 0 |

## B2 Selected-case Effect and Degradation

| dataset | selected_n | improved_cases | degraded_cases | unchanged_cases | mean_drr@10 | positive_rr_changes | negative_rr_changes | zero_rr_changes | top_5_improved_cases | top_5_degraded_cases | top_10_improved_cases | top_10_degraded_cases | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closure-61..100 | 11 | 9 | 1 | 1 | 0.5417 | 9 | 1 | 1 | 6 | 0 | 5 | 0 | Closure-82:RR 1.0000->0.5000 |
| Math-21..40 | 3 | 2 | 0 | 1 | 0.5000 | 2 | 0 | 1 | 1 | 0 | 1 | 0 |  |
| AboutWork-60 | 16 | 9 | 0 | 7 | 0.4275 | 9 | 0 | 7 | 3 | 0 | 2 | 0 |  |
| Easy Finance clean63 | 10 | 10 | 0 | 0 | 0.6815 | 10 | 0 | 0 | 8 | 0 | 8 | 0 |  |
| Mockito-31..38 | 4 | 4 | 0 | 0 | 0.8393 | 4 | 0 | 0 | 2 | 0 | 1 | 0 |  |

## C1 Aggregate Variance

| dataset | setting | runs | top_1_mean | top_1_sd | top_1_min | top_1_max | top_3_mean | top_3_sd | top_3_min | top_3_max | top_5_mean | top_5_sd | top_5_min | top_5_max | top_10_mean | top_10_sd | top_10_min | top_10_max | mrr@10_mean | mrr@10_sd | mrr@10_min | mrr@10_max | invalid_json_count_mean | tokens_mean | runtime_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Closure-61..100 | Selective rerank repeated runs | 5 | 0.5421 | 0.0235 | 0.5263 | 0.5789 | 0.6895 | 0.0288 | 0.6579 | 0.7105 | 0.7579 | 0.0118 | 0.7368 | 0.7632 | 0.8421 | 0.0000 | 0.8421 | 0.8421 | 0.6383 | 0.0163 | 0.6237 | 0.6645 | 0.0000 | 413946.4000 | 236.5630 |

## C2 Per-run Results

| run_id | llm_calls | tokens | runtime | top_1 | top_3 | top_5 | top_10 | mrr@10 | invalid_json_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 11 | 408568 | 178.8380 | 0.5526 | 0.7105 | 0.7632 | 0.8421 | 0.6513 | 0 | original reported run |
| run1 | 11 | 414621 | 238.5890 | 0.5526 | 0.7105 | 0.7632 | 0.8421 | 0.6425 | 0 | follow-up repeated run |
| run2 | 11 | 413333 | 238.3770 | 0.5263 | 0.6579 | 0.7632 | 0.8421 | 0.6237 | 0 | follow-up repeated run |
| run3 | 11 | 415820 | 257.6750 | 0.5263 | 0.7105 | 0.7632 | 0.8421 | 0.6338 | 0 | follow-up repeated run |
| run4 | 11 | 412649 | 221.3740 | 0.5789 | 0.7105 | 0.7632 | 0.8421 | 0.6645 | 0 | follow-up repeated run |
| run5 | 11 | 413309 | 226.8000 | 0.5263 | 0.6579 | 0.7368 | 0.8421 | 0.6272 | 0 | follow-up repeated run |

## Artifacts

```text
outputs/rq2_followup_2026_06_26/
outputs/prompts_rq2_followup_2026_06_26/
outputs/rq2_followup_2026_06_26/run_manifest.csv
outputs/rq2_followup_2026_06_26/run_manifest.json
```
