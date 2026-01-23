"""
Direct Indexing Engine - Personalized Index Construction at Scale

Implements hyper-personalized portfolio construction:
1. Custom index construction with benchmark tracking
2. Factor tilts (value, growth, dividend, momentum, quality)
3. ESG/SRI exclusion filters
4. Tax-lot level optimization integrated with TLH
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict, Optional, Any
from datetime import datetime
import uuid


# =============================================================================
# Factor Definitions
# =============================================================================

class FactorType(Enum):
    """Investment factor types for tilting."""
    VALUE = "value"          # Low P/E, P/B stocks
    GROWTH = "growth"        # High revenue/earnings growth
    DIVIDEND = "dividend"    # High dividend yield
    MOMENTUM = "momentum"    # Price momentum
    QUALITY = "quality"      # High ROE, low debt
    SIZE = "size"           # Small cap tilt
    VOLATILITY = "volatility"  # Low volatility


class ExclusionType(Enum):
    """Types of exclusion filters."""
    SECTOR = "sector"        # Exclude entire sectors
    TICKER = "ticker"        # Exclude specific tickers
    ESG_CATEGORY = "esg_category"  # ESG exclusions
    INDUSTRY = "industry"    # Exclude industries


class Benchmark(Enum):
    """Supported benchmark indices."""
    SP500 = "sp500"
    TOTAL_MARKET = "total_market"
    NASDAQ100 = "nasdaq100"
    RUSSELL1000 = "russell1000"
    RUSSELL2000 = "russell2000"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class FactorTilt:
    """Represents a factor tilt in the custom index."""
    factor: FactorType
    weight: float  # -1.0 to 1.0 (negative = tilt away)
    
    def to_dict(self) -> dict:
        return {
            "factor": self.factor.value,
            "weight": self.weight,
        }


@dataclass
class ExclusionRule:
    """Represents an exclusion rule in the custom index."""
    exclusion_type: ExclusionType
    values: list[str]  # List of sectors/tickers/categories to exclude
    reason: str = ""   # Optional reason for exclusion
    
    def to_dict(self) -> dict:
        return {
            "exclusion_type": self.exclusion_type.value,
            "values": self.values,
            "reason": self.reason,
        }


@dataclass
class CustomIndex:
    """
    A personalized index configuration.
    
    This is the core of the "Segment of One" hyper-personalization,
    allowing each client to have a truly customized portfolio.
    """
    index_id: str
    name: str
    benchmark: Benchmark
    factor_tilts: list[FactorTilt]
    exclusions: list[ExclusionRule]
    min_position_size: float = 0.001  # 0.1% minimum
    max_position_size: float = 0.05   # 5% maximum
    num_holdings: int = 100           # Target number of holdings
    tax_lot_optimization: bool = True # Enable TLH integration
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls,
        name: str,
        benchmark: Benchmark,
        factor_tilts: Optional[list[FactorTilt]] = None,
        exclusions: Optional[list[ExclusionRule]] = None,
        **kwargs
    ) -> "CustomIndex":
        """Factory method to create a new custom index."""
        return cls(
            index_id=f"idx_{uuid.uuid4().hex[:12]}",
            name=name,
            benchmark=benchmark,
            factor_tilts=factor_tilts or [],
            exclusions=exclusions or [],
            **kwargs
        )
    
    def to_dict(self) -> dict:
        return {
            "index_id": self.index_id,
            "name": self.name,
            "benchmark": self.benchmark.value,
            "factor_tilts": [t.to_dict() for t in self.factor_tilts],
            "exclusions": [e.to_dict() for e in self.exclusions],
            "min_position_size": self.min_position_size,
            "max_position_size": self.max_position_size,
            "num_holdings": self.num_holdings,
            "tax_lot_optimization": self.tax_lot_optimization,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class IndexHolding:
    """A single holding in a constructed portfolio."""
    ticker: str
    name: str
    weight: float           # Target weight in portfolio
    shares: float           # Number of shares
    value: float            # Dollar value
    sector: str
    factor_scores: dict     # Scores for each factor
    excluded: bool = False  # If excluded by rules
    exclusion_reason: str = ""
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "weight": self.weight,
            "shares": self.shares,
            "value": self.value,
            "sector": self.sector,
            "factor_scores": self.factor_scores,
            "excluded": self.excluded,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass
class ConstructedPortfolio:
    """Result of portfolio construction."""
    index_id: str
    holdings: list[IndexHolding]
    total_value: float
    tracking_error: float      # Expected vs benchmark
    turnover_estimate: float   # Annual turnover estimate
    tax_efficiency_score: float
    exclusions_applied: int
    factor_exposures: dict     # Actual factor exposures
    
    def to_dict(self) -> dict:
        return {
            "index_id": self.index_id,
            "holdings": [h.to_dict() for h in self.holdings],
            "total_value": self.total_value,
            "tracking_error": self.tracking_error,
            "turnover_estimate": self.turnover_estimate,
            "tax_efficiency_score": self.tax_efficiency_score,
            "exclusions_applied": self.exclusions_applied,
            "factor_exposures": self.factor_exposures,
        }


@dataclass
class Trade:
    """A trade to execute for the direct index."""
    ticker: str
    action: str  # "BUY" or "SELL"
    shares: float
    value: float
    reason: str
    is_tax_lot_optimized: bool = False
    tax_lot_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "action": self.action,
            "shares": self.shares,
            "value": self.value,
            "reason": self.reason,
            "is_tax_lot_optimized": self.is_tax_lot_optimized,
            "tax_lot_id": self.tax_lot_id,
        }


# =============================================================================
# Mock Benchmark Data
# =============================================================================

# Simplified S&P 500 constituents for demo
SP500_CONSTITUENTS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.07, "sector": "Technology", "factors": {"value": -0.5, "growth": 0.8, "dividend": 0.2, "momentum": 0.6, "quality": 0.9}},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "weight": 0.065, "sector": "Technology", "factors": {"value": -0.3, "growth": 0.7, "dividend": 0.3, "momentum": 0.7, "quality": 0.95}},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "weight": 0.04, "sector": "Technology", "factors": {"value": 0.1, "growth": 0.6, "dividend": 0.0, "momentum": 0.5, "quality": 0.85}},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "weight": 0.035, "sector": "Consumer Discretionary", "factors": {"value": -0.6, "growth": 0.9, "dividend": 0.0, "momentum": 0.4, "quality": 0.7}},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "weight": 0.03, "sector": "Technology", "factors": {"value": -0.8, "growth": 0.95, "dividend": 0.1, "momentum": 0.9, "quality": 0.8}},
    {"ticker": "META", "name": "Meta Platforms Inc.", "weight": 0.025, "sector": "Technology", "factors": {"value": 0.3, "growth": 0.5, "dividend": 0.0, "momentum": 0.6, "quality": 0.75}},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway", "weight": 0.02, "sector": "Financials", "factors": {"value": 0.7, "growth": 0.2, "dividend": 0.0, "momentum": 0.3, "quality": 0.9}},
    {"ticker": "JPM", "name": "JPMorgan Chase", "weight": 0.018, "sector": "Financials", "factors": {"value": 0.5, "growth": 0.4, "dividend": 0.6, "momentum": 0.5, "quality": 0.8}},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "weight": 0.015, "sector": "Healthcare", "factors": {"value": 0.4, "growth": 0.2, "dividend": 0.8, "momentum": 0.2, "quality": 0.85}},
    {"ticker": "V", "name": "Visa Inc.", "weight": 0.014, "sector": "Financials", "factors": {"value": -0.2, "growth": 0.6, "dividend": 0.4, "momentum": 0.6, "quality": 0.9}},
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "weight": 0.013, "sector": "Energy", "factors": {"value": 0.6, "growth": 0.1, "dividend": 0.9, "momentum": 0.4, "quality": 0.7}},
    {"ticker": "CVX", "name": "Chevron Corp.", "weight": 0.012, "sector": "Energy", "factors": {"value": 0.5, "growth": 0.1, "dividend": 0.85, "momentum": 0.3, "quality": 0.75}},
    {"ticker": "PG", "name": "Procter & Gamble", "weight": 0.011, "sector": "Consumer Staples", "factors": {"value": 0.2, "growth": 0.3, "dividend": 0.7, "momentum": 0.4, "quality": 0.88}},
    {"ticker": "HD", "name": "Home Depot", "weight": 0.01, "sector": "Consumer Discretionary", "factors": {"value": 0.1, "growth": 0.5, "dividend": 0.6, "momentum": 0.5, "quality": 0.82}},
    {"ticker": "MRK", "name": "Merck & Co.", "weight": 0.01, "sector": "Healthcare", "factors": {"value": 0.3, "growth": 0.4, "dividend": 0.7, "momentum": 0.6, "quality": 0.8}},
    # Tobacco companies (for ESG testing)
    {"ticker": "PM", "name": "Philip Morris", "weight": 0.008, "sector": "Consumer Staples", "factors": {"value": 0.6, "growth": 0.1, "dividend": 0.95, "momentum": 0.3, "quality": 0.7}},
    {"ticker": "MO", "name": "Altria Group", "weight": 0.006, "sector": "Consumer Staples", "factors": {"value": 0.8, "growth": -0.1, "dividend": 0.98, "momentum": 0.1, "quality": 0.5}},
    # Defense companies (for ESG testing)
    {"ticker": "LMT", "name": "Lockheed Martin", "weight": 0.007, "sector": "Industrials", "factors": {"value": 0.4, "growth": 0.3, "dividend": 0.6, "momentum": 0.5, "quality": 0.75}},
    {"ticker": "RTX", "name": "Raytheon Tech", "weight": 0.006, "sector": "Industrials", "factors": {"value": 0.3, "growth": 0.4, "dividend": 0.5, "momentum": 0.4, "quality": 0.7}},
]

# ESG exclusion categories
ESG_EXCLUSIONS = {
    "tobacco": ["PM", "MO", "BTI", "BATS"],
    "defense": ["LMT", "RTX", "NOC", "GD", "BA"],
    "gambling": ["MGM", "LVS", "WYNN", "CZR"],
    "fossil_fuels": ["XOM", "CVX", "COP", "EOG", "OXY", "SLB"],
    "firearms": ["SWBI", "RGR"],
}


# =============================================================================
# Direct Indexing Engine
# =============================================================================

class DirectIndexingEngine:
    """
    Engine for constructing personalized index portfolios.
    
    This is the core of "Direct Indexing at Scale" - enabling
    hyper-personalization for every client.
    """
    
    def __init__(self):
        self._indices: dict[str, CustomIndex] = {}
    
    def register_index(self, index: CustomIndex) -> str:
        """Register a custom index configuration."""
        self._indices[index.index_id] = index
        return index.index_id
    
    def get_index(self, index_id: str) -> Optional[CustomIndex]:
        """Get a registered index by ID."""
        return self._indices.get(index_id)
    
    def list_indices(self) -> list[CustomIndex]:
        """List all registered indices."""
        return list(self._indices.values())
    
    def construct_portfolio(
        self,
        index: CustomIndex,
        investment_amount: float,
        existing_tax_lots: Optional[list[dict]] = None,
    ) -> ConstructedPortfolio:
        """
        Construct a personalized portfolio based on the custom index.
        
        Args:
            index: The custom index configuration
            investment_amount: Total dollars to invest
            existing_tax_lots: Existing positions for tax-lot optimization
            
        Returns:
            ConstructedPortfolio with holdings and analytics
        """
        # Start with benchmark constituents
        constituents = SP500_CONSTITUENTS.copy()
        
        # Apply exclusions
        excluded_count = 0
        for exclusion in index.exclusions:
            if exclusion.exclusion_type == ExclusionType.SECTOR:
                for c in constituents:
                    if c["sector"] in exclusion.values:
                        c["excluded"] = True
                        c["exclusion_reason"] = f"Sector exclusion: {c['sector']}"
                        excluded_count += 1
            elif exclusion.exclusion_type == ExclusionType.TICKER:
                for c in constituents:
                    if c["ticker"] in exclusion.values:
                        c["excluded"] = True
                        c["exclusion_reason"] = f"Ticker exclusion: {c['ticker']}"
                        excluded_count += 1
            elif exclusion.exclusion_type == ExclusionType.ESG_CATEGORY:
                for category in exclusion.values:
                    excluded_tickers = ESG_EXCLUSIONS.get(category, [])
                    for c in constituents:
                        if c["ticker"] in excluded_tickers:
                            c["excluded"] = True
                            c["exclusion_reason"] = f"ESG exclusion: {category}"
                            excluded_count += 1
        
        # Filter out excluded
        active_constituents = [c for c in constituents if not c.get("excluded", False)]
        
        # Apply factor tilts
        for tilt in index.factor_tilts:
            for c in active_constituents:
                factor_score = c["factors"].get(tilt.factor.value, 0)
                # Adjust weight based on factor score and tilt
                c["weight"] *= (1 + tilt.weight * factor_score * 0.5)
        
        # Normalize weights
        total_weight = sum(c["weight"] for c in active_constituents)
        for c in active_constituents:
            c["weight"] = c["weight"] / total_weight
        
        # Apply position size constraints
        for c in active_constituents:
            c["weight"] = max(index.min_position_size, 
                             min(index.max_position_size, c["weight"]))
        
        # Re-normalize after constraints
        total_weight = sum(c["weight"] for c in active_constituents)
        for c in active_constituents:
            c["weight"] = c["weight"] / total_weight
        
        # Calculate holdings
        holdings = []
        for c in active_constituents[:index.num_holdings]:
            value = investment_amount * c["weight"]
            # Assume $100 per share for demo
            shares = value / 100
            
            holdings.append(IndexHolding(
                ticker=c["ticker"],
                name=c["name"],
                weight=c["weight"],
                shares=round(shares, 4),
                value=round(value, 2),
                sector=c["sector"],
                factor_scores=c["factors"],
            ))
        
        # Calculate factor exposures
        factor_exposures = {}
        for factor in FactorType:
            exposure = sum(
                h.weight * h.factor_scores.get(factor.value, 0) 
                for h in holdings
            )
            factor_exposures[factor.value] = round(exposure, 4)
        
        # Calculate tracking error (simplified)
        tracking_error = 0.02 + (len(index.factor_tilts) * 0.005) + (excluded_count * 0.002)
        
        return ConstructedPortfolio(
            index_id=index.index_id,
            holdings=holdings,
            total_value=investment_amount,
            tracking_error=round(tracking_error, 4),
            turnover_estimate=0.15,  # 15% annual turnover estimate
            tax_efficiency_score=0.92 if index.tax_lot_optimization else 0.75,
            exclusions_applied=excluded_count,
            factor_exposures=factor_exposures,
        )
    
    def calculate_tracking_error(
        self,
        custom_portfolio: ConstructedPortfolio,
        benchmark: Benchmark,
    ) -> float:
        """Calculate tracking error vs benchmark."""
        # Simplified tracking error calculation
        return custom_portfolio.tracking_error
    
    def generate_trades(
        self,
        index: CustomIndex,
        investment_amount: float,
        current_holdings: Optional[dict[str, float]] = None,
        existing_tax_lots: Optional[list[dict]] = None,
    ) -> list[Trade]:
        """
        Generate trades to achieve target portfolio.
        
        Args:
            index: Custom index configuration
            investment_amount: Total investment amount
            current_holdings: Current positions {ticker: value}
            existing_tax_lots: Tax lots for TLH optimization
            
        Returns:
            List of trades to execute
        """
        # Construct target portfolio
        target = self.construct_portfolio(index, investment_amount, existing_tax_lots)
        current = current_holdings or {}
        
        trades = []
        
        # Calculate buys and sells
        for holding in target.holdings:
            current_value = current.get(holding.ticker, 0)
            target_value = holding.value
            
            diff = target_value - current_value
            
            if abs(diff) > 10:  # Minimum trade size $10
                trades.append(Trade(
                    ticker=holding.ticker,
                    action="BUY" if diff > 0 else "SELL",
                    shares=abs(diff) / 100,  # Assume $100/share
                    value=abs(diff),
                    reason=f"Rebalance to target weight {holding.weight:.2%}",
                    is_tax_lot_optimized=index.tax_lot_optimization,
                ))
        
        return trades


# =============================================================================
# Pre-configured Sample Indices
# =============================================================================

def create_sample_indices() -> list[CustomIndex]:
    """Create sample custom indices for demo."""
    
    # ESG Conscious Index
    esg_index = CustomIndex.create(
        name="ESG Values Index",
        benchmark=Benchmark.SP500,
        factor_tilts=[
            FactorTilt(FactorType.QUALITY, 0.3),
        ],
        exclusions=[
            ExclusionRule(ExclusionType.ESG_CATEGORY, ["tobacco", "defense", "fossil_fuels"], "ESG values"),
        ],
    )
    
    # High Dividend Index
    dividend_index = CustomIndex.create(
        name="Dividend Champion Index",
        benchmark=Benchmark.SP500,
        factor_tilts=[
            FactorTilt(FactorType.DIVIDEND, 0.8),
            FactorTilt(FactorType.QUALITY, 0.4),
            FactorTilt(FactorType.VALUE, 0.2),
        ],
    )
    
    # Growth Momentum Index
    growth_index = CustomIndex.create(
        name="Growth Momentum Index",
        benchmark=Benchmark.SP500,
        factor_tilts=[
            FactorTilt(FactorType.GROWTH, 0.7),
            FactorTilt(FactorType.MOMENTUM, 0.5),
        ],
    )
    
    return [esg_index, dividend_index, growth_index]


# Global engine instance
_global_engine = DirectIndexingEngine()

# Register sample indices
for idx in create_sample_indices():
    _global_engine.register_index(idx)


def get_global_engine() -> DirectIndexingEngine:
    """Get the global direct indexing engine instance."""
    return _global_engine
