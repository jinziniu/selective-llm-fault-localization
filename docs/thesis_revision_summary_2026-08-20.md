# Thesis Revision Summary

**Author:** Ziniu Jin  
**Date:** 20 August 2026  
**Thesis:** *Selective Evidence-Aware LLM Fault Localization Across Benchmark and Real-World Repositories*

## Purpose

This document summarizes the principal revisions made after the supervisor
review of the earlier thesis draft. The revision focused on thesis structure,
research positioning, comparison with related work, experimental
traceability, and the boundaries of the empirical claims. It did not change
the research topic from file-level fault localization or introduce claims of
automatic repair, statement-level diagnosis, or unrestricted repository
agents.

## Summary of Revisions

| Review concern | Revision made | Main thesis location |
| --- | --- | --- |
| Research questions appeared too late | The three research questions are now introduced in the Introduction, before the method and evaluation chapters. | Introduction, Research Questions |
| The thesis structure was difficult to follow | Scope and task boundaries were moved into the Introduction, and the thesis now follows a problem-to-evidence sequence: Introduction, Background, Related Work, Design, Evaluation Setup, Results, Discussion, Threats to Validity, Reproducibility, and Conclusion. | Full thesis structure |
| The related-work discussion did not expose a clear research gap | The review now uses a SEGRESS-style, Kitchenham-based synthesis and a research-gap matrix that maps method families, established evidence, remaining gaps, and the RQs they motivate. | Related Work |
| State-of-the-art comparison was insufficient | The thesis now identifies direct experimental baselines, mechanism-level comparisons, qualitative positioning targets, and controlled ablations. It discusses recent retrieve-and-rerank and agentic systems, including SweRank, BLAgent, FaR-Loc, SieveFL, RGFL, AgentFL, LocAgent, SWE-agent, Agentless, Project Glasswing, and Mythos Preview. | Related Work and Discussion |
| The novelty claim was too broad | The thesis no longer claims novelty for retrieval-augmented LLM reranking itself. Its contribution is framed as a controlled study of a non-oracle per-bug invocation gate that either requests one-shot reranking or retains deterministic retrieval fallback. | Introduction, Related Work, Discussion, Conclusion |
| Benchmark and case-study evidence were presented too uniformly | Defects4J is treated as controlled benchmark evidence, AboutWork as a company bug-log case study, and Easy Finance as a retrospective git-history-derived case study. Their different evidence strengths are stated explicitly. | Introduction, Evaluation Setup, Results, Threats to Validity |
| The selector was not reproducible enough | The design now defines the selector inputs, decision logic, dataset-specific configurations, frozen settings, false positives, and false negatives. | Design and Evaluation Setup |
| Metric boundaries were inconsistent | Ranking comparisons now use a common MRR@10 boundary. The selected/unselected analysis verifies that fallback cases retain identical retrieval and final rankings. | Evaluation Setup, Results, Supplemental Statistical Analysis |
| The accuracy-cost interpretation was incomplete | Retrieval-only, selective reranking, and full rerank-all are compared under matched candidate pools and evidence settings. The analysis reports gain retention, model requests, provider-reported tokens, runtime, selector coverage, and missed hard cases. | RQ2 Results |
| Evidence quality was only discussed informally | A selected-case Closure ablation compares metadata-only, metadata plus retrieval reasons, and full evidence packages. The thesis treats this as a single-run diagnostic because hosted-model variation prevents a strong causal interpretation. | RQ2 Results and Threats to Validity |
| Agentic and verifier variants lacked a controlled role | Agentic inspection and verifier reranking are now evaluated as RQ3 ablations rather than the main method. Their ranking results, model requests, tokens, runtime, and failure modes are compared with one-shot reranking. | RQ3 Results and Discussion |
| The evaluation did not show enough cross-project context | The current experiments cover 275 unique usable Defects4J bugs across development and validation slices, including a frozen follow-up on 40 previously unused Compress bugs. The thesis still distinguishes the main Closure held-out slice from supporting Math and Compress evidence and does not present all 275 records as independent held-out validation. | Introduction, Evaluation Setup, Results, Threats to Validity |
| Data leakage and private-data handling needed clarification | Repair diffs, changed-file labels, and post-fix source code are excluded from prediction. Easy Finance is identified as the sole retrospective query-provenance exception because its query text is derived from fixing-commit metadata. The private case-study API and publication boundaries are described explicitly. | Design, Evaluation Setup, Ethics and Data Handling, Threats to Validity |
| Hosted-model settings were under-specified | The thesis records the DeepSeek model alias, access date, request format, known client settings, and the parameters that were not explicitly pinned. Provider-default thinking behavior and run-to-run variation are reported as reproducibility limitations. | Design, Reproducibility, Threats to Validity |
| The artifact trail was local and difficult to inspect | A sanitized public reproducibility package now contains shared implementation modules, experiment scripts, frozen Defects4J protocols, non-sensitive result summaries, checksums, and the thesis PDF. | Reproducibility |

