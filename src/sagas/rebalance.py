"""
Rebalance Saga - Portfolio Rebalancing Workflow

Implements the specific saga for rebalancing a portfolio with 4 steps:
1. ValidateMarket - Check market conditions
2. PlaceSellOrders - Sell overweight assets
3. SettleCash - Verify cash settlement
4. PlaceBuyOrders - Buy underweight assets (PIVOT)
"""

from typing import Optional
from datetime import datetime
import time

from .core import (
    TransactionStep,
    SagaContext,
    SagaOrchestrator,
    SagaResult,
    StepLog,
    StepStatus,
)


class ValidateMarketStep(TransactionStep):
    """
    Step 1: Validate market conditions before trading.
    
    Execute: Check if markets are open, spreads are acceptable.
    Compensate: No-op (read-only step).
    """
    
    def __init__(self):
        super().__init__(name="ValidateMarket", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Check market conditions."""
        # Simulate market validation
        # In production: call market data API
        
        # For demo: always pass (could add failure simulation)
        ctx["market_validated"] = True
        ctx["market_status"] = "Markets open. Spreads normal."
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """No-op: read-only step has nothing to compensate."""
        ctx["market_validated"] = None
        return ctx


class PlaceSellOrdersStep(TransactionStep):
    """
    Step 2: Place SELL orders for overweight assets.
    
    Execute: Generate and place SELL orders.
    Compensate: Buy back the sold assets to restore original position.
    """
    
    def __init__(self):
        super().__init__(name="PlaceSellOrders", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Execute SELL trades for overweight positions."""
        trades = ctx.get("proposed_trades", [])
        sell_trades = [t for t in trades if t.get("action") == "SELL"]
        
        # Simulate order placement
        # In production: call broker API
        
        executed_sells = []
        for trade in sell_trades:
            # Mock execution
            executed_sells.append({
                "order_id": f"SELL_{trade['asset']}_{datetime.now().timestamp()}",
                "asset": trade["asset"],
                "amount": trade["amount"],
                "status": "FILLED",
                "fill_price": trade["amount"],  # Simplified: assume filled at par
            })
        
        ctx["executed_sells"] = executed_sells
        ctx["sell_proceeds"] = sum(t["fill_price"] for t in executed_sells)
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """
        Compensate: Buy back sold assets.
        
        In production: Place BUY orders for the same assets sold.
        """
        executed_sells = ctx.get("executed_sells", [])
        
        buyback_orders = []
        for sell in executed_sells:
            buyback_orders.append({
                "order_id": f"BUYBACK_{sell['asset']}_{datetime.now().timestamp()}",
                "asset": sell["asset"],
                "amount": sell["amount"],
                "status": "FILLED",
                "compensation_for": sell["order_id"],
            })
        
        ctx["buyback_orders"] = buyback_orders
        ctx["executed_sells"] = []  # Clear sells as they're now reversed
        ctx["sell_proceeds"] = 0
        
        return ctx


class SettleCashStep(TransactionStep):
    """
    Step 3: Verify cash settlement from sells.
    
    Execute: Wait for/verify cash is available.
    Compensate: No-op (cash settlement is automatic on sell reversal).
    """
    
    def __init__(self):
        super().__init__(name="SettleCash", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Verify cash is available from sell orders."""
        sell_proceeds = ctx.get("sell_proceeds", 0)
        
        # Simulate T+1 settlement check
        # In production: query custodian for cash balance
        
        ctx["cash_settled"] = True
        ctx["available_cash"] = sell_proceeds
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """No-op: cash state handled by sell compensation."""
        ctx["cash_settled"] = False
        ctx["available_cash"] = 0
        return ctx


class PlaceBuyOrdersStep(TransactionStep):
    """
    Step 4: Place BUY orders for underweight assets.
    
    This is the PIVOT TRANSACTION - point of no return.
    Once buys are executed, we don't automatically reverse them.
    
    Execute: Generate and place BUY orders.
    Compensate: Would sell back, but as pivot, this is rarely called.
    """
    
    def __init__(self):
        super().__init__(name="PlaceBuyOrders", is_pivot=True)  # PIVOT!
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Execute BUY trades for underweight positions."""
        trades = ctx.get("proposed_trades", [])
        buy_trades = [t for t in trades if t.get("action") == "BUY"]
        available_cash = ctx.get("available_cash", 0)
        
        # Check if we have enough cash
        total_buy_cost = sum(t.get("amount", 0) for t in buy_trades)
        
        # For demo: add a failure simulation hook
        if ctx.get("simulate_buy_failure"):
            raise Exception("Simulated failure: Insufficient funds for buy orders")
        
        executed_buys = []
        for trade in buy_trades:
            executed_buys.append({
                "order_id": f"BUY_{trade['asset']}_{datetime.now().timestamp()}",
                "asset": trade["asset"],
                "amount": trade["amount"],
                "status": "FILLED",
                "fill_price": trade["amount"],
            })
        
        ctx["executed_buys"] = executed_buys
        ctx["remaining_cash"] = available_cash - total_buy_cost
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """
        Compensate: Sell back bought assets.
        
        Note: Since this is a PIVOT, this is typically not called
        in normal rollback scenarios. Only called if explicitly requested.
        """
        executed_buys = ctx.get("executed_buys", [])
        
        sellback_orders = []
        for buy in executed_buys:
            sellback_orders.append({
                "order_id": f"SELLBACK_{buy['asset']}_{datetime.now().timestamp()}",
                "asset": buy["asset"],
                "amount": buy["amount"],
                "status": "FILLED",
                "compensation_for": buy["order_id"],
            })
        
        ctx["sellback_orders"] = sellback_orders
        ctx["executed_buys"] = []
        
        return ctx


class RebalanceSaga:
    """
    Configured saga for portfolio rebalancing.
    
    Steps:
    1. ValidateMarket - Check conditions
    2. PlaceSellOrders - Sell overweight
    3. SettleCash - Verify cash
    4. PlaceBuyOrders (PIVOT) - Buy underweight
    """
    
    def __init__(
        self,
        on_step_start=None,
        on_step_complete=None,
    ):
        """
        Initialize the rebalance saga.
        
        Args:
            on_step_start: Callback(step_name, index, total) for UI updates
            on_step_complete: Callback(step_name, status) for UI updates
        """
        self.steps = [
            ValidateMarketStep(),
            PlaceSellOrdersStep(),
            SettleCashStep(),
            PlaceBuyOrdersStep(),
        ]
        
        self.orchestrator = SagaOrchestrator(
            steps=self.steps,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
        )
    
    def run(self, ctx: SagaContext) -> SagaResult:
        """
        Execute the rebalance saga.
        
        Args:
            ctx: Context with portfolio_data and proposed_trades
            
        Returns:
            SagaResult with execution status and logs
        """
        return self.orchestrator.run(ctx)
    
    def get_step_names(self) -> list[str]:
        """Get list of step names for UI display."""
        return [step.name for step in self.steps]
    
    def get_pivot_step(self) -> Optional[str]:
        """Get the name of the pivot step."""
        for step in self.steps:
            if step.is_pivot:
                return step.name
        return None
