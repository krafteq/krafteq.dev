"""
Manager node.

Two modes depending on state['iterations']:
  0 → first call: read task, create plan, send to developer
  N → review call: read tester feedback, decide done or another cycle
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rich.console import Console
from rich.rule import Rule
from rich.markdown import Markdown

from state import AgentState
from agents import manager_prompt

console = Console()
MAX_ITERATIONS = 6


def manager_node(state: AgentState, model) -> dict:
    console.print(Rule("[bold green]Manager", style="green"))

    if state["iterations"] == 0:
        # First call — create a plan
        user_msg = HumanMessage(content=f"Task: {state['task']}")
    else:
        # Review call — tester has reported back
        user_msg = HumanMessage(content=(
            f"Task: {state['task']}\n\n"
            f"Tester results:\n{state['feedback']}"
        ))

    messages = [SystemMessage(content=manager_prompt()), user_msg]
    response = model.invoke(messages)
    text = response.content
    console.print(Markdown(text))

    # Parse the manager's decision
    if "DECISION: done" in text or state["iterations"] >= MAX_ITERATIONS:
        status = "done"
        next_node = "done"
    else:
        status = "working"
        next_node = "work"

    return {
        "messages": [AIMessage(content=f"[Manager]\n{text}")],
        "plan": text,
        "status": status,
        "next": next_node,
        "iterations": state["iterations"],  # incremented by tester, not manager
    }
