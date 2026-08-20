# Frozen Protocol: Held-Out Defects4J Validation

Date: 2026-06-01

This protocol freezes the next held-out validation run. Results from the held-out set must not be used to change selector rules, prompt rules, snippet rules, or retrieval parameters before reporting the run.

## Objective

Validate the current selective evidence-aware fault-localization pipeline on a held-out Defects4J slice that was not used to tune the latest Closure and Mockito selectors.

Primary held-out slice:

```text
Closure-61..80
```

Use `--skip-failures` during dataset construction. Deprecated or non-buildable bugs are skipped and reported.

## Main Method

The main method is:

```text
focused hybrid retrieval
-> Closure cost-control v3 selector
-> one-shot DeepSeek rerank on selected cases
-> retrieval fallback for non-selected cases
-> file-level evaluation
```

Controlled agentic inspection and verifier rerank are not part of this held-out main-method run.

## Fixed Retrieval Parameters

Run focused hybrid retrieval with all current Closure-specific deterministic hints enabled:

```text
top_k = 50
force_direct_hints = true
force_pass_chain_hints = true
force_type_system_hints = true
force_reference_hints = false
```

Reference hints remain disabled because previous Closure experiments showed broad reference expansion is noisy.

## Fixed Selector Parameters

Use the current experimental Closure selector exactly as implemented before seeing held-out results:

```text
--closure-cost-control-v3
score_ratio_threshold = 1.02
direct_hint_count_threshold = 7
pass_chain_min_boost = 1000.0
include_top1_without_direct = true
include_patterns = true
```

The selector is non-oracle: it must not use `ground_truth`, fixed commit diffs, post-fix code, or any evaluation rank.

## Fixed Rerank Parameters

Use one-shot DeepSeek rerank:

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

- Top-1, Top-3, Top-5, Top-10, Top-20, Top-50
- MRR
- selected cases / total cases
- total tokens
- average tokens per selected case
- total duration
- per-bug correct ranks

Use the current file-level hit definition:

```text
success if any ground-truth file appears in top-k
```

This is the same metric used by previous experiments. All-file recall remains future work.

## Stop Rule

After the held-out run starts:

- do not tune selector rules
- do not add new prompt rules
- do not add new snippet terms
- do not rerun a failed case with custom diagnostics for the main reported number

If failures are interesting, record them as error analysis only and use them to design a later protocol.

## Commands

Dataset:

```bash
python3 scripts/build_defects4j_dataset.py \
  --project Closure \
  --bugs 61-80 \
  --out data/defects4j/closure_heldout_61_80.jsonl \
  --skip-failures
```

Retrieval:

```bash
python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/closure_heldout_61_80.jsonl \
  --out outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --top-k 50 \
  --force-direct-hints \
  --force-pass-chain-hints \
  --force-type-system-hints
```

Selector:

```bash
python3 scripts/select_rerank_candidates.py \
  --bugs data/defects4j/closure_heldout_61_80.jsonl \
  --pred outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --out outputs/closure_heldout_61_80_selector_closure_cost_control_v3.json \
  --closure-cost-control-v3
```

Rerank:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/closure_heldout_61_80.jsonl \
  --bm25 outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --out outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --provider deepseek \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --max-test-context-chars 12000 \
  --prompt-dir outputs/prompts_closure_heldout_61_80_cost_control_v3_s12_ctx12000_top50
```

The rerank command must include `--bug-ids` with the selector output's selected ids.

Merge and evaluate:

```bash
python3 scripts/merge_selective_rerank.py \
  --baseline outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl \
  --rerank outputs/closure_heldout_61_80_rerank_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --selection outputs/closure_heldout_61_80_selector_closure_cost_control_v3.json \
  --out outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --top-output 10

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/closure_heldout_61_80.jsonl \
  --pred outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50.jsonl \
  --ks 1,3,5,10,20,50 \
  --per-bug \
  --out outputs/closure_heldout_61_80_merged_deepseek_closure_cost_control_v3_s12_ctx12000_top50_eval.json
```
