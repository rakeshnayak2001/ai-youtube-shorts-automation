"""yt-factory dashboard: a local control panel for the pipeline.

    python dashboard/server.py            (or double-click dashboard.bat)
    -> http://127.0.0.1:8765

Start videos, watch the live log, switch models (Claude master / local worker), edit the topic queues
and config, and play finished videos. Listens on 127.0.0.1 only. Uses only the Python standard library.
"""
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402
import llm  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
PORT = int(os.environ.get("YTF_PORT", "8765"))
PY = sys.executable


# ---------------------------------------------------------------- one background job at a time
class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.lines: list[str] = []
        self.name = ""
        self.cmd: list[str] = []
        self.started = 0.0
        self.ended = 0.0
        self.code = None
        self.seq = 0  # increases with every new job so the UI can tell runs apart

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, name: str, cmd: list[str]) -> None:
        with self.lock:
            if self.running():
                raise RuntimeError(f"'{self.name}' is still running")
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
            flags = subprocess.CREATE_NEW_PROCESS_GROUP if common.IS_WINDOWS else 0
            self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                         errors="replace", env=env, creationflags=flags)
            self.lines, self.name, self.cmd = [f"$ {' '.join(['python'] + cmd[2:] if cmd[0] == PY else cmd)}"], name, cmd
            self.started, self.ended, self.code = time.time(), 0.0, None
            self.seq += 1
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc) -> None:
        for line in proc.stdout:
            self.lines.append(line.rstrip("\n"))
            if len(self.lines) > 5000:
                del self.lines[:1000]
        proc.wait()
        self.code, self.ended = proc.returncode, time.time()
        self.lines.append(f"[finished with exit code {proc.returncode}]")

    def stop(self) -> None:
        if self.running():
            self.proc.terminate()
            self.lines.append("[stopped from the dashboard]")

    def info(self) -> dict:
        return {"seq": self.seq, "name": self.name, "running": self.running(), "code": self.code,
                "started": self.started, "ended": self.ended, "lines": len(self.lines)}


JOB = Job()


def build_command(body: dict) -> tuple[str, list[str]]:
    a = body.get("action")
    fmt = body.get("format") or ""
    flags = []
    if body.get("no_upload"):
        flags.append("--no-upload")
    if body.get("no_plan"):
        flags.append("--no-plan")
    if body.get("fake_voice"):
        flags.append("--fake-voice")
    run = [PY, "-u", "run.py"]
    if a == "daily_start":
        return "Daily start", run + ["--daily-start"] + flags
    if a == "daily_finish":
        return "Daily finish", run + ["--daily-finish"] + flags
    if a == "daily_extra":
        return "Extra video", run + ["--daily-extra"] + flags
    if a == "make":
        cmd = run + (["--format", fmt] if fmt else []) + flags
        if body.get("topic"):
            cmd += ["--topic", body["topic"]]
        return f"Make {fmt or 'video'}", cmd
    if a == "finish_slug":
        return f"Finish {body['slug']}", run + ["--slug", body["slug"]] + flags
    if a == "preview":
        return f"Preview {body['slug']}", [PY, "-u", "scripts/render.py", body["slug"], "--allow-missing"]
    if a == "plan":
        return f"Plan topic ({fmt})", [PY, "-u", "scripts/topics.py", "plan", fmt or "stickman"]
    if a == "brainstorm":
        cmd = [PY, "-u", "scripts/ideas.py", fmt or "stickman", "--n", str(int(body.get("n") or 10))]
        if body.get("theme"):
            cmd += ["--theme", body["theme"]]
        return f"Brainstorm {fmt}", cmd
    if a == "pull_model":
        exe = shutil.which("ollama")
        if not exe:
            raise RuntimeError("ollama is not installed (see the Models page)")
        return f"Pull {body['model']}", [exe, "pull", body["model"]]
    if a == "test_worker":
        return "Test worker", [PY, "-u", "scripts/llm.py", "test", "local",
                               body.get("prompt") or "In one sentence, who are you?"]
    if a == "test_master":
        return "Test Claude", [PY, "-u", "scripts/llm.py", "test", "claude",
                               body.get("prompt") or "In one sentence, who are you?"]
    raise RuntimeError(f"unknown action {a!r}")


# ---------------------------------------------------------------- data for the UI
def status() -> dict:
    cfg = common.load_config()
    out = {"format": common.active_format(cfg), "today": common.todays_video(), "job": JOB.info(),
           "queues": {f: len(common.queued_ideas(f)) for f in ("cinematic", "stickman")},
           "llm": llm.status(cfg), "usage": llm.usage_summary(30)["total"],
           "ollama_installed": bool(shutil.which("ollama"))}
    try:
        import credits
        out["credits"] = credits.accounts()
        out["film_cost"] = credits.film_cost(int(cfg.get("cinematic", {}).get("shots", 10)))
    except Exception:  # noqa: BLE001
        out["credits"] = {}
    return out


