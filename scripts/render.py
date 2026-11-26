"""Render the video(s) for a slug with Remotion.

    python scripts/render.py <slug>                 # formats from config.json
    python scripts/render.py <slug> --format Wide
"""
import argparse
import os
import sys

import json
import shutil
import subprocess

from common import IS_WINDOWS, OUT, ROOT, load_config, out_dir, read_json, run, video_dir, which, write_json


def clip_seconds(p) -> float:
    r = subprocess.run([which("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json",
                        str(p)], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def film_props(slug: str, script: dict, cfg: dict, allow_missing: bool) -> dict:
    d = video_dir(slug)
    pub = ROOT / "public" / "films" / slug
    pub.mkdir(parents=True, exist_ok=True)
    clips, missing = [], []
    for i in range(1, len(script["scenes"]) + 1):
        src = d / "clips" / f"shot_{i:02d}.mp4"
        if not src.exists():
            missing.append(i)
            clips.append(None)
            continue
        dst = pub / src.name
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)
        clips.append({"src": f"films/{slug}/{src.name}", "seconds": round(clip_seconds(src), 3)})
    if missing and not allow_missing:
        raise SystemExit(f"Missing clips for shots {missing}. Generate them first "
                         f"(Claude Code: /film-clips {slug}) or render a preview with --allow-missing.")
    cin = cfg.get("cinematic", {})
    music = cin.get("music")
    return {"clips": clips, "clipVolume": cin.get("clip_audio_volume", 0.3),
            "musicSrc": f"music/{music}" if music and (ROOT / "public" / "music" / music).exists() else None,
            "musicVolume": cin.get("music_volume", 0.12), "letterbox": cin.get("letterbox", False)}


def render(slug: str, formats: list[str] | None = None, allow_missing: bool = False) -> list[str]:
    cfg = load_config()
    d = video_dir(slug)
    script = read_json(d / "script.json")
    fmt_name = script.get("format", cfg["video"].get("format"))
    story = fmt_name == "stickman"
    film = fmt_name == "cinematic"
    props = {
        "script": script,
        "timings": read_json(d / "timings.json"),
        "audioSrc": f"audio/{slug}.mp3",
        "theme": (cfg["video"].get("theme_presets", {}).get(fmt_name) or cfg["video"].get("theme", {})),
        "character": cfg.get("story", {}).get("character", {}),
    }
    if film:
        props["film"] = film_props(slug, script, cfg, allow_missing)
    props_path = d / "props.json"
    write_json(props_path, props)

    dest = out_dir(fmt_name)  # out/cinematic, out/stickman, ...
    npx = which("npx.cmd" if IS_WINDOWS else "npx")
    outputs = []
    default_formats = cfg.get("cinematic", {}).get("formats") if film else None
    for fmt in formats or default_formats or cfg["video"].get("formats", ["Short"]):
        out = dest / f"{slug}-{fmt.lower()}.mp4"
        comp = f"Story{fmt}" if story else f"Film{fmt}" if film else fmt
        run([npx, "remotion", "render", "src/index.ts", comp, str(out),
             f"--props={props_path}", "--codec=h264", "--crf=20"]
            + ([f"--browser-executable={os.environ['REMOTION_BROWSER']}"] if os.environ.get("REMOTION_BROWSER") else []),
            cwd=ROOT)
        print(f"  video -> {out.relative_to(ROOT)}")
        outputs.append(str(out))
    return outputs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--format", action="append")
    ap.add_argument("--allow-missing", action="store_true", help="preview with placeholders for missing clips")
    a = ap.parse_args()
    render(a.slug, a.format, a.allow_missing)
    sys.exit(0)
