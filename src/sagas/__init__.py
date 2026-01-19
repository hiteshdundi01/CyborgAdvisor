# Saga Engine Module
"""
Transactional Saga Pattern implementation for Cyborg Advisor.

Includes:
- RebalanceSaga: Portfolio rebalancing workflow
- TaxLossHarvestingSaga: Tax-loss harvesting workflow
"""

from .core import (
    SagaContext,
    SagaResult,
    SagaStatus,
    StepStatus,
    StepLog,
    TransactionStep,
    SagaOrchestrator,
)
from .rebalance import RebalanceSaga
from .tax_loss_harvesting import (
    TaxLossHarvestingSaga,
    TaxLot,
    is_substantially_identical,
    get_replacement_suggestions,
    FUND_FAMILY_MAPPING,
)

__all__ = [
    # Core
    "SagaContext",
    "SagaResult",
    "SagaStatus",
    "StepStatus",
    "StepLog",
    "TransactionStep",
    "SagaOrchestrator",
    # Rebalance Saga
    "RebalanceSaga",
    # Tax Loss Harvesting Saga
    "TaxLossHarvestingSaga",
    "TaxLot",
    "is_substantially_identical",
    "get_replacement_suggestions",
    "FUND_FAMILY_MAPPING",
]

