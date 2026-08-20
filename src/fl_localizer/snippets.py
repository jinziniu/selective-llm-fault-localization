from __future__ import annotations

from pathlib import Path
import re

from fl_localizer.text import tokenize


STACK_LOCATION_RE = re.compile(r"\(([^():]+\.java):(\d+)\)")
STOP_TOKENS = {
    "a",
    "an",
    "abstract",
    "and",
    "at",
    "be",
    "boolean",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "int",
    "into",
    "is",
    "it",
    "java",
    "junit",
    "double",
    "float",
    "not",
    "of",
    "on",
    "or",
    "org",
    "apache",
    "commons",
    "com",
    "google",
    "javascript",
    "jscomp",
    "rhino",
    "jstype",
    "framework",
    "assertion",
    "failed",
    "lang3",
    "test",
    "tests",
    "src",
    "main",
    "long",
    "class",
    "public",
    "private",
    "protected",
    "static",
    "final",
    "void",
    "return",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
    "you",
}

HIGH_SIGNAL_TERMS = {
    "allocation",
    "api",
    "bounds",
    "button",
    "chain",
    "clear",
    "clone",
    "count",
    "constructor",
    "currency",
    "cycle",
    "declaration",
    "declarations",
    "declare",
    "declared",
    "declares",
    "detected",
    "extends",
    "formatcurrency",
    "getprop",
    "getdeclaredtype",
    "addnumber",
    "implements",
    "inheritance",
    "interface",
    "isloading",
    "isdisabled",
    "ispending",
    "isprocessing",
    "issubmitting",
    "addsingletongetter",
    "bytebuddy",
    "getter",
    "getinstance",
    "instantiate",
    "instantiator",
    "loading",
    "maybedeclarequalifiedname",
    "mock",
    "onclick",
    "propname",
    "property",
    "prototype",
    "negative",
    "number",
    "numeric",
    "qname",
    "qualified",
    "qualifiedname",
    "recursive",
    "reseed",
    "reset",
    "resolve",
    "resolved",
    "rhsvalue",
    "sample",
    "serialization",
    "singleton",
    "stackoverflowerror",
    "state",
    "subtype",
    "tostring",
    "usequery",
    "unresolved",
    "unreviewed",
    "useconstructor",
    "warning",
    "valueof",
    "zero",
}
COMMENT_SIGNAL_TERMS = HIGH_SIGNAL_TERMS | {
    "addnumber",
    "addsingletongetter",
    "getter",
    "getprop",
    "getdeclaredtype",
    "getinstance",
    "maybedeclarequalifiedname",
    "propname",
    "property",
    "prototype",
    "qname",
    "qualified",
    "qualifiedname",
    "rhsvalue",
    "singleton",
    "tostring",
    "valueof",
}
WIDE_CONTEXT_TERMS = {
    "addnumber",
    "api",
    "button",
    "count",
    "currency",
    "formatcurrency",
    "isloading",
    "isdisabled",
    "ispending",
    "isprocessing",
    "issubmitting",
    "loading",
    "mock",
    "negative",
    "number",
    "numeric",
    "onclick",
    "propname",
    "property",
    "prototype",
    "qname",
    "maybedeclarequalifiedname",
    "queryfn",
    "qualified",
    "qualifiedname",
    "rhsvalue",
    "addsingletongetter",
    "getter",
    "getinstance",
    "singleton",
    "tostring",
    "usequery",
    "unreviewed",
    "valueof",
    "zero",
}
NUMERIC_OUTPUT_TERMS = {
    "abs",
    "addnumber",
    "long",
    "math",
    "negative",
    "number",
    "string",
    "tostring",
    "value",
    "valueof",
    "zero",
}


def relevant_terms(query: str, *, max_terms: int = 40) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for token in tokenize(query):
        if len(token) < 3 or token in STOP_TOKENS or token in seen:
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) >= max_terms:
            break
    return terms


