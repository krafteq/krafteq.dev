"""
Git utilities — cloning, validation, cleanup.
Kept separate from main.py so the logic is easy to test and extend.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from rich.console import Console

console = Console()


def is_git_url(value: str) -> bool:
    """Return True if the string looks like a git remote URL."""
    if not value:
        return False
    prefixes = ("https://", "http://", "git@", "git://", "ssh://")
    return any(value.startswith(p) for p in prefixes) or value.endswith(".git")


def clone(repo_url: str, branch: str = "main") -> Path:
    """
    Clone a git repo into a temporary directory.
    Returns the path to the cloned repo root.
    Raises RuntimeError if cloning fails.
    """
    tmp = Path(tempfile.mkdtemp(prefix="knitwit-agent-"))
    console.print(f"[dim]Cloning [cyan]{repo_url}[/cyan] (branch: {branch})…[/dim]")

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(tmp)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)

        # If branch not found, try without --branch (uses default branch)
        if "Remote branch" in result.stderr or "not found" in result.stderr.lower():
            console.print(
                f"[yellow]Branch '{branch}' not found — cloning default branch instead.[/yellow]"
            )
            result2 = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(tmp)],
                capture_output=True,
                text=True,
            )
            if result2.returncode != 0:
                raise RuntimeError(
                    f"Git clone failed:\n{result2.stderr.strip()}"
                )
            console.print(f"[dim]Cloned to {tmp}[/dim]")
            return tmp

        raise RuntimeError(f"Git clone failed:\n{result.stderr.strip()}")

    console.print(f"[dim]Cloned to {tmp}[/dim]")
    return tmp


def current_branch(repo_root: Path) -> str:
    """Return the current branch name of a local repo."""
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def cleanup(tmp_dir: Path):
    """Delete a temporary clone. Call this on exit."""
    if tmp_dir and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f"[dim]Cleaned up temp clone: {tmp_dir}[/dim]")
