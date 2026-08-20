# Compress 1--40 Frozen Cross-Project Validation
Date: 2026-08-11

## Protocol Boundary

Compress was not used in prior pilot, selector, prompt, evidence-rule, or error-analysis development. The generic pipeline was frozen before dataset construction. All 40 active bugs were built successfully. The first API batch completed Compress-2 and then encountered a read timeout on Compress-5; the remaining five preselected records were rerun with only the network timeout increased to 300 seconds, as recorded in the frozen protocol.

## Main Result

| Method | N | Calls | Top-1 | Top-3 | Top-5 | Top-10 | MRR@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Retrieval | 40 | 0 | 0.7500 | 0.9250 | 0.9500 | 0.9750 | 0.8299 |
| Selective rerank | 40 | 6 | 0.7750 | 0.9250 | 0.9500 | 0.9750 | 0.8465 |

Selective reranking changes one record: Compress-2 moves from rank 3 to rank 1. The other five selected records remain at rank 1. Top-1 increases from 30/40 to 31/40 and MRR@10 increases by 0.0167; Top-3, Top-5, and Top-10 remain unchanged.

## Selector and Candidate Diagnostics

| Selected | Fraction | Top-5 failures selected | Top-10 failures selected |
| --- | --- | --- | --- |
| 6 | 0.1500 | 0/2 | 0/1 |

The sole Top-10 retrieval failure is Compress-35 (retrieval rank 28), which remains unselected. Recall@50 and Recall@100 are both 1.0000, so this is a selector miss rather than a candidate-retrieval miss.

## Cost and Output Validity

| Requests | Tokens | Seconds | Tokens/request | Seconds/request | Invalid | Duplicates | Fallback added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 247062 | 584.4310 | 41177.0000 | 97.4050 | 0 | 0 | 0 |

## Paired Statistical Description

| Comparison | +RR | -RR | 0RR | Mean dRR@10 | Wilcoxon p | Top-1 b/c | McNemar p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Retrieval vs selective | 1 | 0 | 39 | 0.0167 | 0.3173 | 1/0 | 1.0000 |

The tests are descriptive: only one record changes, so the slice does not provide inferential evidence of a stable improvement despite the positive aggregate direction.

## Interpretation

This fully unseen project strengthens the external-validity evidence for running the pipeline without project-specific tuning, but it also narrows the claim. Retrieval is already very strong on Compress, selective reranking produces only a small Top-1/MRR@10 improvement, and the generic selector misses the hard retrieval cases. The result therefore supports feasibility of the routing pipeline across another Defects4J project, not broad or statistically established cross-project superiority.
