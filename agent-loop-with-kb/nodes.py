"""
Agent nodes — each one calls Claude Code as a subprocess.

No LangChain models, no API keys, no tool schemas.
Claude Code handles all file reading, writing, and shell execution natively.
"""

from langchain_core.messages import AIMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import manager_prompt, developer_prompt, reviewer_prompt, tester_prompt
from claude_code import run, DEVELOPER_TOOLS, REVIEWER_TOOLS, TESTER_TOOLS

console = Console()
MAX_ITERATIONS = 6


# ── Manager ───────────────────────────────────────────────────────────────────

def manager_node(state: AgentState, project_root) -> dict:
    console.print(Rule("[bold green]Manager", style="green"))

    prompt   = manager_prompt(state["task"], state.get("feedback", ""))
    response = run(prompt, cwd=project_root, allowed_tools=["Read"])

    console.print(Markdown(response))

    if "DECISION: done" in response or state["iterations"] >= MAX_ITERATIONS:
        status, next_node = "done", "done"
    else:
        status, next_node = "working", "work"

    return {
        "messages":   [AIMessage(content=f"[Manager]\n{response}")],
        "plan":       response,
        "status":     status,
        "next":       next_node,
        "iterations": state["iterations"],
    }


# ── Developer ─────────────────────────────────────────────────────────────────

def developer_node(state: AgentState, project_root) -> dict:
    console.print(Rule("[bold blue]Developer", style="blue"))

    prompt   = developer_prompt(state["task"], state["plan"], state.get("feedback", ""))
    response = run(prompt, cwd=project_root, allowed_tools=DEVELOPER_TOOLS)

    console.print(Markdown(response))

    return {
        "messages":   [AIMessage(content=f"[Developer]\n{response}")],
        "dev_output": response,
        "feedback":   "",
        "next":       "reviewer",
    }


# ── Reviewer ──────────────────────────────────────────────────────────────────

def reviewer_node(state: AgentState, project_root) -> dict:
    console.print(Rule("[bold yellow]Reviewer", style="yellow"))

    prompt   = reviewer_prompt(state["task"], state["dev_output"])
    response = run(prompt, cwd=project_root, allowed_tools=REVIEWER_TOOLS)

    console.print(Markdown(response))

    next_node = "tester" if "DECISION: approved" in response else "developer"

    return {
        "messages": [AIMessage(content=f"[Reviewer]\n{response}")],
        "feedback": response if next_node == "developer" else "",
        "next":     next_node,
    }


# ── Tester ────────────────────────────────────────────────────────────────────

def tester_node(state: AgentState, project_root) -> dict:
    console.print(Rule("[bold red]Tester", style="red"))

    prompt   = tester_prompt(state["task"], state["dev_output"])
    response = run(prompt, cwd=project_root, allowed_tools=TESTER_TOOLS)

    console.print(Markdown(response))

    passed    = "DECISION: passed" in response
    next_node = "manager" if passed else "developer"

    return {
        "messages":   [AIMessage(content=f"[Tester]\n{response}")],
        "feedback":   response,
        "next":       next_node,
        "iterations": state["iterations"] + 1,
    }