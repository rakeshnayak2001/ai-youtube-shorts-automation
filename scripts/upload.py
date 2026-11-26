"""Upload a rendered video to YouTube (YouTube Data API v3, free).

One-time setup: put your OAuth client file at secrets/client_secret.json (see README),
then run `python scripts/upload.py --auth` once to sign in. The token is saved to
secrets/token.json and reused by scheduled runs.

    python scripts/upload.py <slug>
    python scripts/upload.py <slug> --file out/<slug>-wide.mp4
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

from common import OUT, SECRETS, add_history, load_config, out_dir, read_json, video_dir

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT = SECRETS / "client_secret.json"


def token_path(fmt: str) -> Path:
    """One YouTube channel per format: secrets/token_cinematic.json, secrets/token_stickman.json."""
    return SECRETS / f"token_{fmt}.json"


def channel_linked(fmt: str) -> bool:
    return token_path(fmt).exists()


def get_service(fmt: str):
    TOKEN = token_path(fmt)
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CLIENT.exists():
            raise SystemExit("secrets/client_secret.json missing - see README 'YouTube upload setup'.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
        creds = flow.run_local_server(port=0)
    SECRETS.mkdir(exist_ok=True)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(slug: str, file: str | None = None) -> str:
    from googleapiclient.http import MediaFileUpload

    cfg = load_config()["upload"]
    script = read_json(video_dir(slug) / "script.json")
    fmt = script.get("format", "stickman")
    if not channel_linked(fmt):
        # never mix formats: a stickman video is never uploaded to the cinematic channel (and vice versa)
        print(f"  upload skipped: no YouTube channel linked for '{fmt}' videos "
              f"(run: python scripts/upload.py --auth --format {fmt}). The video stays in out/{fmt}/.")
        return ""
    path = Path(file) if file else out_dir(fmt) / f"{slug}-short.mp4"
    if not path.exists():
        raise SystemExit(f"{path} not found - render first.")
    is_short = "short" in path.name

    title = script["title"].strip()
    if is_short and cfg.get("add_shorts_tag", True) and "#shorts" not in title.lower():
        title = (title[:91] + " #Shorts") if len(title) > 91 else title + " #Shorts"
    desc = script.get("description", "").strip()
    if script.get("sources"):
        desc += "\n\nSources:\n" + "\n".join(f"- {s}" for s in script["sources"])
    tags = [t.strip("#") for t in script.get("tags", [])][:15]

    status = {
        "privacyStatus": cfg.get("privacy", "private"),
        "selfDeclaredMadeForKids": bool(cfg.get("made_for_kids", False)),
        # realistic AI-generated video must be disclosed on YouTube
        "containsSyntheticMedia": bool(cfg.get("contains_synthetic_media", False))
        or script.get("format") == "cinematic",
    }
    delay = float(cfg.get("publish_delay_hours", 0) or 0)
    if delay > 0:  # schedule: upload private, YouTube makes it public at publishAt
        at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=delay)
        status.update(privacyStatus="private", publishAt=at.strftime("%Y-%m-%dT%H:%M:%SZ"))

    body = {
        "snippet": {"title": title, "description": desc, "tags": tags,
                    "categoryId": str(cfg.get("category_id", "28"))},
        "status": status,
    }
    yt = get_service(fmt)
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(path), chunksize=-1, resumable=True,
                                                        mimetype="video/mp4"))
    print(f"  uploading {path.name} ...")
    resp = None
    while resp is None:
        prog, resp = req.next_chunk()
        if prog:
            print(f"    {int(prog.progress() * 100)}%")
    vid = resp["id"]
    url = f"https://youtu.be/{vid}"
    add_history({"slug": slug, "title": script["title"], "topic": script.get("topic", ""),
                 "status": "uploaded", "youtube_id": vid, "url": url,
                 "privacy": status["privacyStatus"],
                 "uploaded_at": dt.datetime.now().isoformat(timespec="seconds")})
    print(f"  uploaded -> {url} ({status['privacyStatus']})")
    return url


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--auth", action="store_true", help="only sign in and save the token")
    ap.add_argument("--format", choices=["cinematic", "stickman", "facts"], default="cinematic",
                    help="which channel to link with --auth (each format uploads to its own channel)")
    a = ap.parse_args()
    if a.auth:
        get_service(a.format)
        print(f"Signed in. '{a.format}' videos will upload to this channel ({token_path(a.format).name}).")
    elif a.slug:
        upload(a.slug, a.file)
    else:
        ap.error("give a slug or --auth")
    sys.exit(0)
