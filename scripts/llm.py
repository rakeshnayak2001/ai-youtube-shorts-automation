"""Model router: Claude is the MASTER; a local LLM (Ollama) or Gemini is the WORKER.

Every LLM call in the pipeline names a *task*; config.json -> llm.tasks decides who does it:

    "llm": {
      "master": {"model": ""},                          # "" = Claude Code default, or sonnet / opus / haiku
      "worker": {"url": "http://localhost:11434", "model": "qwen3:8b", "temperature": 0.3},
      "tasks": {"script": "claude", "topic_plan": "claude", "json_repair": "gemini", "ideas": "gemini"},
      "local_enabled": false,                           # the local model is off unless switched on
      "fallback_to_claude": true
    }

A task value is "claude", "claude:<model>", "local", "local:<ollama-model>", "gemini" or "gemini:<model>".

Gemini (and any later worker such as Codex) comes from the separate agent-squad package
(https://github.com/rakeshnayak2001/agent-squad). When it is installed (`pip install -e "C:\\AI Vid\\agent-squad"`)
or found at llm.squad_path / ../agent-squad, every call goes through it, with Gemini account rotation.
Without it, this file still runs Claude and the local model on its own, and Gemini tasks fall back to Claude.
Judgement work (scripts, fact-checks, timely topics with web search) stays on Claude;
repetitive work (fixing broken JSON, brainstorming topic lists) goes to Gemini by default.
The local model only runs when llm.local_enabled is true; while it is off, "local" tasks go to Gemini
and the local model is left out of the fallback chain too.
Every call is counted in state/llm_usage.json so the dashboard can show what was saved.

    python scripts/llm.py status
    python scripts/llm.py test local "Say hi in five words"
    python scripts/llm.py test gemini "Say hi in five words"
"""
import datetime as dt
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from common import ROOT, STATE, load_config, read_json, write_json

TASKS = {
    "script": "Write the video script (needs accuracy + web search)",
    "topic_plan": "Pick today's timely topic (needs web search)",
    "json_repair": "Fix a script that came back as invalid JSON",
    "ideas": "Brainstorm new topics for the queue",
}
DEFAULT_TASKS = {"script": "claude", "topic_plan": "claude", "json_repair": "gemini", "ideas": "gemini"}
WORKER_KINDS = ("claude", "local", "gemini")  # agent-squad may add more (e.g. codex)
USAGE = STATE / "llm_usage.json"
USAGE_FILE = str(USAGE)  # read by agent-squad's MCP server (SQUAD_SETTINGS_MODULE=llm)


# ---------------------------------------------------------------- agent-squad (optional)
_SQUAD = None


def squad(cfg: dict | None = None):
    """The agent_squad module if it is installed or can be found, else None (standalone mode)."""
    global _SQUAD
    if _SQUAD is not None:
        return _SQUAD or None
    try:
        _SQUAD = importlib.import_module("agent_squad")
    except ImportError:
        cfg = cfg or load_config()
        for cand in [(cfg.get("llm") or {}).get("squad_path") or "", str(ROOT.parent / "agent-squad")]:
            if cand and (os.path.isdir(os.path.join(os.path.expanduser(cand), "agent_squad"))):
                sys.path.insert(0, os.path.expanduser(cand))
                try:
                    _SQUAD = importlib.import_module("agent_squad")
                    break
                except ImportError:
                    pass
        else:
            _SQUAD = False
    return _SQUAD or None


def squad_config(cfg: dict | None = None) -> dict:
    """This app's model settings as an agent-squad config, layered over ~/.agent-squad/squad.json.
    Gemini API keys and cooldowns live in agent-squad's own folders, so they are shared."""
    cfg = cfg or load_config()
    sq = squad(cfg)
    lc = llm_cfg(cfg)
    over = {"workers": {
        "claude": {"model": lc["master"]["model"], "allow_web_search": (cfg.get("claude") or {}).get("allow_web_search", True)},
        "local": {k: lc["worker"][k] for k in ("url", "model", "temperature", "timeout")},
        "gemini": {k: v for k, v in lc["gemini"].items() if v not in ("", None, [])},
    }}
    return sq.load_config(over) if sq else over


