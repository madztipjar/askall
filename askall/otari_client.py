"""Otari integration for AskAll.

EVERY model call in AskAll goes through Mozilla AI's Otari hosted gateway.
There is exactly one integration point, and it is this module:

  * Endpoint .... https://api.otari.ai/api/v1  (OpenAI-compatible)
  * Auth ........ workspace API key from otari.ai ("otk_..."), sent as Bearer
  * Models ...... provider-prefixed IDs, e.g. "deepseek/deepseek-v4-pro-0813";
                  the app discovers what the workspace can call via GET /models
  * Tools ....... Otari's server-side tools, executed by the gateway itself:
                  {"type": "otari_web_search"}, {"type": "otari_code_execution"},
                  {"type": "otari_web_fetch"}. Gateway-run tool activity comes
                  back on the response as `otari_tool_calls`.

No provider SDKs, no provider keys, no direct provider calls anywhere in the
project. Swap the model string and the same code talks to a different
provider — that is the whole point of building on a gateway.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

BASE_URL = os.environ.get("OTARI_BASE_URL", "https://api.otari.ai/api/v1").rstrip("/")

# Otari server-side tools. Declared on a request, executed by the gateway,
# so even an open-weight model with no native tools gets search and code.
WEB_SEARCH_TOOL = {"type": "otari_web_search"}
WEB_FETCH_TOOL = {"type": "otari_web_fetch"}
CODE_EXECUTION_TOOL = {"type": "otari_code_execution"}


class OtariError(RuntimeError):
    """A gateway call failed, with a human-actionable message."""


@dataclass
class ChatResult:
    model: str
    content: str
    usage: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)
    latency_s: float = 0.0
    finish_reason: str = ""


def api_key() -> str:
    key = os.environ.get("OTARI_API_KEY", "").strip()
    if not key:
        raise OtariError(
            "OTARI_API_KEY is not set. Create a workspace API key at otari.ai "
            "(API Keys tab, it starts with otk_) and export it — see README."
        )
    return key


def _request(method: str, path: str, payload: dict | None = None, timeout: int = 180) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key()}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:600]
        hint = {
            401: "unauthorized — check the workspace API key (otk_...).",
            402: "insufficient funds — a new Otari organization gets $2 of credit "
                 "after the account owner completes the welcome questionnaire; "
                 "check Organization > Billing.",
            403: "forbidden — this key's workspace may not allow that model or tool "
                 "(see Tools / API Keys settings in the Otari dashboard).",
            421: "misdirected request — EU-region key: set OTARI_BASE_URL=https://eu.api.otari.ai/api/v1.",
        }.get(e.code, "")
        raise OtariError(f"Otari gateway HTTP {e.code} on {path}. {hint} Body: {body}") from e
    except urllib.error.URLError as e:
        raise OtariError(f"Could not reach the Otari gateway at {BASE_URL}: {e.reason}") from e


def list_models() -> list[str]:
    """Model IDs this workspace can call, straight from the gateway."""
    data = _request("GET", "/models")
    return sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))


def chat(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> ChatResult:
    """One chat completion through Otari. The gateway routes it to the
    provider named in the model ID and runs any otari_* tools itself."""
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
    started = time.time()
    data = _request("POST", "/chat/completions", payload)
    latency = time.time() - started
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return ChatResult(
        model=data.get("model", model),
        content=(message.get("content") or "").strip(),
        usage=data.get("usage") or {},
        tool_calls=data.get("otari_tool_calls") or message.get("otari_tool_calls") or [],
        latency_s=latency,
        finish_reason=choice.get("finish_reason", ""),
    )
