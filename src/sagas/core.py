"""
Saga Core Module - Transactional Saga Pattern Engine

Implements the core Saga pattern components:
- TransactionStep: Abstract base class for saga steps
- SagaOrchestrator: Manages step execution and rollback
- Idempotency: Prevents duplicate transaction execution
- Pivot Transaction: Marks point-of-no-return steps
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict, Optional, Callable, TYPE_CHECKING
from datetime import datetime
import uuid
import hashlib

if TYPE_CHECKING:
    from src.audit import AuditStore, AgentIdentity


class SagaStatus(Enum):
    """Status of a saga execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class StepStatus(Enum):
    """Status of an individual step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


@dataclass
class StepLog:
    """Log entry for a single step execution.
    
    Enhanced with audit metadata for SEC/FCA Explainability Mandate compliance.
    """
    step_name: str
    status: StepStatus
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    error: Optional[str] = None
    # Audit enhancements
    reasoning_trace: str = ""  # Chain of thought explaining WHY
    validation_results: list = field(default_factory=list)  # Gate check results
    is_pivot: bool = False  # Marks point-of-no-return
    
    def to_dict(self) -> dict:
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "error": self.error,
            "reasoning_trace": self.reasoning_trace,
            "validation_results": self.validation_results,
            "is_pivot": self.is_pivot,
        }


class SagaContext(TypedDict, total=False):
    """
    Shared context passed through all saga steps.
    
    Attributes:
        transaction_id: Unique identifier for idempotency
        portfolio_data: Current portfolio state
        proposed_trades: List of trades to execute
        executed_steps: Names of successfully executed steps
        logs: List of StepLog entries
        error: Error message if saga failed
    """
    transaction_id: str
    portfolio_data: dict
    proposed_trades: list
    executed_steps: list[str]
    logs: list[dict]
    error: Optional[str]


@dataclass
class SagaResult:
    """Result of a saga execution."""
    status: SagaStatus
    transaction_id: str
    logs: list[StepLog]
    context: SagaContext
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "transaction_id": self.transaction_id,
            "logs": [log.to_dict() for log in self.logs],
            "error": self.error,
        }


class TransactionStep(ABC):
    """
    Abstract base class for saga transaction steps.
    
    Each step must implement:
    - execute(): Perform the forward action
    - compensate(): Undo the action (the "Ctrl+Z")
    
    Attributes:
        name: Unique identifier for the step
        is_pivot: If True, this is a point-of-no-return (no compensation after)
    """
    
    def __init__(self, name: str, is_pivot: bool = False):
        self.name = name
        self.is_pivot = is_pivot
    
    @abstractmethod
    def execute(self, ctx: SagaContext) -> SagaContext:
        """
        Execute the forward transaction.
        
        Args:
            ctx: Current saga context
            
        Returns:
            Updated context after execution
            
        Raises:
            Exception: If the step fails
        """
        pass
    
    @abstractmethod
    def compensate(self, ctx: SagaContext) -> SagaContext:
        """
        Execute the compensating transaction (rollback).
        
        Args:
            ctx: Current saga context
            
        Returns:
            Updated context after compensation
        """
        pass
    
    def __repr__(self) -> str:
        pivot_marker = " [PIVOT]" if self.is_pivot else ""
        return f"<Step: {self.name}{pivot_marker}>"


class SagaOrchestrator:
    """
    Orchestrates saga execution with rollback support.
    
    Features:
    - Sequential step execution
    - Automatic rollback on failure
    - Idempotency checking
    - Pivot transaction support (point-of-no-return)
    - Step-by-step logging
    """
    
    def __init__(
        self, 
        steps: list[TransactionStep],
        on_step_start: Optional[Callable[[str, int, int], None]] = None,
        on_step_complete: Optional[Callable[[str, StepStatus], None]] = None,
        agent_id: Optional[str] = None,
        audit_store: Optional["AuditStore"] = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            steps: Ordered list of transaction steps
            on_step_start: Callback(step_name, current_index, total) called before each step
            on_step_complete: Callback(step_name, status) called after each step
            agent_id: DID of the executing agent (for audit trail)
            audit_store: AuditStore instance for logging events
        """
        self.steps = steps
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.agent_id = agent_id
        self.audit_store = audit_store
        
        # Idempotency store: {transaction_id: SagaStatus}
        self._idempotency_store: dict[str, SagaStatus] = {}
    
    def generate_transaction_id(self, ctx: SagaContext) -> str:
        """
        Generate a deterministic transaction ID based on context.
        
        This ensures the same input always produces the same ID,
        enabling idempotency checks.
        """
        # Create hash from portfolio + trades
        content = str(ctx.get("portfolio_data", {})) + str(ctx.get("proposed_trades", []))
        hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"saga_{hash_digest}"
    
    def is_duplicate(self, transaction_id: str) -> bool:
        """Check if this transaction has already been processed."""
        return transaction_id in self._idempotency_store
    
    def get_status(self, transaction_id: str) -> Optional[SagaStatus]:
        """Get the status of a previous transaction."""
        return self._idempotency_store.get(transaction_id)
    
    def run(self, ctx: SagaContext) -> SagaResult:
        """
        Execute the saga with all steps.
        
        Args:
            ctx: Initial saga context
            
        Returns:
            SagaResult with status, logs, and final context
        """
        logs: list[StepLog] = []
        
        # Generate or use existing transaction ID
        if "transaction_id" not in ctx or not ctx["transaction_id"]:
            ctx["transaction_id"] = self.generate_transaction_id(ctx)
        
        transaction_id = ctx["transaction_id"]
        
        # Idempotency check
        if self.is_duplicate(transaction_id):
            existing_status = self.get_status(transaction_id)
            logs.append(StepLog(
                step_name="IDEMPOTENCY_CHECK",
                status=StepStatus.SKIPPED,
                message=f"Transaction {transaction_id} already processed with status: {existing_status.value}"
            ))
            return SagaResult(
                status=existing_status,
                transaction_id=transaction_id,
                logs=logs,
                context=ctx,
                error=f"Duplicate transaction. Previous status: {existing_status.value}"
            )
        
        # Initialize tracking
        ctx["executed_steps"] = []
        ctx["logs"] = []
        
        # Mark as executing
        self._idempotency_store[transaction_id] = SagaStatus.EXECUTING
        
        # Execute steps sequentially
        failed_at_index: Optional[int] = None
        
        for i, step in enumerate(self.steps):
            # Callback: step starting
            if self.on_step_start:
                self.on_step_start(step.name, i + 1, len(self.steps))
            
            logs.append(StepLog(
                step_name=step.name,
                status=StepStatus.RUNNING,
                message=f"Executing step {i + 1}/{len(self.steps)}"
            ))
            
            try:
                ctx = step.execute(ctx)
                ctx["executed_steps"].append(step.name)
                
                # Update log to success
                logs[-1] = StepLog(
                    step_name=step.name,
                    status=StepStatus.SUCCESS,
                    message=f"Step completed successfully"
                )
                
                # Callback: step completed
                if self.on_step_complete:
                    self.on_step_complete(step.name, StepStatus.SUCCESS)
                    
            except Exception as e:
                # Step failed
                logs[-1] = StepLog(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    message=f"Step failed",
                    error=str(e)
                )
                
                if self.on_step_complete:
                    self.on_step_complete(step.name, StepStatus.FAILED)
                
                failed_at_index = i
                ctx["error"] = str(e)
                break
        
        # If all steps succeeded
        if failed_at_index is None:
            self._idempotency_store[transaction_id] = SagaStatus.SUCCESS
            return SagaResult(
                status=SagaStatus.SUCCESS,
                transaction_id=transaction_id,
                logs=logs,
                context=ctx,
            )
        
        # Rollback needed
        ctx, rollback_logs = self._rollback(failed_at_index, ctx)
        logs.extend(rollback_logs)
        
        final_status = SagaStatus.ROLLED_BACK
        self._idempotency_store[transaction_id] = final_status
        
        return SagaResult(
            status=final_status,
            transaction_id=transaction_id,
            logs=logs,
            context=ctx,
            error=ctx.get("error"),
        )
    
    def _rollback(
        self, 
        failed_index: int, 
        ctx: SagaContext
    ) -> tuple[SagaContext, list[StepLog]]:
        """
        Execute compensation for all completed steps in reverse order.
        
        Stops at pivot transactions (point-of-no-return).
        
        Args:
            failed_index: Index of the step that failed
            ctx: Current saga context
            
        Returns:
            Tuple of (updated context, rollback logs)
        """
        logs: list[StepLog] = []
        
        logs.append(StepLog(
            step_name="ROLLBACK_START",
            status=StepStatus.COMPENSATING,
            message=f"Starting rollback from step {failed_index}"
        ))
        
        # Compensate in reverse order (up to but not including failed step)
        for i in range(failed_index - 1, -1, -1):
            step = self.steps[i]
            
            # Stop at pivot transaction
            if step.is_pivot:
                logs.append(StepLog(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    message="PIVOT TRANSACTION - Cannot compensate past this point"
                ))
                break
            
            logs.append(StepLog(
                step_name=step.name,
                status=StepStatus.COMPENSATING,
                message=f"Compensating step"
            ))
            
            try:
                ctx = step.compensate(ctx)
                logs[-1] = StepLog(
                    step_name=step.name,
                    status=StepStatus.COMPENSATED,
                    message="Compensation successful"
                )
                
                if self.on_step_complete:
                    self.on_step_complete(step.name, StepStatus.COMPENSATED)
                    
            except Exception as e:
                logs[-1] = StepLog(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    message="Compensation failed",
                    error=str(e)
                )
        
        logs.append(StepLog(
            step_name="ROLLBACK_COMPLETE",
            status=StepStatus.COMPENSATED,
            message="Rollback completed"
        ))
        
        return ctx, logs
