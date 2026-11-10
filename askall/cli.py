"""AskAll CLI.

Every mode talks to models exclusively through the Otari hosted gateway
(see askall/otari_client.py). There are no direct provider calls.

  askall models                       list the models your Otari workspace can call
  askall panel "question"             ask models from different providers, compare
  askall research "question"          answer using Otari's server-side web search
  askall calc "question"              answer using Otari's server-side code execution
  askall ask "question" --model ID    one model, one answer
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from . import otari_client as oc


def _load_dotenv() -> None:
    path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0] if "/" in model_id else model_id


# Fast, inexpensive models are better panellists for a comparison demo.
_PREFERRED = ("flash", "mini", "lite", "small", "fast", "haiku", "nano", "turbo", "oss", "v4")


def pick_panel_models(available: list[str], count: int = 3) -> list[str]:
    """Pick up to `count` models from *different* providers, preferring
    fast/cheap variants, so the panel actually compares providers."""
    by_provider: dict[str, list[str]] = {}
    for m in available:
        by_provider.setdefault(provider_of(m), []).append(m)
    panel: list[str] = []
    for provider in sorted(by_provider):
        models = sorted(
            by_provider[provider],
            key=lambda m: (0 if any(p in m.lower() for p in _PREFERRED) else 1, len(m), m),
        )
        panel.append(models[0])
        if len(panel) == count:
            break
    return panel


def _usage_line(r: oc.ChatResult) -> str:
    u = r.usage or {}
    return (
        f"[tokens: {u.get('prompt_tokens', '?')} in / {u.get('completion_tokens', '?')} out"
        f" | {r.latency_s:.1f}s | via Otari]"
    )


def _print_tool_calls(r: oc.ChatResult) -> None:
    if not r.tool_calls:
        return
    print("  Otari server-side tool calls:")
    for tc in r.tool_calls:
        preview = json.dumps(tc, default=str)
        print(f"    - {preview[:600]}")


def _ask_one(model: str, question: str) -> oc.ChatResult:
    return oc.chat(model, [{"role": "user", "content": question}])


def cmd_models(_args) -> int:
    models = oc.list_models()
    by_provider: dict[str, list[str]] = {}
    for m in models:
        by_provider.setdefault(provider_of(m), []).append(m)
    print(f"{len(models)} models available through this Otari workspace:\n")
    for provider in sorted(by_provider):
        print(f"{provider}:")
        for m in by_provider[provider]:
            print(f"  {m}")
    return 0


def cmd_panel(args) -> int:
    available = oc.list_models()
    if args.models:
        panel = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        panel = pick_panel_models(available, args.count)
    if not panel:
        print("No models available in this workspace.", file=sys.stderr)
        return 1
    print(f"Question: {args.question}\nPanel (via Otari): {', '.join(panel)}\n")
    with ThreadPoolExecutor(max_workers=len(panel)) as pool:
        results = list(pool.map(lambda m: _safe_ask(m, args.question), panel))
    ok = [r for r in results if r is not None]
    for model, r in zip(panel, results):
        print("=" * 78)
        if r is None:
            print(f"{model}: FAILED (see errors above)")
            continue
        print(f"{r.model}\n{_usage_line(r)}\n\n{r.content}\n")
    if args.judge and len(ok) >= 2:
        judge = ok[0].model
        joined = "\n\n".join(f"--- {r.model} ---\n{r.content}" for r in ok)
        verdict = oc.chat(
            judge,
            [
                {
                    "role": "user",
                    "content": (
                        f"Several models answered the question: {args.question!r}\n\n{joined}\n\n"
                        "In at most 200 words: where do they agree, where do they differ, "
                        "and which answer is strongest, and why?"
                    ),
                }
            ],
        )
        print("=" * 78)
        print(f"JUDGE ({verdict.model})\n{_usage_line(verdict)}\n\n{verdict.content}")
    return 0


def _safe_ask(model: str, question: str) -> oc.ChatResult | None:
    try:
        return _ask_one(model, question)
    except oc.OtariError as e:
        print(f"[{model}] {e}", file=sys.stderr)
        return None


def cmd_research(args) -> int:
    model = args.model or pick_panel_models(oc.list_models(), 1)[0]
    r = oc.chat(
        model,
        [
            {
                "role": "system",
                "content": "Answer using up-to-date facts. Use web search when the "
                           "question needs current information, and cite source URLs.",
            },
            {"role": "user", "content": args.question},
        ],
        tools=[oc.WEB_SEARCH_TOOL],
        max_tokens=1600,
    )
    print(f"{r.model}\n{_usage_line(r)}\n")
    _print_tool_calls(r)
    print(f"\n{r.content}")
    return 0


def cmd_calc(args) -> int:
    model = args.model or pick_panel_models(oc.list_models(), 1)[0]
    r = oc.chat(
        model,
        [
            {
                "role": "system",
                "content": "For anything numeric, compute it with the code execution "
                           "tool instead of doing mental arithmetic. Show the result "
                           "and the key numbers you computed.",
            },
            {"role": "user", "content": args.question},
        ],
        tools=[oc.CODE_EXECUTION_TOOL],
        max_tokens=1600,
    )
    print(f"{r.model}\n{_usage_line(r)}\n")
    _print_tool_calls(r)
    print(f"\n{r.content}")
    return 0


def cmd_ask(args) -> int:
    model = args.model or pick_panel_models(oc.list_models(), 1)[0]
    r = _ask_one(model, args.question)
    print(f"{r.model}\n{_usage_line(r)}\n\n{r.content}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="askall", description="Ask once. Every model answers.")
    sub = parser.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("models", help="list models available through your Otari workspace")
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("panel", help="ask models from different providers the same question")
    p.add_argument("question")
    p.add_argument("--models", help="comma-separated model IDs (default: auto-pick by provider)")
    p.add_argument("--count", type=int, default=3, help="panel size when auto-picking")
    p.add_argument("--no-judge", dest="judge", action="store_false", help="skip the judge summary")
    p.set_defaults(func=cmd_panel)

    p = sub.add_parser("research", help="answer with Otari's server-side web search")
    p.add_argument("question")
    p.add_argument("--model")
    p.set_defaults(func=cmd_research)

    p = sub.add_parser("calc", help="answer with Otari's server-side code execution")
    p.add_argument("question")
    p.add_argument("--model")
    p.set_defaults(func=cmd_calc)

    p = sub.add_parser("ask", help="ask a single model")
    p.add_argument("question")
    p.add_argument("--model")
    p.set_defaults(func=cmd_ask)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except oc.OtariError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
