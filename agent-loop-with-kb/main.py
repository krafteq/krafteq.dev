"""
Knitwit Agent — entry point.

Usage:
    python main.py "Add a drop-shoulder pattern"
    python main.py                                          (interactive)
    python main.py --repo https://github.com/you/repo "task"
    python main.py --repo https://github.com/you/repo --branch dev "task"
    python main.py --project /path/to/local/project "task"
    python main.py --config /path/to/agent.config.json "task"
"""

import sys
import atexit
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

console = Console()
DEFAULT_CONFIG = Path(__file__).parent / "agent.config.json"


def main():
    args = sys.argv[1:]

    # ── Parse CLI flags ───────────────────────────────────────────────────────
    config_path, args  = _pop_flag(args, "--config",  DEFAULT_CONFIG, as_path=True)
    cli_repo,    args  = _pop_flag(args, "--repo",    None)
    cli_branch,  args  = _pop_flag(args, "--branch",  None)
    cli_project, args  = _pop_flag(args, "--project", None)

    # ── Load config ───────────────────────────────────────────────────────────
    from config import load_config, make_model, get_agent_cfg
    cfg = load_config(Path(config_path))

    # ── Resolve project root (local or git clone) ─────────────────────────────
    from git_utils import is_git_url, clone, current_branch, cleanup

    tmp_clone = None
    cfg_repo  = cfg.get("repo", "").strip()

    if cli_repo or (cfg_repo and is_git_url(cfg_repo)):
        repo_url = cli_repo or cfg_repo
        branch   = cli_branch or cfg.get("branch", "main")
        project_root = clone(repo_url, branch)
        tmp_clone    = project_root
        console.print(f"[dim]Branch: {current_branch(project_root)}[/dim]")
        atexit.register(lambda: cleanup(tmp_clone))
    elif cli_project:
        project_root = Path(cli_project).resolve()
    elif "project_path" in cfg and cfg["project_path"]:
        project_root = (Path(config_path).parent / cfg["project_path"]).resolve()
    else:
        project_root = Path.cwd()

    if not project_root.exists():
        console.print(f"[red]Project not found:[/red] {project_root}")
        sys.exit(1)

    # ── Inject project root into tools + agents ───────────────────────────────
    import tools as _tools
    import agents as _agents
    _tools.set_project_root(project_root)
    _agents.set_project_root(project_root)

    # ── Build models ──────────────────────────────────────────────────────────
    try:
        manager_model   = make_model(get_agent_cfg(cfg, "manager"))
        developer_model = make_model(get_agent_cfg(cfg, "developer"))
        reviewer_model  = make_model(get_agent_cfg(cfg, "reviewer"))
        tester_model    = make_model(get_agent_cfg(cfg, "tester"))
    except (EnvironmentError, ImportError, ValueError) as e:
        console.print(f"[bold red]Model error:[/bold red] {e}")
        sys.exit(1)

    # ── Print summary ─────────────────────────────────────────────────────────
    console.print(f"\n[bold]Knitwit Agent[/bold]  —  LangGraph\n")
    console.print(f"[bold]Project:[/bold] {project_root}")
    claude_md = project_root / "CLAUDE.md"
    console.print(f"[dim]CLAUDE.md: {'found ✓' if claude_md.exists() else 'not found'}[/dim]\n")

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Node")
    table.add_column("Provider")
    table.add_column("Model", style="cyan")
    for role, model_obj in [
        ("manager",   manager_model),
        ("developer", developer_model),
        ("reviewer",  reviewer_model),
        ("tester",    tester_model),
    ]:
        # Extract model name from the LangChain object
        name = getattr(model_obj, "model_name", None) or getattr(model_obj, "model", "?")
        provider = type(model_obj).__name__.replace("Chat", "")
        table.add_row(role.capitalize(), provider, name)
    console.print(table)
    console.print()

    # ── Get task ──────────────────────────────────────────────────────────────
    task = " ".join(args).strip() if args else ""
    if not task:
        task = Prompt.ask("[yellow]What should the agent do?[/yellow]")
    if not task.strip():
        console.print("[red]No task provided.[/red]")
        sys.exit(1)

    console.print(Panel(f"[bold]Task:[/bold] {task}", style="yellow", expand=False))

    # ── Build and run the graph ───────────────────────────────────────────────
    from graph import build_graph

    app = build_graph(manager_model, developer_model, reviewer_model, tester_model)

    initial_state = {
        "task":       task,
        "plan":       "",
        "dev_output": "",
        "feedback":   "",
        "iterations": 0,
        "status":     "working",
        "next":       "",
        "messages":   [],
    }

    final_state = app.invoke(initial_state)

    console.print(Panel(
        f"✅  Done after {final_state['iterations']} iteration(s).",
        style="bold green",
        expand=False,
    ))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pop_flag(args, flag, default, as_path=False):
    """Extract --flag value from args list, return (value, remaining_args)."""
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
