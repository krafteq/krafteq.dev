"""
Tools available to the Developer agent.
PROJECT_ROOT is injected at runtime from config — the agent is project-agnostic.
"""

import subprocess
from pathlib import Path
from providers.base import ToolParam

# Set at startup by main.py via set_project_root()
PROJECT_ROOT: Path = Path(".")


def set_project_root(path: Path):
    global PROJECT_ROOT
    PROJECT_ROOT = path.resolve()


# ─── Tool schemas ─────────────────────────────────────────────────────────────

TOOLS: list[ToolParam] = [
    ToolParam(
        name="read_file",
        description="Read a file in the project. Path is relative to project root.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "e.g. src/App.jsx"}
            },
            "required": ["path"],
        },
    ),
    ToolParam(
        name="write_file",
        description="Write or overwrite a file. Creates parent dirs if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "File path relative to project root."},
                "content": {"type": "string", "description": "Full file content to write."},
            },
            "required": ["path", "content"],
        },
    ),
    ToolParam(
        name="list_directory",
        description="List files/directories at a path. Defaults to project root.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "."}
            },
            "required": [],
        },
    ),
    ToolParam(
        name="run_command",
        description=(
            "Run a shell command from the project root. "
            "Always run `npm run build` after file changes to verify compilation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "e.g. 'npm run build'"}
            },
            "required": ["command"],
        },
    ),
]


# ─── Implementations ──────────────────────────────────────────────────────────

def _safe(relative: str) -> Path:
    resolved = (PROJECT_ROOT / relative).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path escape blocked: {relative}")
    return resolved


def tool_read_file(path: str) -> str:
    t = _safe(path)
    if not t.exists():  return f"ERROR: not found: {path}"
    if not t.is_file(): return f"ERROR: not a file: {path}"
    try:    return t.read_text(encoding="utf-8")
    except Exception as e: return f"ERROR: {e}"


def tool_write_file(path: str, content: str) -> str:
    t = _safe(path)
    try:
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} chars to {path}"
    except Exception as e: return f"ERROR: {e}"


def tool_list_directory(path: str = ".") -> str:
    t = _safe(path)
    if not t.exists():  return f"ERROR: not found: {path}"
    if not t.is_dir():  return f"ERROR: not a directory: {path}"
    skip = {"node_modules", ".git", "dist", "__pycache__", ".venv"}
    try:
        entries = sorted(t.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = [
            ("📁 " if e.is_dir() else "📄 ") + e.name
            for e in entries if e.name not in skip
        ]
        return "\n".join(lines) or "(empty)"
    except Exception as e: return f"ERROR: {e}"


def tool_run_command(command: str) -> str:
    blocked = ["rm -rf /", "sudo", ":(){:|:&};:"]
    for b in blocked:
        if b in command:
            return f"ERROR: blocked command: {b!r}"
    try:
        r = subprocess.run(
            command, shell=True, cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=60,
        )
        out = []
        if r.stdout.strip(): out.append(r.stdout.strip())
        if r.stderr.strip(): out.append(f"[stderr]\n{r.stderr.strip()}")
        out.append(f"[exit {r.returncode}]")
        return "\n".join(out)
    except subprocess.TimeoutExpired: return "ERROR: timed out"
    except Exception as e:            return f"ERROR: {e}"


def run_tool(name: str, inputs: dict) -> str:
    if name == "read_file":      return tool_read_file(inputs["path"])
    if name == "write_file":     return tool_write_file(inputs["path"], inputs["content"])
    if name == "list_directory": return tool_list_directory(inputs.get("path", "."))
    if name == "run_command":    return tool_run_command(inputs["command"])
    return f"ERROR: unknown tool '{name}'"
