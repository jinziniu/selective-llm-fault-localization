from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
NOISY_STACK_PREFIXES = (
    "java.",
    "java.base/",
    "jdk.",
    "jdk.internal.",
    "org.junit.",
    "junit.framework.",
    "org.apache.tools.ant.",
)


def split_camel(identifier: str) -> list[str]:
    parts: list[str] = []
    for chunk in re.split(r"[^A-Za-z0-9]+", identifier):
        if not chunk:
            continue
        parts.extend(part for part in CAMEL_BOUNDARY_RE.split(chunk) if part)
    return parts


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(text):
        tokens.append(raw.lower())
        for part in split_camel(raw):
            lowered = part.lower()
            if lowered != raw.lower():
                tokens.append(lowered)
    return tokens


def extract_runtime_context(stack_trace: str) -> str:
    lines: list[str] = []
    for raw_line in stack_trace.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("---"):
            lines.append(line)
            continue
        if not line.startswith("at "):
            lines.append(line)
            continue
        frame = line.removeprefix("at ").strip()
        if frame.startswith(NOISY_STACK_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines)
