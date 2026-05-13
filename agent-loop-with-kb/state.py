"""
AgentState — the single object that flows through every node in the graph.

LangGraph passes this dict into each node function and merges the returned
dict back into it. Fields with Annotated[list, add_messages] are appended
(not replaced) each time — everything else is a plain overwrite.
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Inputs (set once, never changed) ──────────────────────────────────────
    task: str                    # the original user task

    # ── Inter-agent communication ─────────────────────────────────────────────
    plan: str                    # manager's latest plan for the developer
    dev_output: str              # developer's work summary → reviewer reads this
    feedback: str                # reviewer or tester feedback → developer reads this

    # ── Control flow ──────────────────────────────────────────────────────────
    iterations: int              # how many full manager→dev→review→test cycles
    status: Literal["working", "done"]
    next: str                    # routing signal set by each node

    # ── Audit log ─────────────────────────────────────────────────────────────
    # add_messages means returned messages are APPENDED, not replaced.
    # Every node pushes its final response here for observability.
    messages: Annotated[list, add_messages]