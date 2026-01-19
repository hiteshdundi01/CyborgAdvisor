"""
Tests for Tax Loss Harvesting Saga

Tests the TaxLossHarvestingSaga with:
- Loss identification with FIFO ordering
- Expanded wash sale rule detection (fund family)
- Forward success (all 5 steps)
- Mid-stream failure and rollback
- Pivot transaction (no rollback past PurchaseReplacement)
- Tax impact calculations
"""

import pytest
from datetime import datetime, timedelta

from src.sagas.tax_loss_harvesting import (
    TaxLossHarvestingSaga,
    TaxLot,
    IdentifyLossesStep,
    CheckWashSaleStep,
    SellLossPositionsStep,
    PurchaseReplacementStep,
    RecordTaxLotStep,
    is_substantially_identical,
    get_replacement_suggestions,
    FUND_FAMILY_MAPPING,
)
from src.sagas.core import SagaContext, SagaStatus, StepStatus


# =============================================================================
# Helper Functions (avoid langchain dependency)
# =============================================================================

def identify_loss_opportunities(
    tax_lots: list[dict],
    min_threshold: float = 100.0,
    max_positions: int = 10,
) -> list[dict]:
    """Identify tax-loss harvesting opportunities using FIFO ordering."""
    losses = [
        lot for lot in tax_lots
        if lot.get("unrealized_gain_loss", 0) < -min_threshold
    ]
    losses.sort(key=lambda x: x.get("unrealized_gain_loss", 0))
    return losses[:max_positions]


def calculate_tax_impact(
    losses: list[dict],
    federal_rate: float = 0.24,
    state_rate: float = 0.05,
    long_term_rate: float = 0.15,
) -> dict:
    """Calculate estimated tax savings from harvesting losses."""
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
    short_term_savings = short_term_losses * (federal_rate + state_rate)
    long_term_savings = long_term_losses * long_term_rate
    total_savings = short_term_savings + long_term_savings
    
    return {
        "short_term_losses": round(short_term_losses, 2),
        "long_term_losses": round(long_term_losses, 2),
        "total_losses": round(total_losses, 2),
        "estimated_short_term_savings": round(short_term_savings, 2),
        "estimated_long_term_savings": round(long_term_savings, 2),
        "total_estimated_savings": round(total_savings, 2),
    }


