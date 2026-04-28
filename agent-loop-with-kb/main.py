"""
Knitwit Agent — standalone CLI.

Usage:
    python main.py "Add a drop-shoulder pattern"
    python main.py                            (interactive)
    python main.py --config /path/to/agent.config.json "task"
    python main.py --project /path/to/project "task"
"""

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

DEFAULT_CONFIG = Path(__file__).parent / "agent.config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        console.print(f"[red]Config not found:[/red] {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def resolve_project_root(cfg: dict, config_path: Path, cli_override: str | None) -> Path:
    """
    Project root resolution order:
      1. --project CLI flag
      2. project_path in config (relative to config file location)
      3. current working directory
    """
    if cli_override:
        return Path(cli_override).resolve()
    if "project_path" in cfg:
        return (config_path.parent / cfg["project_path"]).resolve()
    return Path.cwd()


def print_summary(cfg: dict, project_root: Path):
    console.print(f"\n[bold]Project:[/bold] {project_root}")
    claude_md = project_root / "CLAUDE.md"
    if claude_md.exists():
        console.print(f"[dim]CLAUDE.md found ✓[/dim]")
    else:
        console.print(f"[yellow]No CLAUDE.md in project root — agent will proceed without briefing[/yellow]")

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Agent")
    table.add_column("Provider")
    table.add_column("Model", style="cyan")
    for role in ("manager", "developer"):
        c = cfg[role]
        table.add_row(role.capitalize(), c.get("provider", "?"), c.get("model", "?"))
    console.print(table)
    console.print()


def main():
    args = sys.argv[1:]

    # Parse --config
    config_path = DEFAULT_CONFIG
    if "--config" in args:
        i = args.index("--config")
        config_path = Path(args[i + 1])
        args = args[:i] + args[i + 2:]

    # Parse --project
    project_override = None
    if "--project" in args:
        i = args.index("--project")
        project_override = args[i + 1]
        args = args[:i] + args[i + 2:]

    cfg = load_config(config_path)

    # Resolve project root and inject into tools + agents
    project_root = resolve_project_root(cfg, config_path, project_override)

    if not project_root.exists():
        console.print(f"[red]Project path does not exist:[/red] {project_root}")
        sys.exit(1)

    import tools
    import agents
    tools.set_project_root(project_root)
    agents.set_project_root(project_root)

    # Build providers
    from providers import make_provider
    try:
        manager_provider   = make_provider(cfg["manager"])
        developer_provider = make_provider(cfg["developer"])
    except (EnvironmentError, ValueError) as e:
        console.print(f"[bold red]Provider error:[/bold red] {e}")
        sys.exit(1)

    console.print("\n[bold]Knitwit Agent[/bold]\n")
    print_summary(cfg, project_root)

    task = " ".join(args).strip() if args else ""
    if not task:
        task = Prompt.ask("[yellow]What should the agent do?[/yellow]")

    if not task.strip():
        console.print("[red]No task provided.[/red]")
        sys.exit(1)

    from loop import run
    run(task, manager_provider=manager_provider, developer_provider=developer_provider)


if __name__ == "__main__":
    main()
