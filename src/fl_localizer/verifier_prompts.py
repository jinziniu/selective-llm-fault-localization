from __future__ import annotations

import json
from typing import Any

from fl_localizer.prompts import compact_stack_trace


VERIFIER_SYSTEM_PROMPT = """You are an independent fault-localization verifier.
You must check whether an existing file ranking is supported by the bug report, source snippets, and prior inspection observations.
You cannot call tools, inspect new files, use fixed commits, patches, changed files, or ground truth.
Return strict JSON only."""


def build_verifier_prompt(
    *,
    bug_record: dict[str, Any],
    proposed_ranking: list[dict[str, Any]],
    candidate_evidence: list[dict[str, Any]],
    trace_observations: list[dict[str, Any]],
    top_output: int,
) -> str:
    bug_report = bug_record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}

    bug_payload = {
        "bug_id": bug_record["bug_id"],
        "project": bug_record["project"],
        "bug_report_id": bug_report.get("id", ""),
        "bug_report_text": bug_report.get("text", ""),
        "test_failure": bug_record.get("test_failure", ""),
        "triggering_tests": bug_record.get("triggering_tests", []),
        "stack_trace": compact_stack_trace(str(bug_record.get("stack_trace", ""))),
    }

    rules = [
        "Use only the information in this prompt.",
        "Do not use fixing commits, patches, changed files, or ground truth.",
        "You cannot request tools or inspect additional files.",
        "Every returned file must be selected from proposed_ranking.",
        "Prefer the file that owns the failing behavior over generic table, modal, helper, layout, or API wrapper files.",
        "If the evidence is insufficient to change the ranking, preserve the proposed order.",
        f"Return exactly {min(top_output, len(proposed_ranking))} ranked files unless fewer proposed files exist.",
    ]

    payload = {
        "task": "Verify and, if justified, reorder the proposed fault-localization ranking.",
        "rules": rules,
        "expected_json_schema": {
            "bug_id": "string",
            "ranked_files": [
                {
                    "rank": "integer starting at 1",
                    "file": "file path from proposed_ranking",
                    "confidence": "number between 0 and 1",
                    "reason": "short explanation grounded in evidence",
                    "verdict": "support | weaken | uncertain",
                }
            ],
        },
        "bug": bug_payload,
        "proposed_ranking": proposed_ranking,
        "candidate_evidence": candidate_evidence,
        "prior_agent_observations": trace_observations,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
