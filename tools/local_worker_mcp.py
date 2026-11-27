"""MCP server that gives interactive Claude Code sessions worker models: local (Ollama) or Gemini.

Registered for this project in .mcp.json, so in Claude Code (/make-video, /new-topics, ...)
Claude (the master) can hand repetitive work to a worker and only read a short status line.
Every tool takes worker="local" (default, free) or "gemini" (Google AI Pro accounts, needs agent-squad),
or "<worker>:<model>". Settings come from config.json -> llm.

    pip install mcp            (in requirements.txt)
    claude mcp list            (should show local-worker)
"""
import glob
import json
import os
import sys
from pathlib import Path

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server
except ImportError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as Server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
MAX_RETURN_CHARS = 4000

mcp = Server("local-worker")


def _ask(prompt: str, system: str = "", model: str = "", json_mode: bool = False, worker: str = "local") -> str:
    import llm  # scripts/llm.py: same model settings + usage ledger as the pipeline
    kind, _, m = (worker or "local").partition(":")
    return llm.ask_spec(kind, model or m, prompt, task="mcp", fallback=False, system=system, json_mode=json_mode)


@mcp.tool()
def list_worker_models() -> str:
    """List the workers: local Ollama models and the Gemini accounts, and which are ready."""
    import llm
    st = llm.ollama_status()
    local = ({"configured": st["model"], "available": st["models"]} if st["up"] else
             f"Ollama is not running at {st['url']} ({st.get('error')}). Start it with `ollama serve`.")
    g = llm.gemini_status()
    gem = ({"model": g.get("model"), "rotation": g.get("rotation"), "cli_found": g.get("up"),
            "accounts": [{k: a.get(k) for k in ("name", "signed_in", "cooldown_until", "calls_today")}
                         for a in g.get("accounts", [])]} if g.get("available") else g.get("help"))
    return json.dumps({"local": local, "gemini": gem})


@mcp.tool()
def worker_generate(prompt: str, system: str = "", model: str = "", json_mode: bool = False,
                    worker: str = "local") -> str:
    """Give ONE small, well-specified task to a worker LLM and return its answer.
    worker: "local" (free Ollama) or "gemini" (Gemini on the Google AI Pro accounts).
    Good for: brainstorming lists, rewording, classifying, extracting fields, formatting.
    Not for: facts you must be sure of, final scripts, decisions. Review what it returns."""
    out = _ask(prompt, system, model, json_mode, worker)
    return out if len(out) <= MAX_RETURN_CHARS else out[:MAX_RETURN_CHARS] + "\n...[truncated]"


@mcp.tool()
def worker_generate_to_file(prompt: str, output_path: str, system: str = "", model: str = "",
                            worker: str = "local") -> str:
    """Have the worker write a long output straight to a file (path relative to the project).
    Returns only a status line, so the long text never enters Claude's context."""
    p = (ROOT / output_path).resolve()
    if ROOT not in p.parents:
        return "Refused: output_path must be inside the project folder."
    out = _ask(prompt, system, model, worker=worker)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    return f"Wrote {len(out)} chars to {p.relative_to(ROOT)}"


@mcp.tool()
def worker_batch(instruction: str, input_glob: str, output_dir: str, output_ext: str = ".txt",
                 system: str = "", model: str = "", worker: str = "local") -> str:
    """Apply the same instruction to every file matching input_glob (relative to the project) and save
    each result in output_dir/<name><output_ext>. Returns a compact summary only.
    Test the instruction on one item with worker_generate first."""
    files = sorted(glob.glob(str(ROOT / input_glob), recursive=True))
    if not files:
        return f"No files matched {input_glob}"
    out_dir = (ROOT / output_dir).resolve()
    if ROOT not in out_dir.parents and out_dir != ROOT:
        return "Refused: output_dir must be inside the project folder."
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    for path in files:
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
            out = _ask(f"{instruction}\n\n--- INPUT ---\n{content}", system, model, worker=worker)
            (out_dir / (Path(path).stem + output_ext)).write_text(out, encoding="utf-8")
            ok += 1
        except Exception as e:  # noqa: BLE001
            failed.append(f"{os.path.basename(path)}: {e}")
    msg = f"Done {ok}/{len(files)} files -> {out_dir.relative_to(ROOT)}"
    return msg + ("\nFailed:\n" + "\n".join(failed[:20]) if failed else "")


if __name__ == "__main__":
    mcp.run()