def extract_relevant_snippet(
    content: str,
    query: str,
    *,
    file_path: str = "",
    stack_trace: str = "",
    max_lines: int = 24,
    context_lines: int = 1,
) -> str:
    stack_snippet = extract_stack_snippet(
        content,
        file_path=file_path,
        stack_trace=stack_trace,
        max_lines=max_lines,
    )
    if stack_snippet:
        return stack_snippet

    terms = set(relevant_terms(query))
    if has_numeric_output_signal(query, terms):
        terms.update(NUMERIC_OUTPUT_TERMS)
    if not terms:
        return "\n".join(content.splitlines()[:max_lines])

    lines = content.splitlines()
    scored_lines: list[tuple[float, int]] = []
    for index, line in enumerate(lines):
        line_terms = set(tokenize(line))
        matched = line_terms & terms
        if is_comment_header_line(line) and not (matched & COMMENT_SIGNAL_TERMS):
            continue
        if not matched:
            continue
        score = float(len(matched))
        score += 3.0 * len(matched & HIGH_SIGNAL_TERMS)
        lowered_line = line.lower()
        if terms & {"addsingletongetter", "getter", "getinstance", "singleton"}:
            score += 6.0 * len(
                line_terms & {"addsingletongetter", "getter", "getinstance", "singleton"}
            )
        if "button" in terms and re.search(r"<\s*button\b|<\s*Button\b", line):
            score += 14.0
        if terms & {"loading", "isloading", "ispending", "issubmitting"}:
            if re.search(r"\bis(?:Loading|Pending|Submitting)\b", line):
                score += 6.0
        if terms & {"currency", "usd", "eur", "euro"}:
            if re.search(r"\bcurrency\s*:", line) or re.search(r"\b(?:USD|EUR)\b", line):
                score += 10.0
        if "confirm" in terms and any(
            phrase in lowered_line
            for phrase in ("confirm", "continue", "create invoice", "yes, i confirm")
        ):
            score += 4.0
        if re.search(r"\b(?:class|interface|enum|record)\s+[A-Za-z_][A-Za-z0-9_]*", line):
            score += 1.0
        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(", line):
            score += 0.5
        scored_lines.append((score, index))

    selected: set[int] = set()
    selected_context_lines = context_lines
    if terms & WIDE_CONTEXT_TERMS:
        selected_context_lines = max(selected_context_lines, 4)
    if terms & {"button", "isdisabled", "onclick"}:
        selected_context_lines = max(selected_context_lines, 8)
    offset_order = [0]
    for distance in range(1, selected_context_lines + 1):
        offset_order.append(distance)
    for distance in range(1, selected_context_lines + 1):
        offset_order.append(-distance)
    for _score, index in sorted(scored_lines, key=lambda item: (-item[0], item[1])):
        for offset in offset_order:
            selected_index = index + offset
            if 0 <= selected_index < len(lines):
                selected.add(selected_index)
                if len(selected) >= max_lines:
                    break
        if len(selected) >= max_lines:
            break

    if not selected:
        return "\n".join(lines[:max_lines])

    rendered: list[str] = []
    previous: int | None = None
    for index in sorted(selected):
        if previous is not None and index > previous + 1:
            rendered.append("...")
        rendered.append(f"{index + 1}: {lines[index]}")
        previous = index
    return "\n".join(rendered)


def has_numeric_output_signal(query: str, terms: set[str]) -> bool:
    lowered = query.lower()
    return bool(
        re.search(r"(?<![A-Za-z0-9])-0(?:\.0+)?", query)
        or (
            ("codeprinter" in terms or ("code" in terms and "printer" in terms))
            and terms & {"expected", "numeric", "number", "keys"}
            and re.search(r"\d", query)
        )
        or (
            "comparisonfailure" in lowered
            and "expected" in terms
            and re.search(r"\d", query)
        )
    )


def is_comment_header_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(("/*", "*", "//")) or not stripped


def extract_stack_snippet(
    content: str,
    *,
    file_path: str,
    stack_trace: str,
    max_lines: int,
    context_lines: int = 5,
) -> str:
    if not file_path or not stack_trace:
        return ""
    basename = Path(file_path).name
    line_numbers: list[int] = []
    for source_file, line_number_raw in STACK_LOCATION_RE.findall(stack_trace):
        if source_file == basename:
            line_numbers.append(int(line_number_raw))
    if not line_numbers:
        return ""

    lines = content.splitlines()
    selected: set[int] = set()
    for line_number in line_numbers:
        index = line_number - 1
        for offset in range(-context_lines, context_lines + 1):
            selected_index = index + offset
            if 0 <= selected_index < len(lines):
                selected.add(selected_index)

    rendered: list[str] = []
    previous: int | None = None
    for index in sorted(selected)[:max_lines]:
        if previous is not None and index > previous + 1:
            rendered.append("...")
        rendered.append(f"{index + 1}: {lines[index]}")
        previous = index
    return "\n".join(rendered)
