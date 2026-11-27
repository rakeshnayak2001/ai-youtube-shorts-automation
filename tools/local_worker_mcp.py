"""MCP server that gives interactive Claude Code sessions a local "worker" model (Ollama).

Registered for this project in .mcp.json, so in Claude Code (/make-video, /new-topics, ...)
Claude can hand repetitive work to the free local model and only read a short status line.
Model and URL come from config.json -> llm.worker.

    pip install mcp            (in requirements.txt)
    claude mcp list            (should show local-worker)
"""
import glob
import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
MAX_RETURN_CHARS = 4000

mcp = FastMCP("local-worker")


def _ask(prompt: str, system: str = "", model: str = "", json_mode: bool = False) -> str:
    import llm  # scripts/llm.py: same model settings + usage ledger as the pipeline
    return llm.ask_local(prompt, task="mcp", model=model or None, system=system, json_mode=json_mode)


@mcp.tool()
def list_worker_models() -> str:
    """List local models available to the worker, and which one is configured."""
    import llm
    st = llm.ollama_status()
    if not st["up"]:
        return f"Ollama is not running at {st['url']} ({st.get('error')}). Start it with `ollama serve`."
    return json.dumps({"configured": st["model"], "available": st["models"]})


@mcp.tool()
def worker_generate(prompt: str, system: str = "", model: str = "", json_mode: bool = False) -> str:
    """Give ONE small, well-specified task to the local worker LLM and return its answer.
    Good for: brainstorming lists, rewording, classifying, extracting fields, formatting.
    Not for: facts you must be sure of, final scripts, decisions. Review what it returns."""
    out = _ask(prompt, system, model, json_mode)
    return out if len(out) <= MAX_RETURN_CHARS else out[:MAX_RETURN_CHARS] + "\n...[truncated]"


@mcp.tool()
def worker_generate_to_file(prompt: str, output_path: str, system: str = "", model: str = "") -> str:
    """Have the worker write a long output straight to a file (path relative to the project).
    Returns only a status line, so the long text never enters Claude's context."""
    out = _ask(prompt, system, model)
    p = (ROOT / output_path).resolve()
    if ROOT not in p.parents:
        return "Refused: output_path must be inside the project folder."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    return f"Wrote {len(out)} chars to {p.relative_to(ROOT)}"


@mcp.tool()
def worker_batch(instruction: str, input_glob: str, output_dir: str, output_ext: str = ".txt",
                 system: str = "", model: str = "") -> str:
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
            out = _ask(f"{instruction}\n\n--- INPUT ---\n{content}", system, model)
            (out_dir / (Path(path).stem + output_ext)).write_text(out, encoding="utf-8")
            ok += 1
        except Exception as e:  # noqa: BLE001
            failed.append(f"{os.path.basename(path)}: {e}")
    msg = f"Done {ok}/{len(files)} files -> {out_dir.relative_to(ROOT)}"
    return msg + ("\nFailed:\n" + "\n".join(failed[:20]) if failed else "")


if __name__ == "__main__":
    mcp.run()
