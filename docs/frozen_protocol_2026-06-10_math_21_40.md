# Frozen Protocol: Math-21..40 Fresh Validation

Date: 2026-06-10

This protocol freezes the non-Closure Defects4J fresh validation slice before
any Math-21..40 LLM call. Results from this slice must not be used to change
retrieval, selector, prompt, snippet scoring, or merge rules before reporting
the run.

## Objective

Add one non-Closure Defects4J validation slice:

```text
Project: Math
Bug IDs: 21..40
Expected N: 20 before infrastructure skips
```

This slice is a generalization check for the current pipeline. It is not the
primary benchmark, and it is not a full Defects4J-wide result. The primary clean
held-out benchmark remains Closure-61..100.

## Main Method

The frozen method is:

```text
focused hybrid retrieval with direct hints
-> generic non-oracle selector
-> one-shot DeepSeek rerank on selected cases
-> retrieval fallback for unselected cases
-> file-level evaluation
```

Agentic inspection and verifier rerank are not part of this Math main-method
run.

## Fixed Retrieval Parameters

Use focused hybrid retrieval with direct-hint retention:

```text
top_k = 50
force_direct_hints = true
force_reference_hints = false
force_pass_chain_hints = false
force_type_system_hints = false
```

Run a retrieval-only Top-100 sensitivity output before any LLM call:

```text
top_k = 100
force_direct_hints = true
```

The Top-100 output is used only for Recall@100 and top-50-miss sensitivity. The
main retrieval baseline remains the frozen Top-50 output.

## Fixed Selector Parameters

Use the existing generic selector exactly as implemented:

```text
score_ratio_threshold = 1.02
include_top1_without_direct = true
direct_hint_count_threshold = 7
include_patterns = true
pass_chain_min_boost = 1000.0
```

The selector command must pass `--bugs` so non-oracle bug/test text patterns such
as state-reset evidence are enabled. Do not pass Closure- or Mockito-specific
cost-control switches.

The selector may use:

- retrieval score ratio and top files
- direct stack/test class hint metadata
- bug/test text pattern signals such as state-reset/type-cycle/pass-chain terms
- candidate file names and retrieval metadata

The selector must not use:

- ground-truth files
- fixed commit diffs
- post-fix source code
- evaluation ranks
- manual inspection of Math-21..40 outcomes

## Fixed Rerank Parameters

Use one-shot DeepSeek rerank on selected cases only:

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

The output is normalized by existing validation logic:

- remove files outside the candidate pool
- remove duplicates
- keep top output files
- fill missing entries using retrieval order

## Evaluation

Report retrieval baseline:

- Top-1, Top-3, Top-5, Top-10
- Recall@10, Recall@20, Recall@50, Recall@100
- MRR
- raw counts
- median RR and SD(RR)
- per-bug ranks

Report final merged selective rerank:

- Top-1, Top-3, Top-5, Top-10
- MRR
- raw counts
- median RR and SD(RR)
- selected / unselected subset metrics
- selector false negatives
- total DeepSeek calls
- total token usage

Use the existing file-level hit definition:

```text
success if any ground-truth file appears in top-k
```

## Stop Rule

After the dataset build and retrieval/selector steps begin:

- do not tune selector rules
- do not add prompt rules
- do not add snippet terms
- do not change retrieval weighting
- do not rerun failed LLM cases with custom diagnostics for the main result

If a bug cannot be checked out, compiled, tested, or evaluated, record the bug ID
and reason. Do not silently replace it with another Math bug ID unless a revised
protocol is written before the replacement run.

## Commands

Dataset:

```bash
python3 scripts/build_defects4j_dataset.py \
  --project Math \
  --bugs 21-40 \
  --out data/defects4j/math_fresh_21_40.jsonl \
  --skip-failures
```

Retrieval Top-50:

```bash
python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --out outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --top-k 50 \
  --force-direct-hints
```

Retrieval Top-100 sensitivity:

```bash
python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --out outputs/math_fresh_21_40_hybrid_focused_direct_top100.jsonl \
  --top-k 100 \
  --force-direct-hints
```

Evaluate retrieval:

```bash
python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --pred outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --ks 1,3,5,10,20,50 \
  --per-bug \
  --out outputs/math_fresh_21_40_hybrid_focused_direct_top50_eval.json

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --pred outputs/math_fresh_21_40_hybrid_focused_direct_top100.jsonl \
  --ks 1,3,5,10,20,50,100 \
  --per-bug \
  --out outputs/math_fresh_21_40_hybrid_focused_direct_top100_eval.json
```

Selector:

```bash
python3 scripts/select_rerank_candidates.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --pred outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --out outputs/math_fresh_21_40_selector_generic_t102_h7_patterns.json
```

Rerank dry-run:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --bm25 outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --out outputs/math_fresh_21_40_rerank_dryrun_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --provider dry-run \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --max-test-context-chars 12000 \
  --prompt-dir outputs/prompts_math_fresh_21_40_generic_t102_h7_patterns_s12_ctx12000_top50_dryrun
```

The dry-run and DeepSeek commands must include `--bug-ids` with the selector
output's selected IDs.

DeepSeek rerank:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --bm25 outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --out outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --provider deepseek \
  --model deepseek-v4-flash \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --max-test-context-chars 12000 \
  --prompt-dir outputs/prompts_math_fresh_21_40_generic_t102_h7_patterns_s12_ctx12000_top50_deepseek
```

Merge and evaluate:

```bash
python3 scripts/merge_selective_rerank.py \
  --baseline outputs/math_fresh_21_40_hybrid_focused_direct_top50.jsonl \
  --rerank outputs/math_fresh_21_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --selection outputs/math_fresh_21_40_selector_generic_t102_h7_patterns.json \
  --out outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --top-output 10

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/math_fresh_21_40.jsonl \
  --pred outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --ks 1,3,5,10 \
  --per-bug \
  --out outputs/math_fresh_21_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_eval.json
```

