# AskAll

**Ask once. Every model answers.**

AskAll sends one question to models from *different providers* at the same
time and shows their answers side by side — tokens, latency and all — then a
judge model summarises where they agree, where they differ, and which answer
is strongest. It also answers questions with live web search and with real
code execution.

Every single model call goes through **Otari**, Mozilla AI's hosted gateway
at `api.otari.ai`. AskAll holds no provider keys and calls no provider
directly: one Otari workspace key (`otk_...`) is the only credential, and
switching providers is just a different model string.

Built for Mozilla's **Devs Wilding Online** hackathon (MozFest 2026), on the
`devs-wilding` branch. The first commit on this branch is where Otari came
in: `askall/otari_client.py` is the single integration point for the whole
project.

## Why a gateway is the product here

A model panel is exactly the app a gateway exists for. Direct provider
integrations would mean N SDKs, N keys, N billing relationships and N
error formats. With Otari it is one endpoint, one key, one usage view —
and the panel can include any model the workspace can call, discovered at
runtime via `GET /models`. Otari's server-side tools also give open-weight
models capabilities they don't ship with: AskAll's `research` mode uses
`otari_web_search` and its `calc` mode uses `otari_code_execution`, both
executed by the gateway, not by the model or this app.

## Otari features used

- **Hosted gateway** (`https://api.otari.ai/api/v1`), OpenAI-compatible
  Chat Completions — all traffic, no exceptions.
- **Multi-provider routing** — provider-prefixed model IDs
  (e.g. `deepseek/deepseek-v4-pro-0813`); the panel auto-picks one model
  per provider from the workspace catalog.
- **Model discovery** — `GET /models` lists what the workspace can call;
  AskAll groups and selects from it at runtime.
- **Server-side tools** — `otari_web_search` (research mode) and
  `otari_code_execution` (calc mode), declared as tool types and executed
  by Otari; gateway tool activity is read back from `otari_tool_calls`.
- **Workspace API keys** — a single scoped `otk_` key is the app's only
  credential.
- **Usage tracking** — per-request token usage is surfaced in the CLI/UI
  for every call, and every request is visible in Otari's Usage tab.

## Setup

1. Create a free account at [otari.ai](https://otari.ai) (GitHub, Google or
   email). Complete the welcome questionnaire — a new organization gets
   **$2 of credit**, enough to run this demo on inexpensive models.
2. In your default workspace, open **API Keys → Create Key** and copy the
   `otk_...` token (shown once).
3. Run:

```bash
git clone https://github.com/madztipjar/askall
cd askall
git checkout devs-wilding
export OTARI_API_KEY=otk_your_workspace_key_here   # or put it in .env
python3 -m askall.cli models                       # see what you can call
```

No dependencies: AskAll runs on the Python 3 standard library alone.

## Usage

```bash
python3 -m askall.cli panel "Why is the sky blue?"
python3 -m askall.cli panel "Tabs or spaces?" --models deepseek/deepseek-v4-pro-0813,openai/gpt-4o-mini
python3 -m askall.cli research "What happened at MozFest 2026 this week?"
python3 -m askall.cli calc "If I invest $250 a month at 7% annual return, what is it worth in 20 years?"
python3 -m askall.cli ask "Write a haiku about gateways" 
python3 server.py        # web UI on http://localhost:8765
```

## Layout

- `askall/otari_client.py` — **the** Otari integration: endpoint, auth,
  model discovery, chat calls, tool declarations, error translation.
- `askall/cli.py` — panel / research / calc / ask modes and formatting.
- `server.py` + `web/index.html` — a small web UI over the same gateway.
- `FEEDBACK.md` — our written feedback on building with Otari.

## Notes

- EU-region Otari accounts: set `OTARI_BASE_URL=https://eu.api.otari.ai/api/v1`.
- The API key is read from `OTARI_API_KEY` or a local `.env` file; it is
  never committed (`.env` is git-ignored).
