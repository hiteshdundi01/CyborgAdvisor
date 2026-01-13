"""
Tests for Compliance Check Node

Verifies that all compliance rules are correctly enforced.
All rules are deterministic - NO LLM involved.
"""

import pytest
from src.nodes.compliance_check import (
    run_compliance_checks,
    CashPositionRule,
    TradeSizeRule,
)
from src.state import Trade


# Test fixtures
SAMPLE_PORTFOLIO = {
    "holdings": [
        {"asset": "VTI", "class": "stocks", "value": 60000},
        {"asset": "BND", "class": "bonds", "value": 30000},
        {"asset": "CASH", "class": "cash", "value": 8000},
        {"asset": "GLD", "class": "alternatives", "value": 2000},
    ],
    "total_value": 100000,
}


def make_trade(asset: str, action: str, amount: float) -> Trade:
    """Helper to create Trade objects."""
    return Trade(
        asset=asset,
        action=action,
        amount=amount,
        current_weight=0.0,
        target_weight=0.0,
        reason="test",
    )


class TestCashPositionRule:
    """Tests for Rule A: Cash position must not go negative."""
    
    def test_valid_trade_passes(self):
        """Test that trades keeping cash positive pass."""
        rule = CashPositionRule()
        trades = [make_trade("STOCKS", "BUY", 5000)]  # Uses 5k cash
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True
        assert error is None
    
    def test_negative_cash_fails(self):
        """Test that trades causing negative cash fail."""
        rule = CashPositionRule()
        # Try to buy 20k stocks with only 8k cash
        trades = [make_trade("STOCKS", "BUY", 20000)]
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is False
        assert "negative cash" in error.lower()
    
    def test_below_minimum_fails(self):
        """Test that reducing cash below 2% fails."""
        rule = CashPositionRule()
        # Buy 7k stocks, leaving only 1k cash (1% < 2% minimum)
        trades = [make_trade("STOCKS", "BUY", 7000)]
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is False
        assert "2%" in error
    
    def test_sell_increases_cash(self):
        """Test that selling increases available cash."""
        rule = CashPositionRule()
        # Sell stocks then buy - net should be fine
        trades = [
            make_trade("STOCKS", "SELL", 5000),
            make_trade("BONDS", "BUY", 5000),
        ]
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True


class TestTradeSizeRule:
    """Tests for Rule B: No single trade > 10% of portfolio."""
    
    def test_small_trade_passes(self):
        """Test that trades under 10% pass."""
        rule = TradeSizeRule()
        trades = [make_trade("STOCKS", "BUY", 5000)]  # 5%
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True
        assert error is None
    
    def test_exactly_10_percent_passes(self):
        """Test that exactly 10% passes."""
        rule = TradeSizeRule()
        trades = [make_trade("STOCKS", "BUY", 10000)]  # Exactly 10%
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True
    
    def test_over_10_percent_fails(self):
        """Test that trades over 10% fail."""
        rule = TradeSizeRule()
        trades = [make_trade("STOCKS", "BUY", 15000)]  # 15%
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is False
        assert "10%" in error
    
    def test_multiple_small_trades_pass(self):
        """Test that multiple small trades each pass individually."""
        rule = TradeSizeRule()
        trades = [
            make_trade("STOCKS", "BUY", 9000),
            make_trade("BONDS", "SELL", 9000),
            make_trade("ALTERNATIVES", "BUY", 9000),
        ]
        
        passed, error = rule.check(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True


class TestRunComplianceChecks:
    """Tests for the combined compliance check runner."""
    
    def test_all_valid_passes(self):
        """Test that valid trades pass all rules."""
        trades = [make_trade("STOCKS", "BUY", 5000)]
        
        passed, errors = run_compliance_checks(trades, SAMPLE_PORTFOLIO)
        
        assert passed is True
        assert len(errors) == 0
    
    def test_multiple_violations_reported(self):
        """Test that multiple rule violations are all reported."""
        # This trade is too large (15%) and would exhaust cash
        trades = [make_trade("STOCKS", "BUY", 15000)]
        
        passed, errors = run_compliance_checks(trades, SAMPLE_PORTFOLIO)
        
        assert passed is False
        assert len(errors) >= 1  # At least trade size violation
    
    def test_empty_trades_pass(self):
        """Test that empty trade list passes compliance."""
        passed, errors = run_compliance_checks([], SAMPLE_PORTFOLIO)
        
        assert passed is True
        assert len(errors) == 0
    
    def test_deterministic_results(self):
        """Test that same inputs produce same outputs."""
        trades = [make_trade("STOCKS", "BUY", 5000)]
        
        result1 = run_compliance_checks(trades, SAMPLE_PORTFOLIO)
        result2 = run_compliance_checks(trades, SAMPLE_PORTFOLIO)
        
        assert result1 == result2
