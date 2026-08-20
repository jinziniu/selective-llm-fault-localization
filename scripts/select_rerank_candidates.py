#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.io_utils import read_jsonl
from fl_localizer.text import tokenize


CLOSURE_GENERIC_TOP_FILES = {
    "AbstractCommandLineRunner.java",
    "AbstractCompiler.java",
    "CommandLineRunner.java",
    "Compiler.java",
    "CompilerOptions.java",
    "DefaultPassConfig.java",
    "Normalize.java",
}
CLOSURE_CODE_OUTPUT_FILES = {
    "CodeConsumer.java",
    "CodeGenerator.java",
    "CodePrinter.java",
}
CLOSURE_VALIDATOR_TOP_FILES = {
    "AstValidator.java",
    "SanityCheck.java",
    "Validator.java",
}
CLOSURE_TRANSFORM_DIRECT_FILES = {
    "FunctionRewriter.java",
}

TYPE_CYCLE_TERMS = {
    "cycle",
    "extends",
    "implements",
    "inheritance",
    "interface",
    "recursive",
    "stackoverflowerror",
    "subtype",
}
TYPE_CYCLE_ANCHORS = {"cycle", "recursive", "stackoverflowerror"}
TYPE_CYCLE_CONTEXT = {"extends", "implements", "inheritance", "interface", "subtype", "type"}

STATE_RESET_TERMS = {
    "clear",
    "clone",
    "copy",
    "distribution",
    "gaussian",
    "generator",
    "nextgaussian",
    "random",
    "reseed",
    "reset",
    "sample",
    "seed",
    "state",
}
STATE_RESET_ANCHORS = {"clone", "copy", "reseed", "reset", "state"}
STATE_RESET_CONTEXT = {
    "distribution",
    "gaussian",
    "generator",
    "nextgaussian",
    "random",
    "sample",
    "seed",
}
STACK_FRAME_RE = re.compile(r"^\s*at\s+((?:[a-z_][A-Za-z0-9_]*\.)+[A-Za-z0-9_$]+)\.([A-Za-z0-9_$<>]+)\(")

MOCKITO_INVOCATION_VARARGS_TERMS = {
    "argument",
    "arguments",
    "capture",
    "captor",
    "invocation",
    "invocations",
    "matcher",
    "matchers",
    "vararg",
    "varargs",
    "verification",
    "verify",
}
MOCKITO_GENERIC_TERMS = {
    "captor",
    "deep",
    "deepstub",
    "deepstubs",
    "generic",
    "generics",
    "nested",
    "raw",
}
MOCKITO_INJECTION_TERMS = {
    "access",
    "candidate",
    "field",
    "filter",
    "inject",
    "injection",
    "injectmocks",
    "property",
    "setter",
    "setters",
}
MOCKITO_CONSTRUCTOR_REAL_METHOD_TERMS = {
    "abstract",
    "call",
    "calls",
    "constructor",
    "constructors",
    "method",
    "real",
    "spy",
}
MOCKITO_SERIALIZATION_TERMS = {
    "extrainterfaces",
    "serializable",
    "serialization",
    "serialize",
}
MOCKITO_PRIMITIVE_DEFAULT_TERMS = {
    "default",
    "defaults",
    "primitive",
    "primitives",
    "return",
    "returns",
    "value",
    "values",
}
MOCKITO_INJECTION_EXACT_TYPE_TERMS = {
    "ancestor",
    "ancestors",
    "exact",
    "inject",
    "injection",
    "injectmocks",
    "matching",
    "type",
    "types",
}
MOCKITO_REAL_METHOD_INTERFACE_TERMS = {
    "abstract",
    "call",
    "calling",
    "calls",
    "interface",
    "interfaces",
    "method",
    "methods",
    "real",
}


def has_direct_hint(item: dict[str, Any]) -> bool:
    return any(str(reason).startswith("direct_") for reason in item.get("reasons", []))


