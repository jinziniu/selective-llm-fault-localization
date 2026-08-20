from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any
from urllib import request


class LLMClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    raw: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    provider: str = ""
    model: str = ""


class DeepSeekClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise LLMClientError("DEEPSEEK_API_KEY is required for --provider deepseek")
        self.base_url = (
            base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        ).rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-v4-flash"
        self.timeout = int(os.environ.get("DEEPSEEK_TIMEOUT", timeout))

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - preserve original API failure detail
            raise LLMClientError(f"DeepSeek API call failed: {exc}") from exc

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError(f"Unexpected DeepSeek response shape: {raw}") from exc
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None
        return LLMResponse(
            content=content,
            raw=raw,
            usage=usage,
            provider="deepseek",
            model=self.model,
        )


class CodexClient:
    def __init__(self, *, model: str | None = None, timeout: int = 300) -> None:
        self.model = model
        self.timeout = timeout

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> LLMResponse:
        del temperature
        prompt = system + "\n\n" + user
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "codex-output.txt"
            command = [
                "codex",
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "-o",
                str(output_path),
            ]
            if self.model:
                command.extend(["--model", self.model])
            command.append("-")
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.timeout,
                check=False,
            )
            if result.returncode != 0:
                raise LLMClientError(f"codex exec failed:\n{result.stdout}")
            content = output_path.read_text(encoding="utf-8") if output_path.exists() else result.stdout
        return LLMResponse(content=content, provider="codex", model=self.model or "codex-default")


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise LLMClientError(f"Could not find JSON object in model output:\n{text}")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise LLMClientError(f"Expected JSON object, got {type(parsed).__name__}")
    return parsed
