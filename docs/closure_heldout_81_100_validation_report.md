# Closure Held-Out 81..100 Validation Report

Date: 2026-06-02

Protocol:

```text
docs/frozen_protocol_2026-06-02_closure_81_100.md
```

## Goal

Run a second frozen held-out Closure validation after `Closure-61..80`, without applying any selector, prompt, snippet, or retrieval changes suggested by the previous error analysis.

## Dataset

Requested:

```text
Closure-81..100
```

Built:

```text
records: 19
skipped: Closure-93, not listed in active-bugs.csv
```

Output:

```text
data/defects4j/closure_heldout_81_100.jsonl
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
outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl
outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50_eval.json
```

Retrieval result:

```text
bugs:   19
Top-1:  0.3158
Top-3:  0.5789
Top-5:  0.6316
Top-10: 0.6842
Top-20: 0.7895
Top-50: 0.9474
MRR:    0.4815
```

Per-bug baseline ranks:

```text
Closure-81: 2
Closure-82: 1
Closure-83: 2
Closure-84: 2
Closure-85: 1
Closure-86: 4
Closure-87: 2
Closure-88: 34
Closure-89: 1
Closure-90: 11
Closure-91: 16
Closure-92: 1
Closure-94: 6
Closure-95: 2
Closure-96: 1
Closure-97: 1
Closure-98: miss in top50
Closure-99: 34
Closure-100: 50
```

Interpretation:

- Candidate Recall@50 is 0.9474. `Closure-98` is not in the top-50 candidate pool, so one-shot rerank cannot recover it.
- Top-10 is 0.6842, leaving several developer-facing ranking failures for selective rerank.

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
outputs/closure_heldout_81_100_selector_closure_cost_control_v3.json
```

Selected:

```text
selected: 5 / 19
selected_fraction: 0.2632
selected ids:
Closure-82, Closure-83, Closure-91, Closure-95, Closure-100
```

Reason counts:

```text
low_score_ratio<=1.02: 2
pattern:closure_deep_specific_direct_hint: 1
pattern:type_system: 2
top1_without_direct_hint: 1
```

Selector coverage note:

- Baseline Top-5 failures: `Closure-88`, `Closure-90`, `Closure-91`, `Closure-94`, `Closure-98`, `Closure-99`, `Closure-100`.
- The selector covered 2/7 Top-5 failures: `Closure-91` and `Closure-100`.
- Baseline Top-10 failures: `Closure-88`, `Closure-90`, `Closure-91`, `Closure-98`, `Closure-99`, `Closure-100`.
- The selector covered 2/6 Top-10 failures: `Closure-91` and `Closure-100`.
- `Closure-98` is a candidate-retrieval miss, not a selector miss.

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
outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl
outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50_usage.json
```

Selected-case rerank result:

```text
bugs:   5
Top-1:  0.8000
Top-3:  1.0000
Top-5:  1.0000
Top-10: 1.0000
MRR:    0.9000
```

Selected-case rank changes:

```text
Closure-82:  1  -> 2
Closure-83:  2  -> 1
Closure-91:  16 -> 1
Closure-95:  2  -> 1
Closure-100: 50 -> 1
```

Usage:

```text
records: 5
total_tokens: 183017
avg_total_tokens: 36603.40
total_duration_seconds: 71.853
avg_duration_seconds: 14.371
```

## Merged Result

Output:

```text
outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl
outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
```

Merged result over all 19 records:

```text
Top-1:  0.4737
Top-3:  0.6842
Top-5:  0.7368
Top-10: 0.7895
MRR:    0.6009
```

Improvement over retrieval baseline:

```text
Top-1:  +0.1579
Top-3:  +0.1053
Top-5:  +0.1053
Top-10: +0.1053
MRR:    +0.1194
```

Top-20 and Top-50 should be interpreted from the retrieval baseline, not the merged output, because the main method output is intentionally truncated to Top-10.

Merged ranks:

```text
Closure-81: 2
Closure-82: 2
Closure-83: 1
Closure-84: 2
Closure-85: 1
Closure-86: 4
Closure-87: 2
Closure-88: miss in top10
Closure-89: 1
Closure-90: miss in top10
Closure-91: 1
Closure-92: 1
Closure-94: 6
Closure-95: 1
Closure-96: 1
Closure-97: 1
Closure-98: miss in top10
Closure-99: miss in top10
Closure-100: 1
```

## Decision

This is another positive frozen validation for selected-case rerank behavior and overall Top-k improvement:

- The selected cases all reached Top-3.
- The merged main method improved Top-1, Top-3, Top-5, Top-10, and MRR over frozen retrieval.
- Selector recall remains the main limitation: it selected only 2/7 baseline Top-5 failures and 2/6 baseline Top-10 failures.
- Candidate retrieval also needs attention because `Closure-98` was outside Top-50.

Do not tune on this run. Use these failures to design a later frozen selector/candidate-retrieval protocol.
