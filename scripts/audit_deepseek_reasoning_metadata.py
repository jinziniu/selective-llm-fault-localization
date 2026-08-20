from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "deepseek_reasoning_metadata_audit_2026_07_20"
DOC_PATH = ROOT / "docs" / "deepseek_reasoning_metadata_audit_2026-07-20.md"


def walk_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def reasoning_tokens(record: dict[str, Any]) -> int | None:
    usage = record.get("token_usage")
    if not isinstance(usage, dict):
        return None
    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        return None
    value = details.get("reasoning_tokens")
    return value if isinstance(value, int) else None


def is_deepseek_record(record: dict[str, Any]) -> bool:
    provider = str(record.get("provider", "")).lower()
    model = str(record.get("model", "")).lower()
    method = str(record.get("method", "")).lower()
    return provider == "deepseek" or model.startswith("deepseek") or "deepseek" in method


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    totals = {
        "files_scanned": 0,
        "deepseek_files": 0,
        "deepseek_records": 0,
        "records_with_usage": 0,
        "records_with_reasoning_tokens": 0,
        "records_with_positive_reasoning_tokens": 0,
        "records_with_reasoning_content": 0,
        "records_with_system_fingerprint": 0,
        "records_with_thinking_field": 0,
        "records_with_reasoning_effort_field": 0,
    }

    for path in sorted((ROOT / "outputs").rglob("*.jsonl")):
        totals["files_scanned"] += 1
        file_counts = {
            "path": str(path.relative_to(ROOT)),
            "deepseek_records": 0,
            "records_with_usage": 0,
            "records_with_reasoning_tokens": 0,
            "records_with_positive_reasoning_tokens": 0,
            "records_with_reasoning_content": 0,
            "records_with_system_fingerprint": 0,
            "records_with_thinking_field": 0,
            "records_with_reasoning_effort_field": 0,
        }
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or not is_deepseek_record(record):
                    continue
                file_counts["deepseek_records"] += 1
                totals["deepseek_records"] += 1

                if isinstance(record.get("token_usage"), dict):
                    file_counts["records_with_usage"] += 1
                    totals["records_with_usage"] += 1
                rtokens = reasoning_tokens(record)
                if rtokens is not None:
                    file_counts["records_with_reasoning_tokens"] += 1
                    totals["records_with_reasoning_tokens"] += 1
                    if rtokens > 0:
                        file_counts["records_with_positive_reasoning_tokens"] += 1
                        totals["records_with_positive_reasoning_tokens"] += 1

                keys = {key for key, _ in walk_values(record)}
                if "reasoning_content" in keys:
                    file_counts["records_with_reasoning_content"] += 1
                    totals["records_with_reasoning_content"] += 1
                if "system_fingerprint" in keys:
                    file_counts["records_with_system_fingerprint"] += 1
                    totals["records_with_system_fingerprint"] += 1
                if "thinking" in keys:
                    file_counts["records_with_thinking_field"] += 1
                    totals["records_with_thinking_field"] += 1
                if "reasoning_effort" in keys:
                    file_counts["records_with_reasoning_effort_field"] += 1
                    totals["records_with_reasoning_effort_field"] += 1

        if file_counts["deepseek_records"]:
            totals["deepseek_files"] += 1
            rows.append(file_counts)

    csv_path = OUT_DIR / "deepseek_reasoning_metadata_by_file.csv"
    with csv_path.open("w", encoding="utf-8") as handle:
        fieldnames = list(rows[0].keys()) if rows else ["path"]
        handle.write(",".join(fieldnames) + "\n")
        for row in rows:
            handle.write(",".join(str(row[name]) for name in fieldnames) + "\n")

    json_path = OUT_DIR / "deepseek_reasoning_metadata_summary.json"
    json_path.write_text(json.dumps({"summary": totals, "files": rows}, indent=2), encoding="utf-8")

    md_lines = [
        "# DeepSeek Reasoning Metadata Audit",
        "",
        "Generated from saved JSONL prediction outputs. This audit does not rerun model calls.",
        "",
        "Summary:",
        f"- JSONL files scanned: {totals['files_scanned']}",
        f"- DeepSeek JSONL files: {totals['deepseek_files']}",
        f"- DeepSeek records: {totals['deepseek_records']}",
        f"- Records with provider usage: {totals['records_with_usage']}",
        f"- Records with `completion_tokens_details.reasoning_tokens`: {totals['records_with_reasoning_tokens']}",
        f"- Records with positive `reasoning_tokens`: {totals['records_with_positive_reasoning_tokens']}",
        f"- Records retaining `reasoning_content`: {totals['records_with_reasoning_content']}",
        f"- Records retaining `system_fingerprint`: {totals['records_with_system_fingerprint']}",
        f"- Records retaining a request/response `thinking` field: {totals['records_with_thinking_field']}",
        f"- Records retaining a request/response `reasoning_effort` field: {totals['records_with_reasoning_effort_field']}",
        "",
        "Interpretation boundary:",
        "- The rerank client source does not explicitly set `thinking`, `reasoning_effort`, `top_p`, or `max_tokens` in the DeepSeek request payload.",
        "- Positive provider-reported reasoning-token counts indicate that reasoning-token accounting was present in many saved responses.",
        "- The saved prediction JSONL files do not retain full raw responses or `reasoning_content` for every run, so the thesis should treat the effective thinking-mode setting as a provider-default reproducibility limitation.",
        "",
        "Outputs:",
        f"- `{csv_path.relative_to(ROOT)}`",
        f"- `{json_path.relative_to(ROOT)}`",
    ]
    DOC_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
