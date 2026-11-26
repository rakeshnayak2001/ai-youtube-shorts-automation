"""yt-factory runner: exactly one video per day, cinematic when Flow credits allow, stickman otherwise.

Daily (scheduled):
    python run.py --daily-start     # 2:00 PM: plan a timely topic; start today's film (script + shot list)
                                    #          or, if no account has credits, make today's stickman video
    python run.py --daily-finish    # 4:30 PM: render + upload the film whose clips are ready;
                                    #          if the clips aren't ready, make a stickman video instead
    python run.py --daily-extra     # one-off extra video (finish a ready film, else stickman)
    (the Claude scheduled task at 2:20 PM generates the film's clips in Google Flow in between)

Manual:
    python run.py --slug <slug>             # voice/render/upload an existing script (clips must be present)
    python run.py --topic "..." --format stickman --no-upload
    python run.py --format cinematic        # script a film now (then /film-clips <slug> in Claude Code)

Formats never mix: separate topic queues, channel text, voices, output folders and YouTube channels.
"""
import argparse
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from common import (add_history, load_config, load_history, mark_todays_video, next_idea, read_json,  # noqa: E402
                    todays_video, video_dir)
from generate import generate  # noqa: E402
from render import render  # noqa: E402
from tts import make_voice  # noqa: E402
from upload import upload  # noqa: E402

OUT_OF_CREDITS = 3  # exit code of veo_api.py when quota/billing is exhausted
HERE = Path(__file__).parent


# ---------------------------------------------------------------- helpers
def pending_films() -> tuple[list[str], list[str]]:
    """Cinematic films waiting for clips: (complete -> ready to render, still missing clips), oldest first."""
    from film import clip_status
    ready, waiting = [], []
    for h in load_history():
        if h.get("status") != "needs_clips" or not (video_dir(h["slug"]) / "script.json").exists():
            continue
        _, missing = clip_status(h["slug"])
        (waiting if missing else ready).append(h["slug"])
    return ready, waiting


def film_affordable(cfg: dict) -> bool:
    import credits
    shots = int(cfg.get("cinematic", {}).get("shots", 10))
    ok = credits.can_afford(shots)
    if ok is False:
        print(f"  Flow credits low on every account {credits.accounts()} (a film needs ~{credits.film_cost(shots)}).")
    return ok is not False


def finish(slug, do_upload=True, fake_voice=False):
    """Voice + render + upload one script. Returns the slug."""
    cfg = load_config()
    print(f"  voice   - {slug}")
    make_voice(slug, fake_voice)
    print("  render")
    outputs = render(slug)
    script = read_json(video_dir(slug) / "script.json")
    entry = {"slug": slug, "title": script["title"], "topic": script.get("topic", ""),
             "format": script.get("format"), "status": "rendered", "files": outputs}
    if do_upload and cfg["upload"].get("enabled", True):
        print("  upload")
        urls = [u for u in (upload(slug, f) for f in outputs) if u]
        if urls:
            entry.update(status="uploaded", urls=urls)
    add_history(entry)
    return slug


def make_stickman(do_upload=True, fake_voice=False, topic=None, use_planner=True):
    """Today's stickman video: own topic queue, own channel identity, own folder/channel."""
    from topics import consume, plan
    p = {"topic": topic, "from_queue": False} if topic else plan("stickman", use_planner)
    print(f"\n== stickman video: {p.get('topic') or '(Claude picks)'}")
    slug = generate(p.get("topic"), "stickman", p if p.get("event") else None)
    consume(p, "stickman", "made")
    return finish(slug, do_upload, fake_voice)


