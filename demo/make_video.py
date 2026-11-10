#!/usr/bin/env python3
"""Build the AskAll demo video (3-5 min, 1080p, H.264 yuv420p + AAC).

Scenes = PIL-rendered slides / terminal captures + edge-tts narration.
Terminal scenes use REAL captured output from demo/run_captures.sh — run that
first, with a live OTARI_API_KEY, or this script refuses to fake it.

Usage: python3 demo/make_video.py   ->  demo/demo.mp4
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo")
WORK = os.path.join(DEMO, "work")
CAPTURES = os.path.join(DEMO, "captures")
OUT = os.path.join(DEMO, "demo.mp4")
EDGE_TTS = "/tmp/otarivenv/bin/edge-tts" if os.path.exists("/tmp/otarivenv/bin/edge-tts") else "edge-tts"
VOICE = "en-US-ChristopherNeural"
RATE = "-6%"

W, H = 1920, 1080
BG = (11, 14, 20)
PANEL = (17, 21, 29)
FG = (230, 233, 239)
DIM = (154, 164, 178)
ACCENT = (255, 184, 107)
GREEN = (143, 208, 168)
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

SCENES = [
    {
        "kind": "slide", "title": "AskAll",
        "body": ["Ask once. Every model answers.", "",
                 "Built for Mozilla Devs Wilding Online · MozFest 2026",
                 "Every model call powered by Otari — Mozilla AI's hosted gateway"],
        "narration": "This is AskAll. Ask once, and every model answers. I built it for "
                     "Mozilla's Devs Wilding Online hackathon, and there is exactly one "
                     "place its model calls go: Otari, the hosted AI gateway from Mozilla AI.",
    },
    {
        "kind": "slide", "title": "Why a panel of models?",
        "body": ["• One model gives you one opinion — and one blind spot",
                 "• Comparing providers directly means N SDKs, N API keys, N bills",
                 "• Open-weight models often lack tools like search and code execution"],
        "narration": "One model gives you one opinion, and one blind spot. Comparing "
                     "providers the direct way means a different SDK, API key and bill for "
                     "every provider — and open-weight models often lack basic tools like "
                     "web search and code execution. AskAll removes all of that with a gateway.",
    },
    {
        "kind": "slide", "title": "One gateway, one key",
        "body": ["Endpoint:  https://api.otari.ai/api/v1  (OpenAI-compatible)",
                 "Auth:  a single workspace key (otk_…) — no provider keys anywhere",
                 "Models discovered at runtime via GET /models",
                 "Tools declared as types:  otari_web_search · otari_code_execution"],
        "narration": "Everything talks to one OpenAI-compatible endpoint, api.otari.ai, "
                     "with a single workspace key. No provider keys exist anywhere in the "
                     "project. AskAll even discovers which models the workspace can call, "
                     "at runtime, from the gateway itself. Watch it work.",
    },
    {
        "kind": "terminal", "title": "$ askall models", "capture": "models.txt",
        "narration": "First, discovery. One call lists every model this workspace can "
                     "reach, grouped here by provider. The panel then picks one model per "
                     "provider automatically, preferring fast, inexpensive variants.",
    },
    {
        "kind": "terminal", "title": "$ askall panel", "capture": "panel.txt",
        "narration": "Panel mode sends one question to models from three different "
                     "providers — in parallel, through the same key. You see each answer "
                     "with its token count and latency, and then a judge model summarises "
                     "where they agree, where they differ, and which answer is strongest.",
    },
    {
        "kind": "terminal", "title": "$ askall research", "capture": "research.txt",
        "narration": "Research mode declares Otari's web search tool. The gateway runs "
                     "the search itself, so even a model with no native browsing can answer "
                     "with current facts and sources. The tool calls come back on the "
                     "response, visible in the output.",
    },
    {
        "kind": "terminal", "title": "$ askall calc", "capture": "calc.txt",
        "narration": "Calc mode declares the code execution tool. Instead of doing mental "
                     "arithmetic, the model writes Python and Otari runs it in a sandbox. "
                     "The result is computed, not guessed — compound growth over twenty "
                     "years, exact to the cent.",
    },
    {
        "kind": "slide", "title": "What Otari gave us — and honest feedback",
        "body": ["• One endpoint, one key, one usage view for every provider",
                 "• Server-side tools give open-weight models search + code execution",
                 "• Budgets and per-request tracking in the Otari dashboard",
                 "• Friction: docs are operator-first; model-ID format differs between",
                 "   the SDK readme and the quickstart (issue filed — see FEEDBACK.md)"],
        "narration": "What Otari gave us: one endpoint, one key and one usage view for "
                     "every provider, budgets in the dashboard, and server-side tools that "
                     "give open-weight models search and code. Our honest friction points "
                     "are in the written feedback — the documentation is operator-first, and "
                     "the model ID format differs between the SDK readme and the quickstart. "
                     "We filed an issue for that one.",
    },
    {
        "kind": "slide", "title": "AskAll",
        "body": ["github.com/madztipjar/askall   ·   branch: devs-wilding", "",
                 "Ask once. Every model answers."],
        "narration": "AskAll is open source — the link is on screen. One question, every "
                     "model, one gateway. Thanks for watching.",
    },
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:3]), "…")
    subprocess.run(cmd, check=True, capture_output=True)


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def render_scene(idx: int, scene: dict) -> str:
    from PIL import Image, ImageDraw, ImageFont

    def font(name: str, size: int):
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    if scene["kind"] == "terminal":
        cap_path = os.path.join(CAPTURES, scene["capture"])
        if not os.path.exists(cap_path):
            sys.exit(f"Missing capture {cap_path} — run demo/run_captures.sh with a live "
                     "OTARI_API_KEY first. Refusing to fake terminal output.")
        d.rounded_rectangle([60, 50, W - 60, H - 50], radius=18, fill=PANEL, outline=(42, 49, 64), width=2)
        d.text((100, 78), scene["title"], font=font("DejaVuSansMono-Bold.ttf", 34), fill=GREEN)
        lines: list[str] = []
        for raw in open(cap_path).read().splitlines():
            lines.extend(textwrap.wrap(raw, 98) or [""])
        if len(lines) > 35:
            lines = lines[:29] + ["  …"] + lines[-5:]
        f = font("DejaVuSansMono.ttf", 25)
        y = 140
        for line in lines:
            d.text((100, y), line, font=f, fill=FG)
            y += 27
    else:
        big = scene["title"] == "AskAll"
        d.text((120, 130), scene["title"], font=font("DejaVuSans-Bold.ttf", 84 if big else 56), fill=ACCENT)
        f = font("DejaVuSans.ttf", 36)
        y = 300 if big else 260
        for line in scene["body"]:
            wrapped = textwrap.wrap(line, 78) or [""]
            for wline in wrapped:
                d.text((120, y), wline, font=f, fill=FG)
                y += 52
    path = os.path.join(WORK, f"scene-{idx:02d}.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    segments = []
    for i, scene in enumerate(SCENES):
        png = render_scene(i, scene)
        mp3 = os.path.join(WORK, f"scene-{i:02d}.mp3")
        run([EDGE_TTS, "--voice", VOICE, "--rate", RATE, "--text", scene["narration"],
             "--write-media", mp3])
        dur = duration(mp3) + 0.5
        seg = os.path.join(WORK, f"seg-{i:02d}.mp4")
        run(["ffmpeg", "-y", "-loop", "1", "-i", png, "-i", mp3, "-t", f"{dur:.2f}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-vf", "scale=1920:1080",
             "-c:a", "aac", "-b:a", "160k", "-shortest", seg])
        segments.append(seg)
        print(f"scene {i}: {dur:.1f}s")
    listfile = os.path.join(WORK, "concat.txt")
    with open(listfile, "w") as f:
        for s in segments:
            f.write(f"file '{s}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", OUT])
    # Loudness: measure, then nudge so max sits near -1 dB (narration mean lands ~-20 dB).
    stats = subprocess.run(["ffmpeg", "-i", OUT, "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    mean = maxv = None
    for line in stats.splitlines():
        if "mean_volume" in line:
            mean = float(line.rsplit(" ", 2)[-2])
        if "max_volume" in line:
            maxv = float(line.rsplit(" ", 2)[-2])
    print(f"loudness before trim: mean {mean} dB, max {maxv} dB, total {duration(OUT):.1f}s")
    if maxv is not None and abs(maxv - (-1.0)) > 0.5:
        adj = -1.0 - maxv
        tmp = OUT + ".tmp.mp4"
        run(["ffmpeg", "-y", "-i", OUT, "-c:v", "copy", "-af", f"volume={adj:.1f}dB",
             "-c:a", "aac", "-b:a", "160k", tmp])
        os.replace(tmp, OUT)
        stats = subprocess.run(["ffmpeg", "-i", OUT, "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        for line in stats.splitlines():
            if "mean_volume" in line or "max_volume" in line:
                print("final:", line.strip())
    print(f"total duration: {duration(OUT):.1f}s -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
