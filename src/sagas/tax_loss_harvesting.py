"""
Tax Loss Harvesting Saga - Automated Tax-Efficient Harvesting Workflow

Implements a 5-step saga for tax loss harvesting with transactional integrity:
1. IdentifyLosses - Scan portfolio for unrealized losses above threshold
2. CheckWashSale - Validate 30-day wash sale rule (expanded: fund family)
3. SellLossPositions - Execute SELL orders for loss positions
4. PurchaseReplacement (PIVOT) - Buy similar-but-not-identical securities
5. RecordTaxLot - Log tax lot info for year-end reporting
"""

from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import time

from .core import (
    TransactionStep,
    SagaContext,
    SagaOrchestrator,
    SagaResult,
    StepLog,
    StepStatus,
)


# =============================================================================
# Fund Family Mapping for Expanded Wash Sale Detection
# =============================================================================

FUND_FAMILY_MAPPING = {
    # Vanguard Total Stock Market alternatives
    "VTI": {"family": "total_us_stock", "provider": "Vanguard"},
    "VTSAX": {"family": "total_us_stock", "provider": "Vanguard"},
    "ITOT": {"family": "total_us_stock", "provider": "iShares"},
    "SPTM": {"family": "total_us_stock", "provider": "SPDR"},
    "SCHB": {"family": "total_us_stock", "provider": "Schwab"},
    
    # S&P 500 alternatives
    "SPY": {"family": "sp500", "provider": "SPDR"},
    "VOO": {"family": "sp500", "provider": "Vanguard"},
    "IVV": {"family": "sp500", "provider": "iShares"},
    "SPLG": {"family": "sp500", "provider": "SPDR"},
    
    # Total Bond Market alternatives
    "BND": {"family": "total_bond", "provider": "Vanguard"},
    "AGG": {"family": "total_bond", "provider": "iShares"},
    "SCHZ": {"family": "total_bond", "provider": "Schwab"},
    
    # International Stock alternatives
    "VXUS": {"family": "intl_stock", "provider": "Vanguard"},
    "IXUS": {"family": "intl_stock", "provider": "iShares"},
    "VEU": {"family": "intl_stock", "provider": "Vanguard"},
    
    # Individual stocks (no family - same ticker only)
    "AAPL": {"family": "aapl_individual", "provider": "Individual"},
    "MSFT": {"family": "msft_individual", "provider": "Individual"},
    "GOOGL": {"family": "googl_individual", "provider": "Individual"},
    "GOOG": {"family": "googl_individual", "provider": "Individual"},  # Same as GOOGL
    "AMZN": {"family": "amzn_individual", "provider": "Individual"},
    "NVDA": {"family": "nvda_individual", "provider": "Individual"},
    "META": {"family": "meta_individual", "provider": "Individual"},
    "TSLA": {"family": "tsla_individual", "provider": "Individual"},
    
    # Gold/Commodities alternatives
    "GLD": {"family": "gold", "provider": "SPDR"},
    "IAU": {"family": "gold", "provider": "iShares"},
    "GLDM": {"family": "gold", "provider": "SPDR"},
    
    # REITs
    "VNQ": {"family": "reit", "provider": "Vanguard"},
    "IYR": {"family": "reit", "provider": "iShares"},
    "SCHH": {"family": "reit", "provider": "Schwab"},
}

# Replacement suggestions (different provider in same family)
REPLACEMENT_MAPPING = {
    "VTI": ["ITOT", "SPTM", "SCHB"],
    "ITOT": ["VTI", "SPTM", "SCHB"],
    "SPY": ["VOO", "IVV", "SPLG"],
    "VOO": ["SPY", "IVV", "SPLG"],
    "IVV": ["SPY", "VOO", "SPLG"],
    "BND": ["AGG", "SCHZ"],
    "AGG": ["BND", "SCHZ"],
    "VXUS": ["IXUS", "VEU"],
    "GLD": ["IAU", "GLDM"],
    "VNQ": ["IYR", "SCHH"],
    # Individual stocks - no replacements (can't swap AAPL for similar)
}


