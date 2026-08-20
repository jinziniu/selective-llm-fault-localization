from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class BugReport:
    id: str
    url: str
    text: str = ""


@dataclass(frozen=True)
class GroundTruth:
    classes: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BugRecord:
    bug_id: str
    project: str
    bug_report: BugReport
    test_failure: str
    triggering_tests: list[str]
    stack_trace: str
    repo_path: str
    source_dir: str
    buggy_commit: str
    fixed_commit: str
    ground_truth: GroundTruth
    extra_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

