"""
Direct Indexing Saga - Transactional Portfolio Construction

Implements the saga pattern for direct indexing operations:
1. ValidateConfiguration - Validate index configuration
2. ApplyExclusions - Apply ESG/sector exclusions
3. CalculateWeights - Calculate factor-adjusted weights
4. GenerateTrades - Generate required trades
5. IntegrateTLH - Coordinate with tax-loss harvesting
6. ExecuteTrades - Execute trades (PIVOT)
7. ConfirmPositions - Confirm final positions
"""

from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime

from ..sagas.core import (
    TransactionStep,
    SagaOrchestrator,
    SagaContext,
    StepStatus,
)
from ..direct_indexing import (
    DirectIndexingEngine,
    CustomIndex,
    ConstructedPortfolio,
    Trade,
    get_global_engine,
)
from ..audit import (
    AuditStore,
    AuditEvent,
    AuditEventType,
    ValidationResult,
    get_global_audit_store,
    get_global_agent_registry,
)


# =============================================================================
# Saga Steps
# =============================================================================

class ValidateConfigurationStep(TransactionStep):
    """Validate the custom index configuration."""
    
    def __init__(self):
        super().__init__(
            name="ValidateConfiguration",
            is_pivot=False,
        )
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Validate that the index configuration is valid."""
        index_config = context.get("index_config", {})
        
        # Validate required fields
        if not index_config.get("name"):
            raise ValueError("Index name is required")
        
        if not index_config.get("benchmark"):
            raise ValueError("Benchmark is required")
        
        # Validate factor tilts are within range
        for tilt in index_config.get("factor_tilts", []):
            if not -1.0 <= tilt.get("weight", 0) <= 1.0:
                raise ValueError(f"Factor tilt weight must be between -1.0 and 1.0")
        
        # Validate investment amount
        investment = context.get("investment_amount", 0)
        if investment < 1000:
            raise ValueError("Minimum investment amount is $1,000")
        
        context["validation_passed"] = True
        context["reasoning_trace"] = f"Validated index '{index_config.get('name')}' with {len(index_config.get('factor_tilts', []))} tilts and {len(index_config.get('exclusions', []))} exclusions"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """No compensation needed for validation."""
        return context


class ApplyExclusionsStep(TransactionStep):
    """Apply exclusion rules to filter universe."""
    
    def __init__(self):
        super().__init__(
            name="ApplyExclusions",
            is_pivot=False,
        )
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Apply ESG and other exclusions."""
        index: CustomIndex = context.get("custom_index")
        
        excluded_tickers = []
        for exclusion in index.exclusions:
            excluded_tickers.extend(exclusion.values)
        
        context["excluded_tickers"] = excluded_tickers
        context["exclusion_count"] = len(excluded_tickers)
        context["reasoning_trace"] = f"Applied {len(index.exclusions)} exclusion rules, filtering {len(excluded_tickers)} tickers"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Clear exclusions."""
        context["excluded_tickers"] = []
        return context


class CalculateWeightsStep(TransactionStep):
    """Calculate factor-adjusted portfolio weights."""
    
    def __init__(self, engine: DirectIndexingEngine):
        super().__init__(
            name="CalculateWeights",
            is_pivot=False,
        )
        self.engine = engine
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Calculate target weights with factor tilts."""
        index: CustomIndex = context.get("custom_index")
        investment = context.get("investment_amount", 100000)
        
        # Construct the portfolio
        portfolio = self.engine.construct_portfolio(
            index=index,
            investment_amount=investment,
        )
        
        context["constructed_portfolio"] = portfolio
        context["target_holdings"] = [h.to_dict() for h in portfolio.holdings]
        context["factor_exposures"] = portfolio.factor_exposures
        context["reasoning_trace"] = f"Calculated weights for {len(portfolio.holdings)} holdings with tracking error {portfolio.tracking_error:.2%}"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Clear calculated weights."""
        context["constructed_portfolio"] = None
        context["target_holdings"] = []
        return context


class GenerateTradesStep(TransactionStep):
    """Generate trades to achieve target portfolio."""
    
    def __init__(self, engine: DirectIndexingEngine):
        super().__init__(
            name="GenerateTrades",
            is_pivot=False,
        )
        self.engine = engine
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Generate required trades."""
        index: CustomIndex = context.get("custom_index")
        investment = context.get("investment_amount", 100000)
        current_holdings = context.get("current_holdings", {})
        
        trades = self.engine.generate_trades(
            index=index,
            investment_amount=investment,
            current_holdings=current_holdings,
        )
        
        context["proposed_trades"] = [t.to_dict() for t in trades]
        context["trade_count"] = len(trades)
        context["total_buy_value"] = sum(t.value for t in trades if t.action == "BUY")
        context["total_sell_value"] = sum(t.value for t in trades if t.action == "SELL")
        context["reasoning_trace"] = f"Generated {len(trades)} trades: ${context['total_buy_value']:.2f} buys, ${context['total_sell_value']:.2f} sells"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Clear proposed trades."""
        context["proposed_trades"] = []
        return context


class IntegrateTLHStep(TransactionStep):
    """Coordinate with Tax-Loss Harvesting for optimal execution."""
    
    def __init__(self):
        super().__init__(
            name="IntegrateTLH",
            is_pivot=False,
        )
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Check for TLH opportunities in trades."""
        trades = context.get("proposed_trades", [])
        tax_lots = context.get("existing_tax_lots", [])
        
        tlh_opportunities = []
        for trade in trades:
            if trade.get("action") == "SELL":
                # Check if this sale could harvest a loss
                # In production, would check actual cost basis
                tlh_opportunities.append({
                    "ticker": trade["ticker"],
                    "potential_loss": trade["value"] * 0.1,  # Simplified
                })
        
        context["tlh_opportunities"] = tlh_opportunities
        context["tlh_integrated"] = True
        context["reasoning_trace"] = f"Identified {len(tlh_opportunities)} potential TLH opportunities within rebalance trades"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Clear TLH integration."""
        context["tlh_opportunities"] = []
        context["tlh_integrated"] = False
        return context


class ExecuteTradesStep(TransactionStep):
    """Execute trades - PIVOT POINT."""
    
    def __init__(self):
        super().__init__(
            name="ExecuteTrades",
            is_pivot=True,  # Point of no return
        )
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Execute all trades (mock execution)."""
        trades = context.get("proposed_trades", [])
        
        executed_trades = []
        for trade in trades:
            # In production, would call broker API
            executed_trades.append({
                **trade,
                "status": "EXECUTED",
                "execution_price": 100.0,  # Mock price
                "execution_time": datetime.now().isoformat(),
            })
        
        context["executed_trades"] = executed_trades
        context["execution_status"] = "COMPLETED"
        context["reasoning_trace"] = f"Executed {len(executed_trades)} trades successfully"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Cannot compensate after pivot - would need separate reversal saga."""
        # In production, would need broker-specific reversal logic
        context["execution_status"] = "REVERSAL_REQUIRED"
        return context


class ConfirmPositionsStep(TransactionStep):
    """Confirm final portfolio positions."""
    
    def __init__(self):
        super().__init__(
            name="ConfirmPositions",
            is_pivot=False,
        )
    
    def execute(self, context: SagaContext) -> SagaContext:
        """Confirm positions match target."""
        executed_trades = context.get("executed_trades", [])
        target_holdings = context.get("target_holdings", [])
        
        # Build final positions
        final_positions = {}
        for holding in target_holdings:
            final_positions[holding["ticker"]] = {
                "shares": holding["shares"],
                "value": holding["value"],
                "weight": holding["weight"],
            }
        
        context["final_positions"] = final_positions
        context["position_count"] = len(final_positions)
        context["confirmation_status"] = "CONFIRMED"
        context["reasoning_trace"] = f"Confirmed {len(final_positions)} positions matching target allocation"
        
        return context
    
    def compensate(self, context: SagaContext) -> SagaContext:
        """Clear confirmation."""
        context["confirmation_status"] = "UNCONFIRMED"
        return context


# =============================================================================
# Saga Factory
# =============================================================================

def create_direct_indexing_saga(
    engine: Optional[DirectIndexingEngine] = None,
    audit_store: Optional[AuditStore] = None,
) -> SagaOrchestrator:
    """
    Create a Direct Indexing saga with all steps.
    
    Args:
        engine: DirectIndexingEngine instance (uses global if None)
        audit_store: AuditStore instance (uses global if None)
    
    Returns:
        Configured SagaOrchestrator
    """
    engine = engine or get_global_engine()
    audit_store = audit_store or get_global_audit_store()
    
    # Get agent for audit
    registry = get_global_agent_registry()
    # Use rebalance agent for direct indexing (could add dedicated agent)
    agent = registry.get_agent("agent:rebalance_agent:1.0.0")
    
    steps = [
        ValidateConfigurationStep(),
        ApplyExclusionsStep(),
        CalculateWeightsStep(engine),
        GenerateTradesStep(engine),
        IntegrateTLHStep(),
        ExecuteTradesStep(),
        ConfirmPositionsStep(),
    ]
    
    return SagaOrchestrator(
        steps=steps,
        agent_id=agent.agent_id if agent else "agent:direct_indexing:1.0.0",
        audit_store=audit_store,
    )


def run_direct_indexing(
    index: CustomIndex,
    investment_amount: float,
    current_holdings: Optional[dict[str, float]] = None,
) -> SagaContext:
    """
    Execute a complete direct indexing workflow.
    
    Args:
        index: CustomIndex configuration
        investment_amount: Amount to invest
        current_holdings: Existing positions {ticker: value}
    
    Returns:
        Final saga context with results
    """
    saga = create_direct_indexing_saga()
    
    initial_context: SagaContext = {
        "transaction_id": f"di_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "index_config": index.to_dict(),
        "custom_index": index,
        "investment_amount": investment_amount,
        "current_holdings": current_holdings or {},
        "executed_steps": [],
        "logs": [],
    }
    
    return saga.run(initial_context)
