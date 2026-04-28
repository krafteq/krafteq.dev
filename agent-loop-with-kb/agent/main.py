"""
Knitwit Agent — CLI entry point.

Usage:
    python main.py "Add a drop-shoulder pattern"
    python main.py                  (interactive mode)
    python main.py --config path/to/agent.config.json "task..."
"""

import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

DEFAULT_CONFIG = Path(__file__).parent / "agent.config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        console.print(f"[red]Config file not found:[/red] {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def print_config_summary(cfg: dict):
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Agent",    style="bold")
    table.add_column("Provider")
    table.add_column("Model",    style="cyan")
    table.add_column("Key env")
    for role in ("manager", "developer"):
        c = cfg[role]
        table.add_row(
            role.capitalize(),
            c.get("provider", "?"),
            c.get("model", "?"),
            c.get("api_key_env", "—"),
        )
    console.print(table)
    console.print()


def main():
    args = sys.argv[1:]

    # --config flag
    config_path = DEFAULT_CONFIG
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 >= len(args):
            console.print("[red]--config requires a path argument[/red]")
            sys.exit(1)
        config_path = Path(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    cfg = load_config(config_path)

    # Build providers (this validates env vars early)
    from providers import make_provider
    try:
        manager_provider   = make_provider(cfg["manager"])
        developer_provider = make_provider(cfg["developer"])
    except (EnvironmentError, ValueError) as e:
        console.print(f"[bold red]Config error:[/bold red] {e}")
        sys.exit(1)

    console.print("\n[bold]Knitwit Agent[/bold] — Manager + Developer\n")
    print_config_summary(cfg)

    # Task from remaining args or interactive prompt
    task = " ".join(args).strip() if args else ""
    if not task:
        task = Prompt.ask("[yellow]What should the agent do?[/yellow]")

    if not task.strip():
        console.print("[red]No task provided. Exiting.[/red]")
        sys.exit(1)

    from loop import run
    run(task, manager_provider=manager_provider, developer_provider=developer_provider)


if __name__ == "__main__":
    main()
