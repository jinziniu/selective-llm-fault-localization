#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.env_utils import load_dotenv
from fl_localizer.indexer import SourceFile, index_source_files
from fl_localizer.io_utils import read_jsonl, write_jsonl
from fl_localizer.llm_client import CodexClient, DeepSeekClient, parse_json_object
from fl_localizer.prompts import RERANK_SYSTEM_PROMPT, build_rerank_prompt
from fl_localizer.snippets import extract_relevant_snippet
from fl_localizer.text import extract_runtime_context, tokenize


STACK_FRAME_RE = re.compile(r"^\s*at\s+((?:[a-z_][A-Za-z0-9_]*\.)+[A-Za-z0-9_$]+)\.([A-Za-z0-9_$<>]+)\(")
METHOD_DECL_RE = re.compile(
    r"\b(?:public|protected|private|static|final|synchronized|abstract|native|\s)+"
    r"[A-Za-z_][A-Za-z0-9_<>\[\], ?]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
IMPORT_RE = re.compile(r"^\s*import\s+((?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*);", re.MULTILINE)
COMMON_TEST_DIRS = ("src/test/java", "src/test", "test")
STATE_QUERY_TERMS = {"clone", "copy", "generator", "random", "reseed", "sample", "seed", "state"}
STATE_METHOD_TERMS = {"clear", "copy", "next", "random", "reset", "sample", "seed", "set"}
TYPE_CYCLE_QUERY_TERMS = {
    "cycle",
    "extends",
    "implements",
    "inheritance",
    "interface",
    "recursive",
    "stackoverflowerror",
    "subtype",
}
TYPE_CYCLE_METHOD_TERMS = {"cycle", "handle", "resolve", "subtype", "type"}
PROPERTY_FUNCTION_QUERY_TERMS = {
    "argument",
    "arguments",
    "called",
    "function",
    "param",
    "prototype",
    "property",
    "this",
}
PROPERTY_FUNCTION_CONTEXT_TERMS = {
    "fn",
    "prototype",
    "property",
    "success",
    "this",
}
PROPERTY_FUNCTION_METHOD_TERMS = {
    "declaration",
    "declare",
    "declared",
    "defineslot",
    "getdeclaredtype",
    "getprop",
    "maybedeclarequalifiedname",
    "propname",
    "property",
    "prototype",
    "qname",
    "qualified",
    "rhsvalue",
    "scope",
}
MOCKITO_CONSTRUCTOR_QUERY_TERMS = {
    "abstract",
    "constructor",
    "constructors",
    "inner",
    "mocking",
    "outer",
    "outerinstance",
    "spy",
    "useconstructor",
}
MOCKITO_CONSTRUCTOR_METHOD_TERMS = {
    "bytebuddy",
    "classinstantiator",
    "constructor",
    "create",
    "instantiate",
    "instantiator",
    "mock",
    "mocked",
    "settings",
    "type",
}
FRONTEND_COUNT_QUERY_TERMS = {"api", "count", "counts", "mock", "mocked", "stale", "unreviewed"}
FRONTEND_COUNT_METHOD_TERMS = {
    "api",
    "count",
    "data",
    "fetch",
    "get",
    "getunreviewed",
    "query",
    "queryfn",
    "usequery",
    "unreviewed",
}
FRONTEND_LOADING_QUERY_TERMS = {"loading"}
FRONTEND_LOADING_CONTEXT_TERMS = {"button", "buttons", "confirm", "skeleton"}
FRONTEND_LOADING_METHOD_TERMS = {
    "button",
    "confirm",
    "continue",
    "create",
    "creating",
    "disabled",
    "handlecreateinvoice",
    "handlesubmit",
    "isdisabled",
    "isloading",
    "ispending",
    "isprocessing",
    "issubmitting",
    "loading",
    "mutate",
    "mutation",
    "onclick",
    "pending",
    "processing",
    "setisprocessing",
    "submit",
}
FRONTEND_CURRENCY_QUERY_TERMS = {"currency", "dollar", "dollars", "euro", "euros", "usd"}
FRONTEND_CURRENCY_METHOD_TERMS = {
    "amount",
    "currency",
    "eur",
    "euro",
    "format",
    "formatcurrency",
    "invoice",
    "price",
    "total",
    "usd",
}


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


def infer_project_package(sources: list[SourceFile]) -> str:
    packages = [source.package for source in sources if source.package]
    if not packages:
        return ""
    split_packages = [package.split(".") for package in packages]
    prefix = split_packages[0]
    for parts in split_packages[1:]:
        next_prefix: list[str] = []
        for left, right in zip(prefix, parts):
            if left != right:
                break
            next_prefix.append(left)
        prefix = next_prefix
        if len(prefix) <= 2:
            break
    return ".".join(prefix)


def extract_triggering_classes(record: dict[str, Any]) -> list[str]:
    classes: list[str] = []
    for trigger in record.get("triggering_tests", []):
        class_name = str(trigger).split("::", 1)[0]
        if class_name and class_name not in classes:
            classes.append(class_name)
    test_failure = str(record.get("test_failure", ""))
    if "::" in test_failure:
        class_name = test_failure.split("::", 1)[0]
        if class_name and class_name not in classes:
            classes.append(class_name)
    return classes


def extract_triggering_methods(record: dict[str, Any]) -> list[str]:
    methods: list[str] = []
    for trigger in record.get("triggering_tests", []):
        if "::" not in str(trigger):
            continue
        method = str(trigger).split("::", 1)[1]
        if method and method not in methods:
            methods.append(method)
    test_failure = str(record.get("test_failure", ""))
    if "::" in test_failure:
        method = test_failure.split("::", 1)[1]
        if method and method not in methods:
            methods.append(method)
    return methods


def extract_stack_project_frames(record: dict[str, Any], project_package_hint: str) -> list[tuple[str, str]]:
    frames: list[tuple[str, str]] = []
    for line in str(record.get("stack_trace", "")).splitlines():
        match = STACK_FRAME_RE.match(line)
        if not match:
            continue
        class_fqn, method = match.groups()
        if project_package_hint and not class_fqn.startswith(project_package_hint):
            continue
        if (class_fqn, method) not in frames:
            frames.append((class_fqn, method))
    return frames


def locate_java_file(repo_path: Path, class_fqn: str) -> Path | None:
    relative = Path(*class_fqn.split(".")).with_suffix(".java")
    for test_dir in COMMON_TEST_DIRS:
        candidate = repo_path / test_dir / relative
        if candidate.exists():
            return candidate
    matches = sorted(repo_path.rglob(relative.name))
    for match in matches:
        if "test" in {part.lower() for part in match.parts}:
            return match
    return matches[0] if matches else None


def extract_method_window(content: str, method_name: str, *, context_lines: int = 44) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if method_name not in line:
            continue
        if not METHOD_DECL_RE.search(line):
            continue
        start = max(0, index - context_lines // 3)
        end = min(len(lines), index + context_lines)
        return "\n".join(f"{line_no + 1}: {lines[line_no]}" for line_no in range(start, end))
    return ""


def collect_test_source_context(
    record: dict[str, Any],
    sources: list[SourceFile],
    *,
    max_chars: int,
) -> str:
    if max_chars <= 0:
        return ""

    repo_path = Path(record["repo_path"])
    project_package_hint = infer_project_package(sources)
    methods = set(extract_triggering_methods(record))
    class_names = set(extract_triggering_classes(record))
    for class_fqn, method in extract_stack_project_frames(record, project_package_hint):
        class_names.add(class_fqn)
        methods.add(method)

    contexts: list[str] = []
    for class_fqn in sorted(class_names):
        path = locate_java_file(repo_path, class_fqn)
        if path is None:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        relative_path = path.relative_to(repo_path).as_posix()
        parts = [f"file: {relative_path}", f"class: {class_fqn}"]
        imports = IMPORT_RE.findall(content)
        if imports:
            parts.append("imports:\n" + "\n".join(imports[:30]))
        method_windows = []
        for method in sorted(methods):
            window = extract_method_window(content, method)
            if window:
                method_windows.append(f"method: {method}\n{window}")
        if method_windows:
            parts.append("snippets:\n" + "\n\n".join(method_windows))
        contexts.append("\n".join(parts))

    context = "\n\n---\n\n".join(contexts)
    if len(context) <= max_chars:
        return context
    return context[:max_chars] + "\n...[truncated]"


def build_candidates(
    record: dict[str, Any],
    prediction: dict[str, Any],
    *,
    top_candidates: int,
    max_snippet_lines: int,
    include_retrieval_evidence: bool,
    candidate_detail_level: str = "full",
    snippet_query_extra: str = "",
) -> list[dict[str, Any]]:
    query = build_query(record)
    snippet_query = "\n".join(part for part in [query, snippet_query_extra] if part.strip())
    snippet_query_terms = set(tokenize(snippet_query))
    sources = source_by_file(record)
    candidates: list[dict[str, Any]] = []
    for item in prediction["ranked_files"][:top_candidates]:
        file_path = item["file"]
        source = sources.get(file_path)
        if source is None:
            continue
        candidate_snippet_query = snippet_query
        semantic_terms = semantic_method_terms_for_source(source, snippet_query_terms)
        if semantic_terms:
            candidate_snippet_query = f"{' '.join(sorted(semantic_terms))}\n{snippet_query}"
        candidate = {
            "bm25_rank": item["rank"],
            "bm25_score": item["score"],
            "retrieval_rank": item["rank"],
            "retrieval_score": item["score"],
            "file": file_path,
            "package": source.package,
            "class_names": source.class_names[:10],
            "method_names": source.method_names[:40],
        }
        if candidate_detail_level == "full":
            candidate["relevant_snippet"] = extract_relevant_snippet(
                source.content,
                candidate_snippet_query,
                file_path=file_path,
                stack_trace=str(record.get("stack_trace", "")),
                max_lines=max_snippet_lines,
            )
        if include_retrieval_evidence:
            candidate["retrieval_evidence"] = {
                "method": prediction.get("method", ""),
                "bm25_score": item.get("bm25_score"),
                "test_context_score": item.get("test_context_score"),
                "direct_boost": item.get("direct_boost"),
                "identifier_boost": item.get("identifier_boost"),
                "reference_boost": item.get("reference_boost"),
                "pass_chain_boost": item.get("pass_chain_boost"),
                "reasons": item.get("reasons", []),
            }
        candidates.append(candidate)
    return candidates


def semantic_method_terms_for_source(
    source: SourceFile,
    query_terms: set[str],
) -> set[str]:
    wanted_terms: set[str] = set()
    if query_terms & STATE_QUERY_TERMS:
        wanted_terms.update(STATE_METHOD_TERMS)
    if query_terms & TYPE_CYCLE_QUERY_TERMS:
        wanted_terms.update(TYPE_CYCLE_METHOD_TERMS)
    if (
        query_terms & PROPERTY_FUNCTION_QUERY_TERMS
        and query_terms & PROPERTY_FUNCTION_CONTEXT_TERMS
    ):
        wanted_terms.update(PROPERTY_FUNCTION_METHOD_TERMS)
    if "mockito" in source.file.lower() and query_terms & MOCKITO_CONSTRUCTOR_QUERY_TERMS:
        wanted_terms.update(MOCKITO_CONSTRUCTOR_METHOD_TERMS)
    if source.file.endswith((".ts", ".tsx", ".js", ".jsx")):
        if query_terms & FRONTEND_COUNT_QUERY_TERMS:
            wanted_terms.update(FRONTEND_COUNT_METHOD_TERMS)
        if query_terms & FRONTEND_LOADING_QUERY_TERMS and query_terms & FRONTEND_LOADING_CONTEXT_TERMS:
            wanted_terms.update(FRONTEND_LOADING_METHOD_TERMS)
        if query_terms & FRONTEND_CURRENCY_QUERY_TERMS:
            wanted_terms.update(FRONTEND_CURRENCY_METHOD_TERMS)
    if not wanted_terms:
        return set()

    source_text = " ".join(
        source.method_names + source.class_names + [source.file, source.content[:4000]]
    )
    source_terms = set(tokenize(source_text))
    selected: set[str] = set()
    for term in wanted_terms:
        if term in source_terms:
            selected.add(term)
    for name in source.method_names + source.class_names:
        name_terms = set(tokenize(name))
        if name_terms & wanted_terms:
            selected.update(name_terms)
            selected.add(name.lower())
    return selected


def parse_bug_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def normalize_model_output(
    *,
    bug_id: str,
    parsed: dict[str, Any],
    candidates: list[dict[str, Any]],
    top_output: int,
    provider: str,
    model: str,
    prompt_path: str | None,
    prompt_chars: int,
    response_chars: int,
    duration_seconds: float,
    token_usage: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate_files = [str(candidate["file"]) for candidate in candidates]
    candidate_file_set = set(candidate_files)
    ranked_files = parsed.get("ranked_files", [])
    if not isinstance(ranked_files, list):
        ranked_files = []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_files: list[str] = []
    duplicate_files: list[str] = []

    for index, item in enumerate(ranked_files, start=1):
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
                "source": "llm",
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
                "reason": "Fallback candidate appended in original BM25 order because the model did not return enough valid files.",
                "source": "bm25-fallback",
            }
        )

    return {
        "bug_id": bug_id,
        "method": f"llm-rerank:{provider}",
        "provider": provider,
        "model": model,
        "prompt_path": prompt_path,
        "prompt_chars": prompt_chars,
        "response_chars": response_chars,
        "llm_duration_seconds": round(duration_seconds, 3),
        "token_usage": token_usage or {},
        "candidate_count": len(candidate_files),
        "requested_output_count": top_output,
        "llm_returned_count": len(ranked_files),
        "valid_llm_count": len([item for item in normalized if item["source"] == "llm"]),
        "fallback_added_count": len(fallback_added),
        "fallback_added_files": fallback_added,
        "invalid_files": invalid_files,
        "duplicate_files": duplicate_files,
        "ranked_files": normalized,
    }


def client_for(provider: str, model: str | None):
    if provider == "deepseek":
        return DeepSeekClient(model=model)
    if provider == "codex":
        return CodexClient(model=model)
    raise ValueError(f"Unsupported provider: {provider}")


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="LLM reranking for BM25 fault candidates.")
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--bm25", type=Path, required=True, help="BM25 prediction JSONL input")
    parser.add_argument("--out", type=Path, required=True, help="Reranked prediction JSONL output")
    parser.add_argument(
        "--provider",
        choices=["dry-run", "deepseek", "codex"],
        default="dry-run",
        help="LLM provider. dry-run writes prompts without calling a model.",
    )
    parser.add_argument("--model", help="Provider model name")
    parser.add_argument("--top-candidates", type=int, default=20)
    parser.add_argument("--top-output", type=int, default=10)
    parser.add_argument("--max-snippet-lines", type=int, default=18)
    parser.add_argument(
        "--candidate-detail-level",
        choices=["metadata", "full"],
        default="full",
        help="Use 'metadata' to omit source snippets from candidate files; default preserves existing full behavior.",
    )
    parser.add_argument("--limit", type=int, help="Only process the first N bugs")
    parser.add_argument("--bug-ids", help="Comma-separated bug ids to process, e.g. Math-12,Math-14")
    parser.add_argument(
        "--include-retrieval-evidence",
        action="store_true",
        help="Include retrieval score components and reasons from the prediction file.",
    )
    parser.add_argument(
        "--include-test-context",
        action="store_true",
        help="Include triggering test source excerpts in the prompt.",
    )
    parser.add_argument(
        "--max-test-context-chars",
        type=int,
        default=12000,
        help="Maximum triggering test source context characters when enabled.",
    )
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=ROOT / "outputs" / "prompts",
        help="Directory for prompt JSON files",
    )
    args = parser.parse_args()

    bugs = {record["bug_id"]: record for record in read_jsonl(args.bugs)}
    predictions = read_jsonl(args.bm25)
    selected_bug_ids = parse_bug_ids(args.bug_ids)
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
    records: list[dict[str, Any]] = []
    client = None if args.provider == "dry-run" else client_for(args.provider, args.model)

    for prediction in predictions:
        bug_id = prediction["bug_id"]
        bug_record = bugs[bug_id]
        sources = list(source_by_file(bug_record).values())
        test_source_context = (
            collect_test_source_context(
                bug_record,
                sources,
                max_chars=args.max_test_context_chars,
            )
            if args.include_test_context
            else ""
        )
        candidates = build_candidates(
            bug_record,
            prediction,
            top_candidates=args.top_candidates,
            max_snippet_lines=args.max_snippet_lines,
            include_retrieval_evidence=args.include_retrieval_evidence,
            candidate_detail_level=args.candidate_detail_level,
            snippet_query_extra=test_source_context,
        )
        prompt = build_rerank_prompt(
            bug_record,
            candidates,
            top_output=args.top_output,
            test_source_context=test_source_context,
            evidence_mode=args.include_retrieval_evidence or args.include_test_context,
        )
        prompt_path = args.prompt_dir / f"{bug_id}_rerank_prompt.json"
        prompt_path.write_text(prompt, encoding="utf-8")

        if args.provider == "dry-run":
            records.append(
                {
                    "bug_id": bug_id,
                    "method": "llm-rerank:dry-run",
                    "provider": "dry-run",
                    "model": args.model or "",
                    "prompt_path": str(prompt_path),
                    "prompt_chars": len(prompt),
                    "response_chars": 0,
                    "llm_duration_seconds": 0.0,
                    "token_usage": {},
                    "candidate_count": len(candidates),
                    "requested_output_count": args.top_output,
                    "llm_returned_count": 0,
                    "valid_llm_count": 0,
                    "fallback_added_count": min(args.top_output, len(candidates)),
                    "fallback_added_files": [
                        str(candidate["file"]) for candidate in candidates[: args.top_output]
                    ],
                    "invalid_files": [],
                    "duplicate_files": [],
                    "prompt_features": {
                        "include_retrieval_evidence": args.include_retrieval_evidence,
                        "include_test_context": args.include_test_context,
                        "candidate_detail_level": args.candidate_detail_level,
                        "test_source_context_chars": len(test_source_context),
                    },
                    "ranked_files": [
                        {
                            "rank": index,
                            "file": candidate["file"],
                            "confidence": None,
                            "reason": "dry-run preserves BM25 order",
                            "source": "bm25-fallback",
                        }
                        for index, candidate in enumerate(candidates[: args.top_output], start=1)
                    ],
                }
            )
            print(f"[{bug_id}] wrote prompt {prompt_path}", flush=True)
            continue

        assert client is not None
        started_at = time.perf_counter()
        response = client.complete(system=RERANK_SYSTEM_PROMPT, user=prompt)
        duration_seconds = time.perf_counter() - started_at
        parsed = parse_json_object(response.content)
        record = normalize_model_output(
            bug_id=bug_id,
            parsed=parsed,
            candidates=candidates,
            top_output=args.top_output,
            provider=response.provider,
            model=response.model,
            prompt_path=str(prompt_path),
            prompt_chars=len(prompt),
            response_chars=len(response.content),
            duration_seconds=duration_seconds,
            token_usage=response.usage,
        )
        record["prompt_features"] = {
            "include_retrieval_evidence": args.include_retrieval_evidence,
            "include_test_context": args.include_test_context,
            "candidate_detail_level": args.candidate_detail_level,
            "test_source_context_chars": len(test_source_context),
        }
        records.append(record)
        write_jsonl(args.out, records)
        total_tokens = (response.usage or {}).get("total_tokens")
        token_text = f", total_tokens={total_tokens}" if total_tokens is not None else ""
        print(
            f"[{bug_id}] reranked with {response.provider}:{response.model} "
            f"in {duration_seconds:.1f}s{token_text}",
            flush=True,
        )

    write_jsonl(args.out, records)
    print(f"Wrote {len(records)} record(s) to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