def first_direct_hint_rank(ranked_files: list[Any]) -> int | None:
    for index, item in enumerate(ranked_files, start=1):
        if not isinstance(item, dict) or not has_direct_hint(item):
            continue
        try:
            return int(item.get("rank") or index)
        except (TypeError, ValueError):
            return index
    return None


def candidate_has_reason_prefix(item: dict[str, Any], prefix: str) -> bool:
    return any(str(reason).startswith(prefix) for reason in item.get("reasons", []))


def file_basename(path: Any) -> str:
    return str(path or "").rsplit("/", 1)[-1]


def prediction_pattern_signals(
    record: dict[str, Any],
    *,
    pass_chain_min_boost: float,
) -> dict[str, Any]:
    pass_chain_candidates: list[dict[str, Any]] = []
    high_confidence_pass_chain_candidates: list[dict[str, Any]] = []
    type_system_candidates: list[dict[str, Any]] = []
    high_confidence_type_system_candidates: list[dict[str, Any]] = []
    for item in record.get("ranked_files", []):
        if not isinstance(item, dict):
            continue
        pass_chain_boost = float(item.get("pass_chain_boost", 0.0) or 0.0)
        if pass_chain_boost > 0 or candidate_has_reason_prefix(item, "pass_chain_"):
            pass_chain_candidates.append(
                {
                    "rank": item.get("rank"),
                    "file": item.get("file"),
                    "pass_chain_boost": pass_chain_boost,
                    "reasons": [
                        reason
                        for reason in item.get("reasons", [])
                        if str(reason).startswith("pass_chain_")
                    ],
                }
            )
            if pass_chain_boost >= pass_chain_min_boost:
                high_confidence_pass_chain_candidates.append(pass_chain_candidates[-1])

        type_system_boost = float(item.get("type_system_boost", 0.0) or 0.0)
        if type_system_boost > 0 or candidate_has_reason_prefix(item, "type_system_"):
            type_system_candidates.append(
                {
                    "rank": item.get("rank"),
                    "file": item.get("file"),
                    "type_system_boost": type_system_boost,
                    "reasons": [
                        reason
                        for reason in item.get("reasons", [])
                        if str(reason).startswith("type_system_")
                    ],
                }
            )
            try:
                rank = int(item.get("rank") or 0)
            except (TypeError, ValueError):
                rank = 0
            if type_system_boost >= 100.0 and 0 < rank <= 25:
                high_confidence_type_system_candidates.append(type_system_candidates[-1])

    return {
        "pass_chain_candidates": pass_chain_candidates,
        "pass_chain_high_confidence_candidates": high_confidence_pass_chain_candidates,
        "type_system_candidates": type_system_candidates,
        "type_system_high_confidence_candidates": high_confidence_type_system_candidates,
    }


def bug_record_text(record: dict[str, Any] | None) -> str:
    if not record:
        return ""
    bug_report = record.get("bug_report", {})
    if not isinstance(bug_report, dict):
        bug_report = {}
    parts = [
        str(record.get("bug_id", "")),
        str(record.get("project", "")),
        str(bug_report.get("id", "")),
        str(bug_report.get("text", "")),
        str(record.get("test_failure", "")),
        " ".join(str(item) for item in record.get("triggering_tests", [])),
        str(record.get("stack_trace", "")),
    ]
    return "\n".join(part for part in parts if part)


def stack_method_terms(record: dict[str, Any] | None) -> set[str]:
    if not record:
        return set()
    terms: set[str] = set()
    for line in str(record.get("stack_trace", "")).splitlines():
        match = STACK_FRAME_RE.match(line)
        if not match:
            continue
        class_fqn, method = match.groups()
        terms.update(tokenize(class_fqn.rsplit(".", 1)[-1]))
        terms.update(tokenize(method))
    return terms


