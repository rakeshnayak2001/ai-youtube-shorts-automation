---
description: Make one cinematic AI film end to end (script, Google Flow clips, voice, render)
argument-hint: [topic]
---
Make one cinematic film. Topic: $ARGUMENTS (if empty, use the next blank-status row in ideas.csv).
config.json has video.format = "cinematic". Read config.json → cinematic and channel first.

1. **Script**: `python scripts/generate.py --topic "<topic>"` (omit --topic for ideas.csv). Note the slug.
2. **Edit like a director** (open `videos/<slug>/script.json`):
   - Fact-check the story with web search against the sources; fix anything wrong; name the source text where it matters.
   - Shot 1 must be a real hook. Every narration line ≤ 20 words (it must fit its clip).
   - Follow every rule in `cinematic.content_rules` (deity faces, no gore, respect). Fix any shot that breaks one.
   - Visuals: one simple continuous action per shot, varied framing, character `look` texts detailed and consistent.
   - Save, then run `python scripts/film.py prompts <slug>`. Show me the title and the narration, one line per shot.
3. **Clips**: follow `.claude/commands/film-clips.md` for this slug (generate every missing shot in Google Flow).
4. **Voice + render**: `python scripts/tts.py <slug>` then `python scripts/render.py <slug>`.
5. Report: output file in out/, Flow credits used and remaining, and any shots you think should be redone.
   Do NOT upload. If I say "upload it", run `python scripts/upload.py <slug>` (it marks the video as AI-generated).
