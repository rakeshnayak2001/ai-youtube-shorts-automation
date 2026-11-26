"""Cinematic film format: script prompt, validation, and per-shot video prompts.

    python scripts/film.py prompts <slug>   # (re)write videos/<slug>/shotlist.md + prompts.json
    python scripts/film.py status <slug>    # which clips exist / are missing
"""
import argparse
import json
import sys

from common import load_config, read_json, video_dir, write_json

ALLOWED_SECONDS = (4, 6, 8)
NO_TEXT = "No on-screen text, no subtitles, no captions, no watermark, no logos."


def build_film_prompt(cfg: dict, topic: str, past_titles: list[str], error: str | None) -> str:
    ch = cfg["channel"]
    cin = cfg.get("cinematic", {})
    n = int(cin.get("shots", 10))
    secs = int(cin.get("clip_seconds", 8))
    rules = "\n".join(f"- {r}" for r in cin.get("content_rules", []))
    prompt = f"""You are the writer-director of a faceless cinematic storytelling channel on YouTube.
Every video is a short AI-generated film: a sequence of {secs}-second shots with a narrator's voice-over.

Channel: {ch['niche']}
Audience: {ch['audience']}
Narration language: {ch['language']}
Tone: {ch['style']}
Topic: {topic}

STORY
- Shot 1 is the hook: the most dramatic or surprising moment, shown before any explanation.
- Then build the story: who, what they want, what goes wrong, the turning point, the surprising answer.
- The final shot lands the ending; its narration ends with: "{ch['cta']}"
- Exactly {n} shots. Each narration line is spoken over its shot: max 20 words (it must fit {secs} seconds).
- Accuracy: retell the story as the sources tell it. Say which text or tradition it comes from where that matters
  (e.g. "in the Skanda Purana..."). Never invent names, places or events. List sources.

VISUALS (each shot becomes one prompt for Google Veo / Gemini Omni video generation)
- Write a "style" line used unchanged for every shot: medium, era, palette, lighting, lens, mood.
- Define every recurring character once in "characters" with an exact, detailed visual description
  (age, build, skin, face, hair, clothing with colours, ornaments, weapons). This exact text is pasted
  into every shot so the character looks the same each time. Max 3 characters.
- For each shot: "visual" = what happens on screen in one continuous {secs}-second take (one action, one place),
  "camera" = framing and movement, "sound" = ambient sound effects and music mood (no speech),
  "characters" = ids of the characters visible.
- Optional "dialogue": one short line (max 12 words) a visible character speaks on screen. Use it for at most
  2 key moments; for those shots set "narration" to "".
- Make shots visually varied (wide establishing shots, close-ups, aerials, details) and physically simple:
  avoid crowds fighting in close detail, text, hands doing intricate things.
{rules}

Output ONE JSON object exactly like this:
{{
  "title": "YouTube title, max 90 chars, curiosity-driven, honest",
  "description": "2-3 short lines",
  "tags": ["5-10 lowercase tags"],
  "sources": ["text, publication or URL"],
  "style": "cinematic photoreal ..., 35mm anamorphic, warm firelight, film grain",
  "characters": [{{"id": "short_id", "name": "Name", "look": "exact visual description"}}],
  "scenes": [
    {{"type": "shot", "narration": "...", "visual": "...", "camera": "...", "sound": "...", "characters": ["short_id"], "seconds": {secs}}}
  ]
}}
Do not repeat these existing titles: {json.dumps(past_titles[-30:], ensure_ascii=False)}
Output ONLY the JSON object. No markdown fences, no commentary."""
    if error:
        prompt += f"\n\nYour previous attempt was invalid: {error}\nFix it and output only valid JSON."
    return prompt


