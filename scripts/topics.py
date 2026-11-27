"""Pick a timely topic: checks upcoming festivals, anniversaries and events so videos ride search buzz.

    python scripts/topics.py plan cinematic     # prints a JSON plan and saves it to state/plans/
    python scripts/topics.py plan stickman

Uses headless Claude Code with web search (your subscription). Falls back to the next queued topic.
"""
import argparse
import datetime as dt
import json
import sys

from common import (STATE, channel_for, load_config, load_history, mark_idea, next_idea, queued_ideas,
                    write_json)


def plan_prompt(cfg: dict, fmt: str) -> str:
    ch = channel_for(cfg, fmt)
    t = cfg.get("topics", {})
    days = int(t.get("lookahead_days", 14))
    region = t.get("region", "India")
    today = dt.date.today()
    queue = queued_ideas(fmt)[:40]
    past = [h.get("title", "") for h in load_history()][-40:]
    style = ("a short cinematic AI film (8-second shots, epic visuals, a narrator)" if fmt == "cinematic"
             else "a stick-figure story video answering one 'why' or 'how' question")
    return f"""You plan topics for a YouTube Shorts channel. Today is {today:%A %d %B %Y}. Audience region: {region}.

Channel niche: {ch['niche']}
Audience: {ch['audience']}
Video type: {style}

Use web search to find what is coming up in the next {days} days that this audience will be searching for:
festivals and religious observances (exact dates for this year), anniversaries and jayantis, national days,
big film/series releases, sports events and news moments, as long as they connect NATURALLY to the niche.
Then choose ONE topic for today's video:
- It must fit the niche and be a story the channel can tell accurately (well-documented, not a rumour).
- Prefer a timely hook (event within the next {days} days) with real search interest; avoid tragedies,
  politics and anything that would feel exploitative.
- If a topic from the queue fits an upcoming event, use it word-for-word. Queue: {json.dumps(queue, ensure_ascii=False)}
- Never repeat these past videos: {json.dumps(past, ensure_ascii=False)}
- If nothing timely fits, pick the strongest evergreen topic from the queue.

Output ONLY this JSON (no markdown):
{{"topic": "the question or story to make", "from_queue": true or false, "event": "event name or empty",
  "event_date": "YYYY-MM-DD or empty", "why_now": "one sentence", "title_idea": "a clickable, honest title under 70 chars",
  "keywords": ["5-8 search keywords people use for this event/topic"]}}"""


def plan(fmt: str, use_claude: bool = True) -> dict:
    cfg = load_config()
    fallback = {"topic": next_idea(fmt), "from_queue": True, "event": "", "keywords": []}
    if not use_claude or not cfg.get("topics", {}).get("plan_with_events", True):
        return fallback
    from generate import ask_claude, extract_json
    try:
        data = extract_json(ask_claude(plan_prompt(cfg, fmt), cfg, "topic_plan"))
        if not data.get("topic"):
            raise ValueError("no topic")
    except BaseException as e:  # noqa: BLE001 (SystemExit from ask_claude included)
        print(f"  topic planner failed ({e}); using the next queued topic")
        return fallback
    if data["topic"] in queued_ideas(fmt):
        data["from_queue"] = True
    else:
        data["from_queue"] = False
    write_json(STATE / "plans" / f"{dt.date.today().isoformat()}-{fmt}.json", data)
    print(f"  topic: {data['topic']}" + (f"  (for {data['event']} on {data.get('event_date')})" if data.get("event") else ""))
    return data


def consume(plan_: dict, fmt: str, status: str) -> None:
    if plan_.get("from_queue") and plan_.get("topic"):
        mark_idea(plan_["topic"], status, fmt)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan"])
    ap.add_argument("format", choices=["cinematic", "stickman", "facts"])
    a = ap.parse_args()
    print(json.dumps(plan(a.format), indent=2, ensure_ascii=False))
    sys.exit(0)
