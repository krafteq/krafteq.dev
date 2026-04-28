"""
Tools available to the Developer agent.
Each tool is registered in TOOLS (the schema) and dispatched in run_tool().
"""

import os
import subprocess
import json
from pathlib import Path

from providers.base import ToolParam

# Project root is one level up from agent/
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# ─── Tool schemas (provider-agnostic ToolParam objects) ───────────────────────

TOOLS: list[ToolParam] = [
    ToolParam(
        name="read_file",
        description=(
            "Read the contents of a file in the project. "
            "Path is relative to the project root."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root, e.g. src/App.jsx",
                }
            },
            "required": ["path"],
        },
    ),
    ToolParam(
        name="write_file",
        description=(
            "Write (or overwrite) a file in the project. "
            "Creates parent directories if needed. "
            "Path is relative to the project root."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["path", "content"],
        },
    ),
    ToolParam(
        name="list_directory",
        description=(
            "List files and directories at a path in the project. "
            "Path is relative to the project root. Defaults to root if omitted."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to project root.",
                    "default": ".",
                }
            },
            "required": [],
        },
    ),
    ToolParam(
        name="run_command",
        description=(
            "Run a shell command in the project root directory. "
            "Use this to run `npm run build`, `npm run dev`, etc. "
            "Always run `npm run build` after making file changes to verify the project compiles."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run, e.g. 'npm run build'",
                }
            },
            "required": ["command"],
        },
    ),
]


# ─── Tool implementations ──────────────────────────────────────────────────────

def _safe_path(relative: str) -> Path:
    """Resolve a relative path, ensuring it stays inside PROJECT_ROOT."""
    resolved = (PROJECT_ROOT / relative).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path escape attempt blocked: {relative}")
    return resolved


def tool_read_file(path: str) -> str:
    target = _safe_path(path)
    if not target.exists():
        return f"ERROR: File not found: {path}"
    if not target.is_file():
        return f"ERROR: Not a file: {path}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading file: {e}"


def tool_write_file(path: str, content: str) -> str:
    target = _safe_path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: Written {len(content)} chars to {path}"
    except Exception as e:
        return f"ERROR writing file: {e}"


def tool_list_directory(path: str = ".") -> str:
    target = _safe_path(path)
    if not target.exists():
        return f"ERROR: Directory not found: {path}"
    if not target.is_dir():
        return f"ERROR: Not a directory: {path}"
    try:
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for entry in entries:
            if entry.name in ("node_modules", ".git", "dist", "__pycache__"):
                continue
            prefix = "📁 " if entry.is_dir() else "📄 "
            lines.append(f"{prefix}{entry.name}")
        return "\n".join(lines) if lines else "(empty)"
    except Exception as e:
        return f"ERROR listing directory: {e}"


def tool_run_command(command: str) -> str:
    # Safety: block obviously dangerous commands
    blocked = ["rm -rf", "sudo", "curl", "wget", "pip install", "npm install"]
    for b in blocked:
        if b in command.lower():
            return f"ERROR: Command blocked for safety: '{b}' is not allowed."
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = []
        if result.stdout.strip():
            output.append(result.stdout.strip())
        if result.stderr.strip():
            output.append(f"[stderr]\n{result.stderr.strip()}")
        output.append(f"[exit code: {result.returncode}]")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 60 seconds."
    except Exception as e:
        return f"ERROR running command: {e}"


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def run_tool(name: str, inputs: dict) -> str:
    """Dispatch a tool call by name and return its string result."""
    if name == "read_file":
        return tool_read_file(inputs["path"])
    elif name == "write_file":
        return tool_write_file(inputs["path"], inputs["content"])
    elif name == "list_directory":
        return tool_list_directory(inputs.get("path", "."))
    elif name == "run_command":
        return tool_run_command(inputs["command"])
    else:
        return f"ERROR: Unknown tool '{name}'"