def bug_pattern_signals(record: dict[str, Any] | None) -> dict[str, Any]:
    text = bug_record_text(record)
    terms = set(tokenize(text)) | stack_method_terms(record)
    type_terms = sorted(terms & TYPE_CYCLE_TERMS)
    state_terms = sorted(terms & STATE_RESET_TERMS)
    is_mockito = bool(record and str(record.get("project", "")).lower() == "mockito")
    mockito_invocation_varargs_terms = sorted(terms & MOCKITO_INVOCATION_VARARGS_TERMS)
    mockito_generic_terms = sorted(terms & MOCKITO_GENERIC_TERMS)
    mockito_injection_terms = sorted(terms & MOCKITO_INJECTION_TERMS)
    mockito_constructor_real_method_terms = sorted(
        terms & MOCKITO_CONSTRUCTOR_REAL_METHOD_TERMS
    )
    mockito_serialization_terms = sorted(terms & MOCKITO_SERIALIZATION_TERMS)
    mockito_primitive_default_terms = sorted(terms & MOCKITO_PRIMITIVE_DEFAULT_TERMS)
    mockito_injection_exact_type_terms = sorted(
        terms & MOCKITO_INJECTION_EXACT_TYPE_TERMS
    )
    mockito_real_method_interface_terms = sorted(
        terms & MOCKITO_REAL_METHOD_INTERFACE_TERMS
    )

    has_type_cycle = bool(
        (terms & TYPE_CYCLE_ANCHORS and terms & TYPE_CYCLE_CONTEXT)
        or "stackoverflowerror" in terms
    )
    has_state_reset = bool(terms & STATE_RESET_ANCHORS and terms & STATE_RESET_CONTEXT)
    has_mockito_invocation_varargs = bool(
        is_mockito
        and len(terms & MOCKITO_INVOCATION_VARARGS_TERMS) >= 3
        and terms & {"capture", "vararg", "varargs", "invocation"}
    )
    has_mockito_generic = bool(
        is_mockito
        and terms & {"generic", "generics"}
        and terms & {"captor", "deep", "deepstub", "deepstubs", "nested", "raw"}
    )
    has_mockito_injection = bool(
        is_mockito
        and terms & {"inject", "injection", "injectmocks"}
        and terms & {"field", "filter", "property", "setter", "setters", "candidate"}
    )
    has_mockito_constructor_real_method = bool(
        is_mockito
        and "constructor" in terms
        and terms & {"abstract", "calls", "method", "real", "spy"}
    )
    has_mockito_serialization = bool(
        is_mockito and terms & {"serializable", "serialization", "serialize", "extrainterfaces"}
    )
    has_mockito_primitive_default_values = bool(
        is_mockito
        and terms & {"primitive", "primitives"}
        and terms & {"default", "defaults", "return", "returns", "value", "values"}
    )
    has_mockito_injection_exact_type_ancestor = bool(
        is_mockito
        and terms & {"inject", "injection", "injectmocks"}
        and "type" in terms
        and terms & {"ancestor", "ancestors", "exact", "matching"}
    )
    has_mockito_real_method_interface = bool(
        is_mockito
        and terms & {"interface", "interfaces"}
        and "real" in terms
        and terms & {"call", "calling", "calls", "method", "methods"}
    )

    return {
        "type_cycle": has_type_cycle,
        "type_cycle_terms": type_terms,
        "state_reset": has_state_reset,
        "state_reset_terms": state_terms,
        "mockito_invocation_varargs": has_mockito_invocation_varargs,
        "mockito_invocation_varargs_terms": mockito_invocation_varargs_terms,
        "mockito_generic": has_mockito_generic,
        "mockito_generic_terms": mockito_generic_terms,
        "mockito_injection": has_mockito_injection,
        "mockito_injection_terms": mockito_injection_terms,
        "mockito_constructor_real_method": has_mockito_constructor_real_method,
        "mockito_constructor_real_method_terms": mockito_constructor_real_method_terms,
        "mockito_serialization": has_mockito_serialization,
        "mockito_serialization_terms": mockito_serialization_terms,
        "mockito_primitive_default_values": has_mockito_primitive_default_values,
        "mockito_primitive_default_values_terms": mockito_primitive_default_terms,
        "mockito_injection_exact_type_ancestor": has_mockito_injection_exact_type_ancestor,
        "mockito_injection_exact_type_ancestor_terms": mockito_injection_exact_type_terms,
        "mockito_real_method_interface": has_mockito_real_method_interface,
        "mockito_real_method_interface_terms": mockito_real_method_interface_terms,
    }


