# Selective Evidence-Aware LLM Fault Localization

This repository is the public reproducibility package for Ziniu Jin's MSc
thesis on selective evidence-aware LLM reranking for file-level fault
localization.

The study evaluates a retrieval-first pipeline in which a non-oracle selector
decides whether a bug should receive one-shot LLM reranking or retain the
deterministic retrieval ranking. The public package focuses on the Defects4J
experiments and non-sensitive aggregate analyses.

## Repository Contents

- `scripts/`: dataset construction, retrieval, selection, reranking,
  merge/fallback, evaluation, usage summarization, and analysis scripts.
- `src/fl_localizer/`: shared indexing, prompting, evaluation, and model-client
  modules.
- `docs/`: frozen Defects4J protocols and public experiment reports.
- `docs/thesis_revision_summary_2026-08-20.md`: supervisor-facing summary of
  the thesis restructuring, research-positioning changes, experimental
  clarifications, and remaining claim boundaries.
- `results/`: non-sensitive machine-readable summary tables and checksums.
- `thesis/thesis.pdf`: the thesis PDF corresponding to this artifact snapshot.

## Reproduction Boundary

The public Defects4J experiments require a local Defects4J installation and
buggy project workspaces. Hosted-model reruns additionally require a DeepSeek
API key supplied through the environment. No API credential is stored in this
repository.

The AboutWork and Easy Finance case studies use private repository material.
Their source code, raw bug records, prompts, logs, workspaces, and per-record
model outputs are intentionally excluded. The thesis reports only aggregate
results and describes the resulting reproducibility limitation.

## Environment

Recommended prerequisites:

- Python 3.11 or newer
- Defects4J and its Java/Perl dependencies
- SciPy for the optional Wilcoxon signed-rank analysis
- A DeepSeek API key only for hosted-model reruns

Create a local environment file only when model calls are needed:

```bash
cp .env.example .env
```

Then replace the placeholder value locally. Do not commit `.env`.

## Main Pipeline

The principal execution order is:

```text
dataset construction
-> focused hybrid retrieval
-> non-oracle selection
-> selected-case LLM reranking
-> merge with retrieval fallback
-> file-level evaluation
-> token and runtime summarization
```

Exact split-specific commands, settings, dates, and artifact checksums are
recorded in the frozen protocols and run manifests under `docs/` and
`results/`.

## Citation

The final thesis citation and archival identifier will be added after the
university submission record is available.