# ---------------------------------------------------------------- config
def llm_cfg(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    c = cfg.get("llm") or {}
    worker = {"url": "http://localhost:11434", "model": "qwen3:8b", "temperature": 0.3, "timeout": 600,
              **(c.get("worker") or {})}
    master = {"model": (cfg.get("claude") or {}).get("model", ""), **(c.get("master") or {})}
    gemini = {"model": "gemini-3-pro-preview", "rotation": "failover", **(c.get("gemini") or {})}
    return {"master": master, "worker": worker, "gemini": gemini,
            "tasks": {**DEFAULT_TASKS, **(c.get("tasks") or {})},
            "fallback_to_claude": c.get("fallback_to_claude", True),
            "worker_fallback": c.get("worker_fallback", ["local"]),
            # The local Ollama model is off unless switched on: then nothing runs on it, not even as fallback.
            "local_enabled": bool(c.get("local_enabled", False))}


def local_enabled(cfg: dict | None = None) -> bool:
    return llm_cfg(cfg)["local_enabled"]


def _model_for(kind: str, cfg: dict | None = None) -> str:
    lc = llm_cfg(cfg)
    if kind == "gemini":
        return lc["gemini"].get("agy_model", "") if gemini_backend(cfg) == "agy" else lc["gemini"]["model"]
    return {"claude": lc["master"]["model"], "local": lc["worker"]["model"]}.get(kind, "")


def route(task: str, cfg: dict | None = None) -> tuple[str, str]:
    """('claude' | 'local' | 'gemini' | ..., model) for a task."""
    lc = llm_cfg(cfg)
    spec = lc["tasks"].get(task, "claude") or "claude"
    kind, _, model = spec.partition(":")
    known = set(WORKER_KINDS) | set(getattr(squad(cfg), "WORKERS", {}) or {})
    if kind not in known:
        kind, model = "claude", ""
    if kind == "local" and not lc["local_enabled"]:
        kind, model = "gemini", ""  # local model switched off: Gemini is the worker
    if not model:
        model = _model_for(kind, cfg)  # agy has its own model names ("" = its default)
    return kind, model


def gemini_backend(cfg: dict | None = None) -> str:
    """'api' (AI Studio keys), 'agy' (Pro plan via Antigravity CLI) or 'cli'. Needs agent-squad."""
    cfg = cfg or load_config()
    b = llm_cfg(cfg)["gemini"].get("backend")
    if not b and squad(cfg):
        b = ((squad_config(cfg).get("workers") or {}).get("gemini") or {}).get("backend")
    return b or "api"


def fallback_chain(kind: str, cfg: dict | None = None) -> list[str]:
    """Who takes over when a worker fails or runs out of quota: llm.worker_fallback (default: the local
    model, only if llm.local_enabled), then Claude if llm.fallback_to_claude."""
    lc = llm_cfg(cfg)
    chain = [w for w in lc["worker_fallback"] if w.partition(":")[0] != kind and kind != "claude"
             and (lc["local_enabled"] or w.partition(":")[0] != "local")]
    if lc["fallback_to_claude"] and kind != "claude":
        chain.append("claude")
    return chain


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
            t = tot.setdefault(kind, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "tasks": {},
                                      "accounts": {}})
            for f in ("calls", "tokens_in", "tokens_out"):
                t[f] += b.get(f, 0)
            t["cost_usd"] = round(t["cost_usd"] + b.get("cost_usd", 0), 4)
            for task, n in b.get("tasks", {}).items():
                t["tasks"][task] = t["tasks"].get(task, 0) + n
            for acc, n in (b.get("accounts") or {}).items():
                t["accounts"][acc] = t["accounts"].get(acc, 0) + n
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


