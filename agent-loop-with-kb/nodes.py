"""
All agent nodes in a single file — avoids Windows package resolution issues.
"""

# ── Manager ───────────────────────────────────────────────────────────────────

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import manager_prompt, DEVELOPER_PROMPT, REVIEWER_PROMPT, TESTER_PROMPT
from tools import DEVELOPER_TOOLS, REVIEWER_TOOLS, TESTER_TOOLS, execute_tool

console = Console()
MAX_MANAGER_ITERATIONS = 6
MAX_STEPS = 20


def manager_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold green]Manager", style="green"))

    if state["iterations"] == 0:
        user_msg = HumanMessage(content=f"Task: {state['task']}")
    else:
        user_msg = HumanMessage(content=(
            f"Task: {state['task']}\n\n"
            f"Tester results:\n{state['feedback']}"
        ))

    messages  = [SystemMessage(content=manager_prompt()), user_msg]
    response  = model.invoke(messages)
    text      = response.content
    console.print(Markdown(text))

    if "DECISION: done" in text or state["iterations"] >= MAX_MANAGER_ITERATIONS:
        status, next_node = "done", "done"
    else:
        status, next_node = "working", "work"

    return {
        "messages":   [AIMessage(content=f"[Manager]\n{text}")],
        "plan":       text,
        "status":     status,
        "next":       next_node,
        "iterations": state["iterations"],
    }


# ── Developer ─────────────────────────────────────────────────────────────────

def developer_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold blue]Developer", style="blue"))

    context = f"Task: {state['task']}\n\nManager's plan:\n{state['plan']}"
    if state.get("feedback"):
        context += f"\n\nFeedback to address:\n{state['feedback']}"

    messages   = [SystemMessage(content=DEVELOPER_PROMPT), HumanMessage(content=context)]
    final_text = "Developer did not produce a response."

    for _ in range(MAX_STEPS):
        response = model.invoke(messages)
        messages.append(response)

        if response.content and response.content.strip():
            console.print(Markdown(response.content))

        if not response.tool_calls:
            final_text = response.content
            break

        for tc in response.tool_calls:
            console.print(f"  [dim]🔧 {tc['name']}({_fmt(tc['args'])})[/dim]")
            result = execute_tool(tc["name"], tc["args"])
            preview = result[:200] + "…" if len(result) > 200 else result
            console.print(f"  [dim]   → {preview}[/dim]")
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return {
        "messages":   [AIMessage(content=f"[Developer]\n{final_text}")],
        "dev_output": final_text,
        "feedback":   "",
        "next":       "reviewer",
    }


# ── Reviewer ──────────────────────────────────────────────────────────────────

def reviewer_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold yellow]Reviewer", style="yellow"))

    context = (
        f"Task: {state['task']}\n\n"
        f"Developer's work summary:\n{state['dev_output']}\n\n"
        "Please review this work. You can read files to verify correctness."
    )
    messages   = [SystemMessage(content=REVIEWER_PROMPT), HumanMessage(content=context)]
    final_text = "Reviewer did not produce a response."

    for _ in range(MAX_STEPS):
        response = model.invoke(messages)
        messages.append(response)

        if response.content and response.content.strip():
            console.print(Markdown(response.content))

        if not response.tool_calls:
            final_text = response.content
            break

        for tc in response.tool_calls:
            console.print(f"  [dim]🔍 {tc['name']}({_fmt(tc['args'])})[/dim]")
            result = execute_tool(tc["name"], tc["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    next_node = "tester" if "DECISION: approved" in final_text else "developer"
    return {
        "messages": [AIMessage(content=f"[Reviewer]\n{final_text}")],
        "feedback": final_text if next_node == "developer" else "",
        "next":     next_node,
    }


# ── Tester ────────────────────────────────────────────────────────────────────

def tester_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold red]Tester", style="red"))

    messages = [
        SystemMessage(content=TESTER_PROMPT),
        HumanMessage(content=(
            f"Task: {state['task']}\n\n"
            f"Developer finished:\n{state['dev_output']}\n\n"
            "Please verify by running the build."
        )),
    ]
    final_text = "Tester did not produce a response."

    for _ in range(MAX_STEPS):
        response = model.invoke(messages)
        messages.append(response)

        if response.content and response.content.strip():
            console.print(Markdown(response.content))

        if not response.tool_calls:
            final_text = response.content
            break

        for tc in response.tool_calls:
            console.print(f"  [dim]⚙️  {tc['name']}({_fmt(tc['args'])})[/dim]")
            result = execute_tool(tc["name"], tc["args"])
            preview = result[:300] + "…" if len(result) > 300 else result
            console.print(f"  [dim]   → {preview}[/dim]")
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    passed    = "DECISION: passed" in final_text
    next_node = "manager" if passed else "developer"

    return {
        "messages":   [AIMessage(content=f"[Tester]\n{final_text}")],
        "feedback":   final_text,
        "next":       next_node,
        "iterations": state["iterations"] + 1,
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _fmt(args: dict) -> str:
    return ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())