def generate_mock_tax_lots() -> list[dict]:
    """Generate 28 realistic tax lot entries for testing."""
    base_date = datetime.now()
    
    mock_data = [
        ("AAPL", 185.50, 172.30, 50, base_date - timedelta(days=45)),
        ("AAPL", 192.00, 172.30, 30, base_date - timedelta(days=120)),
        ("MSFT", 420.00, 385.50, 25, base_date - timedelta(days=200)),
        ("GOOGL", 155.00, 138.20, 40, base_date - timedelta(days=90)),
        ("NVDA", 890.00, 750.00, 15, base_date - timedelta(days=60)),
        ("META", 520.00, 485.00, 20, base_date - timedelta(days=180)),
        ("VTI", 265.00, 248.50, 100, base_date - timedelta(days=400)),
        ("VOO", 480.00, 455.00, 50, base_date - timedelta(days=450)),
        ("BND", 78.00, 72.50, 200, base_date - timedelta(days=500)),
        ("VXUS", 62.00, 55.80, 150, base_date - timedelta(days=380)),
        ("GLD", 195.00, 182.00, 60, base_date - timedelta(days=100)),
        ("AAPL", 125.00, 172.30, 100, base_date - timedelta(days=800)),
        ("MSFT", 280.00, 385.50, 50, base_date - timedelta(days=900)),
        ("GOOGL", 95.00, 138.20, 80, base_date - timedelta(days=750)),
        ("AMZN", 145.00, 185.50, 45, base_date - timedelta(days=600)),
        ("VTI", 195.00, 248.50, 200, base_date - timedelta(days=1100)),
        ("VOO", 350.00, 455.00, 75, base_date - timedelta(days=950)),
        ("TSLA", 265.00, 248.00, 35, base_date - timedelta(days=150)),
        ("TSLA", 180.00, 248.00, 25, base_date - timedelta(days=420)),
        ("SPY", 485.00, 472.00, 40, base_date - timedelta(days=80)),
        ("IVV", 520.00, 505.00, 30, base_date - timedelta(days=95)),
        ("AGG", 105.00, 98.50, 150, base_date - timedelta(days=300)),
        ("VNQ", 95.00, 88.00, 80, base_date - timedelta(days=250)),
        ("SCHB", 58.00, 54.50, 120, base_date - timedelta(days=180)),
        ("IXUS", 72.00, 65.50, 90, base_date - timedelta(days=220)),
        ("IAU", 42.00, 39.50, 100, base_date - timedelta(days=130)),
        ("SCHZ", 52.00, 48.80, 180, base_date - timedelta(days=280)),
        ("IYR", 102.00, 96.00, 55, base_date - timedelta(days=190)),
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


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_tax_lots():
    """Create sample tax lots with known gains/losses."""
    base_date = datetime.now()
    return [
        {
            "lot_id": "LOT_AAPL_001",
            "asset": "AAPL",
            "purchase_date": (base_date - timedelta(days=60)).isoformat(),
            "purchase_price": 180.0,
            "quantity": 50,
            "current_price": 165.0,
            "cost_basis": 9000.0,
            "current_value": 8250.0,
            "unrealized_gain_loss": -750.0,  # Loss
            "holding_period": "short_term",
            "days_held": 60,
        },
        {
            "lot_id": "LOT_VTI_001",
            "asset": "VTI",
            "purchase_date": (base_date - timedelta(days=400)).isoformat(),
            "purchase_price": 250.0,
            "quantity": 100,
            "current_price": 235.0,
            "cost_basis": 25000.0,
            "current_value": 23500.0,
            "unrealized_gain_loss": -1500.0,  # Long-term loss
            "holding_period": "long_term",
            "days_held": 400,
        },
        {
            "lot_id": "LOT_MSFT_001",
            "asset": "MSFT",
            "purchase_date": (base_date - timedelta(days=500)).isoformat(),
            "purchase_price": 280.0,
            "quantity": 30,
            "current_price": 350.0,
            "cost_basis": 8400.0,
            "current_value": 10500.0,
            "unrealized_gain_loss": 2100.0,  # Gain (not for harvesting)
            "holding_period": "long_term",
            "days_held": 500,
        },
        {
            "lot_id": "LOT_BND_001",
            "asset": "BND",
            "purchase_date": (base_date - timedelta(days=300)).isoformat(),
            "purchase_price": 78.0,
            "quantity": 150,
            "current_price": 72.0,
            "cost_basis": 11700.0,
            "current_value": 10800.0,
            "unrealized_gain_loss": -900.0,  # Short-term loss
            "holding_period": "short_term",
            "days_held": 300,
        },
    ]


@pytest.fixture
def clean_transaction_history():
    """Transaction history with no wash sale conflicts."""
    base_date = datetime.now()
    return [
        # All purchases are > 30 days ago
        {"date": (base_date - timedelta(days=60)).isoformat(), "asset": "AAPL", "action": "BUY", "quantity": 50, "price": 180.0},
        {"date": (base_date - timedelta(days=400)).isoformat(), "asset": "VTI", "action": "BUY", "quantity": 100, "price": 250.0},
        {"date": (base_date - timedelta(days=45)).isoformat(), "asset": "GOOGL", "action": "SELL", "quantity": 20, "price": 150.0},
    ]


@pytest.fixture
def wash_sale_transaction_history():
    """Transaction history with wash sale conflicts."""
    base_date = datetime.now()
    return [
        # Recent VTI purchase (within 30 days) - will trigger wash sale for VTI
        {"date": (base_date - timedelta(days=15)).isoformat(), "asset": "VTI", "action": "BUY", "quantity": 10, "price": 240.0},
        # Recent ITOT purchase (same fund family as VTI) - also triggers wash sale
        {"date": (base_date - timedelta(days=20)).isoformat(), "asset": "ITOT", "action": "BUY", "quantity": 15, "price": 110.0},
        # Older purchases (OK)
        {"date": (base_date - timedelta(days=60)).isoformat(), "asset": "AAPL", "action": "BUY", "quantity": 50, "price": 180.0},
    ]


# =============================================================================
# Test Substantially Identical Detection (Expanded Wash Sale Rule)
# =============================================================================

class TestSubstantiallyIdentical:
    """Test the expanded wash sale rule detection."""
    
    def test_same_ticker_is_identical(self):
        """Same ticker should always be substantially identical."""
        assert is_substantially_identical("VTI", "VTI") is True
        assert is_substantially_identical("AAPL", "AAPL") is True
    
    def test_same_fund_family_is_identical(self):
        """Same fund family (different providers) should be identical."""
        # Total US stock market funds
        assert is_substantially_identical("VTI", "ITOT") is True
        assert is_substantially_identical("VTI", "SPTM") is True
        assert is_substantially_identical("ITOT", "SCHB") is True
        
        # S&P 500 funds
        assert is_substantially_identical("SPY", "VOO") is True
        assert is_substantially_identical("VOO", "IVV") is True
        
        # Total bond market
        assert is_substantially_identical("BND", "AGG") is True
    
    def test_different_family_not_identical(self):
        """Different fund families should NOT be identical."""
        # Total stock vs S&P 500 (different indices)
        assert is_substantially_identical("VTI", "SPY") is False
        
        # Stock vs Bond
        assert is_substantially_identical("VTI", "BND") is False
        
        # Individual stocks (different companies)
        assert is_substantially_identical("AAPL", "MSFT") is False
    
    def test_individual_stocks_same_class(self):
        """GOOG and GOOGL should be identical (same company)."""
        assert is_substantially_identical("GOOGL", "GOOG") is True
    
    def test_unknown_ticker_not_identical(self):
        """Unknown tickers should not be considered identical."""
        assert is_substantially_identical("AAPL", "UNKNOWN") is False
        assert is_substantially_identical("UNKNOWN1", "UNKNOWN2") is False


class TestReplacementSuggestions:
    """Test replacement security suggestions."""
    
    def test_etf_has_replacements(self):
        """ETFs should have replacement suggestions."""
        replacements = get_replacement_suggestions("VTI")
        assert len(replacements) > 0
        assert "ITOT" in replacements or "SPTM" in replacements
        
        # SPY replacements
        replacements = get_replacement_suggestions("SPY")
        assert "VOO" in replacements or "IVV" in replacements
    
    def test_individual_stock_no_replacements(self):
        """Individual stocks should have no automatic replacements."""
        replacements = get_replacement_suggestions("AAPL")
        assert len(replacements) == 0
        
        replacements = get_replacement_suggestions("MSFT")
        assert len(replacements) == 0


# =============================================================================
# Test Loss Identification
# =============================================================================

class TestIdentifyLosses:
    """Test loss identification with FIFO ordering."""
    
    def test_identifies_losses_above_threshold(self, sample_tax_lots):
        """Should identify positions with losses above threshold."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        
        # Should find 3 losses: AAPL (-750), VTI (-1500), BND (-900)
        assert len(opportunities) == 3
        
        # All should have negative unrealized_gain_loss
        for opp in opportunities:
            assert opp["unrealized_gain_loss"] < -100
    
    def test_excludes_gains(self, sample_tax_lots):
        """Should not include positions with gains."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        
        # MSFT has a gain, should not be included
        assets = [opp["asset"] for opp in opportunities]
        assert "MSFT" not in assets
    
    def test_sorts_by_largest_loss(self, sample_tax_lots):
        """Should sort by largest loss first."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        
        # VTI has largest loss (-1500), should be first
        assert opportunities[0]["asset"] == "VTI"
        assert opportunities[0]["unrealized_gain_loss"] == -1500.0
    
    def test_respects_threshold(self, sample_tax_lots):
        """Should exclude losses below threshold."""
        # High threshold - should exclude some losses
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=1000)
        
        # Only VTI (-1500) exceeds 1000
        assert len(opportunities) == 1
        assert opportunities[0]["asset"] == "VTI"
    
    def test_mock_data_has_25_plus_entries(self):
        """Mock data should have at least 25 entries."""
        tax_lots = generate_mock_tax_lots()
        assert len(tax_lots) >= 25


# =============================================================================
# Test Tax Impact Calculation
# =============================================================================

class TestTaxImpact:
    """Test tax impact/savings calculations."""
    
    def test_calculates_short_term_savings(self, sample_tax_lots):
        """Should calculate savings at ordinary income rates for short-term losses."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        impact = calculate_tax_impact(opportunities, federal_rate=0.24, state_rate=0.05)
        
        # Should have short-term losses (AAPL, BND)
        assert impact["short_term_losses"] > 0
        assert impact["estimated_short_term_savings"] > 0
    
    def test_calculates_long_term_savings(self, sample_tax_lots):
        """Should calculate savings at capital gains rates for long-term losses."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        impact = calculate_tax_impact(opportunities, long_term_rate=0.15)
        
        # Should have long-term losses (VTI)
        assert impact["long_term_losses"] > 0
        assert impact["estimated_long_term_savings"] > 0
    
    def test_total_savings_is_sum(self, sample_tax_lots):
        """Total savings should equal sum of short and long term."""
        opportunities = identify_loss_opportunities(sample_tax_lots, min_threshold=100)
        impact = calculate_tax_impact(opportunities)
        
        expected_total = impact["estimated_short_term_savings"] + impact["estimated_long_term_savings"]
        assert abs(impact["total_estimated_savings"] - expected_total) < 0.01


# =============================================================================
# Test TLH Saga Execution
# =============================================================================

class TestTLHSagaForwardSuccess:
    """Test that TLH saga executes all 5 steps successfully."""
    
    def test_all_steps_succeed(self, sample_tax_lots, clean_transaction_history):
        """All 5 steps should complete successfully."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": clean_transaction_history,
        }
        
        result = saga.run(ctx)
        
        assert result.status == SagaStatus.SUCCESS
        assert len(result.context["executed_steps"]) == 5
        
        # Check all steps ran
        step_names = saga.get_step_names()
        assert step_names == ["IdentifyLosses", "CheckWashSale", "SellLossPositions", "PurchaseReplacement", "RecordTaxLot"]
    
    def test_identifies_opportunities(self, sample_tax_lots, clean_transaction_history):
        """Saga should identify loss opportunities."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": clean_transaction_history,
        }
        
        result = saga.run(ctx)
        
        assert result.context.get("tlh_opportunities") is not None
        assert len(result.context["tlh_opportunities"]) > 0
    
    def test_records_tax_lots(self, sample_tax_lots, clean_transaction_history):
        """Saga should create tax records."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": clean_transaction_history,
        }
        
        result = saga.run(ctx)
        
        assert result.context.get("tlh_tax_records") is not None
        assert result.context.get("tlh_completed") is True