def start_film(do_upload=True, fake_voice=False, topic=None, use_planner=True):
    """Script today's film. With the API engine, also generate clips and finish it right away."""
    from film import clip_status, write_prompts
    from topics import consume, plan
    cfg = load_config()
    p = {"topic": topic, "from_queue": False} if topic else plan("cinematic", use_planner)
    print(f"\n== cinematic film: {p.get('topic') or '(Claude picks)'}")
    slug = generate(p.get("topic"), "cinematic", p if p.get("event") else None)
    consume(p, "cinematic", "filmed")
    write_prompts(slug)
    script = read_json(video_dir(slug) / "script.json")
    add_history({"slug": slug, "title": script["title"], "topic": script.get("topic", ""),
                 "format": "cinematic", "status": "needs_clips"})
    if cfg.get("cinematic", {}).get("engine") == "api":
        r = subprocess.run([sys.executable, str(HERE / "scripts" / "veo_api.py"), slug])
        if r.returncode == OUT_OF_CREDITS:
            print("  Gemini API quota ran out; the film waits for credits.")
            return None
        r.check_returncode()
        if not clip_status(slug)[1]:
            return finish(slug, do_upload, fake_voice)
    print(f"  shot list ready: videos/{slug}/shotlist.md  (clips: Claude task at 2:20 PM or /film-clips {slug})")
    return None


# ---------------------------------------------------------------- daily modes
def daily_start(do_upload=True, fake_voice=False):
    cfg = load_config()
    done = todays_video()
    if done:
        print(f"Today's video is already done: {done}")
        return
    ready, waiting = pending_films()
    if ready or waiting:
        print(f"A film is in progress (ready: {ready}, waiting for clips: {waiting}); "
              "the 4:30 PM run will publish it (or a stickman video if its clips aren't ready).")
        return
    if cfg["video"].get("format") == "cinematic" and film_affordable(cfg):
        slug = start_film(do_upload, fake_voice)
        if slug:  # API engine finished it already
            mark_todays_video(slug, "cinematic")
        return
    slug = make_stickman(do_upload, fake_voice)
    mark_todays_video(slug, "stickman")


def daily_finish(do_upload=True, fake_voice=False):
    done = todays_video()
    if done:
        print(f"Today's video is already done: {done}")
        return
    ready, waiting = pending_films()
    if ready:
        print(f"\n== finishing film {ready[0]}")
        slug = finish(ready[0], do_upload, fake_voice)
        mark_todays_video(slug, "cinematic")
        return
    if waiting:
        print(f"Film {waiting[0]} still needs clips; it will be finished on a later day.")
    slug = make_stickman(do_upload, fake_voice)
    mark_todays_video(slug, "stickman")


def daily_extra(do_upload=True, fake_voice=False):
    """One-off extra video (doesn't use up today's daily slot): finish a film whose clips are ready,
    otherwise make a stickman video."""
    ready, _ = pending_films()
    if ready:
        print(f"\n== extra video: finishing film {ready[0]}")
        finish(ready[0], do_upload, fake_voice)
        return
    print("\n== extra video: no film ready, making a stickman video")
    make_stickman(do_upload, fake_voice)


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-start", action="store_true")
    ap.add_argument("--daily-finish", action="store_true")
    ap.add_argument("--daily-extra", action="store_true", help="one-off extra video (not counted as today's)")
    ap.add_argument("--topic")
    ap.add_argument("--slug")
    ap.add_argument("--format", choices=["cinematic", "stickman", "facts"])
    ap.add_argument("--no-plan", action="store_true", help="skip the event-aware topic planner")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--fake-voice", action="store_true", help="silent voice for offline tests")
    a = ap.parse_args()
    up = not a.no_upload
    try:
        if a.daily_start:
            daily_start(up, a.fake_voice)
        elif a.daily_finish:
            daily_finish(up, a.fake_voice)
        elif a.daily_extra:
            daily_extra(up, a.fake_voice)
        elif a.slug:
            from film import clip_status
            script = read_json(video_dir(a.slug) / "script.json")
            if script.get("format") == "cinematic" and clip_status(a.slug)[1]:
                raise SystemExit(f"Clips missing for shots {clip_status(a.slug)[1]} (run /film-clips {a.slug}).")
            finish(a.slug, up, a.fake_voice)
        else:
            fmt = a.format or load_config()["video"].get("format", "stickman")
            if fmt == "cinematic":
                start_film(up, a.fake_voice, a.topic, not a.no_plan)
            elif fmt == "stickman":
                make_stickman(up, a.fake_voice, a.topic, not a.no_plan)
            else:
                finish(generate(a.topic or next_idea("facts"), "facts"), up, a.fake_voice)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    print("\nDone.")


if __name__ == "__main__":
    main()
