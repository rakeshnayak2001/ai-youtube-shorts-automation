# ai-youtube-shorts-automation: AI video channel pipeline

Three formats, chosen by `config.json -> video.format`:
- **"cinematic"** (current): short AI films. Shots are generated with Google Veo / Gemini Omni in **Google Flow**
  (the user's Google AI Pro account) or through the Gemini API, then assembled here with narration and captions.
- "stickman": free, code-drawn stick-figure stories (Tiko). "facts": motion-graphics explainers.

## Cinematic pipeline
```
generate.py (claude -p writes script.json: style, characters, shots) -> film.py prompts (shotlist.md, prompts.json)
-> clips: /film-clips in Google Flow (built-in browser) + collect.py  |  or veo_api.py (Gemini API, paid per second)
-> tts.py (narrator) -> render.py (FilmShort 1080x1920 / FilmWide 1920x1080) -> upload.py (private, AI-disclosed)
```
- Commands: `/make-film [topic]` (everything), `/film-clips <slug>` (only the Flow clips), `/new-topics`.
- Clips live in `videos/<slug>/clips/shot_NN.mp4`; render.py copies them to `public/films/<slug>/`.
- Preview with missing clips: `python scripts/render.py <slug> --allow-missing`.
- Flow: never type passwords; stop on sign-in/payment/CAPTCHA pages; 1 output per prompt; max 1 redo per shot.
- Always follow `cinematic.content_rules` (no deity faces, no gore, respectful tone).
- **One video per day**: `run.py --daily-start` (2 PM) and `--daily-finish` (4:30 PM); state in `state/daily.json`.
  Film if any Flow account can afford it (`scripts/credits.py`, per account), else stickman. The 2:20 PM Claude
  scheduled task generates clips in Flow and can switch between two Google AI Pro accounts.
- **Formats never mix**: separate topic queues (`ideas_<format>.csv`), `config.json` channels/voices/theme_presets,
  output folders (`out/<format>/`), YouTube tokens (`secrets/token_<format>.json`). Never upload a format to another's channel.
- **Timely topics**: `scripts/topics.py plan <format>` (claude -p + web search for upcoming festivals/events) feeds
  `generate(topic, fmt, plan)`, which adds the event angle and keywords to the script prompt.

## Master / worker models (token saving)
- **Claude = master**: scripts, fact-checks, timely topics (web search), decisions, review.
- **Local Ollama model = worker**: repetitive jobs. Routed per task in `config.json -> llm.tasks`
  (`script`, `topic_plan`, `json_repair`, `ideas`; values `claude`, `claude:<model>`, `local`, `local:<model>`).
  All pipeline LLM calls go through `scripts/llm.py` (`llm.ask(task, prompt)`); usage is logged to `state/llm_usage.json`.
- In chat sessions, the `local-worker` MCP server (`tools/local_worker_mcp.py`, `.mcp.json`) gives you
  `worker_generate`, `worker_generate_to_file`, `worker_batch`. Use them for bulk/boring text (topic lists, rewording,
  reformatting); test the instruction on one item first, spot-check results, never trust it for facts.
- **Gemini worker** (optional): task value `gemini` / `gemini:<model>` calls the Gemini API with up to two Google AI Studio keys
  (failover on 429), through the separate **agent-squad** repo (found when pip-installed, at `llm.squad_path`, or at
  `../agent-squad`). Without agent-squad the app still works and Gemini tasks fall back to Claude. MCP tools take `worker="gemini"`.
- If the worker is down, `llm.fallback_to_claude` sends its tasks to Claude.
- Dashboard: `python dashboard/server.py` (or `dashboard.bat`) -> http://127.0.0.1:8765. Worker setup: `setup_local_llm.bat`.

## Stickman pipeline

A faceless channel pipeline. Every video stars the same stick figure (Tiko) and answers one
"why/how" question as a short story. Everything is free apart from Claude Code itself.

```
ideas.csv -> generate.py (claude -p writes script.json) -> tts.py (edge-tts voice + word timings)
          -> render.py (Remotion) -> out/<slug>-short.mp4 -> upload.py (YouTube API, private)
```

## Slash commands (use these)
- `/make-video [topic]`: script, then your editorial review + fact-check, then voice and render. No upload.
- `/review-script <slug>`: fact-check and tighten an existing script.
- `/batch [n]`: several videos in a row, reviewed, not uploaded.
- `/new-topics [n] [theme]`: add question topics to ideas.csv.
- `/add-asset <thing>`: draw a new setting/pose/prop and register it in the catalogue.

## Files
- `scripts/llm.py`: model router (Claude master / local worker). `scripts/ideas.py <format> --n N`: worker brainstorms topics.
- `dashboard/`: local control-room UI (stdlib server + one HTML file).
- `run.py`: `--daily-start` / `--daily-finish` (scheduled), or manual `--slug S`, `--topic T --format F`, `--no-upload`, `--no-plan`
- `config.json`: channel niche/audience/CTA, `video.format` ("stickman" or "facts"), voice, character look, upload settings.
- `scripts/generate.py`: prompts + validation. Story prompt = `build_story_prompt`.
- `src/story/catalog.ts`: **single source of truth** for allowed settings/poses/moods/props. generate.py parses it.
- `src/story/Stickman.tsx`: the character (pose definitions in `poseAt`, faces, hair, tunic).
- `src/story/Backgrounds.tsx`, `src/story/Props.tsx`: scenery and objects, all drawn as SVG in code.
- `src/story/StoryVideo.tsx`: scene layout (camera push-in, labels, question card, captions).
- `src/Video.tsx` + `src/scenes/`: the older "facts" motion-graphics format (still works with `video.format = "facts"`).
- Compositions: `StoryShort` 1080x1920, `StoryWide` 1920x1080, `Short`, `Wide`.

## Script schema (stickman)
`{title, description, tags[], sources[], format: "stickman", scenes: [...]}`. Scene: `type` "story" | "question",
`narration` (spoken), plus optional `setting, time, pose, mood, position, facing, hold, props[≤2], overhead, crowd(0-3), label(≤4 words)`.
Question scenes also need `question`. Scene 1 = hook, scene 2 = question.

## Rules
- Accuracy first: fact-check every script before rendering; never invent dates, names or numbers.
- Keep Tiko's look consistent: change it only in config.json `story.character`.
- Preview visuals with `npx remotion still src/index.ts StoryShort out/preview.png --frame=N` and look at the PNG; use `npm run studio` for live preview.
- Never upload without the user saying so (uploads go up as private anyway).
- After editing TSX, run `npx tsc --noEmit`.
