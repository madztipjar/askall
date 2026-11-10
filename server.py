"""Minimal web UI for AskAll — stdlib only, same Otari gateway as the CLI.

Run:  OTARI_API_KEY=otk_... python3 server.py   (http://localhost:8765)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from askall import cli, otari_client as oc

cli._load_dotenv()
WEB = os.path.join(os.path.dirname(__file__), "web", "index.html")


def _result_json(r: oc.ChatResult) -> dict:
    return {
        "model": r.model,
        "content": r.content,
        "usage": r.usage,
        "tool_calls": r.tool_calls,
        "latency_s": round(r.latency_s, 1),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            with open(WEB, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/models":
            try:
                self._json(200, {"models": oc.list_models()})
            except oc.OtariError as e:
                self._json(502, {"error": str(e)})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad JSON"})
        question = (body.get("question") or "").strip()
        if not question:
            return self._json(400, {"error": "question required"})
        try:
            if self.path == "/api/panel":
                panel = cli.pick_panel_models(oc.list_models(), int(body.get("count", 3)))
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor(max_workers=len(panel)) as pool:
                    results = list(pool.map(lambda m: cli._safe_ask(m, question), panel))
                out = [_result_json(r) for r in results if r is not None]
                verdict = None
                if len(out) >= 2:
                    joined = "\n\n".join(f"--- {r['model']} ---\n{r['content']}" for r in out)
                    v = oc.chat(
                        out[0]["model"],
                        [{"role": "user", "content": (
                            f"Several models answered the question: {question!r}\n\n{joined}\n\n"
                            "In at most 200 words: where do they agree, where do they differ, "
                            "and which answer is strongest, and why?")}],
                    )
                    verdict = _result_json(v)
                self._json(200, {"results": out, "verdict": verdict})
            elif self.path == "/api/research":
                r = oc.chat(
                    cli.pick_panel_models(oc.list_models(), 1)[0],
                    [
                        {"role": "system", "content": "Answer using up-to-date facts. Use web "
                                                      "search when needed and cite source URLs."},
                        {"role": "user", "content": question},
                    ],
                    tools=[oc.WEB_SEARCH_TOOL],
                    max_tokens=1600,
                )
                self._json(200, {"result": _result_json(r)})
            elif self.path == "/api/calc":
                r = oc.chat(
                    cli.pick_panel_models(oc.list_models(), 1)[0],
                    [
                        {"role": "system", "content": "For anything numeric, compute it with "
                                                      "the code execution tool. Show the result "
                                                      "and the key numbers."},
                        {"role": "user", "content": question},
                    ],
                    tools=[oc.CODE_EXECUTION_TOOL],
                    max_tokens=1600,
                )
                self._json(200, {"result": _result_json(r)})
            else:
                self._json(404, {"error": "not found"})
        except oc.OtariError as e:
            self._json(502, {"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    print(f"AskAll web UI on http://localhost:{port} (all model calls via Otari)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
