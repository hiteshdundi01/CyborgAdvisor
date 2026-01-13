"""
LangGraph State Machine Definition

This module defines the complete graph for the Cyborg Advisor:
- Nodes for each processing step
- Edges defining the workflow
- Conditional routing based on state
- Human-in-the-loop checkpoints
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes.intent_parser import intent_parser, route_by_intent
from .nodes.financial_calculator import financial_calculator
from .nodes.compliance_check import compliance_check, route_by_compliance
from .nodes.response_generator import response_generator
from .nodes.human_review import (
    human_review,
    execute_trades,
    cancel_trades,
    route_by_approval,
)


def create_graph() -> StateGraph:
    """
    Create and configure the LangGraph state machine.
    
    Architecture:
    ```
    START
      │
      ▼
    intent_parser (LLM - System 1)
      │
      ├─[rebalance]──► financial_calculator (Python - System 2)
      │                      │
      │                      ▼
      │               compliance_check (Python - System 2)
      │                      │
      │                      ├─[pass]──► human_review (HITL)
      │                      │                │
      │                      │                ├─[approve]──► execute_trades
      │                      │                │                    │
      │                      │                └─[cancel]───► cancel_trades
      │                      │                                     │
      │                      └─[fail]──► response_generator ◄──────┘
      │                                         │
      └─[query/respond]──────────────────────────┘
                                                │
                                                ▼
                                              END
    ```
    
    Returns:
        StateGraph: Compiled graph ready for execution
    """
    # Initialize the graph with our state type
    graph = StateGraph(AgentState)
    
    # Add all nodes
    graph.add_node("intent_parser", intent_parser)
    graph.add_node("financial_calculator", financial_calculator)
    graph.add_node("compliance_check", compliance_check)
    graph.add_node("human_review", human_review)
    graph.add_node("execute_trades", execute_trades)
    graph.add_node("cancel_trades", cancel_trades)
    graph.add_node("response_generator", response_generator)
    
    # Set the entry point
    graph.set_entry_point("intent_parser")
    
    # Add conditional edge from intent_parser
    graph.add_conditional_edges(
        "intent_parser",
        route_by_intent,
        {
            "financial_calculator": "financial_calculator",
            "response_generator": "response_generator",
        }
    )
    
    # Financial calculator always goes to compliance check
    graph.add_edge("financial_calculator", "compliance_check")
    
    # Add conditional edge from compliance_check
    graph.add_conditional_edges(
        "compliance_check",
        route_by_compliance,
        {
            "human_review": "human_review",
            "response_generator": "response_generator",
        }
    )
    
    # Add conditional edge from human_review
    graph.add_conditional_edges(
        "human_review",
        route_by_approval,
        {
            "execute_trades": "execute_trades",
            "cancel_trades": "cancel_trades",
            "human_review": "human_review",  # Loop back if unclear
        }
    )
    
    # Terminal nodes go to END
    graph.add_edge("execute_trades", END)
    graph.add_edge("cancel_trades", END)
    graph.add_edge("response_generator", END)
    
    return graph


def compile_graph(checkpointer: bool = True):
    """
    Compile the graph for execution.
    
    Args:
        checkpointer: Whether to use a memory checkpointer for HITL
        
    Returns:
        Compiled graph ready for invocation
    """
    graph = create_graph()
    
    if checkpointer:
        # Use memory checkpointer for human-in-the-loop
        memory = MemorySaver()
        return graph.compile(
            checkpointer=memory,
            interrupt_before=["human_review"],  # Pause before human review
        )
    else:
        return graph.compile()


# Pre-compiled graph for convenience
_compiled_graph = None


def get_graph(checkpointer: bool = True):
    """
    Get the compiled graph (singleton pattern).
    
    Args:
        checkpointer: Whether to use checkpointer
        
    Returns:
        Compiled graph
    """
    global _compiled_graph
    
    if _compiled_graph is None:
        _compiled_graph = compile_graph(checkpointer)
    
    return _compiled_graph
