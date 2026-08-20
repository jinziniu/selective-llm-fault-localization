# Frozen Protocol: Closure 81..100 Held-Out Validation

Date: 2026-06-02

This protocol freezes the next held-out validation after `Closure-61..80`. The error analysis from `Closure-61..80` may be reported, but it must not change retrieval, selector, prompt, snippet, or scoring rules for this run.

## Objective

Validate the current selective evidence-aware fault-localization pipeline on a new Closure slice that was not used for selector tuning:

```text
Closure-81..100
```

Use `--skip-failures` during dataset construction. Bugs not listed in `active-bugs.csv` or not buildable are skipped and reported.

## Main Method

The main method remains unchanged:

```text
focused hybrid retrieval
-> Closure cost-control v3 selector
-> one-shot DeepSeek rerank on selected cases
-> retrieval fallback for non-selected cases
-> file-level evaluation
```

Do not add utility-file, code-output, pass-family, or NodeUtil-specific selector changes from the previous error analysis. Those hypotheses are reserved for a later protocol.

## Fixed Retrieval Parameters

```text
top_k = 50
force_direct_hints = true
force_pass_chain_hints = true
force_type_system_hints = true
force_reference_hints = false
```

Reference hints remain disabled because broad Closure reference expansion was previously noisy.

## Fixed Selector Parameters

```text
--closure-cost-control-v3
score_ratio_threshold = 1.02
direct_hint_count_threshold = 7
pass_chain_min_boost = 1000.0
include_top1_without_direct = true
include_patterns = true
```

The selector is non-oracle: it must not use ground truth, fixed commit diffs, post-fix code, or evaluation ranks.

## Fixed Rerank Parameters

```text
provider = deepseek
top_candidates = 50
top_output = 10
max_snippet_lines = 12
include_retrieval_evidence = true
include_test_context = true
max_test_context_chars = 12000
```

The output is normalized by existing validation logic:

- remove files outside the candidate pool
- remove duplicates
- keep top output files
- fill missing entries using retrieval order

## Evaluation

Report:

- Top-1, Top-3, Top-5, Top-10, Top-20, Top-50 from retrieval baseline
- Top-1, Top-3, Top-5, Top-10 and MRR from merged selective-rerank output
- MRR
- selected cases / total cases
- total tokens and average tokens per selected case
- total duration
- per-bug correct ranks
- selector recall over baseline Top-5 and Top-10 failures

Use the existing file-level hit definition:

```text
success if any ground-truth file appears in top-k
```

## Stop Rule

After this held-out run starts:

- do not tune selector rules
- do not add prompt rules
- do not add snippet terms
- do not rerun failed cases with custom diagnostics for the main reported number

Failures should be recorded only as error analysis for a later protocol.

## Commands

Dataset:

```bash
python3 scripts/build_defects4j_dataset.py \
  --project Closure \
  --bugs 81-100 \
  --out data/defects4j/closure_heldout_81_100.jsonl \
  --skip-failures
```

Retrieval:

```bash
python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/closure_heldout_81_100.jsonl \
  --out outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --top-k 50 \
  --force-direct-hints \
  --force-pass-chain-hints \
  --force-type-system-hints
```

Selector:

```bash
python3 scripts/select_rerank_candidates.py \
  --bugs data/defects4j/closure_heldout_81_100.jsonl \
  --pred outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --out outputs/closure_heldout_81_100_selector_closure_cost_control_v3.json \
  --closure-cost-control-v3
```

Rerank:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/closure_heldout_81_100.jsonl \
  --bm25 outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --out outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --provider deepseek \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --max-test-context-chars 12000 \
  --prompt-dir outputs/prompts_closure_heldout_81_100_cost_control_v3_s12_ctx12000_top50
```

The rerank command must include `--bug-ids` with the selector output's selected ids.

Merge and evaluate:

```bash
python3 scripts/merge_selective_rerank.py \
  --baseline outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --rerank outputs/closure_heldout_81_100_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --selection outputs/closure_heldout_81_100_selector_closure_cost_control_v3.json \
  --out outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --top-output 10

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/closure_heldout_81_100.jsonl \
  --pred outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --ks 1,3,5,10,20,50 \
  --per-bug \
  --out outputs/closure_heldout_81_100_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
```
