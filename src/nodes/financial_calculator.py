"""
Financial Calculator Node (System 2 - Deterministic Python)

This node performs all mathematical calculations using pure Python/Pandas.
NO LLM is involved in any calculation - this is the "slow thinking" component.

CRITICAL DESIGN PRINCIPLE:
- LLMs are banned from performing ANY numerical calculations
- All math is done deterministically with Pandas/NumPy
- This ensures accuracy and reproducibility
"""

import pandas as pd
from typing import Optional

from ..state import AgentState, Trade


class CalculationError(Exception):
    """Raised when calculation cannot proceed due to missing/invalid data."""
    pass


def calculate_rebalance(
    portfolio_data: dict,
    target_allocation: dict,
) -> list[Trade]:
    """
    Calculate trades needed to rebalance portfolio to target weights.
    
    This is a PURE PYTHON function - NO LLM involvement.
    Uses Pandas for deterministic, reproducible calculations.
    
    Algorithm:
    1. Calculate current weight of each asset class
    2. Compare to target weights
    3. Generate buy/sell orders to move to targets
    
    Args:
        portfolio_data: Dict with 'holdings' list and 'total_value'
        target_allocation: Dict of asset_class -> target_weight
        
    Returns:
        list[Trade]: List of trades to execute
        
    Raises:
        CalculationError: If required data is missing or invalid
    """
    # Validate inputs
    if not portfolio_data:
        raise CalculationError("Portfolio data is missing. Please provide your current holdings.")
    
    if not target_allocation:
        raise CalculationError("Target allocation is missing. Please specify target weights.")
    
    holdings = portfolio_data.get("holdings")
    total_value = portfolio_data.get("total_value")
    
    if not holdings:
        raise CalculationError("No holdings found in portfolio data.")
    
    if not total_value or total_value <= 0:
        raise CalculationError("Invalid total portfolio value.")
    
    # Convert to DataFrame for calculations
    df = pd.DataFrame(holdings)
    
    # Aggregate by asset class
    class_values = df.groupby("class")["value"].sum().to_dict()
    
    # Calculate current weights
    current_weights = {
        asset_class: value / total_value 
        for asset_class, value in class_values.items()
    }
    
    # Calculate required trades
    trades: list[Trade] = []
    
    for asset_class, target_weight in target_allocation.items():
        current_weight = current_weights.get(asset_class, 0.0)
        weight_diff = target_weight - current_weight
        
        # Skip if already at target (within 0.1% tolerance)
        if abs(weight_diff) < 0.001:
            continue
        
        # Calculate dollar amount to trade
        trade_amount = abs(weight_diff * total_value)
        
        # Determine action
        if weight_diff > 0:
            action = "BUY"
            reason = f"Underweight by {abs(weight_diff)*100:.1f}%"
        else:
            action = "SELL"
            reason = f"Overweight by {abs(weight_diff)*100:.1f}%"
        
        trades.append(Trade(
            asset=asset_class.upper(),
            action=action,
            amount=round(trade_amount, 2),
            current_weight=round(current_weight, 4),
            target_weight=round(target_weight, 4),
            reason=reason,
        ))
    
    return trades


def financial_calculator(state: AgentState) -> dict:
    """
    LangGraph node: Calculate rebalancing trades.
    
    This node:
    1. Reads portfolio data and target allocation from state
    2. Calls the deterministic calculate_rebalance function
    3. Updates state with proposed trades
    
    NO LLM is used in this node - all math is pure Python.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: State updates with proposed trades or error
    """
    try:
        portfolio_data = state.get("portfolio_data")
        target_allocation = state.get("target_allocation")
        
        trades = calculate_rebalance(portfolio_data, target_allocation)
        
        if not trades:
            return {
                "proposed_trades": [],
                "response": "Your portfolio is already balanced. No trades needed.",
            }
        
        return {
            "proposed_trades": trades,
        }
        
    except CalculationError as e:
        # Route back to user for clarification
        return {
            "proposed_trades": None,
            "error": str(e),
            "response": f"I couldn't calculate the rebalance: {str(e)}",
        }
    except Exception as e:
        return {
            "proposed_trades": None,
            "error": f"Unexpected calculation error: {str(e)}",
            "response": "An error occurred during calculation. Please try again.",
        }


def format_trades_summary(trades: list[Trade]) -> str:
    """
    Format trades into a human-readable summary.
    
    Args:
        trades: List of proposed trades
        
    Returns:
        str: Formatted summary string
    """
    if not trades:
        return "No trades required - portfolio is balanced."
    
    lines = ["📊 **Proposed Rebalancing Trades:**\n"]
    
    total_buy = 0
    total_sell = 0
    
    for trade in trades:
        emoji = "🟢" if trade["action"] == "BUY" else "🔴"
        lines.append(
            f"{emoji} **{trade['action']}** ${trade['amount']:,.2f} of {trade['asset']}\n"
            f"   Current: {trade['current_weight']*100:.1f}% → Target: {trade['target_weight']*100:.1f}%\n"
            f"   Reason: {trade['reason']}\n"
        )
        
        if trade["action"] == "BUY":
            total_buy += trade["amount"]
        else:
            total_sell += trade["amount"]
    
    lines.append(f"\n💰 **Summary:** Buy ${total_buy:,.2f} | Sell ${total_sell:,.2f}")
    
    return "\n".join(lines)