def is_mockito_record(record: dict[str, Any] | None) -> bool:
    return bool(record and str(record.get("project", "")).lower() == "mockito")


def is_closure_record(record: dict[str, Any] | None) -> bool:
    return bool(record and str(record.get("project", "")).lower() == "closure")


def direct_hint_candidates(ranked_files: list[Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(ranked_files, start=1):
        if not isinstance(item, dict) or not has_direct_hint(item):
            continue
        try:
            rank = int(item.get("rank") or index)
        except (TypeError, ValueError):
            rank = index
        candidates.append(
            {
                "rank": rank,
                "file": item.get("file"),
                "reasons": [
                    reason
                    for reason in item.get("reasons", [])
                    if str(reason).startswith("direct_")
                ],
            }
        )
    return candidates


def closure_v2_pattern_reasons(
    *,
    record: dict[str, Any],
    bug_record: dict[str, Any] | None,
    ranked_files: list[Any],
    top1_file: str | None,
    score_ratio: float | None,
) -> list[str]:
    if not is_closure_record(bug_record):
        return []

    reasons: list[str] = []
    terms = set(tokenize(bug_record_text(bug_record))) | stack_method_terms(bug_record)
    top20_basenames = {
        file_basename(item.get("file"))
        for item in ranked_files[:20]
        if isinstance(item, dict)
    }
    direct_candidates = direct_hint_candidates(ranked_files)
    top1_basename = file_basename(top1_file)

    if (
        ("codeprinter" in terms or ("code" in terms and "printer" in terms))
        and top20_basenames & CLOSURE_CODE_OUTPUT_FILES
        and (score_ratio is None or score_ratio >= 1.15)
    ):
        reasons.append("pattern:closure_code_output")

    has_deep_specific_direct_hint = any(
        6 <= int(candidate["rank"]) <= 20
        and file_basename(candidate.get("file")) not in CLOSURE_GENERIC_TOP_FILES
        for candidate in direct_candidates
    )
    if (
        has_deep_specific_direct_hint
        and top1_basename in CLOSURE_GENERIC_TOP_FILES
        and (score_ratio is None or score_ratio <= 1.08)
    ):
        reasons.append("pattern:closure_deep_specific_direct_hint")

    return reasons


def closure_v3_pattern_reasons(
    *,
    bug_record: dict[str, Any] | None,
    ranked_files: list[Any],
    top1_file: str | None,
    score_ratio: float | None,
) -> list[str]:
    if not is_closure_record(bug_record):
        return []

    reasons: list[str] = []
    terms = set(tokenize(bug_record_text(bug_record))) | stack_method_terms(bug_record)
    direct_candidates = direct_hint_candidates(ranked_files)
    top1_basename = file_basename(top1_file)

    code_generator_candidate = next(
        (
            candidate
            for candidate in ranked_files
            if isinstance(candidate, dict)
            and file_basename(candidate.get("file")) == "CodeGenerator.java"
        ),
        None,
    )
    if code_generator_candidate:
        try:
            code_generator_rank = int(code_generator_candidate.get("rank") or 0)
        except (TypeError, ValueError):
            code_generator_rank = 0
        if (
            top1_basename == "CodePrinter.java"
            and 0 < code_generator_rank <= 20
            and terms & {"numeric", "key", "keys"}
            and (score_ratio is None or score_ratio <= 1.05)
        ):
            reasons.append("pattern:closure_code_generator_output")

    has_transform_direct_hint = any(
        6 <= int(candidate["rank"]) <= 35
        and file_basename(candidate.get("file")) in CLOSURE_TRANSFORM_DIRECT_FILES
        for candidate in direct_candidates
    )
    if (
        top1_basename in CLOSURE_VALIDATOR_TOP_FILES
        and has_transform_direct_hint
        and "illegalstateexception" in terms
        and "expected" in terms
        and "function" in terms
        and "call" in terms
    ):
        reasons.append("pattern:closure_validator_transform_failure")

    return reasons


def filter_closure_cost_control_reasons(
    reasons: list[str],
    *,
    top1_has_direct_hint: bool,
    score_ratio: float | None,
    direct_hint_count: int,
    direct_hint_rank: int | None,
) -> list[str]:
    reason_set = set(reasons)
    kept: list[str] = []

    def keep(reason: str) -> None:
        if reason in reason_set and reason not in kept:
            kept.append(reason)

    if not top1_has_direct_hint:
        for reason in reasons:
            if reason.startswith("low_score_ratio<="):
                keep(reason)

    if (
        "top1_without_direct_hint" in reason_set
        and not top1_has_direct_hint
        and (direct_hint_rank is None or direct_hint_rank >= 3)
    ):
        keep("top1_without_direct_hint")

    if direct_hint_count >= 7:
        for reason in reasons:
            if reason.startswith("many_direct_hints>="):
                keep(reason)

    if "pattern:pass_chain" in reason_set and (
        not top1_has_direct_hint
        or direct_hint_count >= 7
        or (score_ratio is not None and score_ratio >= 1.40)
    ):
        keep("pattern:pass_chain")

    if "pattern:type_system" in reason_set and (
        not top1_has_direct_hint
        or score_ratio is None
        or score_ratio <= 1.10
    ):
        keep("pattern:type_system")

    if "pattern:type_cycle" in reason_set and not top1_has_direct_hint:
        keep("pattern:type_cycle")

    keep("pattern:closure_code_output")
    keep("pattern:closure_deep_specific_direct_hint")
    keep("pattern:closure_code_generator_output")
    keep("pattern:closure_validator_transform_failure")

    return kept


def filter_mockito_tight_pattern_reasons(
    pattern_reasons: list[str],
    *,
    top1_has_direct_hint: bool,
    score_ratio: float | None,
    direct_hint_count: int,
    cost_control_v2: bool,
) -> list[str]:
    reason_set = set(pattern_reasons)
    kept: list[str] = []

    def keep(reason: str) -> None:
        if reason in reason_set and reason not in kept:
            kept.append(reason)

    for reason in pattern_reasons:
        if not reason.startswith("pattern:mockito_") and reason != "pattern:type_cycle":
            keep(reason)

    if not top1_has_direct_hint:
        for reason in pattern_reasons:
            if reason.startswith("pattern:mockito_"):
                keep(reason)

    if direct_hint_count >= 7:
        keep("pattern:mockito_generic")
        if score_ratio is not None and score_ratio <= 1.10:
            keep("pattern:mockito_constructor_real_method")
        if cost_control_v2:
            keep("pattern:mockito_invocation_varargs")
            keep("pattern:mockito_real_method_interface")

    keep("pattern:mockito_injection")

    if not top1_has_direct_hint:
        keep("pattern:mockito_serialization")

    if (
        "pattern:type_cycle" in reason_set
        and (not top1_has_direct_hint or score_ratio is None or score_ratio <= 1.02)
    ):
        keep("pattern:type_cycle")

    return kept


def select_record(
    record: dict[str, Any],
    *,
    bug_record: dict[str, Any] | None,
    score_ratio_threshold: float,
    include_top1_without_direct: bool,
    top1_without_direct_min_direct_rank: int | None,
    top1_without_direct_max_direct_rank: int | None,
    direct_hint_count_threshold: int,
    include_patterns: bool,
    pass_chain_min_boost: float,
    mockito_tight_patterns: bool,
    mockito_diagnostic_patterns: bool,
    mockito_cost_control_v2: bool,
    closure_cost_control_v1: bool,
    closure_cost_control_v2: bool,
    closure_cost_control_v3: bool,
) -> dict[str, Any] | None:
    direct_class_hints = record.get("direct_class_hints", [])
    if not isinstance(direct_class_hints, list):
        direct_class_hints = []

    pred_signals = prediction_pattern_signals(
        record,
        pass_chain_min_boost=pass_chain_min_boost,
    )
    bug_signals = bug_pattern_signals(bug_record) if include_patterns else {}
    pattern_reasons: list[str] = []
    if include_patterns:
        if pred_signals["pass_chain_high_confidence_candidates"]:
            pattern_reasons.append("pattern:pass_chain")
        if pred_signals["type_system_high_confidence_candidates"]:
            pattern_reasons.append("pattern:type_system")
        if bug_signals.get("type_cycle"):
            pattern_reasons.append("pattern:type_cycle")
        if bug_signals.get("state_reset"):
            pattern_reasons.append("pattern:state_reset")
        if bug_signals.get("mockito_invocation_varargs"):
            pattern_reasons.append("pattern:mockito_invocation_varargs")
        if bug_signals.get("mockito_generic"):
            pattern_reasons.append("pattern:mockito_generic")
        if bug_signals.get("mockito_injection"):
            pattern_reasons.append("pattern:mockito_injection")
        if bug_signals.get("mockito_constructor_real_method"):
            pattern_reasons.append("pattern:mockito_constructor_real_method")
        if bug_signals.get("mockito_serialization"):
            pattern_reasons.append("pattern:mockito_serialization")
        if mockito_diagnostic_patterns and bug_signals.get(
            "mockito_primitive_default_values"
        ):
            pattern_reasons.append("diagnostic:mockito_primitive_default_values")
        if mockito_diagnostic_patterns and bug_signals.get(
            "mockito_injection_exact_type_ancestor"
        ):
            pattern_reasons.append("diagnostic:mockito_injection_exact_type_ancestor")
        if mockito_cost_control_v2 and bug_signals.get("mockito_real_method_interface"):
            pattern_reasons.append("pattern:mockito_real_method_interface")

    ranked_files = record.get("ranked_files", [])
    if not isinstance(ranked_files, list) or not ranked_files:
        return {
            "bug_id": record["bug_id"],
            "reasons": ["empty_ranking"] + pattern_reasons,
            "top1_file": None,
            "score_ratio": None,
            "top1_has_direct_hint": False,
            "first_direct_hint_rank": None,
            "direct_class_hints": direct_class_hints,
            "pattern_signals": {
                **pred_signals,
                **bug_signals,
            },
        }

    top1 = ranked_files[0]
    top2 = ranked_files[1] if len(ranked_files) > 1 else None
    top1_score = float(top1.get("score", 0.0) or 0.0)
    top2_score = float(top2.get("score", 0.0) or 0.0) if top2 else 0.0
    score_ratio = top1_score / top2_score if top2_score > 0 else None
    top1_has_direct_hint = has_direct_hint(top1)
    direct_hint_rank = first_direct_hint_rank(ranked_files)

    reasons: list[str] = []
    if score_ratio is not None and score_ratio <= score_ratio_threshold:
        reasons.append(f"low_score_ratio<={score_ratio_threshold:g}")
    top1_without_direct_matches = include_top1_without_direct and not top1_has_direct_hint
    if top1_without_direct_matches and top1_without_direct_min_direct_rank is not None:
        top1_without_direct_matches = (
            direct_hint_rank is not None
            and direct_hint_rank >= top1_without_direct_min_direct_rank
        )
    if top1_without_direct_matches and top1_without_direct_max_direct_rank is not None:
        top1_without_direct_matches = (
            direct_hint_rank is not None
            and direct_hint_rank <= top1_without_direct_max_direct_rank
        )
    if top1_without_direct_matches:
        reasons.append("top1_without_direct_hint")
    if direct_hint_count_threshold > 0 and len(direct_class_hints) >= direct_hint_count_threshold:
        reasons.append(f"many_direct_hints>={direct_hint_count_threshold}")
    if include_patterns and (closure_cost_control_v2 or closure_cost_control_v3):
        pattern_reasons.extend(
            closure_v2_pattern_reasons(
                record=record,
                bug_record=bug_record,
                ranked_files=ranked_files,
                top1_file=top1.get("file"),
                score_ratio=score_ratio,
            )
        )
    if include_patterns and closure_cost_control_v3:
        pattern_reasons.extend(
            closure_v3_pattern_reasons(
                bug_record=bug_record,
                ranked_files=ranked_files,
                top1_file=top1.get("file"),
                score_ratio=score_ratio,
            )
        )
    if mockito_tight_patterns and is_mockito_record(bug_record):
        pattern_reasons = filter_mockito_tight_pattern_reasons(
            pattern_reasons,
            top1_has_direct_hint=top1_has_direct_hint,
            score_ratio=score_ratio,
            direct_hint_count=len(direct_class_hints),
            cost_control_v2=mockito_cost_control_v2,
        )
    reasons.extend(pattern_reasons)
    if (
        closure_cost_control_v1
        or closure_cost_control_v2
        or closure_cost_control_v3
    ) and is_closure_record(bug_record):
        reasons = filter_closure_cost_control_reasons(
            reasons,
            top1_has_direct_hint=top1_has_direct_hint,
            score_ratio=score_ratio,
            direct_hint_count=len(direct_class_hints),
            direct_hint_rank=direct_hint_rank,
        )

    if not reasons:
        return None

    return {
        "bug_id": record["bug_id"],
        "reasons": reasons,
        "top1_file": top1.get("file"),
        "top2_file": top2.get("file") if top2 else None,
        "top1_score": top1_score,
        "top2_score": top2_score,
        "score_ratio": score_ratio,
        "top1_has_direct_hint": top1_has_direct_hint,
        "first_direct_hint_rank": direct_hint_rank,
        "direct_class_hints": direct_class_hints,
        "pattern_signals": {
            **pred_signals,
            **bug_signals,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select low-confidence retrieval results for LLM reranking."
    )
    parser.add_argument("--pred", type=Path, required=True, help="Hybrid prediction JSONL")
    parser.add_argument(
        "--bugs",
        type=Path,
        help="Bug JSONL input. Enables bug-text pattern selection when provided.",
    )
    parser.add_argument("--out", type=Path, help="Write JSON selection report")
    parser.add_argument(
        "--score-ratio-threshold",
        type=float,
        default=1.02,
        help="Select when top1_score / top2_score is at or below this value",
    )
    parser.add_argument(
        "--no-top1-without-direct",
        action="store_true",
        help="Do not select records whose top-1 candidate lacks a direct hint",
    )
    parser.add_argument(
        "--top1-without-direct-min-direct-rank",
        type=int,
        help="Only apply top1_without_direct when the first direct-hint candidate rank is at least this value.",
    )
    parser.add_argument(
        "--top1-without-direct-max-direct-rank",
        type=int,
        help="Only apply top1_without_direct when the first direct-hint candidate rank is at most this value.",
    )
    parser.add_argument(
        "--direct-hint-count-threshold",
        type=int,
        default=7,
        help="Select when the record has at least this many direct class hints. Use 0 to disable.",
    )
    parser.add_argument(
        "--no-patterns",
        action="store_true",
        help="Disable pass-chain/type-cycle/state-reset pattern selection.",
    )
    parser.add_argument(
        "--pass-chain-min-boost",
        type=float,
        default=1000.0,
        help="Minimum pass_chain_boost required for pattern:pass_chain selection.",
    )
    parser.add_argument(
        "--mockito-tight-patterns",
        action="store_true",
        help="Use narrower Mockito pattern rules to reduce rerank calls while preserving known hard-case families.",
    )
    parser.add_argument(
        "--mockito-diagnostic-patterns",
        action="store_true",
        help="Enable diagnostic-only Mockito patterns for fresh-validation analysis. These are not default production selector rules.",
    )
    parser.add_argument(
        "--mockito-cost-control-v2",
        action="store_true",
        help="Enable experimental Mockito cost-control pattern selection for fresh-validation analysis.",
    )
    parser.add_argument(
        "--closure-cost-control-v1",
        action="store_true",
        help="Enable experimental Closure cost-control pattern selection for fresh-validation analysis.",
    )
    parser.add_argument(
        "--closure-cost-control-v2",
        action="store_true",
        help="Enable experimental Closure cost-control v2 pattern selection for fresh-validation analysis.",
    )
    parser.add_argument(
        "--closure-cost-control-v3",
        action="store_true",
        help="Enable experimental Closure cost-control v3 pattern selection for fresh-validation analysis.",
    )
    parser.add_argument(
        "--ids-only",
        action="store_true",
        help="Print only a comma-separated bug id list",
    )
    args = parser.parse_args()

    records = read_jsonl(args.pred)
    bug_by_id = (
        {str(record["bug_id"]): record for record in read_jsonl(args.bugs)}
        if args.bugs
        else {}
    )
    include_patterns = not args.no_patterns
    selected = [
        item
        for record in records
        if (
            item := select_record(
                record,
                bug_record=bug_by_id.get(str(record["bug_id"])),
                score_ratio_threshold=args.score_ratio_threshold,
                include_top1_without_direct=not args.no_top1_without_direct,
                top1_without_direct_min_direct_rank=args.top1_without_direct_min_direct_rank,
                top1_without_direct_max_direct_rank=args.top1_without_direct_max_direct_rank,
                direct_hint_count_threshold=args.direct_hint_count_threshold,
                include_patterns=include_patterns,
                pass_chain_min_boost=args.pass_chain_min_boost,
                mockito_tight_patterns=args.mockito_tight_patterns,
                mockito_diagnostic_patterns=args.mockito_diagnostic_patterns,
                mockito_cost_control_v2=args.mockito_cost_control_v2,
                closure_cost_control_v1=args.closure_cost_control_v1,
                closure_cost_control_v2=args.closure_cost_control_v2,
                closure_cost_control_v3=args.closure_cost_control_v3,
            )
        )
    ]
    reason_counts: dict[str, int] = {}
    for item in selected:
        for reason in item["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    payload = {
        "input": str(args.pred),
        "criteria": {
            "score_ratio_threshold": args.score_ratio_threshold,
            "include_top1_without_direct": not args.no_top1_without_direct,
            "top1_without_direct_min_direct_rank": args.top1_without_direct_min_direct_rank,
            "top1_without_direct_max_direct_rank": args.top1_without_direct_max_direct_rank,
            "direct_hint_count_threshold": args.direct_hint_count_threshold,
            "include_patterns": include_patterns,
            "bug_input": str(args.bugs) if args.bugs else None,
            "pass_chain_min_boost": args.pass_chain_min_boost,
            "mockito_tight_patterns": args.mockito_tight_patterns,
            "mockito_diagnostic_patterns": args.mockito_diagnostic_patterns,
            "mockito_cost_control_v2": args.mockito_cost_control_v2,
            "closure_cost_control_v1": args.closure_cost_control_v1,
            "closure_cost_control_v2": args.closure_cost_control_v2,
            "closure_cost_control_v3": args.closure_cost_control_v3,
        },
        "summary": {
            "records": len(records),
            "selected": len(selected),
            "selected_fraction": len(selected) / len(records) if records else 0.0,
            "reason_counts": reason_counts,
        },
        "selected_bug_ids": [item["bug_id"] for item in selected],
        "selected": selected,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if args.ids_only:
        print(",".join(payload["selected_bug_ids"]))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