def validate_film(data: dict) -> None:
    for k in ("title", "description", "style", "characters", "scenes"):
        if k not in data:
            raise ValueError(f"missing key '{k}'")
    ids = {c.get("id") for c in data["characters"]}
    if None in ids or len(data["characters"]) > 4:
        raise ValueError("characters need an 'id' each (max 4 characters)")
    for c in data["characters"]:
        if len(c.get("look", "")) < 40:
            raise ValueError(f"character '{c['id']}' needs a detailed 'look' (40+ chars)")
    shots = data["scenes"]
    if not isinstance(shots, list) or not 4 <= len(shots) <= 40:
        raise ValueError("scenes must be a list of 4-40 shots")
    for i, s in enumerate(shots):
        s["type"] = "shot"
        if not s.get("visual"):
            raise ValueError(f"shot {i + 1}: missing 'visual'")
        if not s.get("narration") and not s.get("dialogue"):
            raise ValueError(f"shot {i + 1}: needs narration or dialogue")
        if len(str(s.get("narration", "")).split()) > 24:
            raise ValueError(f"shot {i + 1}: narration too long (max ~20 words)")
        if s.get("seconds") not in ALLOWED_SECONDS:
            s["seconds"] = 8
        bad = [c for c in s.get("characters", []) if c not in ids]
        if bad:
            raise ValueError(f"shot {i + 1}: unknown character ids {bad}")
    if len(data["title"]) > 100:
        raise ValueError("title longer than 100 characters")


def shot_prompt(script: dict, shot: dict) -> str:
    chars = {c["id"]: c for c in script.get("characters", [])}
    parts = [script.get("style", "").strip().rstrip(".") + "."]
    parts.append(shot["visual"].strip().rstrip(".") + ".")
    if shot.get("camera"):
        parts.append(f"Camera: {shot['camera'].strip().rstrip('.')}.")
    for cid in shot.get("characters", []):
        c = chars.get(cid)
        if c:
            parts.append(f"{c['name']}: {c['look'].strip().rstrip('.')}.")
    if shot.get("dialogue"):
        speaker = chars.get((shot.get("characters") or [None])[0], {}).get("name", "The character")
        parts.append(f'{speaker} says, clearly and slowly: "{shot["dialogue"]}"')
        if shot.get("sound"):
            parts.append(f"Background sound: {shot['sound'].strip().rstrip('.')}.")
    else:
        sound = shot.get("sound", "ambient sound").strip().rstrip(".")
        parts.append(f"Audio: {sound}. No speech, no dialogue, no voice-over.")
    parts.append(NO_TEXT)
    return " ".join(p for p in parts if p.strip(" ."))


def write_prompts(slug: str) -> list[dict]:
    cfg = load_config().get("cinematic", {})
    d = video_dir(slug)
    script = read_json(d / "script.json")
    aspect = cfg.get("aspect", "9:16")
    rows = []
    lines = [f"# {script['title']}", "", f"Aspect ratio: **{aspect}** · clip length: 4/6/8 s as listed · "
             f"{len(script['scenes'])} shots", "", "## Characters", ""]
    for c in script.get("characters", []):
        lines += [f"- **{c['name']}** (`{c['id']}`): {c['look']}"]
    lines += ["", "## Shots", ""]
    for i, s in enumerate(script["scenes"], 1):
        p = shot_prompt(script, s)
        rows.append({"shot": i, "file": f"shot_{i:02d}.mp4", "seconds": s.get("seconds", 8),
                     "aspect": aspect, "prompt": p})
        say = f'Dialogue: "{s["dialogue"]}"' if s.get("dialogue") else f"Narration: {s.get('narration', '')}"
        lines += [f"### Shot {i} ({s.get('seconds', 8)}s): save as `clips/shot_{i:02d}.mp4`", "", say, "",
                  "```", p, "```", ""]
    write_json(d / "prompts.json", rows)
    (d / "shotlist.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def clip_status(slug: str) -> tuple[list[int], list[int]]:
    d = video_dir(slug)
    script = read_json(d / "script.json")
    have, missing = [], []
    for i in range(1, len(script["scenes"]) + 1):
        (have if (d / "clips" / f"shot_{i:02d}.mp4").exists() else missing).append(i)
    return have, missing


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prompts", "status"])
    ap.add_argument("slug")
    a = ap.parse_args()
    if a.cmd == "prompts":
        rows = write_prompts(a.slug)
        print(f"wrote videos/{a.slug}/shotlist.md and prompts.json ({len(rows)} shots)")
    have, missing = clip_status(a.slug)
    print(f"clips present: {have or 'none'}")
    print(f"clips missing: {missing or 'none'}")
    sys.exit(0)
