"""
Compliance Check Node (System 2 - Deterministic Rules)

This node applies hard-coded compliance rules to proposed trades.
NO LLM is involved - all rules are deterministic Python logic.

Rules Implemented:
- Rule A: Resulting cash position must not be negative
- Rule B: No single trade > 10% of total portfolio value
"""

from ..state import AgentState, Trade


class ComplianceRule:
    """Base class for compliance rules."""
    
    name: str
    description: str
    
    def check(
        self,
        trades: list[Trade],
        portfolio_data: dict,
    ) -> tuple[bool, str | None]:
        """
        Check if trades comply with this rule.
        
        Args:
            trades: List of proposed trades
            portfolio_data: Current portfolio data
            
        Returns:
            tuple: (passed: bool, error_message: str | None)
        """
        raise NotImplementedError


class CashPositionRule(ComplianceRule):
    """
    Rule A: Resulting cash position must not be negative.
    
    Ensures that after all trades, the cash position remains >= 0.
    Also enforces a minimum 2% cash buffer.
    """
    
    name = "Cash Position Rule"
    description = "Cash position must remain non-negative with 2% minimum"
    MIN_CASH_PERCENTAGE = 0.02  # 2% minimum cash
    
    def check(
        self,
        trades: list[Trade],
        portfolio_data: dict,
    ) -> tuple[bool, str | None]:
        total_value = portfolio_data.get("total_value", 0)
        
        # Find current cash value
        holdings = portfolio_data.get("holdings", [])
        current_cash = sum(
            h["value"] for h in holdings if h.get("class") == "cash"
        )
        
        # Calculate net cash change from trades
        cash_change = 0
        for trade in trades:
            if trade["asset"] == "CASH":
                if trade["action"] == "BUY":
                    cash_change += trade["amount"]
                else:
                    cash_change -= trade["amount"]
            else:
                # Non-cash trades: buys reduce cash, sells increase cash
                if trade["action"] == "BUY":
                    cash_change -= trade["amount"]
                else:
                    cash_change += trade["amount"]
        
        resulting_cash = current_cash + cash_change
        min_required = total_value * self.MIN_CASH_PERCENTAGE
        
        if resulting_cash < 0:
            return False, f"Trades would result in negative cash (${resulting_cash:,.2f})"
        
        if resulting_cash < min_required:
            return False, (
                f"Trades would reduce cash below 2% minimum. "
                f"Resulting: ${resulting_cash:,.2f} (Required: ${min_required:,.2f})"
            )
        
        return True, None


class TradeSizeRule(ComplianceRule):
    """
    Rule B: No single trade > 10% of total portfolio value.
    
    Prevents oversized trades that could cause excessive market impact
    or concentration risk.
    """
    
    name = "Trade Size Rule"
    description = "No single trade can exceed 10% of portfolio value"
    MAX_TRADE_PERCENTAGE = 0.10  # 10% maximum
    
    def check(
        self,
        trades: list[Trade],
        portfolio_data: dict,
    ) -> tuple[bool, str | None]:
        total_value = portfolio_data.get("total_value", 0)
        max_trade_value = total_value * self.MAX_TRADE_PERCENTAGE
        
        for trade in trades:
            if trade["amount"] > max_trade_value:
                return False, (
                    f"Trade of ${trade['amount']:,.2f} for {trade['asset']} "
                    f"exceeds 10% limit (${max_trade_value:,.2f})"
                )
        
        return True, None


# All active compliance rules
COMPLIANCE_RULES = [
    CashPositionRule(),
    TradeSizeRule(),
]


def run_compliance_checks(
    trades: list[Trade],
    portfolio_data: dict,
) -> tuple[bool, list[str]]:
    """
    Run all compliance rules against proposed trades.
    
    This is a PURE PYTHON function - NO LLM involvement.
    All rules are deterministic and auditable.
    
    Args:
        trades: List of proposed trades
        portfolio_data: Current portfolio data
        
    Returns:
        tuple: (all_passed: bool, errors: list[str])
    """
    all_passed = True
    errors = []
    
    for rule in COMPLIANCE_RULES:
        passed, error = rule.check(trades, portfolio_data)
        if not passed:
            all_passed = False
            errors.append(f"[{rule.name}] {error}")
    
    return all_passed, errors


def compliance_check(state: AgentState) -> dict:
    """
    LangGraph node: Check trades against compliance rules.
    
    This node:
    1. Reads proposed trades from state
    2. Applies all deterministic compliance rules
    3. Updates state with pass/fail status and any errors
    
    If compliance fails, trades are cleared and error message is set.
    
    NO LLM is used in this node - all rules are pure Python.
    
    Args:
        state: Current agent state
        
    Returns:
        dict: State updates with compliance status
    """
    trades = state.get("proposed_trades")
    portfolio_data = state.get("portfolio_data")
    
    # If no trades, nothing to check
    if not trades:
        return {
            "compliance_status": True,
            "compliance_errors": [],
        }
    
    # Run all compliance checks
    passed, errors = run_compliance_checks(trades, portfolio_data)
    
    if passed:
        return {
            "compliance_status": True,
            "compliance_errors": [],
        }
    else:
        # Compliance failed - clear trades and set error
        return {
            "compliance_status": False,
            "compliance_errors": errors,
            "proposed_trades": [],  # Clear invalid trades
            "response": format_compliance_errors(errors),
        }


def format_compliance_errors(errors: list[str]) -> str:
    """Format compliance errors into user-friendly message."""
    lines = [
        "⚠️ **Compliance Check Failed**\n",
        "The proposed trades violate the following rules:\n",
    ]
    
    for error in errors:
        lines.append(f"❌ {error}\n")
    
    lines.append("\nPlease adjust your rebalancing request and try again.")
    
    return "\n".join(lines)


def route_by_compliance(state: AgentState) -> str:
    """
    Route based on compliance check result.
    
    This is a conditional edge function for LangGraph.
    
    Args:
        state: Current agent state
        
    Returns:
        str: Next node name
    """
    if state.get("compliance_status") is True:
        return "human_review"
    else:
        return "response_generator"
