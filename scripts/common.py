"""Shared helpers for the yt-factory pipeline."""
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = ROOT / "videos"
PUBLIC_AUDIO = ROOT / "public" / "audio"
OUT = ROOT / "out"
STATE = ROOT / "state"
SECRETS = ROOT / "secrets"
IS_WINDOWS = sys.platform.startswith("win")

# Windows consoles default to cp1252; make prints of titles/emoji safe everywhere
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "video"


def video_dir(slug: str) -> Path:
    d = VIDEOS / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def which(cmd: str) -> str:
    found = shutil.which(cmd)
    if not found:
        raise SystemExit(f"'{cmd}' not found on PATH. Install it first (see README).")
    return found


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("  $", " ".join(str(c) for c in cmd)[:200])
    return subprocess.run(cmd, check=True, **kw)


# ---------- formats are kept completely separate ----------
FORMATS = ("cinematic", "stickman", "facts")
IDEAS_FILES = {"cinematic": "ideas_cinematic.csv", "stickman": "ideas_stickman.csv", "facts": "ideas_facts.csv"}


def active_format(cfg: dict | None = None) -> str:
    return (cfg or load_config())["video"].get("format", "stickman")


def channel_for(cfg: dict, fmt: str) -> dict:
    """Channel description (niche, audience, style, CTA) for one format."""
    return (cfg.get("channels") or {}).get(fmt) or cfg["channel"]


def voice_for(cfg: dict, fmt: str | None) -> dict:
    return {**cfg["voice"], **((cfg.get("voices") or {}).get(fmt or "") or {})}


def out_dir(fmt: str | None) -> Path:
    """Finished videos: out/cinematic/, out/stickman/, out/facts/."""
    d = OUT / (fmt or "other")
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------- topic queues: one CSV per format ----------
def ideas_path(fmt: str | None = None) -> Path:
    fmt = fmt or active_format()
    return ROOT / IDEAS_FILES.get(fmt, f"ideas_{fmt}.csv")


def read_ideas(fmt: str | None = None) -> list[dict]:
    p = ideas_path(fmt)
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_ideas(rows: list[dict], fmt: str | None = None) -> None:
    with ideas_path(fmt).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["topic", "status"])
        w.writeheader()
        for r in rows:
            w.writerow({"topic": r.get("topic", ""), "status": r.get("status", "")})


def queued_ideas(fmt: str | None = None) -> list[str]:
    return [r["topic"] for r in read_ideas(fmt) if r.get("topic") and not (r.get("status") or "").strip()]


def next_idea(fmt: str | None = None) -> str | None:
    q = queued_ideas(fmt)
    return q[0] if q else None


def mark_idea(topic: str, status: str, fmt: str | None = None) -> None:
    rows = read_ideas(fmt)
    for r in rows:
        if r.get("topic") == topic:
            r["status"] = status
    write_ideas(rows, fmt)


# ---------- one video per day ----------
DAILY = STATE / "daily.json"


def today() -> str:
    import datetime as dt
    return dt.date.today().isoformat()


def todays_video() -> dict | None:
    d = read_json(DAILY) if DAILY.exists() else {}
    return d.get(today())


def mark_todays_video(slug: str, fmt: str) -> None:
    d = read_json(DAILY) if DAILY.exists() else {}
    d[today()] = {"slug": slug, "format": fmt}
    d = dict(sorted(d.items())[-60:])  # keep two months
    write_json(DAILY, d)


# ---------- history ----------
HISTORY = STATE / "history.json"


def load_history() -> list[dict]:
    return read_json(HISTORY) if HISTORY.exists() else []


def add_history(entry: dict) -> None:
    h = load_history()
    h = [e for e in h if e.get("slug") != entry.get("slug")]
    h.append(entry)
    write_json(HISTORY, h)
