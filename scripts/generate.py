"""Write videos/<slug>/script.json using headless Claude Code (`claude -p`).

Uses your existing Claude Code login (subscription) — no API key needed.

    python scripts/generate.py                      # next unused topic from ideas.csv
    python scripts/generate.py --topic "Why ..."    # a specific topic
"""
import argparse
import json
import re
import subprocess
import sys

from common import (ROOT, add_history, channel_for, load_config, load_history, next_idea, slugify,
                    video_dir, which, write_json)

SCENE_TYPES = {
    "hook": ["heading"],
    "text": ["heading"],
    "stat": ["value", "label"],
    "list": ["heading", "items"],
    "bars": ["heading", "data"],
    "outro": ["heading"],
}

SCHEMA = """{
  "title": "YouTube title, max 90 chars, honest, curiosity-driven",
  "description": "2-4 short lines for the YouTube description",
  "tags": ["5-10 lowercase tags"],
  "sources": ["URL or publication name for every number used"],
  "scenes": [
    {"type": "hook",  "heading": "3-6 punchy words on screen", "narration": "spoken line"},
    {"type": "text",  "heading": "2-5 words", "body": "optional, max 14 words", "narration": "..."},
    {"type": "stat",  "value": "e.g. 13 billion or 4 or 99.9%", "label": "max 8 words", "narration": "..."},
    {"type": "list",  "heading": "2-5 words", "items": ["2-4 items, max 4 words each"], "narration": "..."},
    {"type": "bars",  "heading": "max 6 words", "unit": "optional suffix like % or B", "data": [{"label": "short", "value": 12.5}], "narration": "..."},
    {"type": "outro", "heading": "max 6 words", "narration": "..."}
  ]
}"""


def load_catalog() -> dict:
    """Read the allowed values from src/story/catalog.ts (single source of truth)."""
    text = (ROOT / "src" / "story" / "catalog.ts").read_text(encoding="utf-8")
    cat = {}
    for name, body in re.findall(r"export const (\w+) = \[(.*?)\] as const", text, re.S):
        cat[name] = re.findall(r"'([^']+)'", body)
    return cat


STORY_SCENE_FIELDS = ["setting", "time", "pose", "mood", "position", "facing", "hold",
                      "props", "overhead", "crowd", "label"]


def build_story_prompt(cfg: dict, topic: str, past_titles: list[str], error: str | None) -> str:
    ch, v = cfg["channel"], cfg["video"]
    st = cfg.get("story", {})
    cat = load_catalog()
    words = int(v["target_seconds"] * 2.6)
    n = int(st.get("scenes", 9))
    name = st.get("character_name", "Tiko")
    rules = "\n".join(f"- {r}" for r in cfg.get("cinematic", {}).get("content_rules", []))
    if rules:
        rules = "Content rules (follow strictly; for stick figures: never draw a deity as a stick figure):\n" + rules
    prompt = f"""You are the director of a faceless stick-figure storytelling channel on YouTube.

Channel: {ch['niche']}
Audience: {ch['audience']}
Language of narration and on-screen text: {ch['language']}
Tone: warm storyteller, simple words, short sentences.
Main character: a stick figure called {name} who appears in every video (same character every time).
Topic (always framed as a question): {topic}

Write the video as a STORY, not a list of facts:
- Scene 1 opens on the most surprising moment of the story (the hook), BEFORE the question is asked.
- Scene 2 is the question card (type "question").
- Then {name} has a problem, something goes wrong, and the story builds to a surprising, satisfying answer.
- Every scene should make the viewer want the next one.
- The last scene wraps up the answer and its narration ends with: "{ch['cta']}"

Exactly {n} scenes. Each narration is 1-2 short sentences. Total narration about {words} words.
Accuracy matters: only state history/science that is well established. Where historians are unsure,
say so in the story ("historians think..."). Never invent dates, names or numbers. List your sources.

Each scene is drawn by code from this fixed catalogue. Use ONLY these values:
- setting: {", ".join(cat["SETTINGS"])}
- time: {", ".join(cat["TIMES"])}
- pose: {", ".join(cat["POSES"])}
- mood: {", ".join(cat["MOODS"])}
- hold (item in hand, optional): {", ".join(cat["HELD"])}
- props (0-2 items placed in the scene, optional): {", ".join(cat["PROPS"])}
- overhead (icon above head, optional): {", ".join(cat["OVERHEAD"])}
- position: {", ".join(cat["POSITIONS"])}; facing: left, right
- crowd: 0-3 extra grey stick figures (optional)
- label: optional on-screen tag, max 4 words (a time or place like "10,000 years ago")
Vary settings, poses and moods so the video feels alive; match them to what the narration describes.
{rules}

Output ONE JSON object, exactly this shape:
{{
  "title": "the question as a YouTube title, max 90 chars",
  "description": "2-3 short lines for YouTube",
  "tags": ["5-10 lowercase tags"],
  "sources": ["publication or URL for each key fact"],
  "scenes": [
    {{"type": "story", "setting": "...", "time": "...", "pose": "...", "mood": "...", "label": "...", "narration": "..."}},
    {{"type": "question", "question": "the question, max 8 words", "setting": "...", "time": "...", "narration": "..."}},
    {{"type": "story", "setting": "...", "time": "...", "pose": "...", "mood": "...", "hold": "...", "props": ["..."], "overhead": "...", "narration": "..."}}
  ]
}}
Do not repeat these existing titles: {json.dumps(past_titles[-30:], ensure_ascii=False)}
Output ONLY the JSON object. No markdown fences, no commentary."""
    if error:
        prompt += f"\n\nYour previous attempt was invalid: {error}\nFix it and output only valid JSON."
    return prompt


