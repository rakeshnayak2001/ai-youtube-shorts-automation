---
description: Generate the missing clips for a film in Google Flow (built-in browser) and collect them
argument-hint: <slug>
---
Generate the missing video clips for `videos/$ARGUMENTS/` in Google Flow, using my Google AI Pro account.

Rules:
- Use the **built-in browser** (Claude_Browser tools). If it isn't available, use Claude in Chrome.
- You can have several Google AI Pro accounts signed in: account 1 is https://flow.google.com/u/0/, account 2 is
  https://flow.google.com/u/1/ (see `python scripts/credits.py show` for the emails). Record credits per account with
  `python scripts/credits.py set <n> --account <email> --resets <date>`; switch accounts when one runs low.
- I'm already signed in. **Never type passwords.** If a sign-in, payment, CAPTCHA, "unusual activity" or
  terms page appears, stop and ask me to handle it, then continue.
- Spend credits carefully: 1 output per prompt, the cheapest model on the preference list, at most 1 redo per shot.

Steps:
1. `python scripts/film.py status $ARGUMENTS` → list of missing shots. Prompts are in `videos/$ARGUMENTS/prompts.json`.
2. Open https://flow.google.com. Check my remaining credits (profile menu) and the next refresh date if shown, and
   record them: `python scripts/credits.py set <credits> [--resets YYYY-MM-DD]`. Tell me the number.
   Estimate the cost (missing shots × the model's per-clip cost shown in Flow, +30% for redos). If there aren't
   enough credits, stop: leave the film waiting (it is finished after the refresh) and say so. The next run of
   `python run.py` will automatically make a stickman video instead while credits are low.
3. Create a new project named after the slug (or reopen it if it already exists).
4. Choose video generation (text to video), then pick the model: the first one available from
   `cinematic.flow_model_preference` in config.json. Set the aspect ratio to `cinematic.aspect`, the clip length to
   the shot's `seconds` if Flow lets you choose, and outputs per prompt to 1.
5. For each missing shot, in order, ONE AT A TIME:
   a. Paste the shot's `prompt` exactly as written and generate. Wait for it to finish (check every ~15 s).
   b. Look at the result (screenshot). Reject it if the character doesn't match the description, captions or other
      text appear in the scene (the small "Veo" mark in the bottom-right corner is required in India: expected, never remove it), bodies are distorted, or a content rule is broken (e.g. a deity's face is shown).
      If rejected, regenerate once with a small fix to the prompt; keep the better of the two.
   c. Download it (720p / original quality). Then immediately run
      `python scripts/collect.py $ARGUMENTS --shot <N>` and check it says the shot was placed.
      If the browser saved the file somewhere other than my Downloads folder, find it and use `--src "<path>"`.
6. When done, re-read the credits in Flow and record them again with `python scripts/credits.py set <credits>`.
   If Flow says credits ran out part-way, record `0` and stop. Run `python scripts/film.py status $ARGUMENTS`
   and tell me the credits used and remaining, plus which shots you redid and why.

Optional, for better consistency: if Flow offers reference images / "ingredients" on my plan, first create one
reference image per character from its `look` text (Nano Banana) and attach it to every shot showing that character.
