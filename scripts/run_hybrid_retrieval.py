#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.bm25 import BM25Index
from fl_localizer.indexer import SourceFile, index_java_sources
from fl_localizer.io_utils import read_jsonl, write_jsonl
from fl_localizer.text import extract_runtime_context, split_camel, tokenize


FQN_RE = re.compile(r"\b(?:[a-z_][A-Za-z0-9_]*\.)+[A-Z][A-Za-z0-9_]*(?:\$[A-Za-z0-9_]+)?")
CLASS_IDENTIFIER_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]{2,}\b")
CONSTRUCTOR_RE = re.compile(r"\bnew\s+([A-Z][A-Za-z0-9_]*)\s*\(")
STACK_FRAME_RE = re.compile(r"^\s*at\s+((?:[a-z_][A-Za-z0-9_]*\.)+[A-Za-z0-9_$]+)\.([A-Za-z0-9_$<>]+)\(")
FAILURE_SECTION_RE = re.compile(r"^---\s+(.+?)\s*$")
METHOD_DECL_RE = re.compile(
    r"\b(?:public|protected|private|static|final|synchronized|abstract|native|\s)+"
    r"[A-Za-z_][A-Za-z0-9_<>\[\], ?]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
IMPORT_RE = re.compile(r"^\s*import\s+((?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*);", re.MULTILINE)
TEST_SUFFIXES = ("Test", "Tests", "TestCase")
COMMON_TEST_DIRS = ("src/test/java", "src/test", "test")
PASS_CHAIN_BOOST = 700.0
PASS_CHAIN_MAX_ITEMS = 12
PASS_CHAIN_EVIDENCE_TERMS = {
    "advanced",
    "check",
    "collapse",
    "compiler",
    "compilation",
    "fold",
    "inline",
    "late",
    "normalize",
    "optimization",
    "optimizations",
    "options",
    "peephole",
    "remove",
    "simple",
    "substitute",
}
PASS_CHAIN_CLASS_TERMS = {
    "alias",
    "check",
    "collapse",
    "collect",
    "compiler",
    "dead",
    "fold",
    "inline",
    "normalize",
    "optimization",
    "optimizations",
    "pass",
    "peephole",
    "remove",
    "substitute",
    "var",
}
NOISY_DIRECT_HINTS = {
    "Assert",
    "AssertionFailedError",
    "BlockJUnit4ClassRunner",
    "DefaultExecutor",
    "DelegatingMethodAccessorImpl",
    "DispatchUtils",
    "FrameworkMethod",
    "InvokeMethod",
    "JUnit4TestAdapter",
    "JUnitTask",
    "JUnitTestRunner",
    "Launcher",
    "Main",
    "Method",
    "NativeMethodAccessorImpl",
    "ParentRunner",
    "Project",
    "ReflectiveCallable",
    "RunAfters",
    "RunBefores",
    "Target",
    "Task",
    "UnknownElement",
}


@dataclass(frozen=True)
class ScoreBreakdown:
    bm25_score: float
    test_context_score: float
    direct_boost: float
    identifier_boost: float
    reference_boost: float
    pass_chain_boost: float
    type_system_boost: float
    reasons: list[str]

    @property
    def total(self) -> float:
        return (
            self.bm25_score
            + self.test_context_score
            + self.direct_boost
            + self.identifier_boost
            + self.reference_boost
            + self.pass_chain_boost
            + self.type_system_boost
        )


def build_query(record: dict[str, Any]) -> str:
    bug_report = record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}
    parts = [
        str(bug_report.get("id", "")),
        str(bug_report.get("text", "")),
        str(record.get("test_failure", "")),
        " ".join(record.get("triggering_tests", [])),
        extract_runtime_context(focused_stack_trace(record)),
    ]
    return "\n".join(part for part in parts if part)


def ranked_score_map(index: BM25Index, query: str) -> dict[str, float]:
    ranked = index.rank(query, top_k=len(index.documents))
    return {item.file: item.score for item in ranked}


