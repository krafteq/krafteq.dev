"""
claude_code.py — runs Claude Code as a subprocess.

Claude Code is the developer engine. Every node that needs to
do real work (read files, write code, run builds) calls this.

Claude Code CLI reference:
  claude -p "prompt"                    non-interactive, prints response
  claude -p "prompt" --output-format json   structured JSON output
  claude --allowedTools "Read,Write,Bash"   restrict available tools
  claude --cwd /path/to/project             set working directory
"""

import subprocess
import json
from pathlib import Path
from rich.console import Console

console = Console()


def run(
    prompt: str,
    cwd: Path,
    allowed_tools: list[str] | None = None,
    max_turns: int = 20,
) -> str:
    """
    Run Claude Code non-interactively on a prompt.
    Returns the text response.

    allowed_tools examples:
      ["Read", "Write", "Bash"]          — full developer access
      ["Read"]                           — read-only (reviewer)
      ["Bash"]                           — shell only (tester)
    """
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "json",
        "--max-turns", str(max_turns),
    ]

    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]

    console.print(f"  [dim]⚡ claude -p {prompt[:80]}…[/dim]")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max per node call
        )

        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            return f"ERROR: Claude Code exited with code {result.returncode}:\n{err}"

        # Parse JSON output
        raw = result.stdout.strip()
        try:
            data = json.loads(raw)
            # Claude Code JSON output has a 'result' field with the text
            return data.get("result", raw)
        except json.JSONDecodeError:
            # Fall back to raw output if not valid JSON
            return raw

    except subprocess.TimeoutExpired:
        return "ERROR: Claude Code timed out after 5 minutes."
    except FileNotFoundError:
        return (
            "ERROR: 'claude' command not found. "
            "Install Claude Code with: npm install -g @anthropic-ai/claude-code"
        )
    except Exception as e:
        return f"ERROR: {e}"


# ── Tool sets — passed as --allowedTools ──────────────────────────────────────

DEVELOPER_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
REVIEWER_TOOLS  = ["Read", "Glob", "Grep"]
TESTER_TOOLS    = ["Read", "Bash"]