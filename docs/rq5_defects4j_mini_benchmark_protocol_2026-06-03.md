# RQ5 Defects4J Diagnostic Mini-Benchmark Protocol

Date: 2026-06-03

This protocol freezes a small Defects4J diagnostic mini-benchmark for RQ5:
whether the agentic reranker and verifier extension are useful beyond the
one-shot evidence-aware reranker.

This is not a new main benchmark split. The main held-out Defects4J result
remains the Closure 61..100 frozen split. This mini-benchmark is diagnostic:
it intentionally covers failure modes already observed during method analysis,
so it should be interpreted as an extension/ablation study rather than as an
unbiased estimate of general performance.

## Objective

Compare three LLM-based strategies on the same frozen input cases:

1. One-shot evidence-aware reranking.
2. Agentic reranking with bounded inspect/search steps.
3. Agentic reranking followed by verifier reranking.

The comparison answers whether additional interaction and verification improve
file-level localization on representative Defects4J failure categories, and
whether any improvement justifies the added token/runtime cost.

## Frozen Case Set

The mini-benchmark contains 10 bugs across Math, Closure, and Mockito.

| Bug | Source slice | Baseline prediction file | Diagnostic role |
| --- | --- | --- | --- |
| Math-12 | `data/defects4j/math_pilot_20.jsonl` | `outputs/math_pilot_20_hybrid_focused_direct_top50.jsonl` | State-reset evidence; true file appears in candidate set but needs semantic evidence. |
| Math-14 | `data/defects4j/math_pilot_20.jsonl` | `outputs/math_pilot_20_hybrid_focused_direct_top50.jsonl` | Matrix/allocation evidence; direct candidate inclusion previously changed the candidate pool. |
| Closure-4 | `data/defects4j/closure_pilot_20.jsonl` | `outputs/closure_pilot_20_hybrid_focused_passchain_direct_top50.jsonl` | Type-cycle evidence; true file was low-ranked before snippet scoring exposed the relevant method. |
| Closure-13 | `data/defects4j/closure_pilot_20.jsonl` | `outputs/closure_pilot_20_hybrid_focused_passchain_direct_top50.jsonl` | Pass-chain retrieval boundary case; true file is candidate-present only after pass-chain retrieval. |
| Closure-65 | `data/defects4j/closure_heldout_61_80.jsonl` | `outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl` | Code-output evidence gap; held-out selector did not rerank it. |
| Closure-67 | `data/defects4j/closure_heldout_61_80.jsonl` | `outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl` | Selector false negative / semantic pass-family mismatch. |
| Closure-75 | `data/defects4j/closure_heldout_61_80.jsonl` | `outputs/closure_heldout_61_80_hybrid_focused_direct_passchain_typesystem_top50.jsonl` | Utility-file ambiguity around `NodeUtil.java`. |
| Closure-98 | `data/defects4j/closure_heldout_81_100.jsonl` | `outputs/closure_heldout_81_100_hybrid_focused_direct_passchain_typesystem_top50.jsonl` | Retrieval top-50 boundary / negative diagnostic case. |
| Mockito-26 | `data/defects4j/mockito_fresh_21_30.jsonl` | `outputs/mockito_fresh_21_30_hybrid_focused_direct_top50.jsonl` | Mockito primitive/default-value pattern not selected by previous gate. |
| Mockito-28 | `data/defects4j/mockito_fresh_21_30.jsonl` | `outputs/mockito_fresh_21_30_hybrid_focused_direct_top50.jsonl` | Mockito injection/ancestor matching pattern not selected by previous gate. |

## Input Construction

The script `scripts/build_rq5_defects4j_mini_benchmark.py` builds:

- `data/defects4j/rq5_defects4j_mini_10.jsonl`
- `outputs/rq5_defects4j_mini_10_baseline_top50.jsonl`
- `outputs/rq5_defects4j_mini_10_manifest.json`

The script only copies frozen bug records and frozen retrieval predictions
from existing files. It does not read fixed source code and does not use
ground-truth labels for prompt construction.

Ground-truth labels are used only for evaluation and for the manifest's
baseline-rank audit.

## Experiment Arms

All arms operate on the same top-50 retrieval candidate pool and produce a
top-10 file ranking.

One-shot:

```bash
python3 scripts/run_llm_rerank.py \
  --bugs data/defects4j/rq5_defects4j_mini_10.jsonl \
  --bm25 outputs/rq5_defects4j_mini_10_baseline_top50.jsonl \
  --out outputs/rq5_defects4j_mini_10_oneshot_deepseek.jsonl \
  --provider deepseek \
  --top-candidates 50 \
  --top-output 10 \
  --max-snippet-lines 12 \
  --include-retrieval-evidence \
  --include-test-context \
  --prompt-dir outputs/prompts_rq5_defects4j_mini_10_oneshot_deepseek
```

Agentic:

```bash
python3 scripts/run_agentic_rerank.py \
  --bugs data/defects4j/rq5_defects4j_mini_10.jsonl \
  --pred outputs/rq5_defects4j_mini_10_baseline_top50.jsonl \
  --out outputs/rq5_defects4j_mini_10_agentic_deepseek.jsonl \
  --trace-out outputs/rq5_defects4j_mini_10_agentic_deepseek_trace.jsonl \
  --provider deepseek \
  --top-candidates 50 \
  --top-output 10 \
  --max-steps 3 \
  --prompt-dir outputs/prompts_rq5_defects4j_mini_10_agentic_deepseek
```

Agentic + verifier:

```bash
python3 scripts/run_verifier_rerank.py \
  --bugs data/defects4j/rq5_defects4j_mini_10.jsonl \
  --pred outputs/rq5_defects4j_mini_10_agentic_deepseek.jsonl \
  --trace outputs/rq5_defects4j_mini_10_agentic_deepseek_trace.jsonl \
  --out outputs/rq5_defects4j_mini_10_agentic_verifier_deepseek.jsonl \
  --provider deepseek \
  --top-output 10 \
  --prompt-dir outputs/prompts_rq5_defects4j_mini_10_agentic_verifier_deepseek
```

## Metrics

Report Top-1, Top-3, Top-5, Top-10, MRR, LLM call count, token usage, and
runtime. Per-bug ranks are required because this mini-benchmark is diagnostic.

The primary comparison is directional:

- Agentic is useful if it improves ranks on candidate-present evidence-miss
  cases without systematically harming already recoverable cases.
- Verifier is useful only if it fixes agentic mistakes or improves MRR enough
  to justify its extra token cost.
- If verifier is flat or worse, report it as a negative ablation, consistent
  with the Easy Finance strict62 result.

## Interpretation Boundary

Because these cases were chosen from known diagnostic categories, the result
cannot replace the main held-out benchmark. A positive result supports the
claim that agentic inspection can address specific failure modes. A negative
or flat result supports keeping one-shot selective reranking as the main
method and treating agentic/verifier as exploratory extensions.