def is_substantially_identical(asset1: str, asset2: str) -> bool:
    """
    Check if two assets are substantially identical (expanded wash sale rule).
    
    Considers:
    - Same ticker (always identical)
    - Same fund family (e.g., VTI and VTSAX are both Vanguard Total Stock)
    
    Args:
        asset1: First asset ticker
        asset2: Second asset ticker
        
    Returns:
        True if assets are substantially identical
    """
    if asset1 == asset2:
        return True
    
    info1 = FUND_FAMILY_MAPPING.get(asset1, {})
    info2 = FUND_FAMILY_MAPPING.get(asset2, {})
    
    family1 = info1.get("family")
    family2 = info2.get("family")
    
    # If either asset isn't in our mapping, assume not identical
    if not family1 or not family2:
        return False
    
    # Same family = substantially identical
    return family1 == family2


def get_replacement_suggestions(asset: str) -> list[str]:
    """
    Get list of replacement securities that are NOT substantially identical.
    
    For ETFs: suggests different-provider ETFs tracking similar (but not identical) indices
    For individual stocks: no automatic replacements
    
    Args:
        asset: Asset ticker to find replacements for
        
    Returns:
        List of suggested replacement tickers
    """
    return REPLACEMENT_MAPPING.get(asset, [])


# =============================================================================
# Tax Lot Data Structure
# =============================================================================

class TaxLot:
    """Represents a single tax lot for cost basis tracking."""
    
    def __init__(
        self,
        lot_id: str,
        asset: str,
        purchase_date: datetime,
        purchase_price: float,
        quantity: float,
        current_price: float,
    ):
        self.lot_id = lot_id
        self.asset = asset
        self.purchase_date = purchase_date
        self.purchase_price = purchase_price
        self.quantity = quantity
        self.current_price = current_price
    
    @property
    def cost_basis(self) -> float:
        """Total cost basis for this lot."""
        return self.purchase_price * self.quantity
    
    @property
    def current_value(self) -> float:
        """Current market value."""
        return self.current_price * self.quantity
    
    @property
    def unrealized_gain_loss(self) -> float:
        """Unrealized gain (positive) or loss (negative)."""
        return self.current_value - self.cost_basis
    
    @property
    def holding_period(self) -> str:
        """'short_term' if held < 1 year, else 'long_term'."""
        days_held = (datetime.now() - self.purchase_date).days
        return "long_term" if days_held >= 365 else "short_term"
    
    @property
    def days_held(self) -> int:
        """Number of days this lot has been held."""
        return (datetime.now() - self.purchase_date).days
    
    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "asset": self.asset,
            "purchase_date": self.purchase_date.isoformat(),
            "purchase_price": self.purchase_price,
            "quantity": self.quantity,
            "current_price": self.current_price,
            "cost_basis": round(self.cost_basis, 2),
            "current_value": round(self.current_value, 2),
            "unrealized_gain_loss": round(self.unrealized_gain_loss, 2),
            "holding_period": self.holding_period,
            "days_held": self.days_held,
        }


# =============================================================================
# TLH Saga Steps
# =============================================================================

