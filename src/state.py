"""
Agent State Definition for Cyborg Advisor

Defines the TypedDict that flows through the LangGraph state machine,
containing all data needed for portfolio rebalancing decisions.
"""

from typing import TypedDict, Optional, Annotated
from operator import add


class Trade(TypedDict):
    """Represents a single trade to be executed."""
    asset: str
    action: str  # "BUY" or "SELL"
    amount: float
    current_weight: float
    target_weight: float
    reason: str


class AgentState(TypedDict):
    """
    State that flows through the LangGraph state machine.
    
    This is the central data structure that all nodes read from and write to.
    It implements the "System 1 vs System 2" pattern where:
    - LLM nodes handle intent parsing (System 1 - fast/intuitive)
    - Python nodes handle calculations (System 2 - slow/deliberate)
    
    Attributes:
        messages: Annotated list of chat messages (LangGraph accumulates these)
        user_input: The current user message being processed
        intent: Classified intent from the LLM (rebalance, query, respond)
        portfolio_data: Dictionary representation of portfolio holdings
        target_allocation: Target weights by asset class (e.g., {"stocks": 0.6})
        proposed_trades: List of trades calculated by the financial calculator
        compliance_status: Whether proposed trades pass all compliance rules
        compliance_errors: List of any compliance rule violations
        human_approval: Whether human has approved the trades (None = pending)
        response: Final response message to return to user
        error: Any error message if something went wrong
    """
    
    # Chat history (accumulates automatically with LangGraph's add reducer)
    messages: Annotated[list, add]
    
    # Current processing state
    user_input: str
    intent: Optional[str]
    
    # Portfolio data (stored as dict for serialization)
    portfolio_data: Optional[dict]
    target_allocation: Optional[dict]
    
    # Trade proposal (calculated deterministically - NO LLM)
    proposed_trades: Optional[list[Trade]]
    
    # Compliance gate (deterministic rules - NO LLM)
    compliance_status: Optional[bool]
    compliance_errors: Optional[list[str]]
    
    # Human-in-the-loop gate
    human_approval: Optional[bool]
    
    # Output
    response: Optional[str]
    error: Optional[str]
    
    # Saga execution tracking
    saga_transaction_id: Optional[str]
    saga_status: Optional[str]  # "pending", "executing", "success", "rolled_back", "failed"
    saga_logs: Optional[list[dict]]
    
    # Tax Loss Harvesting fields
    tax_lots: Optional[list[dict]]  # Tax lot data for cost basis tracking
    transaction_history: Optional[list[dict]]  # Historical transactions for wash sale check
    tlh_opportunities: Optional[list[dict]]  # Identified loss positions
    tlh_wash_sale_violations: Optional[list[dict]]  # Any wash sale conflicts
    tlh_valid_opportunities: Optional[list[dict]]  # Opportunities after wash sale check
    tlh_harvested_losses: Optional[float]  # Total losses harvested
    tlh_replacement_securities: Optional[list[dict]]  # Replacement purchases
    tlh_tax_records: Optional[list[dict]]  # Tax lot records for reporting
    tlh_tax_impact: Optional[dict]  # Estimated tax savings
    tlh_min_threshold: Optional[float]  # Minimum loss threshold for harvesting


def create_initial_state(
    user_input: str,
    portfolio_data: Optional[dict] = None,
    target_allocation: Optional[dict] = None,
) -> AgentState:
    """
    Create an initial state for a new conversation turn.
    
    Args:
        user_input: The user's message
        portfolio_data: Current portfolio holdings as dict
        target_allocation: Target weights by asset class
        
    Returns:
        AgentState: Initialized state ready for graph execution
    """
    return AgentState(
        messages=[],
        user_input=user_input,
        intent=None,
        portfolio_data=portfolio_data,
        target_allocation=target_allocation,
        proposed_trades=None,
        compliance_status=None,
        compliance_errors=None,
        human_approval=None,
        response=None,
        error=None,
        saga_transaction_id=None,
        saga_status=None,
        saga_logs=None,
    )


# Default target allocation for demo purposes
DEFAULT_TARGET_ALLOCATION = {
    "stocks": 0.60,      # 60% in equities
    "bonds": 0.30,       # 30% in fixed income
    "cash": 0.05,        # 5% in cash (minimum 2% required)
    "alternatives": 0.05  # 5% in alternatives
}


# Sample portfolio for demo/testing
SAMPLE_PORTFOLIO = {
    "holdings": [
        {"asset": "AAPL", "class": "stocks", "value": 25000},
        {"asset": "MSFT", "class": "stocks", "value": 20000},
        {"asset": "GOOGL", "class": "stocks", "value": 15000},
        {"asset": "BND", "class": "bonds", "value": 20000},
        {"asset": "TLT", "class": "bonds", "value": 10000},
        {"asset": "CASH", "class": "cash", "value": 8000},
        {"asset": "GLD", "class": "alternatives", "value": 2000},
    ],
    "total_value": 100000,
}
