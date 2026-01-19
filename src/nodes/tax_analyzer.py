"""
Tax Analyzer Node (System 2 - Deterministic Python)

Pure Python node for tax analysis and loss identification.
NO LLM is involved - this is the "slow thinking" component for tax optimization.

CRITICAL DESIGN PRINCIPLE:
- All tax calculations are deterministic
- Uses FIFO (First-In-First-Out) lot selection
- Expanded wash sale detection (fund family, not just ticker)
"""

from datetime import datetime, timedelta
from typing import Optional
import random

from ..state import AgentState


# =============================================================================
# Mock Tax Lot Data (25+ entries for realistic testing)
# =============================================================================

def generate_mock_tax_lots() -> list[dict]:
    """
    Generate 25+ realistic tax lot entries for demonstration.
    
    Includes a mix of:
    - Gains and losses
    - Short-term and long-term positions
    - ETFs and individual stocks
    - Various purchase dates and prices
    """
    base_date = datetime.now()
    
    # Define realistic price scenarios (purchase_price, current_price)
    mock_data = [
        # === LOSSES (good for harvesting) ===
        # Tech stocks with losses
        ("AAPL", 185.50, 172.30, 50, base_date - timedelta(days=45)),    # Short-term loss
        ("AAPL", 192.00, 172.30, 30, base_date - timedelta(days=120)),   # Short-term loss
        ("MSFT", 420.00, 385.50, 25, base_date - timedelta(days=200)),   # Short-term loss
        ("GOOGL", 155.00, 138.20, 40, base_date - timedelta(days=90)),   # Short-term loss
        ("NVDA", 890.00, 750.00, 15, base_date - timedelta(days=60)),    # Short-term loss (big $)
        ("META", 520.00, 485.00, 20, base_date - timedelta(days=180)),   # Short-term loss
        
        # ETFs with losses
        ("VTI", 265.00, 248.50, 100, base_date - timedelta(days=400)),   # Long-term loss
        ("VOO", 480.00, 455.00, 50, base_date - timedelta(days=450)),    # Long-term loss
        ("BND", 78.00, 72.50, 200, base_date - timedelta(days=500)),     # Long-term loss (bonds down)
        ("VXUS", 62.00, 55.80, 150, base_date - timedelta(days=380)),    # Long-term loss
        ("GLD", 195.00, 182.00, 60, base_date - timedelta(days=100)),    # Short-term loss
        
        # === GAINS (not for harvesting, but in portfolio) ===
        ("AAPL", 125.00, 172.30, 100, base_date - timedelta(days=800)),  # Long-term gain
        ("MSFT", 280.00, 385.50, 50, base_date - timedelta(days=900)),   # Long-term gain
        ("GOOGL", 95.00, 138.20, 80, base_date - timedelta(days=750)),   # Long-term gain
        ("AMZN", 145.00, 185.50, 45, base_date - timedelta(days=600)),   # Long-term gain
        ("VTI", 195.00, 248.50, 200, base_date - timedelta(days=1100)),  # Long-term gain
        ("VOO", 350.00, 455.00, 75, base_date - timedelta(days=950)),    # Long-term gain
        
        # === MORE MIXED POSITIONS ===
        ("TSLA", 265.00, 248.00, 35, base_date - timedelta(days=150)),   # Short-term loss
        ("TSLA", 180.00, 248.00, 25, base_date - timedelta(days=420)),   # Long-term gain
        ("SPY", 485.00, 472.00, 40, base_date - timedelta(days=80)),     # Short-term loss
        ("IVV", 520.00, 505.00, 30, base_date - timedelta(days=95)),     # Short-term loss
        ("AGG", 105.00, 98.50, 150, base_date - timedelta(days=300)),    # Short-term loss
        ("VNQ", 95.00, 88.00, 80, base_date - timedelta(days=250)),      # Short-term loss
        ("SCHB", 58.00, 54.50, 120, base_date - timedelta(days=180)),    # Short-term loss
        ("IXUS", 72.00, 65.50, 90, base_date - timedelta(days=220)),     # Short-term loss
        
        # Additional positions for variety
        ("IAU", 42.00, 39.50, 100, base_date - timedelta(days=130)),     # Short-term loss
        ("SCHZ", 52.00, 48.80, 180, base_date - timedelta(days=280)),    # Short-term loss
        ("IYR", 102.00, 96.00, 55, base_date - timedelta(days=190)),     # Short-term loss
    ]
    
    tax_lots = []
    for i, (asset, purchase_price, current_price, quantity, purchase_date) in enumerate(mock_data):
        lot_id = f"LOT_{asset}_{i+1:03d}"
        cost_basis = purchase_price * quantity
        current_value = current_price * quantity
        unrealized_gain_loss = current_value - cost_basis
        days_held = (base_date - purchase_date).days
        holding_period = "long_term" if days_held >= 365 else "short_term"
        
        tax_lots.append({
            "lot_id": lot_id,
            "asset": asset,
            "purchase_date": purchase_date.isoformat(),
            "purchase_price": purchase_price,
            "quantity": quantity,
            "current_price": current_price,
            "cost_basis": round(cost_basis, 2),
            "current_value": round(current_value, 2),
            "unrealized_gain_loss": round(unrealized_gain_loss, 2),
            "holding_period": holding_period,
            "days_held": days_held,
        })
    
    return tax_lots


