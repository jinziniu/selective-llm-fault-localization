# Closure Held-Out 61..80 Validation Report

Date: 2026-06-01

Protocol:

```text
docs/frozen_protocol_2026-06-01.md
```

## Goal

Run a frozen held-out validation after the Closure fresh `21..60` cost-control experiments. This run must not tune selector rules, prompt rules, snippet rules, or retrieval parameters based on held-out results.

## Dataset

Requested:

```text
Closure-61..80
```

Built:

```text
records: 19
skipped: Closure-63, not listed in active-bugs.csv
```

Output:

```text
data/defects4j/closure_heldout_61_80.jsonl
```

## Frozen Retrieval

Command shape:

```text
focused hybrid retrieval
top_k=50
force_direct_hints=true
force_pass_chain_hints=true
force_type_system_hints=true
force_reference_hints=false
```

Output:

```text
outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl
outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50_eval.json
```

Retrieval result:

```text
bugs:   19
Top-1:  0.4737
Top-3:  0.4737
Top-5:  0.5789
Top-10: 0.7368
Top-20: 0.8947
Top-50: 1.0000
MRR:    0.5344
```

Per-bug baseline ranks:

```text
Closure-61: 8
Closure-62: 1
Closure-64: 4
Closure-65: 8
Closure-66: 1
Closure-67: 48
Closure-68: 1
Closure-69: 1
Closure-70: 14
Closure-71: 1
Closure-72: 12
Closure-73: 4
Closure-74: 1
Closure-75: 21
Closure-76: 18
Closure-77: 8
Closure-78: 1
Closure-79: 1
Closure-80: 1
```

Interpretation:

- Candidate Recall@50 is 1.0000, so one-shot rerank has a viable candidate pool for every held-out record.
- Top-10 is only 0.7368, so selective rerank has room to improve developer-facing ranking.

## Frozen Selector

Command shape:

```text
scripts/select_rerank_candidates.py
--closure-cost-control-v3
score_ratio_threshold=1.02
direct_hint_count_threshold=7
pass_chain_min_boost=1000.0
```

Output:

```text
outputs/closure_heldout_61_80_selector_closure_cost_control_v3.json
```

Selected:

```text
selected: 6 / 19
selected_fraction: 0.3158
selected ids:
Closure-64, Closure-69, Closure-70, Closure-72, Closure-76, Closure-77
```

Reason counts:

```text
low_score_ratio<=1.02: 1
pattern:closure_code_output: 1
pattern:closure_deep_specific_direct_hint: 2
pattern:type_system: 2
```

Selector coverage note:

- The selector covered several important baseline hard cases: `Closure-70`, `Closure-72`, `Closure-76`, and `Closure-77`.
- It did not select `Closure-61`, `Closure-65`, `Closure-67`, or `Closure-75`, all of which were outside Top-5 in baseline retrieval.
- This false-negative behavior should be analyzed in a later protocol, but it must not change this frozen held-out result.

## DeepSeek Rerank

Fixed rerank parameters:

```text
provider=deepseek
top_candidates=50
top_output=10
max_snippet_lines=12
include_retrieval_evidence=true
include_test_context=true
max_test_context_chars=12000
```

Output:

```text
outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl
outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50_usage.json
```

Selected-case rerank result:

```text
bugs:   6
Top-1:  0.6667
Top-3:  1.0000
Top-5:  1.0000
Top-10: 1.0000
MRR:    0.8056
```

Selected-case rank changes:

```text
Closure-64: 4  -> 2
Closure-69: 1  -> 1
Closure-70: 14 -> 3
Closure-72: 12 -> 1
Closure-76: 18 -> 1
Closure-77: 8  -> 1
```

Usage:

```text
records: 6
total_tokens: 225551
avg_total_tokens: 37591.83
total_duration_seconds: 106.985
avg_duration_seconds: 17.831
```

Execution note:

- The first DeepSeek attempts hit API read timeouts before output was written.
- `DEEPSEEK_TIMEOUT` support and incremental JSONL writing were added as execution robustness changes.
- These changes do not alter retrieval, selector, prompt, snippet, or scoring behavior.

## Merged Result

Output:

```text
outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl
outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
```

Merged result over all 19 records:

```text
Top-1:  0.6316
Top-3:  0.7368
Top-5:  0.7895
Top-10: 0.8947
MRR:    0.7018
```

Improvement over retrieval baseline:

```text
Top-1:  +0.1579
Top-3:  +0.2632
Top-5:  +0.2105
Top-10: +0.1579
MRR:    +0.1673
```

Top-20 and Top-50 should be interpreted from the retrieval baseline, not the merged output, because the main method output is intentionally truncated to Top-10.

Merged ranks:

```text
Closure-61: 8
Closure-62: 1
Closure-64: 2
Closure-65: 8
Closure-66: 1
Closure-67: miss in top10
Closure-68: 1
Closure-69: 1
Closure-70: 3
Closure-71: 1
Closure-72: 1
Closure-73: 4
Closure-74: 1
Closure-75: miss in top10
Closure-76: 1
Closure-77: 1
Closure-78: 1
Closure-79: 1
Closure-80: 1
```

## Decision

This is a positive held-out validation for the current rerank evidence and selected-case behavior:

- The selected cases all reached Top-3.
- The merged main method improved Top-1, Top-3, Top-5, Top-10, and MRR over frozen retrieval.
- The selector selected only 31.6% of records.

The main limitation is selector recall:

- `Closure-61`, `Closure-65`, `Closure-67`, and `Closure-75` were baseline Top-5 misses but not selected.
- `Closure-67` and `Closure-75` remain the most important main-method misses because their baseline ranks were 48 and 21.

Do not tune on this run. Use these failures as error-analysis inputs for the next frozen protocol.
