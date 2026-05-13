"""
Git utilities — cloning, branching, committing, cleanup.
"""

import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from rich.console import Console

console = Console()


# ── URL detection ─────────────────────────────────────────────────────────────

def is_git_url(value: str) -> bool:
    if not value:
        return False
    prefixes = ("https://", "http://", "git@", "git://", "ssh://")
    return any(value.startswith(p) for p in prefixes) or value.endswith(".git")


# ── Clone ─────────────────────────────────────────────────────────────────────

def clone(repo_url: str, branch: str = "main") -> Path:
    """Clone a repo into a temp dir. Returns the path."""
    tmp = Path(tempfile.mkdtemp(prefix="knitwit-agent-"))
    console.print(f"[dim]Cloning [cyan]{repo_url}[/cyan] (branch: {branch})…[/dim]")

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(tmp)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        if "Remote branch" in result.stderr or "not found" in result.stderr.lower():
            console.print(f"[yellow]Branch '{branch}' not found — using default branch.[/yellow]")
            result2 = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(tmp)],
                capture_output=True, text=True,
            )
            if result2.returncode != 0:
                raise RuntimeError(f"Git clone failed:\n{result2.stderr.strip()}")
            console.print(f"[dim]Cloned to {tmp}[/dim]")
            return tmp
        raise RuntimeError(f"Git clone failed:\n{result.stderr.strip()}")

    console.print(f"[dim]Cloned to {tmp}[/dim]")
    return tmp


# ── Branch management ─────────────────────────────────────────────────────────

def branch_name_from_ticket(key: str, summary: str) -> str:
    """
    Generate a clean branch name from a Jira ticket.

    KAN-2 + "jira_utils.py"  →  feat/KAN-2-jira-utils
    KAN-5 + "Add dark mode"  →  feat/KAN-5-add-dark-mode
    """
    # Slugify the summary — lowercase, replace non-alphanumeric with hyphens
    slug = summary.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)  # replace anything not a-z/0-9 with -
    slug = slug.strip("-")[:40]               # max 40 chars, no leading/trailing hyphens
    slug = re.sub(r"-+", "-", slug)           # collapse multiple hyphens

    return f"feat/{key}-{slug}"


def create_branch(repo_root: Path, branch: str) -> bool:
    """Create and checkout a new branch. Returns True on success."""
    r = subprocess.run(
        ["git", "checkout", "-b", branch],
        cwd=repo_root, capture_output=True, text=True,
    )
    if r.returncode == 0:
        console.print(f"[dim]Created branch: [bold]{branch}[/bold][/dim]")
        return True
    console.print(f"[yellow]Could not create branch '{branch}': {r.stderr.strip()}[/yellow]")
    return False


def commit_and_push(repo_root: Path, message: str) -> bool:
    """
    Stage all changes, commit, and push the current branch.
    Returns True if push succeeded.
    """
    # Stage everything
    subprocess.run(["git", "add", "-A"], cwd=repo_root)

    # Check if there's anything to commit
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if not status.stdout.strip():
        console.print("[dim]Git: nothing to commit.[/dim]")
        return False

    # Commit
    r = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root, capture_output=True, text=True,
    )
    if r.returncode != 0:
        console.print(f"[yellow]Git commit failed: {r.stderr.strip()}[/yellow]")
        return False
    console.print(f"[dim]Committed: {message}[/dim]")

    # Push
    branch = current_branch(repo_root)
    r = subprocess.run(
        ["git", "push", "--set-upstream", "origin", branch],
        cwd=repo_root, capture_output=True, text=True,
    )
    if r.returncode != 0:
        console.print(f"[yellow]Git push failed: {r.stderr.strip()}[/yellow]")
        return False

    console.print(f"[dim]Pushed branch [bold]{branch}[/bold] to origin.[/dim]")
    return True


# ── Helpers ───────────────────────────────────────────────────────────────────

def current_branch(repo_root: Path) -> str:
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root, capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def cleanup(tmp_dir: Path):
    if tmp_dir and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        console.print(f"[dim]Cleaned up temp clone: {tmp_dir}[/dim]")