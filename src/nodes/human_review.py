"""
Human Review Node (Human-in-the-Loop)

This node implements the checkpoint before trade execution.
It pauses the graph and waits for human approval before proceeding.
"""

from langchain_core.messages import AIMessage

from ..state import AgentState
from .financial_calculator import format_trades_summary


def human_review(state: AgentState) -> dict:
    """
    Human-in-the-loop checkpoint node.
    
    This node:
    1. Presents the proposed trades to the user
    2. Pauses execution waiting for approval
    3. Routes to execute or cancel based on response
    
    In LangGraph, this is configured with an interrupt_before checkpoint.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: State update requesting approval
    """
    trades = state.get("proposed_trades", [])
    
    if not trades:
        return {
            "response": "No trades to review.",
            "human_approval": None,
        }
    
    # Format trades for review
    summary = format_trades_summary(trades)
    
    review_message = (
        f"📋 **Trade Review Required**\n\n"
        f"{summary}\n\n"
        f"---\n"
        f"✅ Reply **'approve'** to execute these trades\n"
        f"❌ Reply **'cancel'** to abort\n"
    )
    
    return {
        "response": review_message,
        "messages": [AIMessage(content=review_message)],
        "human_approval": None,  # Indicates waiting for approval
    }


def process_approval(state: AgentState) -> dict:
    """
    Process the human's approval decision.
    
    This is called after the interrupt resumes.
    
    Args:
        state: Current state with user's response
        
    Returns:
        dict: Updated state with approval status
    """
    user_response = state.get("user_input", "").lower().strip()
    
    if user_response in ["approve", "yes", "y", "ok", "execute"]:
        return {"human_approval": True}
    elif user_response in ["cancel", "no", "n", "abort", "reject"]:
        return {"human_approval": False}
    else:
        # Unclear response - ask again
        return {
            "response": "Please reply 'approve' to execute trades or 'cancel' to abort.",
            "human_approval": None,
        }


def route_by_approval(state: AgentState) -> str:
    """
    Route based on human approval status.
    
    Args:
        state: Current agent state
        
    Returns:
        str: Next node name
    """
    approval = state.get("human_approval")
    
    if approval is True:
        return "execute_trades"
    elif approval is False:
        return "cancel_trades"
    else:
        # Still waiting or unclear - go back to review
        return "human_review"


def execute_trades(state: AgentState) -> dict:
    """
    Execute the approved trades (mock implementation).
    
    In a real system, this would integrate with a broker API.
    For this prototype, we just print/log the execution.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: Execution confirmation
    """
    trades = state.get("proposed_trades", [])
    
    # Mock execution - in production this would call broker APIs
    execution_log = ["🚀 **Trades Executed Successfully!**\n"]
    
    for trade in trades:
        execution_log.append(
            f"✓ {trade['action']} ${trade['amount']:,.2f} of {trade['asset']}"
        )
    
    execution_log.append("\n📊 Your portfolio has been rebalanced.")
    
    response = "\n".join(execution_log)
    
    return {
        "response": response,
        "messages": [AIMessage(content=response)],
        "proposed_trades": [],  # Clear executed trades
    }


def cancel_trades(state: AgentState) -> dict:
    """
    Cancel the proposed trades.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: Cancellation confirmation
    """
    response = "❌ **Trades Cancelled**\n\nNo changes were made to your portfolio."
    
    return {
        "response": response,
        "messages": [AIMessage(content=response)],
        "proposed_trades": [],  # Clear cancelled trades
        "human_approval": False,
    }