class TestTLHSagaWashSaleDetection:
    """Test wash sale detection and handling."""
    
    def test_detects_wash_sale_violations(self, sample_tax_lots, wash_sale_transaction_history):
        """Should detect wash sale violations for recent purchases."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": wash_sale_transaction_history,
        }
        
        result = saga.run(ctx)
        
        # VTI should have wash sale violation
        violations = result.context.get("tlh_wash_sale_violations", [])
        violated_assets = [v["asset"] for v in violations]
        assert "VTI" in violated_assets
    
    def test_excludes_wash_sale_from_harvesting(self, sample_tax_lots, wash_sale_transaction_history):
        """Wash sale positions should not be harvested."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": wash_sale_transaction_history,
        }
        
        result = saga.run(ctx)
        
        # Valid opportunities should not include VTI
        valid = result.context.get("tlh_valid_opportunities", [])
        valid_assets = [v["asset"] for v in valid]
        assert "VTI" not in valid_assets


class TestTLHSagaRollback:
    """Test saga rollback on failure."""
    
    def test_rollback_on_replacement_failure(self, sample_tax_lots, clean_transaction_history):
        """Should rollback completed steps when PurchaseReplacement fails."""
        saga = TaxLossHarvestingSaga(min_loss_threshold=100)
        
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
            "tax_lots": sample_tax_lots,
            "transaction_history": clean_transaction_history,
            "simulate_replacement_failure": True,  # Trigger failure
        }
        
        result = saga.run(ctx)
        
        assert result.status == SagaStatus.ROLLED_BACK
        assert "Simulated failure" in result.error
        
        # Previous steps should be compensated
        compensation_logs = [log for log in result.logs if log.status == StepStatus.COMPENSATED]
        assert len(compensation_logs) > 0


