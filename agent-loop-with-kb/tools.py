"""
Tools available to Developer and Tester agents.
PROJECT_ROOT is injected at startup via set_project_root().

Each tool uses the @tool decorator from LangChain — the docstring becomes
the description the LLM reads to decide when to call it.
"""

import subprocess
from pathlib import Path
from langchain_core.tools import tool

PROJECT_ROOT: Path = Path(".")


def set_project_root(p: Path):
    global PROJECT_ROOT
    PROJECT_ROOT = p.resolve()


# ── Path sandbox ──────────────────────────────────────────────────────────────

def _safe(relative: str) -> Path:
    """Resolve path and ensure it stays inside PROJECT_ROOT."""
    resolved = (PROJECT_ROOT / relative).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path escape blocked: {relative!r}")
    return resolved


# ── File tools ────────────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """Read a file in the project. Path is relative to the project root."""
    t = _safe(path)
    if not t.exists():  return f"ERROR: not found: {path}"
    if not t.is_file(): return f"ERROR: not a file: {path}"
    try:    return t.read_text(encoding="utf-8")
    except Exception as e: return f"ERROR reading file: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """Write or overwrite a file. Creates parent directories if needed."""
    t = _safe(path)
    try:
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} chars to {path}"
    except Exception as e: return f"ERROR writing file: {e}"


@tool
def list_directory(path: str = ".") -> str:
    """List files and directories at a path relative to the project root."""
    t = _safe(path)
    if not t.exists():  return f"ERROR: not found: {path}"
    if not t.is_dir():  return f"ERROR: not a directory: {path}"
    skip = {"node_modules", ".git", "dist", "__pycache__", ".venv"}
    try:
        entries = sorted(t.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = [("📁 " if e.is_dir() else "📄 ") + e.name
                 for e in entries if e.name not in skip]
        return "\n".join(lines) or "(empty)"
    except Exception as e: return f"ERROR: {e}"


# ── Shell tools ───────────────────────────────────────────────────────────────

@tool
def run_command(command: str) -> str:
    """Run a shell command from the project root. Use for npm run build, etc."""
    blocked = ["rm -rf /", "sudo", ":(){:|:&};:"]
    for b in blocked:
        if b in command: return f"ERROR: blocked: {b!r}"
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
    except subprocess.TimeoutExpired: return "ERROR: command timed out"
    except Exception as e:            return f"ERROR: {e}"


@tool
def git(subcommand: str) -> str:
    """Run a git command. Pass subcommand without 'git' prefix, e.g. 'status' or 'commit -m msg'."""
    blocked = ["push --force", "push -f", "reset --hard", "clean -fd"]
    for b in blocked:
        if b in subcommand: return f"ERROR: blocked: {b!r}"
    try:
        r = subprocess.run(
            ["git"] + subcommand.split(),
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
        )
        out = []
        if r.stdout.strip(): out.append(r.stdout.strip())
        if r.stderr.strip(): out.append(r.stderr.strip())
        out.append(f"[exit {r.returncode}]")
        return "\n".join(out)
    except Exception as e: return f"ERROR: {e}"


# ── Tool sets per agent role ──────────────────────────────────────────────────

DEVELOPER_TOOLS = [read_file, write_file, list_directory, run_command, git]
TESTER_TOOLS    = [read_file, run_command, git]
REVIEWER_TOOLS  = [read_file, list_directory]


# ── Dispatcher ────────────────────────────────────────────────────────────────

_ALL = {t.name: t for t in DEVELOPER_TOOLS + TESTER_TOOLS + REVIEWER_TOOLS}


def execute_tool(name: str, args: dict) -> str:
    """
    Execute a tool by name with the given args dict.
    Called inside the developer/tester tool loops.
    """
    if name not in _ALL:
        return f"ERROR: unknown tool '{name}'"
    try:
        return str(_ALL[name].invoke(args))
    except Exception as e:
        return f"ERROR executing {name}: {e}"