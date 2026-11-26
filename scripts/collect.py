"""Move clips downloaded from Google Flow into videos/<slug>/clips/shot_NN.mp4.

    python scripts/collect.py <slug> --shot 3                 # newest .mp4 in Downloads -> shot_03.mp4
    python scripts/collect.py <slug> --shot 3 --src "C:/path/clip.mp4"
    python scripts/collect.py <slug> --all --since 45         # assign recent downloads (oldest first) to missing shots
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

from common import load_config, video_dir
from film import clip_status

VIDEO_EXT = {".mp4", ".mov", ".webm"}


def downloads_dirs() -> list[Path]:
    """Windows Downloads, plus the mount used by Claude's scheduled task (~/mnt/Downloads)."""
    raw = load_config().get("cinematic", {}).get("downloads_dir", ["~/Downloads", "~/mnt/Downloads"])
    dirs = [Path(r).expanduser() for r in ([raw] if isinstance(raw, str) else raw)]
    dirs.append(Path("~/mnt/Downloads").expanduser())
    seen, out = set(), []
    for d in dirs:
        if d.exists() and d.resolve() not in seen:
            seen.add(d.resolve())
            out.append(d)
    return out


def downloads_dir() -> Path:
    dirs = downloads_dirs()
    return dirs[0] if dirs else Path("~/Downloads").expanduser()


def mp4_complete(p: Path) -> bool:
    """True if the file is a whole MP4: its top-level boxes add up to the file size and include 'moov'.
    Lets us use a finished download even when the browser is still waiting for a save confirmation."""
    try:
        size = p.stat().st_size
        seen, pos = set(), 0
        with p.open("rb") as f:
            while pos < size:
                f.seek(pos)
                hdr = f.read(8)
                if len(hdr) < 8:
                    return False
                box = int.from_bytes(hdr[:4], "big")
                kind = hdr[4:8]
                if box == 1:
                    box = int.from_bytes(f.read(8), "big")
                elif box == 0:
                    box = size - pos
                if box < 8:
                    return False
                seen.add(kind)
                pos += box
        return pos == size and b"ftyp" in seen and b"moov" in seen and b"mdat" in seen
    except OSError:
        return False


def is_video(p: Path) -> bool:
    """Real video file? The built-in browser saves downloads as <uuid>.tmp, so sniff the MP4 header."""
    if p.suffix.lower() in VIDEO_EXT:
        return True
    if p.suffix.lower() in (".tmp", ""):
        try:
            with p.open("rb") as f:
                head = f.read(12)
            return head[4:8] == b"ftyp"
        except OSError:
            return False
    return False


def recent_videos(since_minutes: float) -> list[Path]:
    dirs = downloads_dirs()
    if not dirs:
        raise SystemExit("Downloads folder not found (set cinematic.downloads_dir in config.json)")
    cutoff = time.time() - since_minutes * 60
    files = [p for d in dirs for p in d.iterdir()
             if p.is_file() and p.stat().st_mtime >= cutoff and is_video(p)
             and not p.name.endswith((".crdownload", ".part"))]
    # a .tmp and its renamed .mp4 can both exist for a moment: keep one per size (prefer the .mp4)
    uniq = {}
    for f in sorted(files, key=lambda q: (q.suffix.lower() != ".mp4", -q.stat().st_mtime)):
        uniq.setdefault(f.stat().st_size, f)
    return sorted(uniq.values(), key=lambda p: p.stat().st_mtime)


def wait_stable(p: Path, timeout: float = 90) -> Path:
    """Wait until a download is a complete video. If the browser renames <uuid>.tmp to the final .mp4
    meanwhile (after a save confirmation), follow it. Returns the path to copy from."""
    t0 = time.time()
    size0 = p.stat().st_size if p.exists() else None
    while time.time() - t0 < timeout:
        if not p.exists():
            # renamed after confirmation: same-size video in the same folder
            twins = [q for q in p.parent.iterdir() if q.is_file() and q.suffix.lower() in VIDEO_EXT
                     and (size0 is None or q.stat().st_size == size0)]
            if twins:
                p = max(twins, key=lambda q: q.stat().st_mtime)
            else:
                time.sleep(1.5)
                continue
        if p.suffix.lower() in (".mov", ".webm"):
            return p
        if mp4_complete(p):
            return p
        time.sleep(1.5)
    raise SystemExit(f"Download did not complete within {timeout:.0f}s: {p.name}. "
                     "If a download confirmation pop-up is open in the Claude app, confirm it and retry.")


def place(slug: str, shot: int, src: Path) -> Path:
    dst = video_dir(slug) / "clips" / f"shot_{shot:02d}.mp4"
    dst.parent.mkdir(exist_ok=True)
    if src.resolve() == dst.resolve():
        print(f"  shot {shot:02d} already in place")
        return dst
    src = wait_stable(src)
    if src.suffix.lower() not in (".mp4", ".tmp", ""):
        import subprocess
        from common import which
        subprocess.run([which("ffmpeg"), "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "18", "-c:a", "aac", str(dst)], check=True)
    else:
        shutil.copy2(src, dst)
    print(f"  shot {shot:02d} <- {src.name}")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--shot", type=int)
    ap.add_argument("--src")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--since", type=float, default=30, help="only look at downloads from the last N minutes")
    a = ap.parse_args()

    if a.shot:
        if a.src:
            src = Path(a.src)
        else:
            vids = recent_videos(a.since)
            if not vids:
                raise SystemExit(f"No video downloaded in the last {a.since:g} minutes in {downloads_dir()}")
            src = vids[-1]
        place(a.slug, a.shot, src)
    elif a.all:
        _, missing = clip_status(a.slug)
        vids = recent_videos(a.since)
        if len(vids) < len(missing):
            print(f"  warning: {len(vids)} recent downloads for {len(missing)} missing shots")
        for shot, src in zip(missing, vids):
            place(a.slug, shot, src)
    have, missing = clip_status(a.slug)
    print(f"  clips present: {have or 'none'} | missing: {missing or 'none'}")


if __name__ == "__main__":
    main()
    sys.exit(0)
