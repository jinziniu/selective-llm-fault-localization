# RQ5 Defects4J Diagnostic Mini-Benchmark Results

Date: 2026-06-03

This report records the Defects4J RQ5 diagnostic mini-benchmark for comparing
one-shot reranking, agentic inspection, and agentic inspection plus verifier.

Protocol:

```text
docs/rq5_defects4j_mini_benchmark_protocol_2026-06-03.md
```

This is a diagnostic mini-benchmark, not a new main held-out benchmark. The
case set intentionally covers known failure categories from prior analysis.
The result should be used to answer RQ5 extension behavior, not to replace the
Closure `61..100` frozen held-out aggregate.

## Artifacts

Input and baseline:

```text
data/defects4j/rq5_defects4j_mini_10.jsonl
outputs/rq5_defects4j_mini_10_baseline_top50.jsonl
outputs/rq5_defects4j_mini_10_manifest.json
outputs/rq5_defects4j_mini_10_baseline_top50_eval.json
```

One-shot:

```text
outputs/rq5_defects4j_mini_10_oneshot_deepseek.jsonl
outputs/rq5_defects4j_mini_10_oneshot_deepseek_eval.json
outputs/rq5_defects4j_mini_10_oneshot_deepseek_usage.json
```

Agentic:

```text
outputs/rq5_defects4j_mini_10_agentic_deepseek.jsonl
outputs/rq5_defects4j_mini_10_agentic_deepseek_trace.jsonl
outputs/rq5_defects4j_mini_10_agentic_deepseek_eval.json
outputs/rq5_defects4j_mini_10_agentic_deepseek_usage.json
```

Agentic + verifier:

```text
outputs/rq5_defects4j_mini_10_agentic_verifier_deepseek.jsonl
outputs/rq5_defects4j_mini_10_agentic_verifier_deepseek_eval.json
outputs/rq5_defects4j_mini_10_agentic_verifier_deepseek_usage.json
```

## Aggregate Results

| Method | API Calls | Top-1 | Top-3 | Top-5 | Top-10 | MRR | Tokens | Duration (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Retrieval baseline top50 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.2000 | 0.0534 | 0 | 0.000 |
| One-shot DeepSeek | 10 | 0.4000 | 0.7000 | 0.8000 | 0.9000 | 0.5644 | 345937 | 174.136 |
| Agentic DeepSeek | 32 | 0.3000 | 0.6000 | 0.6000 | 0.8000 | 0.4768 | 441952 | 244.601 |
| Agentic + verifier DeepSeek | 42 | 0.3000 | 0.6000 | 0.6000 | 0.8000 | 0.4768 | 554133 | 370.117 |

Notes:

- Agentic API calls count all step prompts plus final prompts.
- Agentic + verifier counts agentic calls plus 10 verifier calls.
- Verifier-only extra cost was 112181 tokens and 125.516 seconds.

## Per-Bug Ranks

| Bug | Category | Baseline Rank | One-Shot Rank | Agentic Rank | Agentic+Verifier Rank |
|---|---|---:|---:|---:|---:|
| Math-12 | state-reset evidence | 47 | 9 | miss | miss |
| Math-14 | matrix/allocation evidence | 17 | 1 | 1 | 1 |
| Closure-4 | type-cycle evidence | 49 | 5 | 8 | 8 |
| Closure-13 | pass-chain retrieval boundary | 39 | 3 | 7 | 7 |
| Closure-65 | code-output evidence gap | 8 | 1 | 1 | 1 |
| Closure-67 | selector false negative | 48 | 2 | 2 | 2 |
| Closure-75 | utility-file ambiguity | 21 | 2 | 2 | 2 |
| Closure-98 | retrieval boundary negative | miss | miss | miss | miss |
| Mockito-26 | primitive/default-value pattern | 7 | 1 | 1 | 1 |
| Mockito-28 | injection/ancestor pattern | 14 | 1 | 2 | 2 |

## Interpretation

The one-shot evidence-aware reranker is the best arm on this diagnostic
mini-benchmark. It improves the baseline from Top-10 0.2000 to 0.9000 and MRR
from 0.0534 to 0.5644. It recovers all candidate-present cases into Top-10
except the deliberate retrieval-miss negative case `Closure-98`.

Agentic inspection is technically runnable and produces useful traces, but it
does not outperform one-shot reranking here. It is worse on `Math-12`,
`Closure-4`, `Closure-13`, and `Mockito-28`, while matching one-shot on the
remaining successful cases. The most important regression is `Math-12`: one-shot
keeps the true file at rank 9, while agentic drops it out of the output top10.

Verifier reranking is a negative ablation on this mini-benchmark. It adds
112181 tokens but produces the same aggregate metrics and per-bug ranks as
agentic alone. Because the verifier reranks the agentic top10, it cannot recover
cases such as `Math-12` once agentic has removed the true file from the proposed
top10.

Combined with the Easy Finance strict62 RQ5 result, the Defects4J diagnostic
mini-benchmark supports the same conclusion: agentic/verifier extensions are
feasible, but current evidence does not justify replacing the selective
one-shot reranker as the main method.

## Reproduction Commands

Build inputs:

```bash
python3 scripts/build_rq5_defects4j_mini_benchmark.py
```

Evaluate baseline:

```bash
python3 scripts/evaluate_predictions.py \
  --bugs data/defects4j/rq5_defects4j_mini_10.jsonl \
  --pred outputs/rq5_defects4j_mini_10_baseline_top50.jsonl \
  --ks 1,3,5,10,20,50 \
  --per-bug \
  --out outputs/rq5_defects4j_mini_10_baseline_top50_eval.json
```

Run and evaluate one-shot:

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

Run and evaluate agentic:

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

Run and evaluate verifier:

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