## Revised Research Questions

The thesis is now organized around three questions:

1. To what extent does selective evidence-aware LLM reranking improve
   file-level fault localization over retrieval-only baselines on benchmark
   and real-world repository data?
2. How do candidate recall, evidence quality, and non-oracle selection affect
   the accuracy-cost trade-off of selective LLM reranking?
3. How do controlled agentic inspection and verifier reranking compare with
   one-shot LLM reranking in accuracy, cost, and failure modes?

These questions define the thesis argument. RQ1 evaluates effectiveness under
different evidence settings. RQ2 explains the mechanisms and costs behind the
observed results. RQ3 tests whether additional model interaction improves the
same bounded file-ranking task.

## Current Contribution Statement

The thesis does not present retrieval plus LLM reranking as a new idea. Recent
systems already establish retrieval-filtered, bounded, and evidence-aware LLM
localization as an active research direction. The narrower contribution is an
empirical evaluation of the routing decision: whether a non-oracle selector
can preserve a useful part of rerank-all improvement while reducing model
requests, token usage, and runtime by allowing some bugs to bypass the LLM and
retain deterministic retrieval fallback.

The matched comparisons also identify where this policy loses performance:
the correct file may be absent from the candidate pool, the evidence package
may omit or obscure the relevant signal, or the selector may leave a difficult
case on the retrieval-only path.

## Evidence and Claim Boundaries

The revised thesis keeps the following limitations explicit:

- The main held-out benchmark evidence is the frozen Closure 61--100 slice;
  Math and Compress provide supporting cross-project evidence.
- The 275 Defects4J bugs are the total unique usable development and validation
  coverage, not 275 independent held-out observations.
- AboutWork and Easy Finance support feasibility in additional repository
  settings, not broad industrial generalization.
- Easy Finance is retrospective because its natural-language query is derived
  from fixing-commit metadata.
- Full rerank-all is more accurate than selective reranking under the evaluated
  evidence package; selective reranking is therefore an accuracy-cost policy,
  not the highest-accuracy configuration.
- The evidence-package ablation is diagnostic and subject to hosted-model
  variation.
- Agentic and verifier results apply only to the bounded file-level settings
  evaluated in the thesis and do not establish that agents are generally
  ineffective.
- The study does not claim automatic repair, root-cause proof, statement-level
  localization, or full-Defects4J generalization.

## Reproducibility Package

The public package is available at:

<https://github.com/jinziniu/selective-llm-fault-localization>

The thesis artifact snapshot is marked with the Git tag
`thesis-artifact-v1.0`. Private repository snapshots, raw company bug records,
prompt packages, and per-record company outputs are excluded. This boundary is
intentional and matches the confidentiality statement in the thesis.

## Recommended Review Path

For a focused supervisor review, the most important parts are:

1. **Introduction:** final scope, RQs, contributions, and evidence hierarchy.
2. **Related Work:** SEGRESS/Kitchenham synthesis, SOTA comparison, and the
   research-gap matrix.
3. **Design:** the retrieval-selector-rerank pipeline and non-oracle selector.
4. **Evaluation Setup:** datasets, input boundaries, metrics, and no-leakage
   protocol.
5. **Results:** RQ1 effectiveness, RQ2 accuracy-cost mechanisms, and RQ3
   agentic/verifier ablations.
6. **Discussion and Threats to Validity:** novelty boundary, interpretation,
   and limits of generalization.
7. **Reproducibility:** public artifact, commands, manifests, and remaining
   hosted-model limitations.

