from __future__ import annotations

import json
from typing import Any


RERANK_SYSTEM_PROMPT = """You are evaluating fault localization candidates.
Your task is to re-rank candidate source files by how likely they contain the fault.
Use only the bug report, failing test, stack trace, and candidate source summaries.
Do not assume the original BM25 rank is correct.
Return strict JSON only."""


def compact_stack_trace(
    stack_trace: str,
    *,
    max_consecutive_repeated_frames: int = 3,
    max_chars: int = 60000,
) -> str:
    lines = stack_trace.splitlines()
    compacted: list[str] = []
    previous_line: str | None = None
    repeat_count = 0

    for line in lines:
        is_repeated_frame = line == previous_line and line.lstrip().startswith("at ")
        if is_repeated_frame:
            repeat_count += 1
            if repeat_count <= max_consecutive_repeated_frames:
                compacted.append(line)
            continue

        if repeat_count > max_consecutive_repeated_frames:
            omitted = repeat_count - max_consecutive_repeated_frames
            compacted.append(f"\t... repeated identical frame omitted {omitted} time(s)")

        compacted.append(line)
        previous_line = line
        repeat_count = 1

    if repeat_count > max_consecutive_repeated_frames:
        omitted = repeat_count - max_consecutive_repeated_frames
        compacted.append(f"\t... repeated identical frame omitted {omitted} time(s)")

    rendered = "\n".join(compacted)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars] + "\n...[stack trace truncated]"


def build_rerank_prompt(
    bug_record: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    top_output: int,
    test_source_context: str = "",
    evidence_mode: bool = False,
) -> str:
    bug_report = bug_record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}

    rules = [
        "Use only the information in this prompt.",
        "Do not use fixing commit, patch, changed files, or ground truth.",
        "Return exactly one JSON object.",
        f"Return exactly {min(top_output, len(candidates))} ranked files unless fewer candidate_files exist.",
        "Every returned file must be selected from candidate_files.",
        "Do not assume the original retrieval rank is correct; a lower-ranked candidate can still be the faulty file.",
    ]
    if evidence_mode:
        rules.extend(
            [
                "Use retrieval_evidence as weak supporting evidence, not as ground truth.",
                "Prefer candidates whose source snippet explains the failing assertion, exception, or state transition.",
                "If triggering test source context mentions an operation such as clone, reseed, sample, bounds, or matrix allocation, connect that operation to candidate implementation code.",
                "For stack traces, distinguish the generic frame where an exception is thrown from the upstream file that made the bad allocation, state transition, or validation decision.",
                "For clone, serialization, reseed, repeated sample, or state consistency failures, consider lower-ranked helper classes that manage cached state, seeds, random generators, clear/reset methods, or value sequences.",
                "For recursive type, inheritance, implements/extends, cycle-detected, or StackOverflowError failures, repeated stack frames may be downstream symptoms; also consider lower-ranked resolver or placeholder type classes whose snippets mention resolveInternal, handleTypeCycle, unresolved/named types, or cycle warning text.",
                "For code-printer numeric output failures, distinguish parser or conversion helpers from the final code-emission class; prefer candidates whose snippet owns addNumber, escaping, token emission, or object-key printing logic when that directly explains the expected/actual output.",
                "For Mockito @Spy, useConstructor, constructor, abstract class, or inner class failures, also inspect MockMaker or bytecode creation classes that decide how the mock instance is instantiated; annotation/configuration classes may be downstream callers.",
                "For web frontend bugs about counts, loading states, currency, page display, or API-backed UI data, prefer the page/container file that owns the relevant query, mutation, state, route, or display formatting over a generic table, modal, layout, or dashboard component unless that component snippet directly contains the faulty logic.",
                "For loading-state button bugs, prefer candidates where an async action, mutation, submit handler, or PDF/query action is tied to a primary button that lacks a matching isLoading, isDisabled, isPending, isSubmitting, or processing guard. Downrank candidates whose snippet already shows the relevant loading prop wired to the same action.",
                "For admin, invoice, expense, user, chat, or report UI bugs, treat path/domain mismatch as a warning sign: candidates under the matching page/domain path are often more likely than generic cross-domain components with overlapping words.",
            ]
        )

    bug_payload = {
        "bug_id": bug_record["bug_id"],
        "project": bug_record["project"],
        "bug_report_id": bug_report.get("id", ""),
        "bug_report_text": bug_report.get("text", ""),
        "test_failure": bug_record.get("test_failure", ""),
        "triggering_tests": bug_record.get("triggering_tests", []),
        "stack_trace": compact_stack_trace(str(bug_record.get("stack_trace", ""))),
    }
    if test_source_context:
        bug_payload["triggering_test_source_context"] = test_source_context

    payload = {
        "task": "Re-rank the candidate source files for this bug.",
        "rules": rules,
        "expected_json_schema": {
            "bug_id": "string",
            "ranked_files": [
                {
                    "rank": "integer starting at 1",
                    "file": "candidate file path",
                    "confidence": "number between 0 and 1",
                    "reason": "short evidence-based explanation",
                }
            ],
        },
        "bug": bug_payload,
        "candidate_files": candidates,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
