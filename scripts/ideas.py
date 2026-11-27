"""Brainstorm new topics into a format's queue (ideas_<format>.csv) with the worker model.

    python scripts/ideas.py stickman --n 15
    python scripts/ideas.py cinematic --n 10 --theme "forgotten kings of Odisha"

Runs on the local model by default (config.json -> llm.tasks.ideas). Duplicates of queued topics
and past videos are dropped. Claude still fact-checks each topic when it writes the script.
"""
import argparse
import json
import re
import sys

from common import channel_for, load_config, load_history, read_ideas, write_ideas

STYLE = {
    "cinematic": "a short cinematic AI film about one untold story (a person, a legend, a turning point)",
    "stickman": "a stick-figure story answering ONE 'Why...?' or 'How did...?' question with a real, verifiable answer",
    "facts": "a motion-graphics explainer built around real numbers",
}


def build_prompt(cfg: dict, fmt: str, n: int, theme: str, avoid: list[str]) -> str:
    ch = channel_for(cfg, fmt)
    return f"""You brainstorm video topics for a YouTube Shorts channel.

Channel niche: {ch['niche']}
Audience: {ch['audience']}
Each video is {STYLE.get(fmt, STYLE['stickman'])}.
{f'Theme for this batch: {theme}' if theme else 'Mix sub-topics so the list is varied.'}

Rules:
- {n} topics. Each one line, under 90 characters, specific (names, places, objects), not generic.
- Only well-documented stories with a real answer. No rumours, politics, tragedies or mockery.
- Things people actually search for. A surprising angle beats a famous summary.
- Do not repeat or rephrase any of these: {json.dumps(avoid[-80:], ensure_ascii=False)}

Output ONLY JSON: {{"topics": ["...", "..."]}}"""


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def brainstorm(fmt: str, n: int = 10, theme: str = "") -> list[str]:
    import llm
    from generate import extract_json
    cfg = load_config()
    rows = read_ideas(fmt)
    avoid = [r["topic"] for r in rows] + [h.get("topic", "") or h.get("title", "") for h in load_history()]
    reply = llm.ask("ideas", build_prompt(cfg, fmt, n, theme, avoid), cfg, json_mode=True)
    data = extract_json(reply)
    topics = data.get("topics", []) if isinstance(data, dict) else []
    seen = {_norm(a) for a in avoid if a}
    added = []
    for t in topics:
        t = str(t).strip().strip('"')
        if 8 <= len(t) <= 120 and _norm(t) not in seen:
            seen.add(_norm(t))
            added.append(t)
    write_ideas(rows + [{"topic": t, "status": ""} for t in added], fmt)
    print(f"  added {len(added)} topics to ideas_{fmt}.csv")
    for t in added:
        print("   +", t)
    return added


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=["cinematic", "stickman", "facts"])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--theme", default="")
    a = ap.parse_args()
    brainstorm(a.format, a.n, a.theme)
    sys.exit(0)