def ask_spec(kind: str, model: str, prompt: str, cfg: dict | None = None, task: str = "worker",
             fallback: bool | None = None, **kw) -> str:
    """Run one prompt on a named worker ("claude" | "local" | "gemini" | ...).
    With agent-squad: it does the call (Gemini account rotation, fallback chain, shared usage ledger).
    Without it: the built-in Claude / Ollama code below."""
    cfg = cfg or load_config()
    fb = llm_cfg(cfg)["fallback_to_claude"] if fallback is None else fallback
    if kind == "local" and not local_enabled(cfg):
        print("  local model is switched off (llm.local_enabled); using Gemini")
        kind, model = "gemini", _model_for("gemini", cfg)
    sq = squad(cfg)
    if sq:
        opts = {k: kw[k] for k in ("system", "json_mode", "temperature", "web") if k in kw and kw[k] is not None}
        try:
            r = sq.ask(f"{kind}:{model}" if model else kind, prompt, task=task, config=squad_config(cfg),
                       fallback=[] if fallback is False else fallback_chain(kind, cfg),
                       usage_file=USAGE, **opts)
        except sq.WorkerError as e:
            raise RuntimeError(str(e)) from e
        return r.text
    if kind == "claude":
        return ask_claude(prompt, cfg, task, model or None, kw.get("web"))
    if kind != "local":
        msg = f"the '{kind}' worker needs agent-squad (pip install -e <path to agent-squad>)"
        if not fb:
            raise RuntimeError(msg)
        print(f"  {msg}; falling back to Claude")
        return ask_claude(prompt, cfg, task, None, kw.get("web"))
    try:
        return ask_local(prompt, cfg, task, model or None, **{k: v for k, v in kw.items()
                                                            if k in ("system", "json_mode", "temperature")})
    except RuntimeError as e:
        if not fb:
            raise
        print(f"  worker failed ({e}); falling back to Claude")
        return ask_claude(prompt, cfg, task, None, kw.get("web"))


def ask(task: str, prompt: str, cfg: dict | None = None, **kw) -> str:
    """Send a prompt to whoever config.json says should do `task`."""
    cfg = cfg or load_config()
    kind, model = route(task, cfg)
    return ask_spec(kind, model, prompt, cfg, task, **kw)


# ---------------------------------------------------------------- status
def ollama_status(cfg: dict | None = None) -> dict:
    w = llm_cfg(cfg)["worker"]
    if not local_enabled(cfg):
        return {"enabled": False, "up": False, "url": w["url"], "models": [], "model": w["model"],
                "model_ready": False, "error": "switched off (llm.local_enabled)"}
    try:
        with urllib.request.urlopen(w["url"].rstrip("/") + "/api/tags", timeout=3) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return {"enabled": True, "up": True, "url": w["url"], "models": models, "model": w["model"],
                "model_ready": any(m == w["model"] or m.split(":")[0] == w["model"] for m in models)}
    except Exception as e:  # noqa: BLE001
        return {"enabled": True, "up": False, "url": w["url"], "models": [], "model": w["model"],
                "model_ready": False, "error": str(e)}


def gemini_status(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    sq = squad(cfg)
    if not sq:
        return {"available": False, "up": False, "accounts": [],
                "help": "Install agent-squad to use Gemini: git clone https://github.com/rakeshnayak2001/agent-squad, "
                        "then run its setup.bat"}
    try:
        st = sq.get_worker("gemini", squad_config(cfg)).status()
    except Exception as e:  # noqa: BLE001
        return {"available": True, "up": False, "accounts": [], "error": str(e)}
    return {"available": True, **st}


def status(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    sq = squad(cfg)
    return {"claude_cli": bool(shutil.which("claude")), "ollama": ollama_status(cfg), "gemini": gemini_status(cfg),
            "squad": {"installed": bool(sq), "version": getattr(sq, "__version__", None),
                      "path": os.path.dirname(os.path.dirname(sq.__file__)) if sq else None,
                      "workers": sorted(getattr(sq, "WORKERS", {}) or [])},
            "routes": {t: route(t, cfg) for t in TASKS}, "fallback_to_claude": llm_cfg(cfg)["fallback_to_claude"]}


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["status"]:
        print(json.dumps(status(), indent=2))
    elif args[:1] == ["test"] and len(args) >= 3:
        kind, _, model = args[1].partition(":")
        if kind == "local" and not local_enabled():
            sys.exit("The local model is switched off. Turn on 'Use local model' in the dashboard "
                     "(Models page) or set llm.local_enabled to true in config.json.")
        print(ask_spec(kind, model, " ".join(args[2:]), task="test", fallback=False))
    elif args[:1] == ["usage"]:
        print(json.dumps(usage_summary()["total"], indent=2))
    else:
        print(__doc__)
