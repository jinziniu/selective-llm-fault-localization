from __future__ import annotations

from typing import Any

from fl_localizer.indexer import SourceFile
from fl_localizer.snippets import extract_relevant_snippet
from fl_localizer.text import tokenize


def build_candidate_brief(
    *,
    prediction_item: dict[str, Any],
    source: SourceFile,
) -> dict[str, Any]:
    return {
        "retrieval_rank": prediction_item.get("rank"),
        "retrieval_score": prediction_item.get("score"),
        "file": source.file,
        "package": source.package,
        "class_names": source.class_names[:8],
        "method_names": source.method_names[:20],
    }


def search_candidate_files(
    *,
    query: str,
    candidate_files: list[str],
    sources_by_file: dict[str, SourceFile],
    max_results: int,
    max_line_hits: int = 4,
) -> list[dict[str, Any]]:
    query_terms = {term for term in tokenize(query) if len(term) >= 3}
    if not query_terms:
        return []

    results: list[dict[str, Any]] = []
    for file_path in candidate_files:
        source = sources_by_file.get(file_path)
        if source is None:
            continue

        path_terms = set(tokenize(source.file))
        class_terms = set(tokenize(" ".join(source.class_names)))
        method_terms = set(tokenize(" ".join(source.method_names)))
        content_terms = set(tokenize(source.content[:20000]))

        matched_terms = sorted(query_terms & (path_terms | class_terms | method_terms | content_terms))
        if not matched_terms:
            continue

        score = 0.0
        score += 8.0 * len(query_terms & path_terms)
        score += 6.0 * len(query_terms & class_terms)
        score += 5.0 * len(query_terms & method_terms)
        score += 1.0 * len(query_terms & content_terms)

        line_hits = find_line_hits(source.content, query_terms, max_hits=max_line_hits)
        score += 2.0 * len(line_hits)
        results.append(
            {
                "file": source.file,
                "score": round(score, 3),
                "matched_terms": matched_terms[:20],
                "line_hits": line_hits,
            }
        )

    return sorted(results, key=lambda item: (-float(item["score"]), item["file"]))[:max_results]


def find_line_hits(content: str, query_terms: set[str], *, max_hits: int) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for index, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "*", "/*")):
            continue
        line_terms = set(tokenize(stripped))
        matched = query_terms & line_terms
        if not matched:
            continue
        hits.append(
            {
                "line": index,
                "matched_terms": sorted(matched)[:12],
                "text": truncate_text(stripped, 220),
            }
        )
        if len(hits) >= max_hits:
            break
    return hits


def inspect_candidate(
    *,
    file_path: str,
    sources_by_file: dict[str, SourceFile],
    query: str,
    max_snippet_lines: int,
) -> dict[str, Any]:
    source = sources_by_file.get(file_path)
    if source is None:
        return {"ok": False, "error": "file is not in the candidate pool", "file": file_path}

    return {
        "ok": True,
        "file": source.file,
        "package": source.package,
        "class_names": source.class_names[:12],
        "method_names": source.method_names[:40],
        "relevant_snippet": extract_relevant_snippet(
            source.content,
            query,
            file_path=source.file,
            max_lines=max_snippet_lines,
        ),
    }


def read_file_window(
    *,
    file_path: str,
    sources_by_file: dict[str, SourceFile],
    start_line: int,
    end_line: int,
    max_lines: int,
) -> dict[str, Any]:
    source = sources_by_file.get(file_path)
    if source is None:
        return {"ok": False, "error": "file is not in the candidate pool", "file": file_path}

    lines = source.content.splitlines()
    if not lines:
        return {"ok": True, "file": source.file, "start_line": 1, "end_line": 0, "content": ""}

    start = max(1, start_line)
    end = max(start, end_line)
    if end - start + 1 > max_lines:
        end = start + max_lines - 1
    start = min(start, len(lines))
    end = min(end, len(lines))

    rendered = "\n".join(
        f"{line_number}: {lines[line_number - 1]}"
        for line_number in range(start, end + 1)
    )
    return {
        "ok": True,
        "file": source.file,
        "start_line": start,
        "end_line": end,
        "content": rendered,
    }


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 15].rstrip() + " ...[truncated]"
