"""
Core agentic loop — provider-agnostic.

Flow:
  User task
    → Manager plans
      → Developer executes (tool loop)
        → Manager reviews
          → DONE or REVISION → loop again
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

from providers.base import BaseProvider, ToolResult
from tools import TOOLS, run_tool
from agents import manager_system_prompt, DEVELOPER_SYSTEM_PROMPT

console = Console()

MAX_MANAGER_ROUNDS  = 6
MAX_DEVELOPER_STEPS = 20


# ─── Developer (has tools, loops until no more tool calls) ────────────────────

def run_developer(
    provider: BaseProvider,
    task: str,
    history: list[dict],
) -> tuple[str, list[dict]]:

    console.print(Rule(f"[bold blue]Developer  [{provider.name}]", style="blue"))

    history = history + [{"role": "user", "content": task}]

    for _ in range(MAX_DEVELOPER_STEPS):
        response = provider.chat(
            system=DEVELOPER_SYSTEM_PROMPT,
            messages=history,
            tools=TOOLS,
        )

        # Print any text the developer produces
        if response.text.strip():
            console.print(Markdown(response.text))

        # No tool calls → developer is done
        if not response.tool_calls:
            history = history + [
                provider.make_assistant_history_entry(response, None)
            ]
            return response.text, history

        # Execute each tool call
        tool_results = []
        for tc in response.tool_calls:
            console.print(
                f"  [dim]🔧 {tc.name}([/dim]"
                f"[cyan]{_summarise(tc.inputs)}[/cyan][dim])[/dim]"
            )
            result = run_tool(tc.name, tc.inputs)
            preview = result[:200] + "…" if len(result) > 200 else result
            console.print(f"  [dim]   → {preview}[/dim]")
            tool_results.append(ToolResult(tool_call_id=tc.id, content=result))

        # Append assistant turn + tool results to history
        history = history + [
            provider.make_assistant_history_entry(response, None),
            provider.make_tool_result_entry(tool_results),
        ]

    return "Developer reached max steps without finishing.", history


# ─── Manager (no tools, plans and reviews) ───────────────────────────────────

def run_manager(
    provider: BaseProvider,
    user_message: str,
    history: list[dict],
) -> tuple[str, list[dict]]:

    history = history + [{"role": "user", "content": user_message}]
    response = provider.chat(
        system=manager_system_prompt(),
        messages=history,
    )
    text = response.text
    history = history + [{"role": "assistant", "content": text}]

    console.print(Rule(f"[bold green]Manager  [{provider.name}]", style="green"))
    console.print(Markdown(text))
    return text, history


# ─── Main orchestration ───────────────────────────────────────────────────────

def run(task: str, manager_provider: BaseProvider, developer_provider: BaseProvider):
    console.print(Panel(f"[bold]Task:[/bold] {task}", style="yellow", expand=False))

    manager_history   = []
    developer_history = []

    manager_response, manager_history = run_manager(
        manager_provider, task, manager_history
    )

    for round_num in range(MAX_MANAGER_ROUNDS):
        dev_task = _extract_task(manager_response)

        if not dev_task:
            console.print("[yellow]Manager did not produce a TASK — ending.[/yellow]")
            break

        dev_response, developer_history = run_developer(
            developer_provider, dev_task, developer_history
        )

        review_input = f"Developer report:\n\n{dev_response}"
        manager_response, manager_history = run_manager(
            manager_provider, review_input, manager_history
        )

        if "DONE" in manager_response.upper():
            console.print(Panel("✅  Task complete!", style="bold green", expand=False))
            break

        if round_num == MAX_MANAGER_ROUNDS - 1:
            console.print(Panel("⚠️  Reached max review rounds.", style="yellow", expand=False))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_task(text: str) -> str | None:
    upper = text.upper()
    if "TASK:" in upper:
        return text[upper.index("TASK:") + 5:].strip()
    if "DONE" in upper:
        return None
    return text.strip()


def _summarise(inputs: dict) -> str:
    parts = []
    for k, v in inputs.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "…"
        parts.append(f"{k}={s!r}")
    return ", ".join(parts)