class IdentifyLossesStep(TransactionStep):
    """
    Step 1: Identify positions with unrealized losses.
    
    Execute: Scan tax lots for losses exceeding threshold (FIFO order).
    Compensate: No-op (read-only step).
    """
    
    def __init__(self, min_loss_threshold: float = 100.0):
        super().__init__(name="IdentifyLosses", is_pivot=False)
        self.min_loss_threshold = min_loss_threshold
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Scan portfolio for loss-harvesting opportunities."""
        tax_lots = ctx.get("tax_lots", [])
        
        # Find lots with losses exceeding threshold
        loss_opportunities = []
        for lot in tax_lots:
            if isinstance(lot, dict):
                loss = lot.get("unrealized_gain_loss", 0)
            else:
                loss = lot.unrealized_gain_loss
            
            if loss < -self.min_loss_threshold:  # Negative = loss
                lot_dict = lot if isinstance(lot, dict) else lot.to_dict()
                loss_opportunities.append(lot_dict)
        
        # Sort by largest loss first (maximize tax benefit)
        loss_opportunities.sort(key=lambda x: x.get("unrealized_gain_loss", 0))
        
        ctx["tlh_opportunities"] = loss_opportunities
        ctx["tlh_total_potential_loss"] = sum(
            opp.get("unrealized_gain_loss", 0) for opp in loss_opportunities
        )
        
        if not loss_opportunities:
            ctx["tlh_status_message"] = "No tax-loss harvesting opportunities found above threshold."
        else:
            ctx["tlh_status_message"] = (
                f"Found {len(loss_opportunities)} loss-harvesting opportunities "
                f"totaling ${abs(ctx['tlh_total_potential_loss']):,.2f} in losses."
            )
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """No-op: read-only step has nothing to compensate."""
        ctx["tlh_opportunities"] = None
        ctx["tlh_total_potential_loss"] = None
        return ctx


class CheckWashSaleStep(TransactionStep):
    """
    Step 2: Validate no wash sale violations.
    
    Execute: Check 30-day window for substantially identical purchases.
    Compensate: No-op (read-only validation).
    
    Uses EXPANDED wash sale rule:
    - Same ticker is always a violation
    - Same fund family (e.g., VTI/VTSAX) is also a violation
    """
    
    def __init__(self):
        super().__init__(name="CheckWashSale", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Validate 30-day wash sale rule for all opportunities."""
        opportunities = ctx.get("tlh_opportunities", [])
        transaction_history = ctx.get("transaction_history", [])
        current_date = datetime.now()
        
        wash_sale_violations = []
        valid_opportunities = []
        
        for opp in opportunities:
            asset = opp.get("asset")
            violation_found = False
            violation_details = None
            
            # Check transaction history for purchases in wash sale window
            for txn in transaction_history:
                txn_date = datetime.fromisoformat(txn["date"]) if isinstance(txn["date"], str) else txn["date"]
                days_diff = abs((current_date - txn_date).days)
                
                # Check if within 30-day window (before OR after)
                if days_diff <= 30:
                    txn_asset = txn.get("asset")
                    txn_action = txn.get("action", "").upper()
                    
                    # Check if this is a substantially identical purchase
                    if txn_action == "BUY" and is_substantially_identical(asset, txn_asset):
                        violation_found = True
                        violation_details = {
                            "loss_asset": asset,
                            "conflicting_asset": txn_asset,
                            "conflicting_date": txn_date.isoformat(),
                            "days_from_today": days_diff,
                            "reason": f"Purchase of {txn_asset} on {txn_date.date()} is substantially identical to {asset}"
                        }
                        break
            
            if violation_found:
                opp["wash_sale_violation"] = violation_details
                wash_sale_violations.append(opp)
            else:
                opp["wash_sale_clear"] = True
                valid_opportunities.append(opp)
        
        ctx["tlh_wash_sale_violations"] = wash_sale_violations
        ctx["tlh_valid_opportunities"] = valid_opportunities
        
        if wash_sale_violations:
            ctx["tlh_wash_sale_warning"] = (
                f"⚠️ {len(wash_sale_violations)} positions have wash sale conflicts and will be skipped."
            )
        
        if not valid_opportunities:
            raise Exception("No valid tax-loss harvesting opportunities after wash sale check.")
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """No-op: read-only validation."""
        ctx["tlh_wash_sale_violations"] = None
        ctx["tlh_valid_opportunities"] = None
        return ctx


