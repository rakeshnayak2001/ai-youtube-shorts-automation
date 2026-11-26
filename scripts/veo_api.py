"""Generate missing clips through the Gemini API (fully automatic, pay per second).

Uses Gemini Omni Flash (the Gemini API's video model since the Veo preview models were retired).
Approx. cost: $0.10 per second of 720p video -> ~$0.80 per 8-second shot, ~$8 for a 10-shot film.
Google AI Pro includes a monthly Google Cloud credit (claim it in Google AI Studio) that can cover some of this.

Setup: create an API key in https://aistudio.google.com (Get API key), enable billing on its project, then
put the key in secrets/gemini_api_key.txt (or set GEMINI_API_KEY).

    python scripts/veo_api.py <slug>            # all missing shots
    python scripts/veo_api.py <slug> --shots 2,5
    python scripts/veo_api.py <slug> --dry-run  # show prompts + cost estimate only
"""
import argparse
import base64
import os
import sys
import time
from pathlib import Path

from common import ROOT, SECRETS, load_config, read_json, video_dir
from film import clip_status, write_prompts

class CreditsExhausted(RuntimeError):
    """API quota or billing ran out: the pipeline falls back to the stickman format."""


QUOTA_WORDS = ("RESOURCE_EXHAUSTED", "quota", "billing", "429", "insufficient", "credit")

PRICE_PER_SECOND = 0.10  # USD, 720p, check https://ai.google.dev/gemini-api/docs/pricing


def api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    f = SECRETS / "gemini_api_key.txt"
    if not key and f.exists():
        key = f.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("No Gemini API key. Put it in secrets/gemini_api_key.txt (see README, 'API engine').")
    return key


def ref_images(script: dict, shot: dict) -> list[tuple[str, Path]]:
    """Character reference images: characters/<id>.png|jpg in the video folder or the project root."""
    out = []
    for cid in shot.get("characters", []):
        candidates = [base / f"{cid}{ext}"
                      for base in (video_dir(script["slug"]) / "characters", ROOT / "characters")
                      for ext in (".png", ".jpg", ".jpeg")]
        found = next((p for p in candidates if p.exists()), None)
        if found:
            out.append((cid, found))
    return out


def generate_clip(client, model: str, prompt: str, refs: list[tuple[str, Path]], aspect: str,
                  resolution: str, dst: Path) -> None:
    if refs:
        tags = " ".join(f"<IMAGE_REF_{i}> is {cid}." for i, (cid, _) in enumerate(refs))
        parts = [{"type": "image", "data": base64.b64encode(p.read_bytes()).decode(),
                  "mime_type": "image/png" if p.suffix == ".png" else "image/jpeg"} for _, p in refs]
        inp = parts + [{"type": "text", "text": f"{tags} {prompt}"}]
    else:
        inp = prompt
    interaction = client.interactions.create(
        model=model,
        input=inp,
        response_format={"type": "video", "delivery": "uri", "aspect_ratio": aspect, "resolution": resolution},
    )
    video = interaction.output_video
    name = video.uri.split("/")[-1]
    while True:
        info = client.files.get(name=f"files/{name}")
        if info.state.name == "ACTIVE":
            break
        if info.state.name == "FAILED":
            raise RuntimeError("generation failed")
        time.sleep(5)
    dst.parent.mkdir(exist_ok=True)
    client.files.download(file=video.uri, destination=str(dst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--shots", help="comma list, default: all missing")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = load_config().get("cinematic", {})
    d = video_dir(a.slug)
    script = read_json(d / "script.json")
    script["slug"] = a.slug
    rows = write_prompts(a.slug)
    _, missing = clip_status(a.slug)
    todo = [int(x) for x in a.shots.split(",")] if a.shots else missing
    secs = sum(rows[i - 1]["seconds"] for i in todo)
    print(f"  {len(todo)} shots, ~{secs}s of video, est. ${secs * PRICE_PER_SECOND:.2f}")
    if a.dry_run or not todo:
        return

    from google import genai
    client = genai.Client(api_key=api_key())
    model = cfg.get("api_model", "gemini-omni-1.1-flash")
    for i in todo:
        shot = script["scenes"][i - 1]
        dst = d / "clips" / f"shot_{i:02d}.mp4"
        for attempt in range(2):
            try:
                print(f"  shot {i:02d}: generating...")
                generate_clip(client, model, rows[i - 1]["prompt"], ref_images(script, shot),
                              cfg.get("aspect", "9:16"), cfg.get("api_resolution", "720p"), dst)
                print(f"  shot {i:02d}: saved")
                break
            except Exception as e:  # noqa: BLE001
                print(f"  shot {i:02d}: attempt {attempt + 1} failed: {e}")
                if any(w.lower() in str(e).lower() for w in QUOTA_WORDS):
                    raise CreditsExhausted(str(e)) from e
                if attempt == 1:
                    raise


if __name__ == "__main__":
    try:
        main()
    except CreditsExhausted as e:
        print(f"  API quota/billing exhausted: {e}")
        sys.exit(3)  # run.py treats exit code 3 as "out of credits"
    sys.exit(0)
