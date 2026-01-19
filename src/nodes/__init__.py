"""
Nodes package for Cyborg Advisor graph.

Exports all node functions for easy importing.
"""

from .intent_parser import intent_parser, route_by_intent
from .financial_calculator import (
    financial_calculator,
    calculate_rebalance,
    CalculationError,
    format_trades_summary,
)
from .compliance_check import (
    compliance_check,
    run_compliance_checks,
    route_by_compliance,
)
from .response_generator import response_generator
from .human_review import (
    human_review,
    process_approval,
    execute_trades,
    cancel_trades,
    route_by_approval,
)
from .tax_analyzer import (
    tax_analyzer,
    identify_loss_opportunities,
    calculate_tax_impact,
    check_wash_sale_window,
    generate_mock_tax_lots,
    generate_mock_transaction_history,
    format_tlh_summary,
)

__all__ = [
    # Intent Parser
    "intent_parser",
    "route_by_intent",
    # Financial Calculator
    "financial_calculator",
    "calculate_rebalance",
    "CalculationError",
    "format_trades_summary",
    # Compliance Check
    "compliance_check",
    "run_compliance_checks",
    "route_by_compliance",
    # Response Generator
    "response_generator",
    # Human Review
    "human_review",
    "process_approval",
    "execute_trades",
    "cancel_trades",
    "route_by_approval",
    # Tax Analyzer
    "tax_analyzer",
    "identify_loss_opportunities",
    "calculate_tax_impact",
    "check_wash_sale_window",
    "generate_mock_tax_lots",
    "generate_mock_transaction_history",
    "format_tlh_summary",
]

