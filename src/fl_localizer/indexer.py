from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re


CLASS_RE = re.compile(r"\b(?:class|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)")
PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
METHOD_RE = re.compile(
    r"\b(?:public|protected|private|static|final|synchronized|abstract|native|\s)+"
    r"[A-Za-z_][A-Za-z0-9_<>\[\], ?]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
PY_FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
JS_FUNCTION_RE = re.compile(
    r"\b(?:function\s+|const\s+|let\s+|var\s+|async\s+function\s+)"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|\()"
)
PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][A-Za-z0-9_.]*);", re.MULTILINE)
SUPPORTED_SOURCE_EXTENSIONS = {".java", ".py", ".ts", ".tsx", ".js", ".jsx"}


@dataclass(frozen=True)
class SourceFile:
    file: str
    absolute_path: str
    package: str
    class_names: list[str]
    method_names: list[str]
    content: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def document_text(self) -> str:
        return "\n".join(
            [
                self.file,
                self.package,
                " ".join(self.class_names),
                " ".join(self.method_names),
                self.content,
            ]
        )


def index_java_sources(repo_path: Path, source_dir: str) -> list[SourceFile]:
    return index_source_files(repo_path, source_dir, extensions={".java"})


def index_source_files(
    repo_path: Path,
    source_dir: str,
    *,
    extensions: set[str] | None = None,
) -> list[SourceFile]:
    source_root = repo_path / source_dir
    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    allowed_extensions = extensions or SUPPORTED_SOURCE_EXTENSIONS
    files: list[SourceFile] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix not in allowed_extensions:
            continue
        if should_skip(path):
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(repo_path).as_posix()
        package_match = PACKAGE_RE.search(content)
        files.append(
            SourceFile(
                file=relative,
                absolute_path=str(path),
                package=package_match.group(1) if package_match else "",
                class_names=extract_class_names(path, content),
                method_names=extract_method_names(path, content),
                content=content,
            )
        )
    return files


def extract_class_names(path: Path, content: str) -> list[str]:
    if path.suffix == ".py":
        return sorted(set(PY_CLASS_RE.findall(content)))
    return sorted(set(CLASS_RE.findall(content)))


def extract_method_names(path: Path, content: str) -> list[str]:
    if path.suffix == ".py":
        return sorted(set(PY_FUNCTION_RE.findall(content)))
    names = set(METHOD_RE.findall(content))
    if path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
        names.update(JS_FUNCTION_RE.findall(content))
    return sorted(names)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    skip_dirs = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "format_files",
        "generated",
        "generated-sources",
        "migrations",
        "node_modules",
        "regression_tests",
        "target",
        "test",
        "tests",
        "venv",
    }
    if parts & skip_dirs:
        return True
    name = path.name
    return (
        name.startswith("test_")
        or name == "tests.py"
        or name == "conftest.py"
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
        or name.endswith(".d.ts")
        or name.endswith(".min.js")
    )
