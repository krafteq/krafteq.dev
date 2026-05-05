"""
graph.py — builds the LangGraph StateGraph.
"""

from langgraph.graph import StateGraph, END

from state import AgentState
from tools import DEVELOPER_TOOLS, REVIEWER_TOOLS, TESTER_TOOLS
from nodes import manager_node, developer_node, reviewer_node, tester_node


def route_manager(state: AgentState) -> str:
    return END if state["next"] == "done" else "developer"

def route_reviewer(state: AgentState) -> str:
    return state["next"]

def route_tester(state: AgentState) -> str:
    return state["next"]


def build_graph(manager_model, developer_model, reviewer_model, tester_model):
    dev_model  = developer_model.bind_tools(DEVELOPER_TOOLS)
    rev_model  = reviewer_model.bind_tools(REVIEWER_TOOLS)
    test_model = tester_model.bind_tools(TESTER_TOOLS)

    def manager(state):   return manager_node(state,   manager_model)
    def developer(state): return developer_node(state, dev_model)
    def reviewer(state):  return reviewer_node(state,  rev_model)
    def tester(state):    return tester_node(state,    test_model)

    graph = StateGraph(AgentState)
    graph.add_node("manager",   manager)
    graph.add_node("developer", developer)
    graph.add_node("reviewer",  reviewer)
    graph.add_node("tester",    tester)

    graph.set_entry_point("manager")
    graph.add_conditional_edges("manager",  route_manager,  {"developer": "developer", END: END})
    graph.add_edge("developer", "reviewer")
    graph.add_conditional_edges("reviewer", route_reviewer, {"tester": "tester", "developer": "developer"})
    graph.add_conditional_edges("tester",   route_tester,   {"manager": "manager", "developer": "developer"})

    return graph.compile()