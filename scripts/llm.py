"""Model router: Claude is the MASTER, a local LLM (Ollama) is the WORKER.

Every LLM call in the pipeline names a *task*; config.json -> llm.tasks decides who does it:

    "llm": {
      "master": {"model": ""},                          # "" = Claude Code default, or sonnet / opus / haiku
      "worker": {"url": "http://localhost:11434", "model": "qwen3:8b", "temperature": 0.3},
      "tasks": {"script": "claude", "topic_plan": "claude", "json_repair": "local", "ideas": "local"},
      "fallback_to_claude": true
    }

A task value is "claude", "claude:<model>", "local" or "local:<ollama-model>".
Judgement work (scripts, fact-checks, timely topics with web search) stays on Claude;
repetitive work (fixing broken JSON, brainstorming topic lists) goes to the free local model.
Every call is counted in state/llm_usage.json so the dashboard can show what was saved.

    python scripts/llm.py status
    python scripts/llm.py test local "Say hi in five words"
"""
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from common import STATE, load_config, read_json, write_json

TASKS = {
    "script": "Write the video script (needs accuracy + web search)",
    "topic_plan": "Pick today's timely topic (needs web search)",
    "json_repair": "Fix a script that came back as invalid JSON",
    "ideas": "Brainstorm new topics for the queue",
}
DEFAULT_TASKS = {"script": "claude", "topic_plan": "claude", "json_repair": "local", "ideas": "local"}
USAGE = STATE / "llm_usage.json"


# ---------------------------------------------------------------- config
def llm_cfg(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    c = cfg.get("llm") or {}
    worker = {"url": "http://localhost:11434", "model": "qwen3:8b", "temperature": 0.3, "timeout": 600,
              **(c.get("worker") or {})}
    master = {"model": (cfg.get("claude") or {}).get("model", ""), **(c.get("master") or {})}
    return {"master": master, "worker": worker, "tasks": {**DEFAULT_TASKS, **(c.get("tasks") or {})},
            "fallback_to_claude": c.get("fallback_to_claude", True)}


def route(task: str, cfg: dict | None = None) -> tuple[str, str]:
    """('claude' | 'local', model) for a task."""
    lc = llm_cfg(cfg)
    spec = lc["tasks"].get(task, "claude") or "claude"
    kind, _, model = spec.partition(":")
    if kind not in ("claude", "local"):
        kind, model = "claude", ""
    if not model:
        model = lc["master"]["model"] if kind == "claude" else lc["worker"]["model"]
    return kind, model


# ---------------------------------------------------------------- usage ledger
def _record(kind: str, task: str, tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0,
            seconds: float = 0.0, ok: bool = True) -> None:
    try:
        data = read_json(USAGE) if USAGE.exists() else {}
        day = data.setdefault(dt.date.today().isoformat(), {})
        b = day.setdefault(kind, {"calls": 0, "failed": 0, "tokens_in": 0, "tokens_out": 0,
                                  "cost_usd": 0.0, "seconds": 0.0, "tasks": {}})
        b["calls"] += 1
        b["failed"] += 0 if ok else 1
        b["tokens_in"] += int(tokens_in or 0)
        b["tokens_out"] += int(tokens_out or 0)
        b["cost_usd"] = round(b["cost_usd"] + float(cost or 0), 4)
        b["seconds"] = round(b["seconds"] + seconds, 1)
        b["tasks"][task] = b["tasks"].get(task, 0) + 1
        write_json(USAGE, dict(sorted(data.items())[-90:]))
    except Exception:  # noqa: BLE001 - usage stats must never break a run
        pass


def usage_summary(days: int = 30) -> dict:
    data = read_json(USAGE) if USAGE.exists() else {}
    keys = sorted(data)[-days:]
    tot = {}
    for k in keys:
        for kind, b in data[k].items():
            t = tot.setdefault(kind, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "tasks": {}})
            for f in ("calls", "tokens_in", "tokens_out"):
                t[f] += b.get(f, 0)
            t["cost_usd"] = round(t["cost_usd"] + b.get("cost_usd", 0), 4)
            for task, n in b.get("tasks", {}).items():
                t["tasks"][task] = t["tasks"].get(task, 0) + n
    return {"days": {k: data[k] for k in keys}, "total": tot}