def generate_mock_transaction_history() -> list[dict]:
    """
    Generate mock transaction history for wash sale checking.
    
    Includes some recent purchases that would trigger wash sale violations.
    """
    base_date = datetime.now()
    
    transactions = [
        # Recent purchases (within 30 days) - potential wash sale triggers
        {"date": (base_date - timedelta(days=15)).isoformat(), "asset": "VTI", "action": "BUY", "quantity": 10, "price": 252.00},
        {"date": (base_date - timedelta(days=22)).isoformat(), "asset": "ITOT", "action": "BUY", "quantity": 15, "price": 112.00},  # Same family as VTI!
        
        # Older purchases (outside 30-day window)
        {"date": (base_date - timedelta(days=45)).isoformat(), "asset": "AAPL", "action": "BUY", "quantity": 50, "price": 185.50},
        {"date": (base_date - timedelta(days=60)).isoformat(), "asset": "NVDA", "action": "BUY", "quantity": 15, "price": 890.00},
        {"date": (base_date - timedelta(days=90)).isoformat(), "asset": "GOOGL", "action": "BUY", "quantity": 40, "price": 155.00},
        
        # Some sells
        {"date": (base_date - timedelta(days=10)).isoformat(), "asset": "META", "action": "SELL", "quantity": 10, "price": 490.00},
        {"date": (base_date - timedelta(days=35)).isoformat(), "asset": "AMZN", "action": "SELL", "quantity": 20, "price": 180.00},
    ]
    
    return transactions


# =============================================================================
# Tax Analysis Functions (Pure Python - NO LLM)
# =============================================================================

def identify_loss_opportunities(
    tax_lots: list[dict],
    min_threshold: float = 100.0,
    max_positions: int = 10,
) -> list[dict]:
    """
    Identify tax-loss harvesting opportunities.
    
    Uses FIFO (First-In-First-Out) ordering by default.
    
    Args:
        tax_lots: List of tax lot dictionaries
        min_threshold: Minimum loss amount to consider
        max_positions: Maximum positions to return
        
    Returns:
        List of loss opportunities sorted by largest loss first
    """
    losses = [
        lot for lot in tax_lots
        if lot.get("unrealized_gain_loss", 0) < -min_threshold
    ]
    
    # Sort by loss amount (most negative first = largest loss)
    losses.sort(key=lambda x: x.get("unrealized_gain_loss", 0))
    
    return losses[:max_positions]


def calculate_tax_impact(
    losses: list[dict],
    federal_rate: float = 0.24,
    state_rate: float = 0.05,
    long_term_rate: float = 0.15,
) -> dict:
    """
    Calculate estimated tax savings from harvesting losses.
    
    Args:
        losses: List of loss positions
        federal_rate: Marginal federal tax rate
        state_rate: State tax rate
        long_term_rate: Long-term capital gains rate
        
    Returns:
        Dictionary with tax impact details
    """
    short_term_losses = sum(
        abs(lot.get("unrealized_gain_loss", 0))
        for lot in losses
        if lot.get("holding_period") == "short_term"
    )
    
    long_term_losses = sum(
        abs(lot.get("unrealized_gain_loss", 0))
        for lot in losses
        if lot.get("holding_period") == "long_term"
    )
    
    total_losses = short_term_losses + long_term_losses
    
    # Short-term losses offset at ordinary income rates
    short_term_savings = short_term_losses * (federal_rate + state_rate)
    
    # Long-term losses offset at capital gains rates
    long_term_savings = long_term_losses * long_term_rate
    
    total_savings = short_term_savings + long_term_savings
    
    return {
        "short_term_losses": round(short_term_losses, 2),
        "long_term_losses": round(long_term_losses, 2),
        "total_losses": round(total_losses, 2),
        "estimated_short_term_savings": round(short_term_savings, 2),
        "estimated_long_term_savings": round(long_term_savings, 2),
        "total_estimated_savings": round(total_savings, 2),
        "assumptions": {
            "federal_rate": federal_rate,
            "state_rate": state_rate,
            "long_term_rate": long_term_rate,
        }
    }


