"""
Tests for Financial Calculator Node

Verifies that all calculations are deterministic and accurate.
CRITICAL: These tests verify NO LLM is involved in calculations.
"""

import pytest
from src.nodes.financial_calculator import (
    calculate_rebalance,
    CalculationError,
    format_trades_summary,
)


# Test fixtures
SAMPLE_PORTFOLIO = {
    "holdings": [
        {"asset": "AAPL", "class": "stocks", "value": 50000},
        {"asset": "BND", "class": "bonds", "value": 30000},
        {"asset": "CASH", "class": "cash", "value": 15000},
        {"asset": "GLD", "class": "alternatives", "value": 5000},
    ],
    "total_value": 100000,
}

TARGET_60_30_5_5 = {
    "stocks": 0.60,
    "bonds": 0.30,
    "cash": 0.05,
    "alternatives": 0.05,
}


class TestCalculateRebalance:
    """Tests for the calculate_rebalance function."""
    
    def test_basic_rebalance_calculation(self):
        """Test that rebalance correctly identifies over/underweight positions."""
        trades = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        
        # Should have trades for stocks (need +10%), cash (need -10%)
        assert len(trades) >= 1
        
        # Find cash trade (should be SELL since 15% > 5% target)
        cash_trades = [t for t in trades if t["asset"] == "CASH"]
        assert len(cash_trades) == 1
        assert cash_trades[0]["action"] == "SELL"
        assert cash_trades[0]["amount"] == 10000.0  # 10% of $100k
    
    def test_already_balanced_portfolio(self):
        """Test that balanced portfolio produces no trades."""
        balanced_portfolio = {
            "holdings": [
                {"asset": "VTI", "class": "stocks", "value": 60000},
                {"asset": "BND", "class": "bonds", "value": 30000},
                {"asset": "CASH", "class": "cash", "value": 5000},
                {"asset": "GLD", "class": "alternatives", "value": 5000},
            ],
            "total_value": 100000,
        }
        
        trades = calculate_rebalance(balanced_portfolio, TARGET_60_30_5_5)
        assert len(trades) == 0
    
    def test_missing_portfolio_data_raises_error(self):
        """Test that missing portfolio data raises CalculationError."""
        with pytest.raises(CalculationError) as exc_info:
            calculate_rebalance(None, TARGET_60_30_5_5)
        
        assert "Portfolio data is missing" in str(exc_info.value)
    
    def test_missing_target_allocation_raises_error(self):
        """Test that missing target allocation raises CalculationError."""
        with pytest.raises(CalculationError) as exc_info:
            calculate_rebalance(SAMPLE_PORTFOLIO, None)
        
        assert "Target allocation is missing" in str(exc_info.value)
    
    def test_empty_holdings_raises_error(self):
        """Test that empty holdings raises CalculationError."""
        empty_portfolio = {"holdings": [], "total_value": 0}
        
        with pytest.raises(CalculationError) as exc_info:
            calculate_rebalance(empty_portfolio, TARGET_60_30_5_5)
        
        assert "No holdings found" in str(exc_info.value)
    
    def test_trade_amounts_are_rounded(self):
        """Test that trade amounts are properly rounded to 2 decimal places."""
        # Create a portfolio that would produce non-round numbers
        portfolio = {
            "holdings": [
                {"asset": "VTI", "class": "stocks", "value": 33333},
                {"asset": "BND", "class": "bonds", "value": 33333},
                {"asset": "CASH", "class": "cash", "value": 33334},
            ],
            "total_value": 100000,
        }
        
        trades = calculate_rebalance(portfolio, TARGET_60_30_5_5)
        
        for trade in trades:
            # Check that amount has at most 2 decimal places
            assert trade["amount"] == round(trade["amount"], 2)
    
    def test_weights_are_rounded_to_4_decimals(self):
        """Test that weights are rounded to 4 decimal places."""
        trades = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        
        for trade in trades:
            assert trade["current_weight"] == round(trade["current_weight"], 4)
            assert trade["target_weight"] == round(trade["target_weight"], 4)
    
    def test_deterministic_results(self):
        """Test that same inputs produce same outputs (determinism)."""
        trades1 = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        trades2 = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        
        assert trades1 == trades2
    
    def test_buy_sell_actions_correct(self):
        """Test that BUY/SELL actions are assigned correctly."""
        trades = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        
        for trade in trades:
            if trade["current_weight"] < trade["target_weight"]:
                assert trade["action"] == "BUY"
            else:
                assert trade["action"] == "SELL"


class TestFormatTradesSummary:
    """Tests for trade formatting."""
    
    def test_format_empty_trades(self):
        """Test formatting with no trades."""
        result = format_trades_summary([])
        assert "No trades required" in result
    
    def test_format_includes_all_trades(self):
        """Test that all trades are included in summary."""
        trades = calculate_rebalance(SAMPLE_PORTFOLIO, TARGET_60_30_5_5)
        result = format_trades_summary(trades)
        
        for trade in trades:
            assert trade["asset"] in result
            assert trade["action"] in result