def simple_name(fqn_or_name: str) -> str:
    return fqn_or_name.rsplit(".", 1)[-1].split("$", 1)[0]


def strip_test_suffix(class_name: str) -> str | None:
    for suffix in TEST_SUFFIXES:
        if class_name.endswith(suffix) and len(class_name) > len(suffix):
            return class_name[: -len(suffix)]
    return None


def source_hint_from_test_class_name(class_name: str) -> str | None:
    stripped_suffix = strip_test_suffix(class_name)
    if stripped_suffix:
        return stripped_suffix.split("_", 1)[0]

    if class_name.startswith("Test") and len(class_name) > len("Test"):
        stripped_prefix = class_name[len("Test") :]
        return stripped_prefix.split("_", 1)[0]

    return None


def source_class_names(source: SourceFile) -> set[str]:
    names = set(source.class_names)
    names.add(Path(source.file).stem)
    return names


def source_fqns(source: SourceFile) -> set[str]:
    names = source_class_names(source)
    if source.package:
        return {f"{source.package}.{name}" for name in names}
    return names


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


def focused_stack_trace(record: dict[str, Any]) -> str:
    stack_trace = str(record.get("stack_trace", ""))
    if "--- " not in stack_trace:
        return stack_trace

    wanted = set(str(trigger) for trigger in record.get("triggering_tests", []))
    test_failure = str(record.get("test_failure", ""))
    if test_failure:
        wanted.add(test_failure)
    if not wanted:
        return stack_trace

    sections: list[tuple[str, list[str]]] = []
    current_header = ""
    current_lines: list[str] = []
    for line in stack_trace.splitlines():
        match = FAILURE_SECTION_RE.match(line)
        if match:
            if current_header or current_lines:
                sections.append((current_header, current_lines))
            current_header = match.group(1).strip()
            current_lines = [line]
            continue
        current_lines.append(line)
    if current_header or current_lines:
        sections.append((current_header, current_lines))

    selected = [lines for header, lines in sections if header in wanted]
    if not selected:
        return stack_trace
    return "\n".join(line for lines in selected for line in lines)


def extract_stack_project_frames(
    stack_trace: str,
    project_package_hint: str,
) -> list[tuple[str, str]]:
    frames: list[tuple[str, str]] = []
    for line in stack_trace.splitlines():
        match = STACK_FRAME_RE.match(line)
        if not match:
            continue
        class_fqn, method = match.groups()
        if project_package_hint and not class_fqn.startswith(project_package_hint):
            continue
        if (class_fqn, method) not in frames:
            frames.append((class_fqn, method))
    return frames


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