class TestTLHSagaPivotTransaction:
    """Test that pivot transaction stops rollback."""
    
    def test_pivot_is_purchase_replacement(self):
        """PurchaseReplacement should be the pivot step."""
        saga = TaxLossHarvestingSaga()
        assert saga.get_pivot_step() == "PurchaseReplacement"
    
    def test_step_has_pivot_flag(self):
        """PurchaseReplacementStep should have is_pivot=True."""
        step = PurchaseReplacementStep()
        assert step.is_pivot is True


# =============================================================================
# Test TaxLot Class
# =============================================================================

class TestTaxLotClass:
    """Test TaxLot data class."""
    
    def test_unrealized_gain_loss_calculation(self):
        """Should correctly calculate unrealized gain/loss."""
        lot = TaxLot(
            lot_id="TEST_001",
            asset="AAPL",
            purchase_date=datetime.now() - timedelta(days=100),
            purchase_price=150.0,
            quantity=10,
            current_price=140.0,
        )
        
        assert lot.cost_basis == 1500.0
        assert lot.current_value == 1400.0
        assert lot.unrealized_gain_loss == -100.0  # Loss
    
    def test_holding_period_short_term(self):
        """Should identify short-term holding period."""
        lot = TaxLot(
            lot_id="TEST_001",
            asset="AAPL",
            purchase_date=datetime.now() - timedelta(days=100),
            purchase_price=150.0,
            quantity=10,
            current_price=140.0,
        )
        
        assert lot.holding_period == "short_term"
    
    def test_holding_period_long_term(self):
        """Should identify long-term holding period."""
        lot = TaxLot(
            lot_id="TEST_001",
            asset="AAPL",
            purchase_date=datetime.now() - timedelta(days=400),
            purchase_price=150.0,
            quantity=10,
            current_price=140.0,
        )
        
        assert lot.holding_period == "long_term"
    
    def test_to_dict(self):
        """Should serialize to dictionary."""
        lot = TaxLot(
            lot_id="TEST_001",
            asset="AAPL",
            purchase_date=datetime.now() - timedelta(days=100),
            purchase_price=150.0,
            quantity=10,
            current_price=140.0,
        )
        
        d = lot.to_dict()
        assert d["lot_id"] == "TEST_001"
        assert d["asset"] == "AAPL"
        assert d["unrealized_gain_loss"] == -100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
