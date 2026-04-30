"""
Tester node.

Runs shell commands (npm run build, etc.) to verify the implementation.
Has its own tool loop like the developer. Reports to manager on completion:
  DECISION: passed → graph returns to manager for review
  DECISION: failed → graph loops back to developer with failure details
"""

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import TESTER_PROMPT
from tools import TESTER_TOOLS, execute_tool

console = Console()
MAX_STEPS = 10


def tester_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold red]Tester", style="red"))

    messages = [
        SystemMessage(content=TESTER_PROMPT),
        HumanMessage(content=(
            f"Task: {state['task']}\n\n"
            f"The developer has finished their work:\n{state['dev_output']}\n\n"
            "Please verify the implementation by running the build."
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

    # Parse the decision
    passed = "DECISION: passed" in final_text
    next_node = "manager" if passed else "developer"

    return {
        "messages": [AIMessage(content=f"[Tester]\n{final_text}")],
        "feedback": final_text,
        "next": next_node,
        # Increment iteration counter — one full cycle just completed
        "iterations": state["iterations"] + 1,
    }


def _fmt(args: dict) -> str:
    return ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())