def extract_method_window(content: str, method_name: str, *, context_lines: int = 35) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if method_name not in line:
            continue
        if not METHOD_DECL_RE.search(line):
            continue
        start = max(0, index - context_lines // 3)
        end = min(len(lines), index + context_lines)
        return "\n".join(lines[start:end])
    return ""


def collect_test_context(record: dict[str, Any], project_package_hint: str) -> str:
    repo_path = Path(record["repo_path"])
    methods = set(extract_triggering_methods(record))
    contexts: list[str] = []

    class_names = set(extract_triggering_classes(record))
    stack_trace = focused_stack_trace(record)
    for class_fqn, method in extract_stack_project_frames(stack_trace, project_package_hint):
        class_names.add(class_fqn)
        methods.add(method)

    for class_fqn in sorted(class_names):
        path = locate_java_file(repo_path, class_fqn)
        if path is None:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        contexts.append("\n".join(IMPORT_RE.findall(content)))
        for method in methods:
            window = extract_method_window(content, method)
            if window:
                contexts.append(window)
        if not any(method in content for method in methods):
            contexts.append("\n".join(content.splitlines()[:80]))

    return "\n".join(part for part in contexts if part)


def collect_direct_class_hints(record: dict[str, Any], project_package_hint: str) -> set[str]:
    hints: set[str] = set()
    stack_trace = focused_stack_trace(record)

    for class_fqn in extract_triggering_classes(record):
        name = simple_name(class_fqn)
        stripped = source_hint_from_test_class_name(name)
        if stripped:
            hints.add(stripped)

    for class_fqn, _method in extract_stack_project_frames(stack_trace, project_package_hint):
        name = simple_name(class_fqn)
        stripped = source_hint_from_test_class_name(name)
        if stripped:
            hints.add(stripped)
        elif not name.endswith("Test"):
            hints.add(name)

    for fqn in FQN_RE.findall(stack_trace):
        if project_package_hint and not fqn.startswith(project_package_hint):
            continue
        name = simple_name(fqn)
        stripped = source_hint_from_test_class_name(name)
        if stripped:
            hints.add(stripped)
        elif not name.endswith("Test"):
            hints.add(name)

    return {hint for hint in hints if hint not in NOISY_DIRECT_HINTS}


def collect_identifier_terms(record: dict[str, Any], test_context: str) -> set[str]:
    text = "\n".join(
        [
            str(record.get("test_failure", "")),
            " ".join(record.get("triggering_tests", [])),
            extract_runtime_context(focused_stack_trace(record)),
            test_context,
        ]
    )
    terms = set(tokenize(text))
    return {term for term in terms if len(term) >= 4}


def direct_boost_for(source: SourceFile, direct_hints: set[str]) -> tuple[float, list[str]]:
    boost = 0.0
    reasons: list[str] = []
    names = source_class_names(source)
    for hint in sorted(direct_hints):
        if hint in names:
            boost += 90.0
            reasons.append(f"direct_class_hint:{hint}")
        elif hint.lower() == Path(source.file).stem.lower():
            boost += 90.0
            reasons.append(f"direct_file_hint:{hint}")
    return boost, reasons


def identifier_boost_for(source: SourceFile, identifier_terms: set[str]) -> tuple[float, list[str]]:
    names = source_class_names(source)
    source_terms: set[str] = set()
    for name in names:
        source_terms.add(name.lower())
        source_terms.update(part.lower() for part in split_camel(name))
    source_terms.update(term.lower() for term in source.method_names)
    source_terms.update(tokenize(source.file))

    overlap = sorted(term for term in source_terms if term in identifier_terms and len(term) >= 4)
    if not overlap:
        return 0.0, []

    capped = overlap[:8]
    return min(32.0, 4.0 * len(capped)), [f"identifier_overlap:{','.join(capped)}"]


def type_system_boost_for(
    source: SourceFile,
    *,
    direct_hints: set[str],
    identifier_terms: set[str],
) -> tuple[float, list[str]]:
    if "TypeCheck" not in direct_hints:
        return 0.0, []
    if "type" not in identifier_terms:
        return 0.0, []
    if not (identifier_terms & {"mismatch", "inconsistent", "required", "found"}):
        return 0.0, []

    class_terms: set[str] = set()
    for name in source_class_names(source):
        class_terms.update(class_name_terms(name))
    file_path = source.file

    boost = 0.0
    reasons: list[str] = []
    if file_path.endswith("TypeInference.java") and (
        identifier_terms & {"function", "object", "return", "type"}
    ):
        boost = max(boost, 130.0)
        reasons.append("type_system_hint:type_inference")

    if "/rhino/jstype/" in file_path and "type" in class_terms:
        overlap = class_terms & identifier_terms
        if "object" in class_terms and "object" in identifier_terms:
            boost = max(boost, 130.0)
            reasons.append("type_system_hint:jstype_object")
        elif overlap:
            boost = max(boost, 55.0)
            reasons.append(f"type_system_hint:jstype:{','.join(sorted(overlap)[:4])}")

    return boost, reasons


def collect_reference_class_hints(
    selected: list[tuple[str, float, ScoreBreakdown]],
    source_by_file: dict[str, SourceFile],
    available_class_names: set[str],
    *,
    top_n: int = 12,
) -> set[str]:
    hints: set[str] = set()
    for file_path, _score, _breakdown in selected[:top_n]:
        source = source_by_file[file_path]
        own_names = source_class_names(source)
        for name in CLASS_IDENTIFIER_RE.findall(source.content):
            if name in own_names:
                continue
            if name in available_class_names:
                hints.add(name)
    return hints


def class_name_terms(class_name: str) -> set[str]:
    terms = {class_name.lower()}
    terms.update(part.lower() for part in split_camel(class_name))
    return {term for term in terms if term}


def is_pass_config_source(source: SourceFile) -> bool:
    names = source_class_names(source)
    return any(name.endswith("PassConfig") for name in names)


def pass_chain_boost_for_name(class_name: str, identifier_terms: set[str]) -> float:
    terms = class_name_terms(class_name)
    boost = PASS_CHAIN_BOOST
    if terms & {"optimization", "optimizations"} and identifier_terms & {
        "optimization",
        "optimizations",
    }:
        boost += 520.0
    if "peephole" in terms and identifier_terms & {"optimization", "optimizations"}:
        boost += 160.0
    return boost


def collect_pass_chain_class_hints(
    selected: list[tuple[str, float, ScoreBreakdown]],
    source_by_file: dict[str, SourceFile],
    available_class_names: set[str],
    identifier_terms: set[str],
    *,
    top_n: int = 20,
) -> dict[str, set[str]]:
    evidence_terms = identifier_terms & PASS_CHAIN_EVIDENCE_TERMS
    if not evidence_terms:
        return {}

    hints: dict[str, set[str]] = {}
    for file_path, _score, _breakdown in selected[:top_n]:
        source = source_by_file[file_path]
        if not is_pass_config_source(source):
            continue
        own_names = source_class_names(source)
        origin = Path(source.file).stem
        for name in CONSTRUCTOR_RE.findall(source.content):
            if name in own_names or name not in available_class_names:
                continue
            terms = class_name_terms(name)
            if "pass" not in terms and "peephole" not in terms and not (
                terms & PASS_CHAIN_CLASS_TERMS & evidence_terms
            ):
                continue
            hints.setdefault(name, set()).add(origin)
    return hints


def hybrid_rank(
    record: dict[str, Any],
    *,
    top_k: int,
    force_direct_hints: bool = False,
    force_reference_hints: bool = False,
    force_pass_chain_hints: bool = False,
    force_type_system_hints: bool = False,
) -> dict[str, Any]:
    repo_path = Path(record["repo_path"])
    sources = index_java_sources(repo_path, record["source_dir"])
    source_by_file = {source.file: source for source in sources}
    available_class_names = {name for source in sources for name in source_class_names(source)}
    documents = [(source.file, source.document_text()) for source in sources]
    index = BM25Index(documents)
    bm25_scores = ranked_score_map(index, build_query(record))

    project_package_hint = infer_project_package(sources)
    test_context = collect_test_context(record, project_package_hint)
    test_scores = ranked_score_map(index, test_context) if test_context.strip() else {}
    direct_hints = collect_direct_class_hints(record, project_package_hint)
    identifier_terms = collect_identifier_terms(record, test_context)

    scored: list[tuple[str, float, ScoreBreakdown]] = []
    for source in sources:
        direct_boost, direct_reasons = direct_boost_for(source, direct_hints)
        identifier_boost, identifier_reasons = identifier_boost_for(source, identifier_terms)
        type_system_boost, type_system_reasons = (
            type_system_boost_for(
                source,
                direct_hints=direct_hints,
                identifier_terms=identifier_terms,
            )
            if force_type_system_hints
            else (0.0, [])
        )
        breakdown = ScoreBreakdown(
            bm25_score=bm25_scores.get(source.file, 0.0),
            test_context_score=0.55 * test_scores.get(source.file, 0.0),
            direct_boost=direct_boost,
            identifier_boost=identifier_boost,
            reference_boost=0.0,
            pass_chain_boost=0.0,
            type_system_boost=type_system_boost,
            reasons=direct_reasons + identifier_reasons + type_system_reasons,
        )
        scored.append((source.file, breakdown.total, breakdown))

    scored.sort(key=lambda item: (-item[1], item[0]))
    selected = scored[:top_k]
    selected_files = {file_path for file_path, _score, _breakdown in selected}

    if force_direct_hints and top_k > 0:
        direct_items = [
            item
            for item in scored[top_k:]
            if item[0] not in selected_files
            and any(reason.startswith("direct_") for reason in item[2].reasons)
        ]
        for direct_item in direct_items:
            replace_index = None
            for index in range(len(selected) - 1, -1, -1):
                if not any(reason.startswith("direct_") for reason in selected[index][2].reasons):
                    replace_index = index
                    break
            if replace_index is None:
                break
            selected_files.remove(selected[replace_index][0])
            selected[replace_index] = direct_item
            selected_files.add(direct_item[0])
        selected.sort(key=lambda item: (-item[1], item[0]))

    if force_reference_hints and top_k > 0:
        reference_hints = collect_reference_class_hints(
            selected,
            source_by_file,
            available_class_names,
        )
        reference_items = []
        for file_path, _score, breakdown in scored[top_k:]:
            if file_path in selected_files:
                continue
            source = source_by_file[file_path]
            matched = sorted(source_class_names(source) & reference_hints)
            if not matched:
                continue
            boosted_breakdown = replace(
                breakdown,
                reference_boost=max(breakdown.reference_boost, 260.0),
                reasons=breakdown.reasons + [f"reference_class_hint:{','.join(matched[:4])}"],
            )
            reference_items.append((file_path, boosted_breakdown.total, boosted_breakdown))

        reference_items.sort(key=lambda item: (-item[1], item[0]))
        for reference_item in reference_items:
            replace_index = None
            for index in range(len(selected) - 1, -1, -1):
                reasons = selected[index][2].reasons
                if not any(reason.startswith(("direct_", "reference_")) for reason in reasons):
                    replace_index = index
                    break
            if replace_index is None:
                break
            selected_files.remove(selected[replace_index][0])
            selected[replace_index] = reference_item
            selected_files.add(reference_item[0])
        selected.sort(key=lambda item: (-item[1], item[0]))

    if force_pass_chain_hints and top_k > 0:
        pass_chain_hints = collect_pass_chain_class_hints(
            selected,
            source_by_file,
            available_class_names,
            identifier_terms,
        )
        pass_chain_items = []
        for file_path, _score, breakdown in scored[top_k:]:
            if file_path in selected_files:
                continue
            source = source_by_file[file_path]
            matched = sorted(source_class_names(source) & set(pass_chain_hints))
            if not matched:
                continue
            reasons = []
            for name in matched[:4]:
                origins = ",".join(sorted(pass_chain_hints[name])[:3])
                reasons.append(f"pass_chain_hint:{origins}->{name}")
            pass_chain_boost = max(
                pass_chain_boost_for_name(name, identifier_terms) for name in matched
            )
            boosted_breakdown = replace(
                breakdown,
                pass_chain_boost=max(breakdown.pass_chain_boost, pass_chain_boost),
                reasons=breakdown.reasons + reasons,
            )
            pass_chain_items.append((file_path, boosted_breakdown.total, boosted_breakdown))

        pass_chain_items.sort(key=lambda item: (-item[1], item[0]))
        inserted = 0
        replacement_indices: list[int] = []
        for pass_chain_item in pass_chain_items:
            if inserted >= PASS_CHAIN_MAX_ITEMS:
                break
            replace_index = None
            for index in range(len(selected) - 1, -1, -1):
                reasons = selected[index][2].reasons
                if not any(
                    reason.startswith(("direct_", "reference_", "pass_chain_"))
                    for reason in reasons
                ):
                    replace_index = index
                    break
            if replace_index is None:
                break
            selected_files.remove(selected[replace_index][0])
            selected[replace_index] = pass_chain_item
            selected_files.add(pass_chain_item[0])
            replacement_indices.append(replace_index)
            inserted += 1
        if replacement_indices:
            inserted_items = sorted(
                (selected[index] for index in replacement_indices),
                key=lambda item: (-item[1], item[0]),
            )
            for index, item in zip(sorted(replacement_indices), inserted_items):
                selected[index] = item

    ranked_files = []
    for rank, (file_path, score, breakdown) in enumerate(selected, start=1):
        ranked_files.append(
            {
                "rank": rank,
                "file": file_path,
                "score": round(score, 6),
                "bm25_score": breakdown.bm25_score,
                "test_context_score": round(breakdown.test_context_score, 6),
                "direct_boost": round(breakdown.direct_boost, 6),
                "identifier_boost": round(breakdown.identifier_boost, 6),
                "reference_boost": round(breakdown.reference_boost, 6),
                "pass_chain_boost": round(breakdown.pass_chain_boost, 6),
                "type_system_boost": round(breakdown.type_system_boost, 6),
                "reasons": breakdown.reasons,
            }
        )

    method = "hybrid-bm25-test-context"
    if force_direct_hints:
        method += "+direct-hint-include"
    if force_reference_hints:
        method += "+reference-hint-include"
    if force_pass_chain_hints:
        method += "+pass-chain-hint-include"
    if force_type_system_hints:
        method += "+type-system-hints"

    return {
        "bug_id": record["bug_id"],
        "method": method,
        "query_sources": [
            "bug_report.id",
            "bug_report.text",
            "test_failure",
            "triggering_tests",
            "stack_trace",
            "triggering_test_source",
            "stack_project_frames",
            "test_class_to_source_class_hints",
            "pass_chain_reference_hints",
            "type_system_hints",
        ],
        "indexed_files": len(sources),
        "test_context_chars": len(test_context),
        "direct_class_hints": sorted(direct_hints),
        "force_direct_hints": force_direct_hints,
        "force_reference_hints": force_reference_hints,
        "force_pass_chain_hints": force_pass_chain_hints,
        "force_type_system_hints": force_type_system_hints,
        "ranked_files": ranked_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run hybrid file-level retrieval for fault localization."
    )
    parser.add_argument("--bugs", type=Path, required=True, help="Bug JSONL input")
    parser.add_argument("--out", type=Path, required=True, help="Prediction JSONL output")
    parser.add_argument("--top-k", type=int, default=50, help="Number of files to rank")
    parser.add_argument(
        "--force-direct-hints",
        action="store_true",
        help="Ensure files matching direct stack/test class hints stay in the top-k pool.",
    )
    parser.add_argument(
        "--force-reference-hints",
        action="store_true",
        help="Ensure files referenced by high-ranked candidate source classes stay in the top-k pool.",
    )
    parser.add_argument(
        "--force-pass-chain-hints",
        action="store_true",
        help="Ensure compiler pass implementations referenced by high-ranked pass config files stay in the top-k pool.",
    )
    parser.add_argument(
        "--force-type-system-hints",
        action="store_true",
        help="Boost Closure type-system candidates for TypeCheck/type-mismatch failures.",
    )
    args = parser.parse_args()

    predictions: list[dict[str, Any]] = []
    for record in read_jsonl(args.bugs):
        prediction = hybrid_rank(
            record,
            top_k=args.top_k,
            force_direct_hints=args.force_direct_hints,
            force_reference_hints=args.force_reference_hints,
            force_pass_chain_hints=args.force_pass_chain_hints,
            force_type_system_hints=args.force_type_system_hints,
        )
        predictions.append(prediction)
        print(
            f"[{record['bug_id']}] indexed {prediction['indexed_files']} files, "
            f"test_context_chars={prediction['test_context_chars']}, wrote top {args.top_k}",
            flush=True,
        )

    write_jsonl(args.out, predictions)
    print(f"Wrote {len(predictions)} prediction(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