def validate_story(data: dict) -> None:
    cat = load_catalog()
    allowed = {"setting": cat["SETTINGS"], "time": cat["TIMES"], "pose": cat["POSES"],
               "mood": cat["MOODS"], "hold": cat["HELD"], "overhead": cat["OVERHEAD"],
               "position": cat["POSITIONS"], "facing": ["left", "right"]}
    for k in ("title", "description", "scenes"):
        if k not in data:
            raise ValueError(f"missing key '{k}'")
    scenes = data["scenes"]
    if not isinstance(scenes, list) or not 5 <= len(scenes) <= 14:
        raise ValueError("scenes must be a list of 5-14 items")
    if not any(s.get("type") == "question" for s in scenes):
        raise ValueError("needs one scene of type 'question'")
    for i, s in enumerate(scenes):
        if s.get("type") not in ("story", "question"):
            raise ValueError(f"scene {i}: type must be 'story' or 'question'")
        if not str(s.get("narration", "")).strip():
            raise ValueError(f"scene {i}: empty narration")
        if s["type"] == "question" and not s.get("question"):
            raise ValueError(f"scene {i}: question scene needs 'question'")
        for key, values in allowed.items():
            if key in s and s[key] not in values:
                # fix silently-recoverable values instead of failing the whole script
                if key in ("hold", "overhead"):
                    s.pop(key)
                else:
                    raise ValueError(f"scene {i}: {key}='{s[key]}' not allowed; use one of {values}")
        s["props"] = [p for p in s.get("props", []) if p in cat["PROPS"]][:2]
        s["crowd"] = max(0, min(3, int(s.get("crowd", 0) or 0)))
    if len(data["title"]) > 100:
        raise ValueError("title longer than 100 characters")


def build_prompt(cfg: dict, topic: str, past_titles: list[str], error: str | None) -> str:
    ch, v = cfg["channel"], cfg["video"]
    words = int(v["target_seconds"] * 2.6)
    prompt = f"""You are the scriptwriter for a faceless YouTube Shorts channel.

Channel niche: {ch['niche']}
Audience: {ch['audience']}
Language of narration and on-screen text: {ch['language']}
Style: {ch['style']}
Topic for this video: {topic}

Write ONE video script as a single JSON object matching this schema exactly:
{SCHEMA}

Rules:
- 6 to 9 scenes. First scene type "hook", last scene type "outro" whose narration ends with: "{ch['cta']}"
- Total narration about {words} words (~{v['target_seconds']} seconds). Each scene's narration 1-2 short sentences.
- Mix scene types; use at least one "stat" or "bars" scene with REAL numbers.
- Accuracy matters more than drama. Only use facts and numbers you are confident are correct and current; verify them with web search if available, and list sources. If a number is uncertain, phrase it as approximate or leave it out. Never invent data.
- On-screen text must be short (it is read on a phone). Narration says more than the screen.
- Write numbers in narration the way they are spoken ("thirteen billion"), and in "value" fields as digits.
- Add something original: a clear explanation, comparison or takeaway — not a generic list of facts.
- Do not repeat these existing titles: {json.dumps(past_titles[-30:], ensure_ascii=False)}

Output ONLY the JSON object. No markdown fences, no commentary."""
    if error:
        prompt += f"\n\nYour previous attempt was invalid: {error}\nFix it and output only valid JSON."
    return prompt


def extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in Claude's reply")
    return json.loads(text[start : end + 1])


def validate(data: dict) -> None:
    for k in ("title", "description", "scenes"):
        if k not in data:
            raise ValueError(f"missing key '{k}'")
    scenes = data["scenes"]
    if not isinstance(scenes, list) or not 4 <= len(scenes) <= 12:
        raise ValueError("scenes must be a list of 4-12 items")
    for i, s in enumerate(scenes):
        t = s.get("type")
        if t not in SCENE_TYPES:
            raise ValueError(f"scene {i}: unknown type '{t}'")
        if not str(s.get("narration", "")).strip():
            raise ValueError(f"scene {i}: empty narration")
        for k in SCENE_TYPES[t]:
            if k not in s:
                raise ValueError(f"scene {i} ({t}): missing '{k}'")
        if t == "bars":
            for d in s["data"]:
                if not isinstance(d.get("value"), (int, float)):
                    raise ValueError(f"scene {i}: bars values must be numbers")
    if len(data["title"]) > 100:
        raise ValueError("title longer than 100 characters")


def ask_claude(prompt: str, cfg: dict) -> str:
    cmd = [which("claude"), "-p", "--output-format", "json"]
    if cfg["claude"].get("allow_web_search", True):
        cmd += ["--allowedTools", "WebSearch,WebFetch"]
    if cfg["claude"].get("model"):
        cmd += ["--model", cfg["claude"]["model"]]
    print("  asking Claude Code for a script...")
    res = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                         encoding="utf-8", timeout=900)
    if res.returncode != 0:
        raise RuntimeError(f"claude exited {res.returncode}: {res.stderr[-800:]}")
    try:
        outer = json.loads(res.stdout)
    except json.JSONDecodeError:
        return res.stdout
    if outer.get("is_error"):
        raise SystemExit(
            f"Claude Code returned an error: {outer.get('result')}\n"
            "Open a terminal, run `claude`, make sure you're logged in, then try again.")
    return outer.get("result", res.stdout)


def generate(topic: str | None = None, fmt: str | None = None, plan: dict | None = None) -> str:
    """Write a script. `plan` (from topics.py) adds the timely angle: event, date, keywords."""
    cfg = load_config()
    fmt = fmt or cfg["video"].get("format", "stickman")
    cfg = {**cfg, "channel": channel_for(cfg, fmt)}  # each format has its own channel identity
    topic = topic or next_idea(fmt)
    if not topic:
        topic = "Pick a fresh, specific question that fits the channel niche"
    past = [h.get("title", "") for h in load_history()]
    prompt_topic = topic
    if plan and plan.get("event"):
        prompt_topic += (f"\nTimely angle: this video is published around {plan['event']}"
                         f" ({plan.get('event_date', 'soon')}). {plan.get('why_now', '')}"
                         f"\nWork these search keywords naturally into the title, description and tags: "
                         f"{', '.join(plan.get('keywords', []))}. Title idea: {plan.get('title_idea', '')}")

    if fmt == "cinematic":
        from film import build_film_prompt, validate_film
        builder, checker = build_film_prompt, validate_film
    elif fmt == "stickman":
        builder, checker = build_story_prompt, validate_story
    else:
        builder, checker = build_prompt, validate
    error = None
    for attempt in range(3):
        reply = ask_claude(builder(cfg, prompt_topic, past, error), cfg)
        try:
            data = extract_json(reply)
            checker(data)
            break
        except Exception as e:  # noqa: BLE001
            error = str(e)
            print(f"  attempt {attempt + 1} invalid: {error}")
    else:
        raise SystemExit(f"Claude did not return a valid script: {error}")

    slug = slugify(data["title"])
    data["slug"] = slug
    data["topic"] = topic
    data["format"] = fmt
    if plan:
        data["plan"] = plan
    data.setdefault("tags", [])
    write_json(video_dir(slug) / "script.json", data)
    if fmt == "cinematic":
        from film import write_prompts
        write_prompts(slug)
        print(f"  shot list -> videos/{slug}/shotlist.md")
    add_history({"slug": slug, "title": data["title"], "topic": topic, "format": fmt, "status": "scripted"})
    print(f"  script -> videos/{slug}/script.json  ({data['title']})")
    return slug


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--format", choices=["cinematic", "stickman", "facts"], help="override config video.format")
    a = ap.parse_args()
    generate(a.topic, a.format)
    sys.exit(0)
