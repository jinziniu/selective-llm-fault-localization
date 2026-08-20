from __future__ import annotations

import json
from typing import Any

from fl_localizer.prompts import compact_stack_trace


AGENT_SYSTEM_PROMPT = """You are a controlled fault-localization inspection agent.
You may request limited evidence from the provided tool schema, but you must never use fixes, patches, changed files, commits, or ground truth.
The candidate pool is closed: every file you inspect or rank must come from candidate_files.
Return strict JSON only."""


def build_agent_prompt(
    *,
    bug_record: dict[str, Any],
    candidate_files: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    step: int,
    max_steps: int,
    top_output: int,
    force_finish: bool = False,
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

    tool_schema = {
        "search_files": {
            "description": "Search only inside candidate_files. Use this when the bug report names behavior, domain terms, UI labels, API fields, or method concepts.",
            "input": {"action": "search_files", "query": "short search query"},
        },
        "inspect_candidate": {
            "description": "Read metadata and an automatically selected relevant snippet for one candidate file.",
            "input": {"action": "inspect_candidate", "file": "candidate file path"},
        },
        "read_file_window": {
            "description": "Read a specific line window from one candidate file after search/inspect reveals useful line numbers.",
            "input": {
                "action": "read_file_window",
                "file": "candidate file path",
                "start_line": "integer",
                "end_line": "integer",
            },
        },
        "finish": {
            "description": "Produce the final file ranking.",
            "input": {
                "action": "finish",
                "ranked_files": [
                    {
                        "rank": "integer starting at 1",
                        "file": "candidate file path",
                        "confidence": "number between 0 and 1",
                        "reason": "short evidence-based explanation",
                    }
                ],
            },
        },
    }

    rules = [
        "Use only bug, candidate_files, and observations in this prompt.",
        "Do not infer from fixed commits, patch files, changed files, or ground truth.",
        "All tool requests and final ranked files must use paths from candidate_files.",
        "Prefer files whose code owns the failing behavior, state transition, API query, calculation, route/page, or UI action.",
        "Downrank generic layout/table/modal/helper files when a page/domain owner file better explains the behavior.",
        f"Final ranking must contain exactly {min(top_output, len(candidate_files))} files unless fewer candidate_files exist.",
    ]
    if force_finish:
        rules.append("You must finish now. Return only a finish action.")
    else:
        rules.append("If more evidence is needed, request exactly one tool action. If enough evidence is present, finish.")

    payload = {
        "task": "Controlled agentic inspection for file-level fault localization.",
        "step": step,
        "max_steps": max_steps,
        "rules": rules,
        "available_tools": {} if force_finish else tool_schema,
        "expected_response": tool_schema["finish"]["input"] if force_finish else tool_schema,
        "bug": bug_payload,
        "candidate_files": candidate_files,
        "observations": observations,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
