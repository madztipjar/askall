# Draft issue for github.com/mozilla-ai/otari (file under madztipjar)

**Title:** Docs: model ID format differs between Python SDK readme (`provider:model`) and hosted quickstart (`provider/model`)

**Body:**

Hi! Building a hackathon project (Devs Wilding) against the hosted platform, I hit a small but confusing inconsistency in the model ID format:

- The **Python SDK readme on PyPI** (`otari` package) shows:
  `model="openai:gpt-4o-mini"` — with a **colon** separator.
- The **hosted quickstart** at docs.otari.ai shows:
  `"model": "deepseek/deepseek-v4-pro-0813"` — with a **slash** separator.

Both are official sources, and the model string is the first thing a new user copies, so it's worth making them agree (I went with the quickstart/slash form, and defensively used whatever IDs `GET /models` returns rather than hardcoding any).

Possibly the SDK accepts both forms — if so, a one-line note saying that in both places would also fix the confusion. Thanks!
