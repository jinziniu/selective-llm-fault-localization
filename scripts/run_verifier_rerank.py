#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.env_utils import load_dotenv
from fl_localizer.indexer import SourceFile, index_source_files
from fl_localizer.io_utils import read_jsonl, write_jsonl
from fl_localizer.llm_client import CodexClient, DeepSeekClient, parse_json_object
from fl_localizer.snippets import extract_relevant_snippet
from fl_localizer.text import extract_runtime_context
from fl_localizer.verifier_prompts import VERIFIER_SYSTEM_PROMPT, build_verifier_prompt


def build_query(record: dict[str, Any]) -> str:
    bug_report = record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}
    parts = [
        str(bug_report.get("id", "")),
        str(bug_report.get("text", "")),
        str(record.get("test_failure", "")),
        " ".join(record.get("triggering_tests", [])),
        extract_runtime_context(str(record.get("stack_trace", ""))),
    ]
    return "\n".join(part for part in parts if part)


def source_by_file(record: dict[str, Any]) -> dict[str, SourceFile]:
    sources = index_source_files(Path(record["repo_path"]), record["source_dir"])
    return {source.file: source for source in sources}


def client_for(provider: str, model: str | None):
    if provider == "deepseek":
        return DeepSeekClient(model=model)
    if provider == "codex":
        return CodexClient(model=model)
    raise ValueError(f"Unsupported provider: {provider}")


