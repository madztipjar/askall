# Feedback on Otari — from building AskAll

Project: **AskAll** (Devs Wilding Online). Everything below is from actually
building and wiring this project against the hosted platform at otari.ai and
its documentation. Written answers to the hackathon's three questions first,
then a short "what worked / what didn't" list.

## 1. When were you most tempted to skip Otari and call the provider directly? What happened?

Twice, both times in the documentation rather than the API.

First, the model ID format. The Python SDK readme on PyPI shows
`model="openai:gpt-4o-mini"` (colon), while the hosted quickstart uses
`"deepseek/deepseek-v4-pro-0813"` (slash). When the two official sources
disagree on the most basic string in the whole integration, the temptation
is to go back to a provider API where you already know the format. We
resolved it by trusting the hosted quickstart — and, more importantly, by
not hardcoding model IDs at all: AskAll calls `GET /models` and uses the
IDs the gateway itself returns, so the format question can't bite at
runtime. (We filed an issue about this — see the repo's submission notes.)

Second, the tools documentation. Declaring a server-side tool turned out to
be beautifully simple — `"tools": [{"type": "otari_web_search"}]` — but
finding that line meant reading a ~1,000-line page written for gateway
*operators* (pricing rows, deployment settings, settlement rules). A
five-line client-first example ("declare this type; the gateway runs it;
results come back in `otari_tool_calls`") would have saved real time.

## 2. What did you end up building yourself that Otari should've done for you?

- **Panel routing policy.** AskAll's whole point is "one model per
  provider, preferring fast/cheap variants." We built that selection by
  hand on top of `GET /models`: group by provider prefix, rank by name
  heuristics. A gateway-side routing preset ("one representative model per
  provider" / "cheapest per provider") is a natural Otari feature —
  multi-provider routing is already a dashboard concept.
- **Defensive tool-call parsing.** Gateway-run tool activity is documented
  as `otari_tool_calls` on the Chat Completions response; we read it from
  two possible locations because we couldn't confirm a single canonical
  one from the docs alone.
- **Cost translation.** Responses carry token usage but not the settled
  dollar cost, so the app can show tokens and latency but must send users
  to the Usage tab for money. A `cost` field (or cost breakdown like the
  dashboard's pricing lines) on the response would close that loop.
- Small stuff: a `.env` loader and HTTP plumbing (we deliberately kept
  zero dependencies and used the raw OpenAI-compatible endpoint).

## 3. If the rules hadn't required Otari, would you have continued using Otari? Why or why not?

Yes — for this kind of app, genuinely. AskAll is a multi-model product: the
value is comparing providers, and Otari collapses N integrations, N keys
and N bills into one endpoint, one `otk_` key and one usage view. The
server-side tools are the strongest argument: giving an open-weight model
web search and code execution by declaring a tool type is something no
direct provider call gives you uniformly. The $2 welcome credit also made
the first requests work with zero payment setup, which is how a gateway
should onboard.

What would make us hesitate on a bigger project: the documentation is
operator-first and client-second (see Q1), and cost visibility lives in
the dashboard rather than the API response. Both are fixable, and neither
changes the core verdict: the gateway earned its place in the architecture.

## What worked well

- One OpenAI-compatible endpoint for every provider; model switching is a
  string change, exactly as promised.
- `GET /models` discovery — the app never hardcodes a model catalog.
- Server-side tools as declarative types; the gateway runs them.
- $2 welcome credit after the questionnaire: first requests work before
  any payment method exists.
- Error for EU keys (421) names the correct host — self-healing errors
  are a small thing that saved a support round-trip.

## What didn't work / friction

- Model ID format inconsistency between the SDK readme (colon) and the
  hosted quickstart (slash).
- Tools docs are operator-oriented; the client contract is buried.
- Tool availability depends on workspace toggles (Tools settings) — a
  request can declare a tool that the workspace has disabled, and the
  failure mode isn't obvious from the client side alone.