# ---------------------------------------------------------------- backends
def ask_claude(prompt: str, cfg: dict | None = None, task: str = "script", model: str | None = None,
               web: bool | None = None) -> str:
    """Headless Claude Code (`claude -p`) on your subscription."""
    cfg = cfg or load_config()
    exe = shutil.which("claude")
    if not exe:
        raise SystemExit("'claude' not found on PATH. Install Claude Code and run `claude` once to log in.")
    cmd = [exe, "-p", "--output-format", "json"]
    if web if web is not None else (cfg.get("claude") or {}).get("allow_web_search", True):
        cmd += ["--allowedTools", "WebSearch,WebFetch"]
    model = model if model is not None else llm_cfg(cfg)["master"]["model"]
    if model:
        cmd += ["--model", model]
    print(f"  [master] Claude{' ' + model if model else ''} -> {task}")
    t0 = time.time()
    res = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900)
    if res.returncode != 0:
        _record("claude", task, seconds=time.time() - t0, ok=False)
        raise RuntimeError(f"claude exited {res.returncode}: {res.stderr[-800:]}")
    try:
        outer = json.loads(res.stdout)
    except json.JSONDecodeError:
        _record("claude", task, seconds=time.time() - t0)
        return res.stdout
    u = outer.get("usage") or {}
    _record("claude", task,
            tokens_in=(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                       + u.get("cache_creation_input_tokens", 0)),
            tokens_out=u.get("output_tokens", 0), cost=outer.get("total_cost_usd", 0),
            seconds=time.time() - t0, ok=not outer.get("is_error"))
    if outer.get("is_error"):
        raise SystemExit(
            f"Claude Code returned an error: {outer.get('result')}\n"
            "Open a terminal, run `claude`, make sure you're logged in, then try again.")
    return outer.get("result", res.stdout)


def ask_local(prompt: str, cfg: dict | None = None, task: str = "worker", model: str | None = None,
              system: str = "", json_mode: bool = False, temperature: float | None = None) -> str:
    """The local worker model through Ollama's HTTP API."""
    w = llm_cfg(cfg)["worker"]
    model = model or w["model"]
    body = {"model": model, "prompt": prompt, "system": system, "stream": False,
            "options": {"temperature": w["temperature"] if temperature is None else temperature}}
    if json_mode:
        body["format"] = "json"
    print(f"  [worker] local {model} -> {task}")
    t0 = time.time()
    req = urllib.request.Request(w["url"].rstrip("/") + "/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(w.get("timeout", 600))) as r:
            out = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        _record("local", task, seconds=time.time() - t0, ok=False)
        raise RuntimeError(f"local model unavailable ({e}). Is Ollama running? `ollama serve`") from e
    _record("local", task, tokens_in=out.get("prompt_eval_count", 0), tokens_out=out.get("eval_count", 0),
            seconds=time.time() - t0)
    text = out.get("response", "")
    # reasoning models (qwen3, deepseek-r1) may wrap their thinking in <think>...</think>
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def ask(task: str, prompt: str, cfg: dict | None = None, **kw) -> str:
    """Send a prompt to whoever config.json says should do `task`."""
    cfg = cfg or load_config()
    kind, model = route(task, cfg)
    if kind == "local":
        try:
            return ask_local(prompt, cfg, task, model, **{k: v for k, v in kw.items()
                                                         if k in ("system", "json_mode", "temperature")})
        except RuntimeError as e:
            if not llm_cfg(cfg)["fallback_to_claude"]:
                raise
            print(f"  worker failed ({e}); falling back to Claude")
            model = None
    return ask_claude(prompt, cfg, task, model or None, kw.get("web"))


# ---------------------------------------------------------------- status
def ollama_status(cfg: dict | None = None) -> dict:
    w = llm_cfg(cfg)["worker"]
    try:
        with urllib.request.urlopen(w["url"].rstrip("/") + "/api/tags", timeout=3) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return {"up": True, "url": w["url"], "models": models, "model": w["model"],
                "model_ready": any(m == w["model"] or m.split(":")[0] == w["model"] for m in models)}
    except Exception as e:  # noqa: BLE001
        return {"up": False, "url": w["url"], "models": [], "model": w["model"], "model_ready": False,
                "error": str(e)}


def status(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    return {"claude_cli": bool(shutil.which("claude")), "ollama": ollama_status(cfg),
            "routes": {t: route(t, cfg) for t in TASKS}, "fallback_to_claude": llm_cfg(cfg)["fallback_to_claude"]}


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["status"]:
        print(json.dumps(status(), indent=2))
    elif args[:1] == ["test"] and len(args) >= 3:
        fn = ask_local if args[1] == "local" else ask_claude
        print(fn(" ".join(args[2:]), task="test"))
    elif args[:1] == ["usage"]:
        print(json.dumps(usage_summary()["total"], indent=2))
    else:
        print(__doc__)
