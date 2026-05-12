"""
Knitwit Agent — entry point.

Usage:
    python main.py
    python main.py "Add a drop-shoulder pattern"
    python main.py --repo https://github.com/you/repo "task"
    python main.py --repo https://github.com/you/repo --branch dev "task"
    python main.py --project /path/to/local/project "task"
    python main.py --config /path/to/agent.config.json "task"
"""

import sys
import json
import atexit
from pathlib import Path

# Always resolve agent dir first — must be before any local imports
AGENT_DIR = Path(__file__).parent.resolve()
if str(AGENT_DIR) in sys.path:
    sys.path.remove(str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR))

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()
DEFAULT_CONFIG = AGENT_DIR / "agent.config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        console.print(f"[red]Config not found:[/red] {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def main():
    args = sys.argv[1:]

    # ── Parse CLI flags ───────────────────────────────────────────────────────
    config_path, args  = _pop_flag(args, "--config",  DEFAULT_CONFIG, as_path=True)
    cli_repo,    args  = _pop_flag(args, "--repo",    None)
    cli_branch,  args  = _pop_flag(args, "--branch",  None)
    cli_project, args  = _pop_flag(args, "--project", None)

    cfg = load_config(Path(config_path))

    # ── Resolve project root ──────────────────────────────────────────────────
    from git_utils import is_git_url, clone, current_branch, cleanup

    tmp_clone = None
    cfg_repo  = cfg.get("repo", "").strip()

    if cli_repo or (cfg_repo and is_git_url(cfg_repo)):
        repo_url     = cli_repo or cfg_repo
        branch       = cli_branch or cfg.get("branch", "main")
        project_root = clone(repo_url, branch)
        tmp_clone    = project_root
        console.print(f"[dim]Branch: {current_branch(project_root)}[/dim]")
        atexit.register(lambda: cleanup(tmp_clone))
    elif cli_project:
        project_root = Path(cli_project).resolve()
    elif cfg.get("project_path"):
        project_root = (Path(config_path).parent / cfg["project_path"]).resolve()
    else:
        project_root = Path.cwd()

    if not project_root.exists():
        console.print(f"[red]Project not found:[/red] {project_root}")
        sys.exit(1)

    # Inject into agents (for CLAUDE.md loading)
    import agents as _agents
    _agents.set_project_root(project_root)

    # ── Print summary ─────────────────────────────────────────────────────────
    console.print(f"\n[bold]Knitwit Agent[/bold]  —  Claude Code\n")
    console.print(f"[bold]Project:[/bold] {project_root}")
    claude_md = project_root / "CLAUDE.md"
    console.print(f"[dim]CLAUDE.md: {'found ✓' if claude_md.exists() else 'not found'}[/dim]")
    console.print(f"[dim]Developer: Claude Code (claude CLI)[/dim]\n")

    # ── Get task: CLI arg → Jira → interactive prompt ─────────────────────────
    from jira_utils import make_jira_client, format_task

    task       = " ".join(args).strip() if args else ""
    jira       = make_jira_client(cfg)
    jira_issue = None

    if not task and jira:
        console.print("[dim]No task provided — checking Jira board…[/dim]")
        try:
            ticket = jira.fetch_next_ticket()
            if ticket:
                task       = format_task(ticket["summary"], ticket["description"], ticket["key"])
                jira_issue = ticket
                console.print(f"[dim]Pulled [bold]{ticket['key']}[/bold]: {ticket['summary']}[/dim]")
                jira.start_ticket(ticket["key"])
            else:
                console.print(f"[yellow]No '{jira.pull_status}' tickets on the board.[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Jira fetch failed: {e}[/yellow]")

    if not task:
        task = Prompt.ask("[yellow]What should the agent do?[/yellow]")

    if not task.strip():
        console.print("[red]No task provided.[/red]")
        sys.exit(1)

    label = (
        f"[bold]{jira_issue['key']}[/bold] — {jira_issue['summary']}"
        if jira_issue else task
    )
    console.print(Panel(f"[bold]Task:[/bold] {label}", style="yellow", expand=False))

    # ── Create branch ─────────────────────────────────────────────────────────
    from git_utils import branch_name_from_ticket, create_branch, commit_and_push

    if jira_issue:
        branch = branch_name_from_ticket(jira_issue["key"], jira_issue["summary"])
        create_branch(project_root, branch)

    # ── Build and run the graph ───────────────────────────────────────────────
    from graph import build_graph

    app = build_graph(project_root)

    final_state = app.invoke({
        "task":       task,
        "plan":       "",
        "dev_output": "",
        "feedback":   "",
        "iterations": 0,
        "status":     "working",
        "next":       "",
        "messages":   [],
    })

    # ── Commit, push, resolve Jira ────────────────────────────────────────────
    if jira_issue:
        pushed = commit_and_push(project_root, f"{jira_issue['key']}: {jira_issue['summary']}")
        if pushed:
            console.print("[dim]Branch ready for PR on GitHub.[/dim]")

    if jira and jira_issue:
        try:
            jira.complete_ticket(jira_issue["key"])
            jira.add_comment(
                jira_issue["key"],
                f"Agent completed after {final_state['iterations']} iteration(s).\n\n"
                f"Summary:\n{final_state.get('dev_output', '')[:1000]}"
            )
        except Exception as e:
            console.print(f"[yellow]Jira update failed: {e}[/yellow]")

    console.print(Panel(
        f"✅  Done after {final_state['iterations']} iteration(s).",
        style="bold green", expand=False,
    ))


def _pop_flag(args, flag, default, as_path=False):
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            console.print(f"[red]{flag} requires a value[/red]")
            sys.exit(1)
        value = args[i + 1]
        args  = args[:i] + args[i + 2:]
        return (Path(value) if as_path else value), args
    return (Path(default) if as_path and default else default), args


if __name__ == "__main__":
    main()