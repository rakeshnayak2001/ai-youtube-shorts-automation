"""Make the voiceover + word-level timings for a script.

edge-tts gives word boundaries directly, so captions need no Whisper step.

    python scripts/tts.py <slug>
    python scripts/tts.py <slug> --fake-voice   # silent audio with estimated timings (offline testing)
"""
import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from common import PUBLIC_AUDIO, load_config, read_json, run, video_dir, voice_for, which, write_json

TICKS = 10_000_000  # edge-tts offsets are in 100-nanosecond units


async def speak(text: str, out: Path, voice: str, rate: str, pitch: str) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with out.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS
                words.append({"text": chunk["text"], "start": start,
                              "end": start + chunk["duration"] / TICKS})
    if out.stat().st_size == 0:
        raise RuntimeError("edge-tts returned no audio (check internet / voice name)")
    return words


def fake_speak(text: str, out: Path) -> list[dict]:
    words, t = [], 0.15
    for w in text.split():
        d = 0.22 + 0.035 * len(w)
        words.append({"text": w, "start": t, "end": t + d})
        t += d + (0.25 if w[-1] in ".!?," else 0.05)
    run([which("ffmpeg"), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "anullsrc=r=24000:cl=mono", "-t", f"{t + 0.1:.3f}", "-q:a", "9", str(out)])
    return words


def silence(out: Path, seconds: float) -> None:
    run([which("ffmpeg"), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{seconds:.3f}", "-q:a", "9", str(out)])


def pad_to(p: Path, seconds: float) -> None:
    tmp = p.with_suffix(".pad.mp3")
    run([which("ffmpeg"), "-y", "-loglevel", "error", "-i", str(p), "-af", f"apad=whole_dur={seconds:.3f}",
         "-b:a", "192k", str(tmp)])
    tmp.replace(p)


def duration(p: Path) -> float:
    r = subprocess.run([which("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def make_voice(slug: str, fake: bool = False) -> Path:
    d = video_dir(slug)
    script = read_json(d / "script.json")
    cfg = voice_for(load_config(), script.get("format"))
    parts_dir = d / "voice_parts"
    parts_dir.mkdir(exist_ok=True)
    gap = float(cfg.get("gap_seconds", 0.25))

    files, all_words, scenes, t = [], [], [], 0.0
    for i, scene in enumerate(script["scenes"]):
        part = parts_dir / f"{i:02d}.mp3"
        text = (scene.get("narration") or "").strip()
        min_d = float(scene.get("seconds", 0) or 0)  # cinematic shots: let the whole clip play
        # optional per-scene overrides: "speak" (what the voice says, e.g. in another script),
        # "voice" ({name, rate, pitch}) and "fx" ("echo" for a temple-hall call)
        spoken = str(scene.get("speak") or text).strip()
        v = {**cfg, **(scene.get("voice") or {})}
        if not spoken:  # e.g. a film shot where a character speaks on screen instead
            silence(part, max(min_d, 2.0))
            words = []
        elif fake:
            words = fake_speak(spoken, part)
        else:
            words = asyncio.run(speak(spoken, part, v["name"], v["rate"], v["pitch"]))
        if spoken and not fake:
            # edge-tts leaves ~1s of silence at the end of each line: trim it (the gap adds a pause back)
            trimmed = part.with_name(part.stem + "_trim.mp3")
            run([which("ffmpeg"), "-y", "-loglevel", "error", "-i", str(part), "-af",
                 "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
                 str(trimmed)])
            trimmed.replace(part)
        if scene.get("fx") == "echo":
            wet = part.with_name(part.stem + "_fx.mp3")
            run([which("ffmpeg"), "-y", "-loglevel", "error", "-i", str(part), "-af",
                 "apad=pad_dur=1.2,aecho=0.8:0.85:280|560:0.45|0.3,volume=1.6,alimiter=limit=0.95", str(wet)])
            wet.replace(part)
        if min_d and duration(part) < min_d - gap:
            pad_to(part, min_d - gap)
        dur = duration(part)
        if spoken and spoken != text:
            # captions show the narration text, spread evenly over what was spoken
            shown = text.split()
            s0 = words[0]["start"] if words else 0.1
            s1 = words[-1]["end"] if words else dur - 0.1
            step = (s1 - s0) / max(1, len(shown))
            words = [{"text": wd, "start": s0 + j * step, "end": s0 + (j + 1) * step} for j, wd in enumerate(shown)]
        scenes.append({"start": round(t, 3), "duration": round(dur + gap, 3)})
        all_words += [{"text": w["text"], "start": round(t + w["start"], 3),
                       "end": round(t + w["end"], 3)} for w in words]
        files.append(part)
        t += dur + gap
        print(f"  scene {i}: {dur:.1f}s, {len(words)} words")

    # join parts with a short pause after each
    PUBLIC_AUDIO.mkdir(parents=True, exist_ok=True)
    final = PUBLIC_AUDIO / f"{slug}.mp3"
    cmd = [which("ffmpeg"), "-y", "-loglevel", "error"]
    for f in files:
        cmd += ["-i", str(f)]
    filt = "".join(f"[{i}:a]aresample=44100,apad=pad_dur={gap}[a{i}];" for i in range(len(files)))
    filt += "".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1[out]"
    cmd += ["-filter_complex", filt, "-map", "[out]", "-ac", "2", "-b:a", "192k", str(final)]
    run(cmd)

    timings = {"total": round(t, 3), "scenes": scenes, "words": all_words}
    write_json(d / "timings.json", timings)
    print(f"  voice -> public/audio/{slug}.mp3 ({t:.1f}s)")
    return final


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--fake-voice", action="store_true")
    a = ap.parse_args()
    make_voice(a.slug, a.fake_voice)
    sys.exit(0)