def compact_observations(observations: list[dict[str, Any]], *, max_chars: int) -> list[dict[str, Any]]:
    rendered = json.dumps(observations, ensure_ascii=False)
    if len(rendered) <= max_chars:
        return observations
    compacted: list[dict[str, Any]] = []
    remaining = max_chars
    for observation in observations:
        if remaining <= 0:
            break
        item = compact_value(observation, max_chars=min(remaining, max_chars // 2))
        text = json.dumps(item, ensure_ascii=False)
        remaining -= len(text)
        compacted.append(item)
    return compacted


def compact_value(value: Any, *, max_chars: int) -> Any:
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= max_chars:
        return value
    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"content", "relevant_snippet", "text"} and isinstance(item, str):
                compacted[key] = truncate_text(item, max_chars=1200)
            elif key in {"results", "line_hits"} and isinstance(item, list):
                compacted[key] = item[:5]
            else:
                compacted[key] = item
        compacted["_truncated"] = True
        return compacted
    if isinstance(value, str):
        return truncate_text(value, max_chars=max_chars)
    return value


def build_candidate_evidence(
    *,
    bug_record: dict[str, Any],
    prediction: dict[str, Any],
    sources_by_file: dict[str, SourceFile],
    max_snippet_lines: int,
) -> list[dict[str, Any]]:
    query = build_query(bug_record)
    evidence: list[dict[str, Any]] = []
    for item in prediction.get("ranked_files", []):
        if not isinstance(item, dict):
            continue
        file_path = str(item.get("file", ""))
        source = sources_by_file.get(file_path)
        if source is None:
            continue
        evidence.append(
            {
                "file": source.file,
                "proposed_rank": item.get("rank"),
                "proposed_confidence": item.get("confidence"),
                "proposed_reason": item.get("reason", ""),
                "package": source.package,
                "class_names": source.class_names[:10],
                "method_names": source.method_names[:35],
                "relevant_snippet": extract_relevant_snippet(
                    source.content,
                    query,
                    file_path=source.file,
                    stack_trace=str(bug_record.get("stack_trace", "")),
                    max_lines=max_snippet_lines,
                ),
            }
        )
    return evidence


def normalize_verifier_output(
    *,
    bug_id: str,
    parsed: dict[str, Any],
    proposal: dict[str, Any],
    top_output: int,
    provider: str,
    model: str,
    prompt_path: str | None,
    prompt_chars: int,
    response_chars: int,
    duration_seconds: float,
    token_usage: dict[str, Any] | None,
) -> dict[str, Any]:
    proposed_items = [
        item for item in proposal.get("ranked_files", [])[:top_output] if isinstance(item, dict)
    ]
    proposed_files = [str(item.get("file", "")) for item in proposed_items]
    proposed_file_set = set(proposed_files)
    ranked_files = parsed.get("ranked_files", [])
    if not isinstance(ranked_files, list):
        ranked_files = []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_files: list[str] = []
    duplicate_files: list[str] = []

    for item in ranked_files:
        if not isinstance(item, dict) or "file" not in item:
            continue
        file_path = str(item["file"])
        if file_path not in proposed_file_set:
            invalid_files.append(file_path)
            continue
        if file_path in seen:
            duplicate_files.append(file_path)
            continue
        seen.add(file_path)
        normalized.append(
            {
                "rank": len(normalized) + 1,
                "file": file_path,
                "confidence": item.get("confidence"),
                "reason": str(item.get("reason", "")),
                "verdict": str(item.get("verdict", "")),
                "source": "verifier",
            }
        )
        if len(normalized) >= top_output:
            break

    fallback_added: list[str] = []
    for file_path in proposed_files:
        if len(normalized) >= top_output:
            break
        if file_path in seen:
            continue
        seen.add(file_path)
        fallback_added.append(file_path)
        normalized.append(
            {
                "rank": len(normalized) + 1,
                "file": file_path,
                "confidence": None,
                "reason": "Fallback candidate appended in proposed order because the verifier did not return enough valid files.",
                "verdict": "fallback",
                "source": "proposal-fallback",
            }
        )

    return {
        "bug_id": bug_id,
        "method": f"verifier-rerank:{provider}",
        "provider": provider,
        "model": model,
        "input_method": proposal.get("method", ""),
        "prompt_path": prompt_path,
        "prompt_chars": prompt_chars,
        "response_chars": response_chars,
        "llm_duration_seconds": round(duration_seconds, 3),
        "token_usage": token_usage or {},
        "candidate_count": len(proposed_files),
        "requested_output_count": top_output,
        "valid_verifier_count": len([item for item in normalized if item["source"] == "verifier"]),
        "fallback_added_count": len(fallback_added),
        "fallback_added_files": fallback_added,
        "invalid_files": invalid_files,
        "duplicate_files": duplicate_files,
        "ranked_files": normalized,
    }


def truncate_text(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 15].rstrip() + " ...[truncated]"


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Verifier pass for fault-localization rankings.")
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--pred", type=Path, required=True, help="Proposed prediction JSONL input")
    parser.add_argument("--out", type=Path, required=True, help="Verifier prediction JSONL output")
    parser.add_argument("--provider", choices=["dry-run", "deepseek", "codex"], default="dry-run")
    parser.add_argument("--model", help="Provider model name")
    parser.add_argument("--trace", type=Path, help="Optional agent trace JSONL input")
    parser.add_argument("--top-output", type=int, default=10)
    parser.add_argument("--max-snippet-lines", type=int, default=16)
    parser.add_argument("--max-trace-chars", type=int, default=10000)
    parser.add_argument("--limit", type=int, help="Only process the first N predictions")
    parser.add_argument("--bug-ids", help="Comma-separated bug ids to process")
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=ROOT / "outputs" / "prompts_verifier",
        help="Directory for verifier prompts",
    )
    args = parser.parse_args()

    bugs = {record["bug_id"]: record for record in read_jsonl(args.bugs)}
    predictions = read_jsonl(args.pred)
    trace_by_bug = {record["bug_id"]: record for record in read_jsonl(args.trace)} if args.trace else {}
    selected_bug_ids = {part.strip() for part in args.bug_ids.split(",") if part.strip()} if args.bug_ids else set()
    if selected_bug_ids:
        predictions = [
            prediction for prediction in predictions if str(prediction["bug_id"]) in selected_bug_ids
        ]
    if args.limit is not None:
        predictions = predictions[: args.limit]

    args.prompt_dir.mkdir(parents=True, exist_ok=True)
    client = None if args.provider == "dry-run" else client_for(args.provider, args.model)
    records: list[dict[str, Any]] = []

    for prediction in predictions:
        bug_id = str(prediction["bug_id"])
        bug_record = bugs[bug_id]
        sources_by_file = source_by_file(bug_record)
        proposed_ranking = prediction.get("ranked_files", [])[: args.top_output]
        trace_record = trace_by_bug.get(bug_id, {})
        observations = trace_record.get("observations", [])
        if not isinstance(observations, list):
            observations = []
        candidate_evidence = build_candidate_evidence(
            bug_record=bug_record,
            prediction=prediction,
            sources_by_file=sources_by_file,
            max_snippet_lines=args.max_snippet_lines,
        )
        prompt = build_verifier_prompt(
            bug_record=bug_record,
            proposed_ranking=proposed_ranking,
            candidate_evidence=candidate_evidence,
            trace_observations=compact_observations(observations, max_chars=args.max_trace_chars),
            top_output=args.top_output,
        )
        prompt_path = args.prompt_dir / f"{bug_id}_verifier_prompt.json"
        prompt_path.write_text(prompt, encoding="utf-8")

        if args.provider == "dry-run":
            parsed = {"ranked_files": proposed_ranking}
            record = normalize_verifier_output(
                bug_id=bug_id,
                parsed=parsed,
                proposal=prediction,
                top_output=args.top_output,
                provider="dry-run",
                model="",
                prompt_path=str(prompt_path),
                prompt_chars=len(prompt),
                response_chars=0,
                duration_seconds=0.0,
                token_usage={},
            )
            records.append(record)
            print(f"[{bug_id}] wrote verifier prompt {prompt_path}", flush=True)
            continue

        assert client is not None
        started_at = time.perf_counter()
        response = client.complete(system=VERIFIER_SYSTEM_PROMPT, user=prompt)
        duration_seconds = time.perf_counter() - started_at
        parsed = parse_json_object(response.content)
        record = normalize_verifier_output(
            bug_id=bug_id,
            parsed=parsed,
            proposal=prediction,
            top_output=args.top_output,
            provider=response.provider or args.provider,
            model=response.model or args.model or "",
            prompt_path=str(prompt_path),
            prompt_chars=len(prompt),
            response_chars=len(response.content),
            duration_seconds=duration_seconds,
            token_usage=response.usage,
        )
        records.append(record)
        print(
            f"[{bug_id}] verifier rerank in {duration_seconds:.1f}s "
            f"tokens={(response.usage or {}).get('total_tokens')}",
            flush=True,
        )

    write_jsonl(args.out, records)
    print(f"Wrote {len(records)} verifier prediction(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
