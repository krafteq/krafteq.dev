"""
Reviewer node.

Reads the developer's work summary from state['dev_output'] and can also
inspect actual files using read-only tools. Decides:
  DECISION: approved      → graph moves to tester
  DECISION: needs_changes → graph loops back to developer
"""

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import REVIEWER_PROMPT
from tools import REVIEWER_TOOLS, execute_tool

console = Console()
MAX_STEPS = 10


def reviewer_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold yellow]Reviewer", style="yellow"))

    context = (
        f"Task: {state['task']}\n\n"
        f"Developer's work summary:\n{state['dev_output']}\n\n"
        "Please review this work. You can read files to verify correctness."
    )

    messages = [
        SystemMessage(content=REVIEWER_PROMPT),
        HumanMessage(content=context),
    ]

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

    # Parse the decision
    next_node = "tester" if "DECISION: approved" in final_text else "developer"
    feedback = final_text if next_node == "developer" else ""

    return {
        "messages": [AIMessage(content=f"[Reviewer]\n{final_text}")],
        "feedback": feedback,
        "next": next_node,
    }


def _fmt(args: dict) -> str:
    return ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())
