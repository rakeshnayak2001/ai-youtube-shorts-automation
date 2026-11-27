---
description: Brainstorm new video topics and add them to ideas.csv
argument-hint: [how many, default 20] [optional theme]
---
Add new topics to ideas.csv. Request: $ARGUMENTS

- Read config.json (channel niche/audience) and the existing topics in ideas.csv and state/history.json so you don't repeat anything.
- Every topic must be a question ("Why...?", "How did...?") that has a real, verifiable answer and a natural story with a character, a problem and a surprising answer.
- Prefer questions people actually search for. Mix history, science and everyday things unless I gave a theme.
- Save tokens: if the `local-worker` MCP tools are available, have the worker draft about twice as many candidates (`worker_generate`, ask for JSON), then you pick the best, fix wording, drop anything you can't verify, and add your own if needed. Or run `python scripts/ideas.py <format> --n N`, which appends worker ideas directly; then review them.
- Append them to the format's queue (ideas_cinematic.csv / ideas_stickman.csv) with an empty status column (keep the header and existing rows). Default 20 topics.
- Show me the list you added.