class SellLossPositionsStep(TransactionStep):
    """
    Step 3: Execute SELL orders for loss positions.
    
    Execute: Place SELL orders for validated loss positions.
    Compensate: Buy back sold positions to restore original state.
    """
    
    def __init__(self):
        super().__init__(name="SellLossPositions", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Execute SELL trades for loss positions."""
        opportunities = ctx.get("tlh_valid_opportunities", [])
        
        executed_sells = []
        total_proceeds = 0.0
        total_losses_harvested = 0.0
        
        for opp in opportunities:
            # Simulate order execution
            # In production: call broker API
            current_value = opp.get("current_value", 0)
            loss = opp.get("unrealized_gain_loss", 0)
            
            sell_order = {
                "order_id": f"TLH_SELL_{opp['asset']}_{opp['lot_id']}_{datetime.now().timestamp()}",
                "asset": opp["asset"],
                "lot_id": opp["lot_id"],
                "quantity": opp.get("quantity", 0),
                "sell_price": opp.get("current_price", 0),
                "proceeds": current_value,
                "cost_basis": opp.get("cost_basis", 0),
                "realized_loss": loss,
                "holding_period": opp.get("holding_period", "short_term"),
                "status": "FILLED",
                "timestamp": datetime.now().isoformat(),
            }
            
            executed_sells.append(sell_order)
            total_proceeds += current_value
            total_losses_harvested += abs(loss)
        
        ctx["tlh_executed_sells"] = executed_sells
        ctx["tlh_total_proceeds"] = total_proceeds
        ctx["tlh_harvested_losses"] = total_losses_harvested
        ctx["tlh_available_for_reinvestment"] = total_proceeds
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """
        Compensate: Buy back sold positions.
        
        In production: Place BUY orders to restore original positions.
        """
        executed_sells = ctx.get("tlh_executed_sells", [])
        
        buyback_orders = []
        for sell in executed_sells:
            buyback = {
                "order_id": f"TLH_BUYBACK_{sell['asset']}_{datetime.now().timestamp()}",
                "asset": sell["asset"],
                "quantity": sell["quantity"],
                "price": sell["sell_price"],  # May differ in practice
                "status": "FILLED",
                "compensation_for": sell["order_id"],
                "timestamp": datetime.now().isoformat(),
            }
            buyback_orders.append(buyback)
        
        ctx["tlh_buyback_orders"] = buyback_orders
        ctx["tlh_executed_sells"] = []  # Clear as they're reversed
        ctx["tlh_harvested_losses"] = 0
        
        return ctx


class PurchaseReplacementStep(TransactionStep):
    """
    Step 4: Purchase replacement securities (PIVOT TRANSACTION).
    
    This is the PIVOT - point of no return.
    Once replacements are purchased, we don't automatically reverse.
    
    Execute: Buy replacement securities that are NOT substantially identical.
    Compensate: Would sell replacements, but as pivot, this is rarely called.
    """
    
    def __init__(self):
        super().__init__(name="PurchaseReplacement", is_pivot=True)  # PIVOT!
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Purchase replacement securities."""
        executed_sells = ctx.get("tlh_executed_sells", [])
        available_cash = ctx.get("tlh_available_for_reinvestment", 0)
        
        # Failure simulation hook for testing
        if ctx.get("simulate_replacement_failure"):
            raise Exception("Simulated failure: Unable to purchase replacement securities")
        
        replacement_purchases = []
        total_invested = 0.0
        
        for sell in executed_sells:
            original_asset = sell["asset"]
            replacements = get_replacement_suggestions(original_asset)
            
            if replacements:
                # Pick first available replacement
                replacement_asset = replacements[0]
                investment_amount = sell["proceeds"]
                
                purchase = {
                    "order_id": f"TLH_BUY_{replacement_asset}_{datetime.now().timestamp()}",
                    "asset": replacement_asset,
                    "original_asset": original_asset,
                    "amount": investment_amount,
                    "status": "FILLED",
                    "timestamp": datetime.now().isoformat(),
                    "note": f"Replacement for {original_asset} (TLH)",
                }
                
                replacement_purchases.append(purchase)
                total_invested += investment_amount
            else:
                # No replacement available - keep as cash
                ctx.setdefault("tlh_kept_as_cash", []).append({
                    "original_asset": original_asset,
                    "amount": sell["proceeds"],
                    "reason": "No suitable replacement security found"
                })
        
        ctx["tlh_replacement_purchases"] = replacement_purchases
        ctx["tlh_total_reinvested"] = total_invested
        ctx["tlh_remaining_cash"] = available_cash - total_invested
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """
        Compensate: Sell back replacement securities.
        
        Note: Since this is a PIVOT, this is typically not called
        in normal rollback scenarios.
        """
        replacement_purchases = ctx.get("tlh_replacement_purchases", [])
        
        sellback_orders = []
        for purchase in replacement_purchases:
            sellback = {
                "order_id": f"TLH_SELLBACK_{purchase['asset']}_{datetime.now().timestamp()}",
                "asset": purchase["asset"],
                "amount": purchase["amount"],
                "status": "FILLED",
                "compensation_for": purchase["order_id"],
                "timestamp": datetime.now().isoformat(),
            }
            sellback_orders.append(sellback)
        
        ctx["tlh_sellback_orders"] = sellback_orders
        ctx["tlh_replacement_purchases"] = []
        
        return ctx


class RecordTaxLotStep(TransactionStep):
    """
    Step 5: Record tax lot information for year-end reporting.
    
    Execute: Log all TLH activity for tax reporting.
    Compensate: Mark records as reverted.
    """
    
    def __init__(self):
        super().__init__(name="RecordTaxLot", is_pivot=False)
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        """Record tax lot information."""
        executed_sells = ctx.get("tlh_executed_sells", [])
        replacement_purchases = ctx.get("tlh_replacement_purchases", [])
        
        tax_records = []
        
        for sell in executed_sells:
            record = {
                "record_id": f"TAX_{datetime.now().timestamp()}_{sell['lot_id']}",
                "type": "loss_harvest",
                "date": datetime.now().isoformat(),
                "asset_sold": sell["asset"],
                "lot_id": sell["lot_id"],
                "quantity": sell["quantity"],
                "proceeds": sell["proceeds"],
                "cost_basis": sell["cost_basis"],
                "realized_loss": sell["realized_loss"],
                "holding_period": sell["holding_period"],
                "tax_year": datetime.now().year,
                "status": "recorded",
            }
            tax_records.append(record)
        
        # Find matching replacement for each sale
        for record in tax_records:
            original_asset = record["asset_sold"]
            for purchase in replacement_purchases:
                if purchase.get("original_asset") == original_asset:
                    record["replacement_asset"] = purchase["asset"]
                    record["replacement_cost"] = purchase["amount"]
                    break
        
        ctx["tlh_tax_records"] = tax_records
        ctx["tlh_completed"] = True
        ctx["tlh_summary"] = {
            "total_losses_harvested": ctx.get("tlh_harvested_losses", 0),
            "total_reinvested": ctx.get("tlh_total_reinvested", 0),
            "positions_harvested": len(executed_sells),
            "replacements_purchased": len(replacement_purchases),
            "tax_year": datetime.now().year,
            "completion_time": datetime.now().isoformat(),
        }
        
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """Mark tax records as reverted."""
        tax_records = ctx.get("tlh_tax_records", [])
        
        for record in tax_records:
            record["status"] = "reverted"
            record["revert_time"] = datetime.now().isoformat()
        
        ctx["tlh_completed"] = False
        
        return ctx


# =============================================================================
# TLH Saga Orchestrator
# =============================================================================

class TaxLossHarvestingSaga:
    """
    Configured saga for tax-loss harvesting.
    
    Steps:
    1. IdentifyLosses - Find loss positions above threshold
    2. CheckWashSale - Validate 30-day rule (expanded)
    3. SellLossPositions - Execute loss-harvesting sells
    4. PurchaseReplacement (PIVOT) - Buy replacements
    5. RecordTaxLot - Log for tax reporting
    """
    
    def __init__(
        self,
        min_loss_threshold: float = 100.0,
        on_step_start=None,
        on_step_complete=None,
    ):
        """
        Initialize the TLH saga.
        
        Args:
            min_loss_threshold: Minimum loss amount to consider for harvesting
            on_step_start: Callback(step_name, index, total) for UI updates
            on_step_complete: Callback(step_name, status) for UI updates
        """
        self.steps = [
            IdentifyLossesStep(min_loss_threshold=min_loss_threshold),
            CheckWashSaleStep(),
            SellLossPositionsStep(),
            PurchaseReplacementStep(),  # PIVOT
            RecordTaxLotStep(),
        ]
        
        self.orchestrator = SagaOrchestrator(
            steps=self.steps,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
        )
    
    def run(self, ctx: SagaContext) -> SagaResult:
        """
        Execute the TLH saga.
        
        Args:
            ctx: Context with tax_lots and transaction_history
            
        Returns:
            SagaResult with execution status and logs
        """
        return self.orchestrator.run(ctx)
    
    def get_step_names(self) -> list[str]:
        """Get list of step names for UI display."""
        return [step.name for step in self.steps]
    
    def get_pivot_step(self) -> str:
        """Get the name of the pivot step."""
        for step in self.steps:
            if step.is_pivot:
                return step.name
        return None
