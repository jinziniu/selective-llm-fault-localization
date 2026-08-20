# Revision Summary in Response to the Previous Supervisor Meeting

**Student:** Ziniu Jin<br>
**Supervisor:** Ana Oprescu<br>
**Date:** 20 August 2026<br>
**Thesis:** *Selective Evidence-Aware LLM Fault Localization Across Benchmark and Real-World Repositories*

## Purpose

This note summarizes how the current thesis responds to the main points raised
in the previous supervisor meeting. It focuses only on the requested changes:
the abstract, placement of the research questions, thesis structure, VU thesis
format, related-work synthesis, research-gap matrix, state-of-the-art
comparison, and the connection to Mythos and related agentic work.

## Meeting Requirements and Responses

The locations below refer to the current 20 August 2026 PDF. Section titles are
the stable reference if later pagination changes.

| Requirement raised in the meeting | Status | Response in the current thesis | Where to verify |
| --- | --- | --- | --- |
| Make the abstract broader and less implementation-heavy. | **Completed** | The abstract now begins with the fault-localization problem and the accuracy--cost motivation. It summarizes the method family, evaluation scope, main finding, and limitations without reproducing detailed tables, parameter lists, or dataset-by-dataset results. | **Abstract, p. 1**, especially its opening problem statement and final interpretation paragraph. |
| Present the research questions before explaining the methodology. | **Completed** | RQ1--RQ3 now appear in the Introduction. The design and evaluation chapters follow them and are organized around answering those questions. | **Section 1.2, Research Questions, p. 3**; compare with **Section 4, Design, p. 8** and **Section 5, Evaluation Setup, p. 11**. |
| Restructure the thesis because the previous version was difficult to read. | **Completed** | The thesis now follows a conventional argument: Introduction, Background, Related Work, Design, Evaluation Setup, Results, Discussion, Threats to Validity, Reproducibility, and Conclusion. Scope and task boundaries were moved into the Introduction instead of remaining as a separate chapter between Related Work and Methodology. | **Contents, p. 1**; **Section 1.1, Task Definition and Scope, p. 3**; full chapter order in **Sections 1--10, pp. 3--26**. |
| Use the thesis template provided for the VU/UvA Computer Science programme rather than the literature-study format. | **Completed** | The current source uses the VU/UvA thesis front matter and A4 layout. The literature-study document remains separate and is not used as the thesis template. | **Cover page** and the A4 thesis layout throughout the PDF. |
| Compare the thesis with existing approaches and the state of the art. | **Completed** | Related Work now distinguishes direct baselines, mechanism-level comparison targets, qualitative positioning targets, and controlled ablations. The Discussion returns to the closest systems and explains what can and cannot be compared under the thesis's file-level protocol. | **Section 3.6, Selected State-of-the-Art Comparison Targets, p. 7**; **Section 5.3, Comparison Strategy, p. 12**; **Section 7.2, Implications for State-of-the-Art Comparison, p. 23**. |
| Apply the SEGRESS/Kitchenham-style literature-synthesis procedure used in the earlier research study. | **Completed** | Related Work explicitly identifies the synthesis as SEGRESS-style and Kitchenham-based. Prior work is grouped into method families and compared by evidence requirements, localization granularity, evaluation setting, and compatibility with the thesis protocol. | **Section 3.7, State-of-the-Art Comparison and Research Gap Matrix, p. 7**, in the paragraphs immediately before the gap matrix. |
| Build a matrix of research gaps. | **Completed** | The Related Work chapter contains a research-gap matrix that records what each method family establishes, what remains insufficiently evaluated, and which research question addresses that gap. | **Section 3.7, Research Gap Matrix, pp. 7--8**. |
| Ensure that the identified gaps support the research questions. | **Completed** | The gap synthesis now leads directly to RQ1, RQ2, and RQ3: evaluation across benchmark and repository settings; the candidate/evidence/selection mechanisms behind the accuracy--cost trade-off; and controlled comparison of one-shot, agentic, and verifier reranking. | Closing paragraphs of **Section 3.7, pp. 7--8**, read together with **Section 1.2, p. 3**. |
| Select relevant state-of-the-art work from Related Work for comparison. | **Completed** | The thesis identifies the closest retrieval-based, LLM-based, retrieve-and-rerank, and agentic systems. It uses numerical comparison only where the input boundary, output granularity, labels, and protocol are compatible; otherwise it provides an explicit mechanism-level or qualitative comparison instead of presenting incomparable published scores as a leaderboard. | Comparison table and explanation in **Section 3.6, p. 7**; comparison boundary in **Section 5.3, p. 12**; interpretation in **Section 7.2, p. 23**. |
| Relate the work to Mythos and the broader tool-using model direction discussed in the meeting. | **Completed** | Project Glasswing and Mythos Preview are discussed in Related Work as practical evidence that frontier models are increasingly used for multi-step investigation, tool use, confirmation, and vulnerability discovery. The Discussion connects this direction to RQ3: the thesis tests whether additional controlled inspection or verifier passes improve file-level ranking under a bounded evidence setting. | **Section 3.4, Agentic Software Engineering Systems, p. 6**; **Section 3.6, p. 7**; and the agentic-systems paragraph in **Section 7.2, p. 23**. |

