---
description: Make one stickman story video, with a script review before rendering
argument-hint: [optional topic question]
---
Make one video for the channel.

Topic: $ARGUMENTS (if empty, use the next row in ideas.csv with a blank status).

1. Run `python scripts/generate.py --topic "<topic>"` (omit --topic when using ideas.csv). Note the slug it prints.
2. Open `videos/<slug>/script.json` and review it like an editor:
   - Is scene 1 a genuine hook (the most surprising moment), and scene 2 the question?
   - Does it read as a story with a problem, a twist and a satisfying answer?
   - Fact-check every claim with web search. Fix anything wrong or overstated; soften uncertain history ("historians think").
   - Settings, poses and props must match what the narration says and be from src/story/catalog.ts.
   Edit script.json directly with your fixes, then show me the final narration (one line per scene) and the title.
3. Run `python scripts/tts.py <slug>` then `python scripts/render.py <slug>`.
4. Tell me the output path in out/. Do NOT upload. If I say "upload it", run `python scripts/upload.py <slug>`.