def videos() -> list[dict]:
    hist = {h["slug"]: h for h in common.load_history() if h.get("slug")}
    items = []
    for d in sorted(common.VIDEOS.glob("*/script.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        slug = d.parent.name
        try:
            s = common.read_json(d)
        except Exception:  # noqa: BLE001
            continue
        h = hist.get(slug, {})
        files = [str(p.relative_to(common.OUT)).replace("\\", "/")
                 for p in common.OUT.glob(f"**/{slug}-*.mp4")]
        clips = len(list((d.parent / "clips").glob("shot_*.mp4"))) if (d.parent / "clips").exists() else 0
        items.append({"slug": slug, "title": s.get("title", slug), "format": s.get("format", h.get("format")),
                      "status": h.get("status", "scripted"), "topic": s.get("topic", ""), "files": files,
                      "urls": h.get("urls", []), "clips": clips, "shots": len(s.get("shots", [])),
                      "modified": d.stat().st_mtime})
    return items


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the console quiet
        pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _file(self, path: Path):
        if not path.is_file():
            return self._json({"error": "not found"}, 404)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = min(int(b), size - 1) if b else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 16, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        try:
            if p in ("/", "/index.html"):
                return self._file(STATIC / "index.html")
            if p.startswith("/static/"):
                f = (STATIC / p[len("/static/"):]).resolve()
                return self._file(f) if STATIC in f.parents else self._json({"error": "no"}, 403)
            if p.startswith("/media/"):
                f = (common.OUT / urllib.parse.unquote(p[len("/media/"):])).resolve()
                ok = common.OUT.resolve() in f.parents and f.suffix.lower() in (".mp4", ".png", ".jpg")
                return self._file(f) if ok else self._json({"error": "no"}, 403)
            if p == "/api/status":
                return self._json(status())
            if p == "/api/config":
                return self._json(common.load_config())
            if p == "/api/videos":
                return self._json(videos())
            if p == "/api/ideas":
                return self._json(common.read_ideas(q.get("format", ["stickman"])[0]))
            if p == "/api/script":
                slug = q["slug"][0]
                f = common.VIDEOS / slug / "script.json"
                return self._json(common.read_json(f)) if f.exists() else self._json({}, 404)
            if p == "/api/usage":
                return self._json(llm.usage_summary(30))
            if p == "/api/job/log":
                since = int(q.get("since", ["0"])[0])
                return self._json({"job": JOB.info(), "lines": JOB.lines[since:], "next": len(JOB.lines)})
            return self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)

    def do_POST(self):  # noqa: N802
        p = urllib.parse.urlparse(self.path).path
        try:
            body = self._body()
            if p == "/api/run":
                name, cmd = build_command(body)
                JOB.start(name, cmd)
                return self._json({"ok": True, "job": JOB.info()})
            if p == "/api/job/stop":
                JOB.stop()
                return self._json({"ok": True})
            if p == "/api/config":
                cfg = body.get("config")
                if not isinstance(cfg, dict) or "video" not in cfg or "voice" not in cfg:
                    raise ValueError("that doesn't look like a full config.json")
                src = common.ROOT / "config.json"
                (common.STATE).mkdir(exist_ok=True)
                shutil.copy(src, common.STATE / "config.backup.json")
                common.write_json(src, cfg)
                return self._json({"ok": True})
            if p == "/api/config/patch":
                cfg = common.load_config()
                for dotted, value in (body.get("set") or {}).items():
                    node = cfg
                    *parents, last = dotted.split(".")
                    for k in parents:
                        node = node.setdefault(k, {})
                    node[last] = value
                common.write_json(common.ROOT / "config.json", cfg)
                return self._json({"ok": True, "config": cfg})
            if p == "/api/ideas":
                fmt = body["format"]
                rows = common.read_ideas(fmt)
                op = body.get("op")
                if op == "add":
                    for t in body.get("topics", []):
                        if t.strip() and t.strip() not in {r["topic"] for r in rows}:
                            rows.append({"topic": t.strip(), "status": ""})
                elif op == "delete":
                    rows = [r for r in rows if r["topic"] != body["topic"]]
                elif op == "move_top":
                    rows.sort(key=lambda r: r["topic"] != body["topic"])
                elif op == "reset":
                    for r in rows:
                        if r["topic"] == body["topic"]:
                            r["status"] = ""
                common.write_ideas(rows, fmt)
                return self._json(common.read_ideas(fmt))
            return self._json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 400)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"yt-factory dashboard running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        JOB.stop()


if __name__ == "__main__":
    main()
