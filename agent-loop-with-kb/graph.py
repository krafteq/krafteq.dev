"""
graph.py — builds the LangGraph StateGraph.

This is where the architecture lives:
  - Nodes are added with graph.add_node()
  - Fixed edges with graph.add_edge()
  - Conditional edges with graph.add_conditional_edges()
    (a router function reads state and returns the next node name)
"""

from langgraph.graph import StateGraph, END

from state import AgentState
from tools import DEVELOPER_TOOLS, REVIEWER_TOOLS, TESTER_TOOLS
from nodes.manager   import manager_node
from nodes.developer import developer_node
from nodes.reviewer  import reviewer_node
from nodes.tester    import tester_node


# ── Routing functions ─────────────────────────────────────────────────────────
# These read state["next"] (set by each node) and return the node name to go to.

def route_manager(state: AgentState) -> str:
    """After manager: done → END, else → developer."""
    return END if state["next"] == "done" else "developer"


def route_reviewer(state: AgentState) -> str:
    """After reviewer: approved → tester, needs_changes → developer."""
    return state["next"]   # "tester" or "developer"


def route_tester(state: AgentState) -> str:
    """After tester: passed → manager, failed → developer."""
    return state["next"]   # "manager" or "developer"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(manager_model, developer_model, reviewer_model, tester_model):
    """
    Wire up models to nodes, add all edges, compile and return the graph.

    bind_tools() tells the LLM which tools it can call and sends their
    schemas in the API request. The tool EXECUTION happens inside each
    node's own loop (not via LangGraph's ToolNode).
    """
    dev_model      = developer_model.bind_tools(DEVELOPER_TOOLS)
    reviewer_model = reviewer_model.bind_tools(REVIEWER_TOOLS)
    tester_model   = tester_model.bind_tools(TESTER_TOOLS)

    # Wrap each node as a closure so it receives its model without extra args
    def manager(state):   return manager_node(state,   manager_model)
    def developer(state): return developer_node(state, dev_model)
    def reviewer(state):  return reviewer_node(state,  reviewer_model)
    def tester(state):    return tester_node(state,    tester_model)

    # ── Build the graph ───────────────────────────────────────────────────────
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("manager",   manager)
    graph.add_node("developer", developer)
    graph.add_node("reviewer",  reviewer)
    graph.add_node("tester",    tester)

    # Entry point
    graph.set_entry_point("manager")

    # Edges
    graph.add_conditional_edges("manager",  route_manager,  {"developer": "developer", END: END})
    graph.add_edge("developer", "reviewer")                  # developer always goes to reviewer
    graph.add_conditional_edges("reviewer", route_reviewer, {"tester": "tester", "developer": "developer"})
    graph.add_conditional_edges("tester",   route_tester,   {"manager": "manager",   "developer": "developer"})

    return graph.compile()
