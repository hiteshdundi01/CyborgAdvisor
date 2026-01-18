"""
Tests for Saga Core Module

Tests the SagaOrchestrator with:
- Forward success (all steps pass)
- Mid-stream failure and rollback
- Idempotency (duplicate prevention)
- Pivot transaction (no rollback past pivot)
"""

import pytest
from src.sagas.core import (
    TransactionStep,
    SagaOrchestrator,
    SagaContext,
    SagaResult,
    SagaStatus,
    StepStatus,
)


class MockSuccessStep(TransactionStep):
    """A step that always succeeds."""
    
    def __init__(self, name: str, is_pivot: bool = False):
        super().__init__(name, is_pivot)
        self.executed = False
        self.compensated = False
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        self.executed = True
        ctx.setdefault("execution_order", []).append(self.name)
        return ctx
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        self.compensated = True
        ctx.setdefault("compensation_order", []).append(self.name)
        return ctx


class MockFailingStep(TransactionStep):
    """A step that always fails."""
    
    def __init__(self, name: str, error_message: str = "Step failed"):
        super().__init__(name, is_pivot=False)
        self.error_message = error_message
        self.executed = False
        self.compensated = False
    
    def execute(self, ctx: SagaContext) -> SagaContext:
        self.executed = True
        raise Exception(self.error_message)
    
    def compensate(self, ctx: SagaContext) -> SagaContext:
        self.compensated = True
        ctx.setdefault("compensation_order", []).append(self.name)
        return ctx


class TestSagaForwardSuccess:
    """Test that saga executes all steps successfully."""
    
    def test_all_steps_succeed(self):
        step1 = MockSuccessStep("Step1")
        step2 = MockSuccessStep("Step2")
        step3 = MockSuccessStep("Step3")
        
        orchestrator = SagaOrchestrator(steps=[step1, step2, step3])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        result = orchestrator.run(ctx)
        
        assert result.status == SagaStatus.SUCCESS
        assert step1.executed
        assert step2.executed
        assert step3.executed
        assert not step1.compensated
        assert not step2.compensated
        assert not step3.compensated
        assert result.context["execution_order"] == ["Step1", "Step2", "Step3"]
    
    def test_transaction_id_generated(self):
        step1 = MockSuccessStep("Step1")
        orchestrator = SagaOrchestrator(steps=[step1])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {"test": "data"},
            "proposed_trades": [{"action": "BUY"}],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        result = orchestrator.run(ctx)
        
        assert result.transaction_id.startswith("saga_")
        assert len(result.transaction_id) == 21  # "saga_" + 16 hex chars


class TestSagaRollback:
    """Test that saga rolls back on failure."""
    
    def test_rollback_on_mid_stream_failure(self):
        step1 = MockSuccessStep("Step1")
        step2 = MockSuccessStep("Step2")
        step3 = MockFailingStep("Step3", "Insufficient funds")
        step4 = MockSuccessStep("Step4")
        
        orchestrator = SagaOrchestrator(steps=[step1, step2, step3, step4])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        result = orchestrator.run(ctx)
        
        assert result.status == SagaStatus.ROLLED_BACK
        assert result.error == "Insufficient funds"
        
        # Steps 1 and 2 executed, step 3 tried but failed, step 4 never reached
        assert step1.executed
        assert step2.executed
        assert step3.executed
        assert not step4.executed
        
        # Compensation in reverse order (step2 then step1, not step3)
        assert step1.compensated
        assert step2.compensated
        assert not step3.compensated
        assert not step4.compensated
        
        assert result.context["compensation_order"] == ["Step2", "Step1"]
    
    def test_first_step_failure_no_compensation(self):
        step1 = MockFailingStep("Step1", "Connection failed")
        step2 = MockSuccessStep("Step2")
        
        orchestrator = SagaOrchestrator(steps=[step1, step2])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        result = orchestrator.run(ctx)
        
        assert result.status == SagaStatus.ROLLED_BACK
        assert step1.executed
        assert not step2.executed
        # Nothing to compensate - first step failed
        assert not step1.compensated


class TestSagaIdempotency:
    """Test that duplicate transactions are prevented."""
    
    def test_duplicate_transaction_skipped(self):
        step1 = MockSuccessStep("Step1")
        
        orchestrator = SagaOrchestrator(steps=[step1])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {"same": "data"},
            "proposed_trades": [{"action": "SELL"}],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        # First execution
        result1 = orchestrator.run(ctx)
        assert result1.status == SagaStatus.SUCCESS
        
        # Reset step state for second attempt
        step1.executed = False
        
        # Second execution with same context
        result2 = orchestrator.run(ctx)
        
        # Should be skipped due to idempotency
        assert result2.status == SagaStatus.SUCCESS  # Returns previous status
        assert "Duplicate transaction" in result2.error
        assert not step1.executed  # Step was not re-executed


class TestSagaPivotTransaction:
    """Test that pivot transactions stop rollback."""
    
    def test_pivot_stops_rollback(self):
        step1 = MockSuccessStep("Step1")
        step2 = MockSuccessStep("Step2", is_pivot=True)  # PIVOT
        step3 = MockSuccessStep("Step3")
        step4 = MockFailingStep("Step4", "External failure")
        
        orchestrator = SagaOrchestrator(steps=[step1, step2, step3, step4])
        ctx: SagaContext = {
            "transaction_id": "",
            "portfolio_data": {},
            "proposed_trades": [],
            "executed_steps": [],
            "logs": [],
            "error": None,
        }
        
        result = orchestrator.run(ctx)
        
        assert result.status == SagaStatus.ROLLED_BACK
        
        # All executed before failure
        assert step1.executed
        assert step2.executed
        assert step3.executed
        assert step4.executed
        
        # Compensation: step3 compensated, but stops at pivot (step2)
        assert step3.compensated
        assert not step2.compensated  # PIVOT - no compensation
        assert not step1.compensated  # Before pivot - not reached
        
        # Check logs mention the pivot
        pivot_log = [l for l in result.logs if l.step_name == "Step2" and "PIVOT" in l.message]
        assert len(pivot_log) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