## 1. Abstract and Introduction

The revised abstract is intentionally broad. It first states why file-level
fault localization matters, then introduces selective evidence-aware
reranking as an accuracy--cost trade-off. It avoids presenting the abstract as
an implementation summary.

The Introduction now contains:

1. the problem and motivation;
2. the file-level task and its boundaries;
3. the three research questions;
4. the contribution statement; and
5. a concise description of the evaluation evidence and its limits.

This ordering ensures that readers know what the thesis asks before they read
the system design or experimental protocol.

## 2. Thesis Structure

The previous standalone *Overview and Scope* chapter has been removed. Its
necessary content is now integrated into the Introduction, where the task,
inputs, outputs, ground-truth role, and exclusions are first defined. The
remaining chapters follow the research logic rather than the chronology of
the implementation work:

```text
Introduction and RQs
-> Background
-> Related Work and Research Gaps
-> Design
-> Evaluation Setup
-> Results by RQ
-> Discussion and SOTA Positioning
-> Threats to Validity
-> Reproducibility
-> Conclusion
```

The Results chapter is organized directly by RQ1, RQ2, and RQ3, so the reader
can trace each research question to the corresponding evidence and answer.

## 3. SEGRESS/Kitchenham Synthesis and Research-Gap Matrix

The Related Work chapter now applies the requested synthesis procedure rather
than presenting papers as an unstructured list. It groups prior work into:

- information-retrieval-based bug localization;
- traditional and learning-based fault localization;
- LLM-based and retrieval-augmented fault localization;
- adjacent LLM-based testing and vulnerability tasks;
- agentic software-engineering and vulnerability-discovery systems; and
- benchmark and real-repository evaluation.

For each family, the research-gap matrix records:

1. what existing work establishes;
2. what remains insufficiently evaluated; and
3. which thesis RQ follows from that gap.

This matrix provides the explicit link requested in the meeting: the RQs are
not introduced independently of the literature, but are supported by the
gaps derived from the structured synthesis.

## 4. State-of-the-Art Comparison

The thesis now selects comparison targets according to compatibility rather
than name recognition or published score alone. The closest retrieve-and-rank
and agentic systems are discussed in the Related Work and Discussion chapters.
The comparison distinguishes four roles:

- **Direct experimental baselines:** methods that can be run with the same
  file-level inputs, labels, and metric boundary.
- **Mechanism-level comparisons:** related systems that use retrieval,
  filtering, bounded candidates, reranking, or selective processing but differ
  in model training, granularity, runtime evidence, or dataset.
- **Qualitative positioning targets:** systems whose task is adjacent but whose
  published scores are not directly comparable.
- **Controlled ablations:** one-shot, agentic, and verifier variants evaluated
  inside the thesis protocol.

This avoids an invalid cross-paper leaderboard while still making the thesis's
position relative to the state of the art explicit. The resulting claim is
also narrower: the thesis does not claim novelty for retrieval plus LLM
reranking. It studies the per-bug routing decision between one-shot reranking
and deterministic retrieval fallback.

## 5. Mythos, Glasswing, and RQ3

The link to Mythos is now presented as part of the thesis motivation for
studying controlled agentic behavior, not as an unrelated security example.
Mythos Preview and Project Glasswing illustrate a broader movement toward
models that use tools, gather evidence over multiple steps, and perform an
additional confirmation or review stage before producing a result.

The thesis translates that broader direction into a narrower and testable
file-localization question. RQ3 compares:

- one-shot evidence-aware reranking;
- controlled agentic inspection; and
- verifier reranking.

The comparison examines accuracy, model use, runtime, and failure modes under
the same bounded file-level setting. Mythos and Glasswing therefore provide
practical motivation and a design relationship for the agentic/verifier
comparison, while the thesis's own experiment remains file-level fault
localization rather than vulnerability discovery.

## Remaining Administrative Item

The VU/UvA thesis layout is in use, but the final cover still requires the
confirmed daily-supervisor and second-reader names if the programme requires
those fields. This item is not marked as completed because the names are not
currently available in the source.

## Recommended Review Locations

The meeting-related changes can be reviewed most efficiently in:

1. **Abstract, p. 1:** broader problem/method/finding summary.
2. **Sections 1.1--1.2, p. 3:** scope and RQ1--RQ3 before methodology.
3. **Sections 3.4, 3.6, and 3.7, pp. 6--8:** Mythos/Glasswing context,
   selected SOTA targets, SEGRESS/Kitchenham synthesis, and the research-gap
   matrix.
4. **Sections 6.1--6.3, pp. 15--21:** evidence organized by RQ1, RQ2, and RQ3.
5. **Section 7.2, p. 23:** final SOTA positioning and interpretation of the
   agentic/verifier comparison.
