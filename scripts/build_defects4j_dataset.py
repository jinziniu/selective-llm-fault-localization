#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from fl_localizer.schema import BugRecord, BugReport, GroundTruth


def parse_bug_ids(raw: str) -> list[int]:
    bug_ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            start, end = int(start_raw), int(end_raw)
            if end < start:
                raise ValueError(f"Invalid bug range: {part}")
            bug_ids.extend(range(start, end + 1))
        else:
            bug_ids.append(int(part))
    return bug_ids


def read_active_bug_ids(defects4j_home: Path, project: str) -> list[int]:
    active_bugs = defects4j_home / "framework" / "projects" / project / "active-bugs.csv"
    with active_bugs.open(newline="", encoding="utf-8") as handle:
        return [int(row["bug.id"]) for row in csv.DictReader(handle)]


def defects4j_env(defects4j_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    perl_lib = defects4j_home / "local" / "perl5" / "lib" / "perl5"
    existing_perl5lib = env.get("PERL5LIB", "")
    env["DEFECTS4J_HOME"] = str(defects4j_home)
    env["PERL5LIB"] = str(perl_lib) + (f":{existing_perl5lib}" if existing_perl5lib else "")
    env["PATH"] = ":".join(
        [
            str(defects4j_home / "framework" / "bin"),
            "/opt/homebrew/opt/openjdk@11/bin",
            "/opt/homebrew/bin",
            env.get("PATH", ""),
        ]
    )
    env["TZ"] = "America/Los_Angeles"
    return env


def run_command(
    args: list[str],
    cwd: Path,
    env: dict[str, str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {command}\n{result.stdout}"
        )
    return result


def read_active_bug_metadata(defects4j_home: Path, project: str, bug_id: int) -> dict[str, str]:
    active_bugs = defects4j_home / "framework" / "projects" / project / "active-bugs.csv"
    with active_bugs.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["bug.id"] == str(bug_id):
                return row
    raise ValueError(f"{project}-{bug_id} is not listed in {active_bugs}")


def clean_export_output(output: str) -> list[str]:
    lines: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Running ant "):
            continue
        lines.append(stripped)
    return lines


def export_property(
    defects4j_bin: str,
    prop: str,
    workspace: Path,
    env: dict[str, str],
) -> list[str]:
    result = run_command([defects4j_bin, "export", "-p", prop], cwd=workspace, env=env)
    return clean_export_output(result.stdout)


def class_to_file(source_dir: str, class_name: str) -> str:
    outer_class = class_name.split("$", 1)[0]
    return str(Path(source_dir) / Path(*outer_class.split("."))).replace("\\", "/") + ".java"


def checkout_bug(
    defects4j_bin: str,
    project: str,
    bug_id: int,
    workspace_root: Path,
    env: dict[str, str],
    *,
    clean: bool,
) -> Path:
    workspace = workspace_root / f"{project}-{bug_id}b"
    if clean and workspace.exists():
        shutil.rmtree(workspace)
    if (workspace / ".defects4j.config").exists():
        return workspace
    if workspace.exists() and any(workspace.iterdir()):
        raise RuntimeError(
            f"Workspace exists but is not a Defects4J checkout: {workspace}. "
            "Use --clean to recreate it."
        )
    workspace.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [defects4j_bin, "checkout", "-p", project, "-v", f"{bug_id}b", "-w", str(workspace)],
        cwd=PROJECT_ROOT,
        env=env,
    )
    return workspace


def build_record(
    defects4j_home: Path,
    project: str,
    bug_id: int,
    workspace_root: Path,
    *,
    clean: bool,
    run_compile: bool,
    run_tests: bool,
) -> BugRecord:
    env = defects4j_env(defects4j_home)
    defects4j_bin = str(defects4j_home / "framework" / "bin" / "defects4j")
    metadata = read_active_bug_metadata(defects4j_home, project, bug_id)
    workspace = checkout_bug(defects4j_bin, project, bug_id, workspace_root, env, clean=clean)

    if run_compile:
        print(f"[{project}-{bug_id}] compile", flush=True)
        run_command([defects4j_bin, "compile"], cwd=workspace, env=env)
    if run_tests:
        print(f"[{project}-{bug_id}] test", flush=True)
        run_command([defects4j_bin, "test"], cwd=workspace, env=env)

    source_dirs = export_property(defects4j_bin, "dir.src.classes", workspace, env)
    if not source_dirs:
        raise RuntimeError(f"No source directory exported for {project}-{bug_id}")
    source_dir = source_dirs[0]

    modified_classes = export_property(defects4j_bin, "classes.modified", workspace, env)
    triggering_tests = export_property(defects4j_bin, "tests.trigger", workspace, env)
    ground_truth_files = [class_to_file(source_dir, class_name) for class_name in modified_classes]

    failing_tests_path = workspace / "failing_tests"
    stack_trace = failing_tests_path.read_text(encoding="utf-8") if failing_tests_path.exists() else ""

    report_id = metadata.get("report.id", "")
    report_url = metadata.get("report.url", "")
    test_failure = triggering_tests[0] if triggering_tests else ""

    return BugRecord(
        bug_id=f"{project}-{bug_id}",
        project=project,
        bug_report=BugReport(id=report_id, url=report_url, text=""),
        test_failure=test_failure,
        triggering_tests=triggering_tests,
        stack_trace=stack_trace,
        repo_path=str(workspace),
        source_dir=source_dir,
        buggy_commit=metadata.get("revision.id.buggy", ""),
        fixed_commit=metadata.get("revision.id.fixed", ""),
        ground_truth=GroundTruth(classes=modified_classes, files=ground_truth_files),
        extra_context={
            "source": "Defects4J",
            "version": "buggy",
            "available_artifacts": [
                "active-bugs.csv",
                "classes.modified",
                "tests.trigger",
                "failing_tests",
            ],
            "leakage_note": "Fixing commit metadata and ground truth are for evaluation only.",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build JSONL bug records from Defects4J checkouts."
    )
    parser.add_argument("--project", default="Lang", help="Defects4J project id, e.g. Lang")
    parser.add_argument("--bugs", default="1", help="Bug ids, e.g. 1 or 1,3,4 or 1-5")
    parser.add_argument(
        "--first-active",
        type=int,
        help="Use the first N active bug ids from active-bugs.csv. Overrides --bugs.",
    )
    parser.add_argument(
        "--defects4j-home",
        type=Path,
        default=PROJECT_ROOT / "defects4j",
        help="Path to the initialized Defects4J checkout",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=PROJECT_ROOT / "workspaces" / "defects4j",
        help="Directory where buggy versions are checked out",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "defects4j" / "bugs.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--append", action="store_true", help="Append to output instead of overwrite")
    parser.add_argument("--clean", action="store_true", help="Recreate existing workspaces")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip defects4j test. This also skips generating a fresh failing_tests file.",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip defects4j compile and read metadata from existing checkouts.",
    )
    parser.add_argument(
        "--skip-failures",
        action="store_true",
        help="Continue after a bug fails to checkout/compile/test and print skipped ids.",
    )
    args = parser.parse_args()

    defects4j_home = args.defects4j_home.resolve()
    if args.first_active is not None:
        if args.first_active <= 0:
            raise ValueError("--first-active must be positive")
        bug_ids = read_active_bug_ids(defects4j_home, args.project)[: args.first_active]
    else:
        bug_ids = parse_bug_ids(args.bugs)
    mode = "a" if args.append else "w"
    args.out.parent.mkdir(parents=True, exist_ok=True)

    skipped: list[tuple[int, str]] = []
    with args.out.open(mode, encoding="utf-8") as handle:
        for bug_id in bug_ids:
            print(f"[{args.project}-{bug_id}] build record", flush=True)
            try:
                record = build_record(
                    args.defects4j_home.resolve(),
                    args.project,
                    bug_id,
                    args.workspace_root.resolve(),
                    clean=args.clean,
                    run_compile=not args.skip_compile,
                    run_tests=not args.skip_tests,
                )
            except Exception as exc:
                if not args.skip_failures:
                    raise
                skipped.append((bug_id, str(exc).splitlines()[0]))
                print(f"[{args.project}-{bug_id}] skipped: {exc}", flush=True)
                continue
            handle.write(record.to_json_line() + "\n")
            handle.flush()

    written = len(bug_ids) - len(skipped)
    print(f"Wrote {written} record(s) to {args.out}", flush=True)
    if skipped:
        print("Skipped bug ids:", flush=True)
        for bug_id, reason in skipped:
            print(f"- {args.project}-{bug_id}: {reason}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
