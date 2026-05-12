"""
graph.py — LangGraph state machine.
Nodes now receive project_root instead of a model object.
"""

from langgraph.graph import StateGraph, END
from pathlib import Path

from state import AgentState
from nodes import manager_node, developer_node, reviewer_node, tester_node


def route_manager(state: AgentState) -> str:
    return END if state["next"] == "done" else "developer"

def route_reviewer(state: AgentState) -> str:
    return state["next"]

def route_tester(state: AgentState) -> str:
    return state["next"]


def build_graph(project_root: Path):
    """Build and compile the graph. Only needs project_root now — no models."""

    def manager(state):   return manager_node(state,   project_root)
    def developer(state): return developer_node(state, project_root)
    def reviewer(state):  return reviewer_node(state,  project_root)
    def tester(state):    return tester_node(state,    project_root)

    graph = StateGraph(AgentState)
    graph.add_node("manager",   manager)
    graph.add_node("developer", developer)
    graph.add_node("reviewer",  reviewer)
    graph.add_node("tester",    tester)

    graph.set_entry_point("manager")
    graph.add_conditional_edges("manager",  route_manager,  {"developer": "developer", END: END})
    graph.add_edge("developer", "reviewer")
    graph.add_conditional_edges("reviewer", route_reviewer, {"tester": "tester", "developer": "developer"})
    graph.add_conditional_edges("tester",   route_tester,   {"manager": "manager",   "developer": "developer"})

    return graph.compile()