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

from fl_localizer.agent_prompts import AGENT_SYSTEM_PROMPT, build_agent_prompt
from fl_localizer.agent_tools import (
    build_candidate_brief,
    inspect_candidate,
    read_file_window,
    search_candidate_files,
)
from fl_localizer.env_utils import load_dotenv
from fl_localizer.indexer import SourceFile, index_source_files
from fl_localizer.io_utils import read_jsonl, write_jsonl
from fl_localizer.llm_client import CodexClient, DeepSeekClient, LLMResponse, parse_json_object
from fl_localizer.text import extract_runtime_context


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


def load_selected_bug_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = payload.get("selected_bug_ids", [])
    if not isinstance(selected, list):
        raise ValueError(f"{path} does not contain selected_bug_ids")
    return {str(bug_id) for bug_id in selected}


def parse_bug_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def client_for(provider: str, model: str | None):
    if provider == "deepseek":
        return DeepSeekClient(model=model)
    if provider == "codex":
        return CodexClient(model=model)
    raise ValueError(f"Unsupported provider: {provider}")


def usage_add(left: dict[str, Any], right: dict[str, Any] | None) -> dict[str, Any]:
    if not right:
        return left
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, (int, float)) and isinstance(merged.get(key), (int, float)):
            merged[key] += value
        elif isinstance(value, (int, float)) and key not in merged:
            merged[key] = value
    return merged


def build_candidates(
    *,
    prediction: dict[str, Any],
    sources_by_file: dict[str, SourceFile],
    top_candidates: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    candidate_files: list[str] = []
    candidate_briefs: list[dict[str, Any]] = []
    for item in prediction.get("ranked_files", [])[:top_candidates]:
        file_path = str(item.get("file", ""))
        source = sources_by_file.get(file_path)
        if source is None:
            continue
        candidate_files.append(file_path)
        candidate_briefs.append(build_candidate_brief(prediction_item=item, source=source))
    return candidate_files, candidate_briefs


def execute_action(
    *,
    action: dict[str, Any],
    query: str,
    candidate_files: list[str],
    sources_by_file: dict[str, SourceFile],
    max_search_results: int,
    max_read_lines: int,
    max_inspect_lines: int,
) -> dict[str, Any]:
    action_name = str(action.get("action", "")).strip()
    if action_name == "search_files":
        search_query = str(action.get("query", "")).strip()
        return {
            "action": action_name,
            "query": search_query,
            "results": search_candidate_files(
                query=search_query,
                candidate_files=candidate_files,
                sources_by_file=sources_by_file,
                max_results=max_search_results,
            ),
        }

    if action_name == "inspect_candidate":
        file_path = str(action.get("file", "")).strip()
        return {
            "action": action_name,
            "file": file_path,
            "result": inspect_candidate(
                file_path=file_path,
                sources_by_file=sources_by_file,
                query=query,
                max_snippet_lines=max_inspect_lines,
            ),
        }

    if action_name == "read_file_window":
        file_path = str(action.get("file", "")).strip()
        start_line = parse_line_number(action.get("start_line"), default=1)
        end_line = parse_line_number(action.get("end_line"), default=start_line + max_read_lines - 1)
        return {
            "action": action_name,
            "file": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "result": read_file_window(
                file_path=file_path,
                sources_by_file=sources_by_file,
                start_line=start_line,
                end_line=end_line,
                max_lines=max_read_lines,
            ),
        }

    return {"action": action_name or "<missing>", "ok": False, "error": "unsupported action"}


def parse_line_number(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_finish(
    *,
    bug_id: str,
    parsed: dict[str, Any],
    candidate_files: list[str],
    top_output: int,
    provider: str,
    model: str,
    prompt_paths: list[str],
    prompt_chars: int,
    response_chars: int,
    duration_seconds: float,
    token_usage: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    ranked_files = parsed.get("ranked_files", [])
    if str(parsed.get("action", "")) != "finish" or not isinstance(ranked_files, list):
        ranked_files = []

    candidate_file_set = set(candidate_files)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_files: list[str] = []
    duplicate_files: list[str] = []

    for item in ranked_files:
        if not isinstance(item, dict) or "file" not in item:
            continue
        file_path = str(item["file"])
        if file_path not in candidate_file_set:
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
                "source": "agent",
            }
        )
        if len(normalized) >= top_output:
            break

    fallback_added: list[str] = []
    for file_path in candidate_files:
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
                "reason": "Fallback candidate appended in original retrieval order because the agent did not return enough valid files.",
                "source": "retrieval-fallback",
            }
        )

    return {
        "bug_id": bug_id,
        "method": f"agentic-rerank:{provider}",
        "provider": provider,
        "model": model,
        "prompt_paths": prompt_paths,
        "prompt_chars": prompt_chars,
        "response_chars": response_chars,
        "llm_duration_seconds": round(duration_seconds, 3),
        "token_usage": token_usage,
        "candidate_count": len(candidate_files),
        "requested_output_count": top_output,
        "agent_observation_count": len(observations),
        "valid_agent_count": len([item for item in normalized if item["source"] == "agent"]),
        "fallback_added_count": len(fallback_added),
        "fallback_added_files": fallback_added,
        "invalid_files": invalid_files,
        "duplicate_files": duplicate_files,
        "ranked_files": normalized,
    }