def check_wash_sale_window(
    asset: str,
    target_date: datetime,
    transaction_history: list[dict],
    fund_family_mapping: dict = None,
) -> dict:
    """
    Check if selling an asset would trigger a wash sale.
    
    Uses EXPANDED wash sale rule (fund family, not just ticker).
    
    Args:
        asset: Asset ticker to check
        target_date: Date of proposed sale
        transaction_history: List of past transactions
        fund_family_mapping: Optional mapping of tickers to fund families
        
    Returns:
        Dictionary with wash sale check results
    """
    from ..sagas.tax_loss_harvesting import is_substantially_identical
    
    window_start = target_date - timedelta(days=30)
    window_end = target_date + timedelta(days=30)
    
    violations = []
    
    for txn in transaction_history:
        txn_date = datetime.fromisoformat(txn["date"]) if isinstance(txn["date"], str) else txn["date"]
        
        if window_start <= txn_date <= window_end:
            txn_asset = txn.get("asset")
            txn_action = txn.get("action", "").upper()
            
            if txn_action == "BUY" and is_substantially_identical(asset, txn_asset):
                violations.append({
                    "conflicting_transaction": txn,
                    "days_from_sale": (txn_date - target_date).days,
                    "substantially_identical": True,
                })
    
    return {
        "asset": asset,
        "target_date": target_date.isoformat(),
        "has_violation": len(violations) > 0,
        "violations": violations,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }


# =============================================================================
# LangGraph Node
# =============================================================================

def tax_analyzer(state: AgentState) -> dict:
    """
    LangGraph node: Analyze portfolio for tax-loss harvesting opportunities.
    
    This node:
    1. Loads tax lot data (mock or real)
    2. Identifies loss positions above threshold
    3. Calculates potential tax savings
    
    NO LLM is used - all analysis is pure Python.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: State updates with TLH analysis
    """
    try:
        # Use provided tax lots or generate mock data
        tax_lots = state.get("tax_lots")
        if not tax_lots:
            tax_lots = generate_mock_tax_lots()
        
        # Identify opportunities
        min_threshold = state.get("tlh_min_threshold", 100.0)
        opportunities = identify_loss_opportunities(tax_lots, min_threshold)
        
        if not opportunities:
            return {
                "tlh_opportunities": [],
                "tlh_tax_impact": None,
                "response": "No tax-loss harvesting opportunities found above the minimum threshold.",
            }
        
        # Calculate tax impact
        tax_impact = calculate_tax_impact(opportunities)
        
        return {
            "tax_lots": tax_lots,
            "tlh_opportunities": opportunities,
            "tlh_tax_impact": tax_impact,
        }
        
    except Exception as e:
        return {
            "tlh_opportunities": None,
            "error": f"Tax analysis error: {str(e)}",
            "response": f"An error occurred during tax analysis: {str(e)}",
        }


def format_tlh_summary(opportunities: list[dict], tax_impact: dict) -> str:
    """
    Format TLH opportunities into a human-readable summary.
    
    Args:
        opportunities: List of loss opportunities
        tax_impact: Tax impact calculation results
        
    Returns:
        Formatted summary string
    """
    if not opportunities:
        return "No tax-loss harvesting opportunities found."
    
    lines = ["📊 **Tax-Loss Harvesting Opportunities:**\n"]
    
    for opp in opportunities:
        asset = opp.get("asset", "Unknown")
        loss = opp.get("unrealized_gain_loss", 0)
        holding = opp.get("holding_period", "unknown")
        days = opp.get("days_held", 0)
        
        emoji = "🔴" if holding == "short_term" else "🟡"
        lines.append(
            f"{emoji} **{asset}** | Loss: ${abs(loss):,.2f} | "
            f"{holding.replace('_', ' ').title()} ({days} days)\n"
        )
    
    lines.append(f"\n💰 **Estimated Tax Savings:**\n")
    lines.append(f"- Short-term: ${tax_impact.get('estimated_short_term_savings', 0):,.2f}\n")
    lines.append(f"- Long-term: ${tax_impact.get('estimated_long_term_savings', 0):,.2f}\n")
    lines.append(f"- **Total: ${tax_impact.get('total_estimated_savings', 0):,.2f}**\n")
    
    return "".join(lines)
