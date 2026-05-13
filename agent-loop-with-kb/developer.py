"""
Developer node.

Runs an INTERNAL tool loop — the LLM calls tools (read_file, write_file,
run_command, etc.) and keeps going until it produces a response with no
tool calls. Only then does the graph advance to the reviewer.

This inner loop is what makes it an agent and not a chatbot:
  LLM call → tool call → result → LLM call → tool call → ... → done
"""

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import DEVELOPER_PROMPT
from tools import DEVELOPER_TOOLS, execute_tool

console = Console()
MAX_STEPS = 20


def developer_node(state: AgentState, model) -> dict:
    """
    model here is already bound to DEVELOPER_TOOLS via model.bind_tools().
    The node runs its own loop — it does NOT rely on LangGraph's ToolNode.
    """
    console.print(Rule("[bold blue]Developer", style="blue"))

    # Build a fresh message thread for this developer session
    context = f"Task: {state['task']}\n\nManager's plan:\n{state['plan']}"
    if state.get("feedback"):
        context += f"\n\nFeedback to address:\n{state['feedback']}"

    messages = [
        SystemMessage(content=DEVELOPER_PROMPT),
        HumanMessage(content=context),
    ]

    final_text = "Developer did not produce a response."

    for step in range(MAX_STEPS):
        response = model.invoke(messages)
        messages.append(response)

        # Print any text the developer produces mid-loop
        if response.content and response.content.strip():
            console.print(Markdown(response.content))

        # No tool calls = developer is done with this session
        if not response.tool_calls:
            final_text = response.content
            break

        # Execute every requested tool call
        for tc in response.tool_calls:
            console.print(
                f"  [dim]🔧 {tc['name']}([/dim]"
                f"[cyan]{_fmt(tc['args'])}[/cyan][dim])[/dim]"
            )
            result = execute_tool(tc["name"], tc["args"])
            preview = result[:200] + "…" if len(result) > 200 else result
            console.print(f"  [dim]   → {preview}[/dim]")

            # Append tool result so the LLM sees it on the next iteration
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return {
        "messages": [AIMessage(content=f"[Developer]\n{final_text}")],
        "dev_output": final_text,
        "feedback": "",   # clear previous feedback
        "next": "reviewer",
    }


def _fmt(args: dict) -> str:
    parts = []
    for k, v in args.items():
        s = str(v)
        if len(s) > 50: s = s[:47] + "…"
        parts.append(f"{k}={s!r}")
    return ", ".join(parts)