def dry_run_finish(
    *,
    bug_id: str,
    query: str,
    candidate_files: list[str],
    sources_by_file: dict[str, SourceFile],
    top_output: int,
    max_search_results: int,
    max_inspect_lines: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observations = [
        {
            "action": "search_files",
            "query": query,
            "results": search_candidate_files(
                query=query,
                candidate_files=candidate_files,
                sources_by_file=sources_by_file,
                max_results=max_search_results,
            ),
        }
    ]
    if candidate_files:
        observations.append(
            {
                "action": "inspect_candidate",
                "file": candidate_files[0],
                "result": inspect_candidate(
                    file_path=candidate_files[0],
                    sources_by_file=sources_by_file,
                    query=query,
                    max_snippet_lines=max_inspect_lines,
                ),
            }
        )
    parsed = {
        "action": "finish",
        "ranked_files": [
            {
                "rank": index,
                "file": file_path,
                "confidence": None,
                "reason": "dry-run keeps original retrieval order",
            }
            for index, file_path in enumerate(candidate_files[:top_output], start=1)
        ],
    }
    record = normalize_finish(
        bug_id=bug_id,
        parsed=parsed,
        candidate_files=candidate_files,
        top_output=top_output,
        provider="dry-run",
        model="",
        prompt_paths=[],
        prompt_chars=0,
        response_chars=0,
        duration_seconds=0.0,
        token_usage={},
        observations=observations,
    )
    return record, observations


def complete_json(
    *,
    client: Any,
    prompt: str,
) -> tuple[dict[str, Any], LLMResponse, float]:
    started_at = time.perf_counter()
    response = client.complete(system=AGENT_SYSTEM_PROMPT, user=prompt)
    duration_seconds = time.perf_counter() - started_at
    return parse_json_object(response.content), response, duration_seconds


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Controlled agentic reranking for fault localization.")
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--pred", type=Path, required=True, help="Baseline prediction JSONL input")
    parser.add_argument("--out", type=Path, required=True, help="Agentic prediction JSONL output")
    parser.add_argument("--trace-out", type=Path, required=True, help="Agent trace JSONL output")
    parser.add_argument(
        "--provider",
        choices=["dry-run", "deepseek", "codex"],
        default="dry-run",
        help="Provider used by the inspection agent.",
    )
    parser.add_argument("--model", help="Provider model name")
    parser.add_argument("--selection", type=Path, help="Selection JSON containing selected_bug_ids")
    parser.add_argument("--bug-ids", help="Comma-separated bug ids to process")
    parser.add_argument("--limit", type=int, help="Only process the first N filtered predictions")
    parser.add_argument("--top-candidates", type=int, default=50)
    parser.add_argument("--top-output", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--max-search-results", type=int, default=8)
    parser.add_argument("--max-read-lines", type=int, default=80)
    parser.add_argument("--max-inspect-lines", type=int, default=24)
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=ROOT / "outputs" / "prompts_agentic",
        help="Directory for agent prompt JSON files",
    )
    args = parser.parse_args()

    selected_bug_ids = load_selected_bug_ids(args.selection) | parse_bug_ids(args.bug_ids)
    bugs = {record["bug_id"]: record for record in read_jsonl(args.bugs)}
    predictions = read_jsonl(args.pred)
    if selected_bug_ids:
        predictions = [
            prediction for prediction in predictions if str(prediction["bug_id"]) in selected_bug_ids
        ]
        found_bug_ids = {str(prediction["bug_id"]) for prediction in predictions}
        missing_bug_ids = selected_bug_ids - found_bug_ids
        if missing_bug_ids:
            raise ValueError(f"Bug ids not found in prediction file: {sorted(missing_bug_ids)}")
    if args.limit is not None:
        predictions = predictions[: args.limit]

    args.prompt_dir.mkdir(parents=True, exist_ok=True)
    client = None if args.provider == "dry-run" else client_for(args.provider, args.model)
    records: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for prediction in predictions:
        bug_id = str(prediction["bug_id"])
        bug_record = bugs[bug_id]
        query = build_query(bug_record)
        sources_by_file = source_by_file(bug_record)
        candidate_files, candidate_briefs = build_candidates(
            prediction=prediction,
            sources_by_file=sources_by_file,
            top_candidates=args.top_candidates,
        )

        if args.provider == "dry-run":
            record, observations = dry_run_finish(
                bug_id=bug_id,
                query=query,
                candidate_files=candidate_files,
                sources_by_file=sources_by_file,
                top_output=args.top_output,
                max_search_results=args.max_search_results,
                max_inspect_lines=args.max_inspect_lines,
            )
            records.append(record)
            traces.append(
                {
                    "bug_id": bug_id,
                    "provider": "dry-run",
                    "candidate_count": len(candidate_files),
                    "observations": observations,
                    "final_ranked_files": record["ranked_files"],
                }
            )
            print(f"[{bug_id}] dry-run agent trace observations={len(observations)}", flush=True)
            continue

        assert client is not None
        observations: list[dict[str, Any]] = []
        prompt_paths: list[str] = []
        prompt_chars = 0
        response_chars = 0
        duration_seconds = 0.0
        token_usage: dict[str, Any] = {}
        parsed: dict[str, Any] | None = None
        provider_name = args.provider
        model_name = args.model or ""

        for step in range(1, args.max_steps + 1):
            prompt = build_agent_prompt(
                bug_record=bug_record,
                candidate_files=candidate_briefs,
                observations=observations,
                step=step,
                max_steps=args.max_steps,
                top_output=args.top_output,
            )
            prompt_path = args.prompt_dir / f"{bug_id}_step{step}_prompt.json"
            prompt_path.write_text(prompt, encoding="utf-8")
            prompt_paths.append(str(prompt_path))
            prompt_chars += len(prompt)
            parsed, response, elapsed = complete_json(client=client, prompt=prompt)
            provider_name = response.provider or provider_name
            model_name = response.model or model_name
            response_chars += len(response.content)
            duration_seconds += elapsed
            token_usage = usage_add(token_usage, response.usage)

            action_name = str(parsed.get("action", ""))
            if action_name == "finish":
                break

            observation = execute_action(
                action=parsed,
                query=query,
                candidate_files=candidate_files,
                sources_by_file=sources_by_file,
                max_search_results=args.max_search_results,
                max_read_lines=args.max_read_lines,
                max_inspect_lines=args.max_inspect_lines,
            )
            observation["requested_by_model"] = parsed
            observations.append(observation)
            print(f"[{bug_id}] step {step}: {action_name}", flush=True)

        if parsed is None or str(parsed.get("action", "")) != "finish":
            final_step = args.max_steps + 1
            prompt = build_agent_prompt(
                bug_record=bug_record,
                candidate_files=candidate_briefs,
                observations=observations,
                step=final_step,
                max_steps=args.max_steps,
                top_output=args.top_output,
                force_finish=True,
            )
            prompt_path = args.prompt_dir / f"{bug_id}_final_prompt.json"
            prompt_path.write_text(prompt, encoding="utf-8")
            prompt_paths.append(str(prompt_path))
            prompt_chars += len(prompt)
            parsed, response, elapsed = complete_json(client=client, prompt=prompt)
            provider_name = response.provider or provider_name
            model_name = response.model or model_name
            response_chars += len(response.content)
            duration_seconds += elapsed
            token_usage = usage_add(token_usage, response.usage)

        record = normalize_finish(
            bug_id=bug_id,
            parsed=parsed,
            candidate_files=candidate_files,
            top_output=args.top_output,
            provider=provider_name,
            model=model_name,
            prompt_paths=prompt_paths,
            prompt_chars=prompt_chars,
            response_chars=response_chars,
            duration_seconds=duration_seconds,
            token_usage=token_usage,
            observations=observations,
        )
        records.append(record)
        traces.append(
            {
                "bug_id": bug_id,
                "provider": provider_name,
                "model": model_name,
                "candidate_count": len(candidate_files),
                "prompt_paths": prompt_paths,
                "observations": observations,
                "final_ranked_files": record["ranked_files"],
                "token_usage": token_usage,
                "llm_duration_seconds": round(duration_seconds, 3),
            }
        )
        print(
            f"[{bug_id}] agentic rerank observations={len(observations)} "
            f"duration={duration_seconds:.1f}s tokens={token_usage.get('total_tokens')}",
            flush=True,
        )

    write_jsonl(args.out, records)
    write_jsonl(args.trace_out, traces)
    print(f"Wrote {len(records)} prediction(s) to {args.out}")
    print(f"Wrote {len(traces)} trace record(s) to {args.trace_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
