# Math-21..40 Fresh Validation Report

Date: 2026-06-10

This report adds a small non-Closure Defects4J validation slice after the main
Closure-61..100 held-out result. It is a generalization check, not a full
Defects4J-wide benchmark.

Protocol:

```text
docs/frozen_protocol_2026-06-10_math_21_40.md
```

## Dataset

| Field | Value |
|---|---:|
| Project | Math |
| Bug IDs | 21..40 |
| Expected N | 20 |
| Usable N | 20 |
| Skipped bugs | 0 |

Dataset file:

```text
data/defects4j/math_fresh_21_40.jsonl
```

## Method

Frozen pipeline:

```text
focused hybrid retrieval with direct hints
-> generic selector
-> one-shot DeepSeek on selected cases
-> retrieval fallback for unselected cases
```

Selector settings:

```text
score_ratio_threshold = 1.02
include_top1_without_direct = true
direct_hint_count_threshold = 7
include_patterns = true
pass_chain_min_boost = 1000.0
closure-specific switches = false
mockito-specific switches = false
```

Rerank settings:

```text
provider = deepseek
model = deepseek-v4-flash
top_candidates = 50
top_output = 10
max_snippet_lines = 12
include_retrieval_evidence = true
include_test_context = true
max_test_context_chars = 12000
```

## Results

| Dataset | Method | Calls | Top-1 | Top-3 | Top-5 | Top-10 | MRR |
|---|---|---:|---:|---:|---:|---:|---:|
| Math-21..40 | Retrieval Top-50 | 0 / 20 | 14/20 | 19/20 | 19/20 | 19/20 | 0.8186 |
| Math-21..40 | Selective DeepSeek | 3 / 20 | 16/20 | 20/20 | 20/20 | 20/20 | 0.8917 |

The method improves Top-1 by 2 bugs and closes the one baseline Top-10 miss.
The main recovered case is `Math-31`, which moves from retrieval rank 26 to
reranked rank 1.

## Recall@K

| Method | R@10 | R@20 | R@50 | R@100 | R@100 - R@50 |
|---|---:|---:|---:|---:|---:|
| Retrieval | 0.95 | 0.95 | 1.00 | 1.00 | 0.00 |

For this Math slice, Top-50 already contains every ground-truth file. Increasing
the retrieval output to Top-100 does not add candidate recall.

## Selector Behavior

The selector chose 3 / 20 bugs:

| Bug | Selector reason | Retrieval rank | Final rank |
|---|---|---:|---:|
| Math-22 | low_score_ratio<=1.02 | 1 | 1 |
| Math-29 | top1_without_direct_hint | 2 | 1 |
| Math-31 | pattern:state_reset | 26 | 1 |

Subset metrics:

| Subset | N | Baseline Top-5 | Final Top-5 | Baseline MRR | Final MRR |
|---|---:|---:|---:|---:|---:|
| Selected | 3 | 0.6667 | 1.0000 | 0.5128 | 1.0000 |
| Unselected | 17 | 1.0000 | 1.0000 | 0.8725 | 0.8725 |

The selector concentrated calls on the only hard Top-10 miss (`Math-31`) and one
rank-2 case (`Math-29`). Unselected cases were already strong under retrieval
fallback.

## Paired Tests

| Test | b | c | p |
|---|---:|---:|---:|
| McNemar Top-1 | 2 | 0 | 0.5000 |
| McNemar Top-3 | 1 | 0 | 1.0000 |
| McNemar Top-5 | 1 | 0 | 1.0000 |
| McNemar Top-10 | 1 | 0 | 1.0000 |
| Wilcoxon over reciprocal rank | positive=2 | negative=0 | 0.1797 |

These tests are descriptive. The sample is small and the baseline is already
very strong, so the Math slice is better interpreted as a generalization check
than as a significance-driven benchmark.

## Token Usage

| Calls | Total tokens | Avg tokens/call | Total duration seconds | Avg duration seconds |
|---:|---:|---:|---:|---:|
| 3 | 106016 | 35338.67 | 48.862 | 16.287 |

Usage file:

```text
outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_usage.json
```

## Error Analysis

There are no final Top-10 misses. Remaining non-Top-1 cases are unselected
fallback cases:

| Bug | Final rank | Note |
|---|---:|---|
| Math-32 | 2 | Retrieval fallback already places the file in Top-3 |
| Math-33 | 2 | Retrieval fallback already places the file in Top-3 |
| Math-39 | 3 | Retrieval fallback already places the file in Top-3 |
| Math-40 | 2 | Retrieval fallback already places the file in Top-3 |

The main limitation exposed by this slice is not candidate recall. Candidate
recall is complete by Top-50. The practical question is whether calling DeepSeek
on additional rank-2/rank-3 cases is worth the cost. Under the frozen selector,
the method spends only 3 calls and improves the single genuinely hard miss,
which is a favorable cost-control outcome.

## Interpretation

Math-21..40 supports the broader claim that the selective rerank pipeline is not
only a Closure artifact. However, this slice is easier than Closure-61..100
under the current focused retrieval: retrieval already reaches Top-5/Top-10
0.95 and Top-50 recall 1.00. Therefore, the thesis should use Math-21..40 as
supporting non-Closure validation, while keeping Closure-61..100 as the main
held-out benchmark.

## Artifacts

```text
data/defects4j/math_fresh_21_40.jsonl
outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl
outputs/math_fresh_21_40_hybrid_focused_direct_top50_eval.json
outputs/math_fresh_21_40_hybrid_focused_direct_top100.jsonl
outputs/math_fresh_21_40_hybrid_focused_direct_top100_eval.json
outputs/math_fresh_21_40_selector_generic_t102_h7_patterns.json
outputs/math_fresh_21_40_rerank_dryrun_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl
outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl
outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_usage.json
outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl
outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_eval.json
```

