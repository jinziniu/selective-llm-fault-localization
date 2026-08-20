# Frozen Protocol: Compress 1--40 Cross-Project Validation

Date: 2026-08-11

This protocol was written before constructing the Compress dataset, inspecting
retrieval results, selecting records, or making any LLM call. Compress has not
previously been used for method development, selector tuning, prompt design,
evidence-rule development, or diagnostic analysis in this thesis.

## Objective

Add an independent Defects4J project-level validation slice:

```text
Project: Compress
Active bug IDs: 1--40
Expected N: 40
```

The result must be reported regardless of direction. It is a frozen follow-up
validation and does not retroactively become part of the original June 2026
validation plan.

## Frozen Code State

Workspace Git commit at protocol creation:

```text
a6711cb Narrow thesis contribution statement
```

The experiment scripts are untracked in the workspace, so their contents are
frozen with SHA-256 hashes:

```text
0d4cbb4a4bf4e6f8848fa38e7952b7b2caf384f4586a790b4aa51044e3ce7a67  scripts/build_defects4j_dataset.py
aacbcfbae483004a6da63de63e55464b999491c5c67523894146945674b45cde  scripts/run_hybrid_retrieval.py
51f3bfa0af82184233c21217ee1a337ab902c2221dd82627f64d9124fc77036b  scripts/select_rerank_candidates.py
a1cf0bc2d1aa66a18d9fe4fb59b7748e3b51cea9324d73b5a35249fa351455e1  scripts/run_llm_rerank.py
12e1eda191aa5da9176596de8172835878536ba8f8868d1399b8a28261541ca9  scripts/merge_selective_rerank.py
c904eba9e65591f44f83039236af85f2d1be616300fa4c06d0b66a610db99fae  scripts/evaluate_predictions.py
e1452542f3875d8be188541da111ce65763ae84b674bf3b66cf35b23341fee9e  scripts/summarize_llm_usage.py
```

## Frozen Main Method

```text
focused hybrid retrieval with direct-hint retention
-> generic non-oracle selector
-> one-shot DeepSeek rerank on selected records
-> deterministic retrieval fallback on unselected records
-> file-level evaluation
```

No Compress-specific selector, retrieval, prompt, or snippet rule may be added.
Agentic inspection, verifier reranking, full rerank-all, and repeated hosted-
model runs are outside this validation.

## Retrieval Parameters

Main retrieval output:

```text
top_k = 50
force_direct_hints = true
force_reference_hints = false
force_pass_chain_hints = false
force_type_system_hints = false
```

A Top-100 output uses the same direct-hint setting and is used only for
candidate-recall sensitivity.

## Selector Parameters

Use the existing generic selector exactly as implemented:

```text
score_ratio_threshold = 1.02
include_top1_without_direct = true
direct_hint_count_threshold = 7
include_patterns = true
pass_chain_min_boost = 1000.0
project-specific switches = false
```

The selector receives the bug JSONL only to enable existing non-oracle bug/test
text patterns. It must not use ground-truth files, fixed commits, repair diffs,
post-fix code, or evaluation ranks.

## Rerank Parameters

```text
provider = deepseek
model alias = deepseek-v4-flash
top_candidates = 50
top_output = 10
max_snippet_lines = 12
include_retrieval_evidence = true
include_test_context = true
max_test_context_chars = 12000
```

The execution date and returned usage/model metadata must be retained. The
historical provider-default thinking-mode limitation documented in the thesis
also applies to this follow-up run.

## Evaluation

Report the following without dropping negative or degraded records:

- usable and skipped bug IDs;
- retrieval Top-1, Top-3, Top-5, Top-10, and MRR@10;
- retrieval Recall@10, Recall@20, Recall@50, and Recall@100;
- selective Top-1, Top-3, Top-5, Top-10, and MRR@10;
- raw hit counts and per-bug first-correct-file ranks;
- selected fraction and selected IDs;
- selector coverage over retrieval Top-5 and Top-10 failures;
- total model requests, provider-reported tokens, and wall-clock seconds;
- invalid, duplicate, out-of-pool, fallback-completed, or missing outputs.

The success definition remains:

```text
success if any ground-truth modified source file appears within Top-k
```

## Stop Rule

After dataset construction begins:

- do not modify any frozen script;
- do not tune selector thresholds or add Compress-specific patterns;
- do not change candidate-pool or evidence settings;
- do not replace selected IDs manually;
- do not rerun individual records with custom prompts for the main result;
- record infrastructure failures and skipped IDs without silent replacement;
- preserve and report a negative or null aggregate result.

## Execution Note: Network Timeout Amendment

The initial selected-case run completed `Compress-2` and then stopped while
waiting for the `Compress-5` response because the DeepSeek client raised a read
timeout. The completed `Compress-2` record is preserved and is not rerun. Before
retrying the remaining five preselected IDs, the client network timeout is
raised from its default 120 seconds to 300 seconds through the
`DEEPSEEK_TIMEOUT` environment variable. The provider, model alias, selected
IDs, prompts, candidate pool, evidence settings, decoding request, and output
normalization remain unchanged. Retry outputs are written to a separate file,
and the timeout event remains part of the experiment record.

## Commands

Run from `project/fl-localizer` after loading `../defects4j-env.sh`.

### Dataset

```bash
python3 scripts/build_defects4j_dataset.py \
  --project Compress \
  --bugs 1-40 \
  --out data/defects4j/compress_frozen_1_40.jsonl \
  --skip-failures
```

### Retrieval

```bash
python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --out outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl \
  --top-k 50 \
  --force-direct-hints

python3 scripts/run_hybrid_retrieval.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --out outputs/compress_frozen_1_40_hybrid_focused_direct_top100.jsonl \
  --top-k 100 \
  --force-direct-hints
```

### Retrieval Evaluation

```bash
python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --pred outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl \
  --ks 1,3,5,10,20,50 \
  --per-bug \
  --out outputs/compress_frozen_1_40_hybrid_focused_direct_top50_eval.json

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --pred outputs/compress_frozen_1_40_hybrid_focused_direct_top100.jsonl \
  --ks 1,3,5,10,20,50,100 \
  --per-bug \
  --out outputs/compress_frozen_1_40_hybrid_focused_direct_top100_eval.json
```

### Selector

```bash
python3 scripts/select_rerank_candidates.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --pred outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl \
  --out outputs/compress_frozen_1_40_selector_generic_t102_h7_patterns.json
```

### Rerank

Use exactly the `selected_bug_ids` from the selector report:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --bm25 outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl \
  --out outputs/compress_frozen_1_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --provider deepseek \
  --model deepseek-v4-flash \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --max-test-context-chars 12000 \
  --bug-ids SELECTED_IDS \
  --prompt-dir outputs/prompts_compress_frozen_1_40_generic_t102_h7_patterns_s12_ctx12000_top50
```

### Merge and Evaluation

```bash
python3 scripts/merge_selective_rerank.py \
  --baseline outputs/compress_frozen_1_40_hybrid_focused_direct_top50.jsonl \
  --rerank outputs/compress_frozen_1_40_rerank_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --selection outputs/compress_frozen_1_40_selector_generic_t102_h7_patterns.json \
  --out outputs/compress_frozen_1_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --top-output 10

python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/compress_frozen_1_40.jsonl \
  --pred outputs/compress_frozen_1_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50.jsonl \
  --ks 1,3,5,10 \
  --per-bug \
  --out outputs/compress_frozen_1_40_merged_deepseek_generic_t102_h7_patterns_s12_ctx12000_top50_eval.json
```
