"""
Audit Module - Auditability System Foundation

Implements the enterprise-grade auditability infrastructure:
1. Know Your Agent (KYA) Framework - Agent identity, scope, and authority
2. Deterministic Validation Gates - Pre-execution compliance checks
3. Agentic Audit Log - Immutable trail capturing "Why", "What", "Who"
4. System of Record Linkage - Traceability to source systems
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict, Optional, Any
from datetime import datetime
import uuid
import hashlib
import json


# =============================================================================
# 1. KNOW YOUR AGENT (KYA) FRAMEWORK
# =============================================================================

class AgentAuthority(Enum):
    """Scope of authority for agents (RBAC).
    
    Defines what actions an agent is permitted to take, following
    the principle of "least privilege" from the KYA framework.
    """
    READ_ONLY = "read_only"           # Query data, no mutations
    TRADE_SMALL = "trade_small"       # Trades up to $10k
    TRADE_MEDIUM = "trade_medium"     # Trades up to $100k  
    TRADE_LARGE = "trade_large"       # Unlimited (requires HITL approval)
    ADMIN = "admin"                   # Full system access


@dataclass
class AgentIdentity:
    """Decentralized Identifier (DID) for agent traceability.
    
    Every AI agent is assigned a unique, cryptographically verifiable
    identifier ensuring every action is attributable to a specific agent.
    """
    agent_id: str              # Unique DID (e.g., "agent:tlh:v1.2.3")
    agent_type: str            # "TLH_AGENT", "REBALANCE_AGENT", etc.
    version: str               # Semantic version of agent code
    authority: AgentAuthority  # Scope of what agent can do
    created_at: datetime = field(default_factory=datetime.now)
    owner: str = ""            # Human supervisor responsible
    description: str = ""      # What this agent does
    
    @classmethod
    def create(
        cls, 
        agent_type: str, 
        version: str,
        authority: AgentAuthority,
        owner: str = "",
        description: str = ""
    ) -> "AgentIdentity":
        """Factory method to create a new agent with generated DID."""
        agent_id = f"agent:{agent_type.lower()}:{version}:{uuid.uuid4().hex[:8]}"
        return cls(
            agent_id=agent_id,
            agent_type=agent_type,
            version=version,
            authority=authority,
            owner=owner,
            description=description,
        )
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "version": self.version,
            "authority": self.authority.value,
            "created_at": self.created_at.isoformat(),
            "owner": self.owner,
            "description": self.description,
        }


class AgentRegistry:
    """Central registry of all agents (System of Record for agents).
    
    Provides agent lifecycle management and authority validation.
    """
    
    def __init__(self):
        self._agents: dict[str, AgentIdentity] = {}
        
    def register_agent(self, identity: AgentIdentity) -> str:
        """Register a new agent and return its ID."""
        self._agents[identity.agent_id] = identity
        return identity.agent_id
    
    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Retrieve agent by ID."""
        return self._agents.get(agent_id)
    
    def validate_authority(
        self, 
        agent_id: str, 
        required_authority: AgentAuthority
    ) -> bool:
        """Check if agent has sufficient authority for an action."""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        
        # Authority hierarchy: ADMIN > TRADE_LARGE > TRADE_MEDIUM > TRADE_SMALL > READ_ONLY
        authority_levels = {
            AgentAuthority.READ_ONLY: 0,
            AgentAuthority.TRADE_SMALL: 1,
            AgentAuthority.TRADE_MEDIUM: 2,
            AgentAuthority.TRADE_LARGE: 3,
            AgentAuthority.ADMIN: 4,
        }
        return authority_levels[agent.authority] >= authority_levels[required_authority]
    
    def list_agents(
        self, 
        authority: Optional[AgentAuthority] = None
    ) -> list[AgentIdentity]:
        """List all agents, optionally filtered by authority level."""
        agents = list(self._agents.values())
        if authority:
            agents = [a for a in agents if a.authority == authority]
        return agents


# =============================================================================
# 2. DETERMINISTIC VALIDATION GATES
# =============================================================================

class ValidationType(Enum):
    """Types of validation gates."""
    COMPLIANCE = "compliance"     # Regulatory rules (Reg BI, wash sale, etc.)
    AUTHORITY = "authority"       # Agent permission check
    LIMIT = "limit"              # Trade/value limits
    CONSTRAINT = "constraint"    # Portfolio constraints (min cash, etc.)


@dataclass
class ValidationGate:
    """Pre-execution compliance check (the "Math Ban" enforced).
    
    Represents a deterministic rule that must pass before action execution.
    """
    gate_id: str
    gate_type: ValidationType
    rule_name: str               # Human-readable rule name
    rule_expression: str         # Deterministic rule (e.g., "cash >= 0.02")
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "rule_name": self.rule_name,
            "rule_expression": self.rule_expression,
            "description": self.description,
        }


@dataclass  
class ValidationResult:
    """Result of a validation gate check."""
    gate_id: str
    gate_type: ValidationType
    passed: bool
    rule_evaluated: str          # The exact rule that was checked
    input_values: dict           # Values used in evaluation
    reason: str                  # Why it passed/failed
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "passed": self.passed,
            "rule_evaluated": self.rule_evaluated,
            "input_values": self.input_values,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class DeterministicValidator:
    """Enforces deterministic rules before any action.
    
    This is the "nervous system" that ensures all AI actions pass
    through verifiable, logic-gated checks before execution.
    """
    
    # Pre-defined compliance gates
    GATES = {
        "CASH_MINIMUM": ValidationGate(
            gate_id="gate_cash_min",
            gate_type=ValidationType.CONSTRAINT,
            rule_name="Minimum Cash Constraint",
            rule_expression="cash_percent >= 0.02",
            description="Portfolio must maintain at least 2% cash"
        ),
        "WASH_SALE": ValidationGate(
            gate_id="gate_wash_sale",
            gate_type=ValidationType.COMPLIANCE,
            rule_name="Wash Sale Rule",
            rule_expression="days_since_sale >= 30 OR NOT substantially_identical",
            description="IRS wash sale rule: no repurchase within 30 days"
        ),
        "TRADE_LIMIT_SMALL": ValidationGate(
            gate_id="gate_trade_small",
            gate_type=ValidationType.LIMIT,
            rule_name="Small Trade Limit",
            rule_expression="trade_value <= 10000",
            description="Trade must be under $10,000 for TRADE_SMALL authority"
        ),
        "TRADE_LIMIT_MEDIUM": ValidationGate(
            gate_id="gate_trade_medium",
            gate_type=ValidationType.LIMIT,
            rule_name="Medium Trade Limit",
            rule_expression="trade_value <= 100000",
            description="Trade must be under $100,000 for TRADE_MEDIUM authority"
        ),
    }
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self.custom_gates: list[ValidationGate] = []
        
    def add_gate(self, gate: ValidationGate):
        """Add a custom validation gate."""
        self.custom_gates.append(gate)
    
    def validate_trade(
        self, 
        trade_value: float, 
        portfolio: dict,
        agent_id: str
    ) -> list[ValidationResult]:
        """Validate a trade against all applicable gates."""
        results = []
        
        # Check cash minimum constraint
        cash_percent = portfolio.get("cash_percent", 0)
        results.append(ValidationResult(
            gate_id="gate_cash_min",
            gate_type=ValidationType.CONSTRAINT,
            passed=cash_percent >= 0.02,
            rule_evaluated="cash_percent >= 0.02",
            input_values={"cash_percent": cash_percent},
            reason="Cash constraint satisfied" if cash_percent >= 0.02 
                   else f"Cash {cash_percent:.1%} below 2% minimum"
        ))
        
        # Check trade limits based on agent authority
        agent = self.agent_registry.get_agent(agent_id)
        if agent:
            if agent.authority == AgentAuthority.TRADE_SMALL:
                results.append(ValidationResult(
                    gate_id="gate_trade_small",
                    gate_type=ValidationType.LIMIT,
                    passed=trade_value <= 10000,
                    rule_evaluated="trade_value <= 10000",
                    input_values={"trade_value": trade_value, "limit": 10000},
                    reason="Within small trade limit" if trade_value <= 10000
                           else f"Trade ${trade_value:,.2f} exceeds $10,000 limit"
                ))
            elif agent.authority == AgentAuthority.TRADE_MEDIUM:
                results.append(ValidationResult(
                    gate_id="gate_trade_medium",
                    gate_type=ValidationType.LIMIT,
                    passed=trade_value <= 100000,
                    rule_evaluated="trade_value <= 100000",
                    input_values={"trade_value": trade_value, "limit": 100000},
                    reason="Within medium trade limit" if trade_value <= 100000
                           else f"Trade ${trade_value:,.2f} exceeds $100,000 limit"
                ))
        
        return results
    
    def validate_authority(
        self, 
        agent_id: str, 
        required_authority: AgentAuthority
    ) -> ValidationResult:
        """Validate that an agent has required authority."""
        has_authority = self.agent_registry.validate_authority(
            agent_id, required_authority
        )
        agent = self.agent_registry.get_agent(agent_id)
        
        return ValidationResult(
            gate_id="gate_authority",
            gate_type=ValidationType.AUTHORITY,
            passed=has_authority,
            rule_evaluated=f"agent.authority >= {required_authority.value}",
            input_values={
                "agent_id": agent_id,
                "agent_authority": agent.authority.value if agent else "unknown",
                "required_authority": required_authority.value,
            },
            reason="Authority validated" if has_authority 
                   else f"Insufficient authority: requires {required_authority.value}"
        )
    
    def validate_all(
        self,
        trade_value: float,
        portfolio: dict,
        agent_id: str,
        required_authority: AgentAuthority
    ) -> tuple[bool, list[ValidationResult]]:
        """Run all validations and return overall pass/fail with results."""
        results = []
        
        # Authority check
        results.append(self.validate_authority(agent_id, required_authority))
        
        # Trade validations
        results.extend(self.validate_trade(trade_value, portfolio, agent_id))
        
        all_passed = all(r.passed for r in results)
        return all_passed, results


# =============================================================================
# 3. AGENTIC AUDIT LOG (The "Why", "What", "Who")
# =============================================================================

class AuditEventType(Enum):
    """Types of auditable events."""
    SAGA_STARTED = "saga_started"
    SAGA_COMPLETED = "saga_completed"
    STEP_EXECUTED = "step_executed"
    STEP_FAILED = "step_failed"
    COMPLIANCE_CHECK = "compliance_check"
    DECISION_MADE = "decision_made"
    ERROR_OCCURRED = "error_occurred"
    VALIDATION_GATE_PASSED = "validation_gate_passed"
    VALIDATION_GATE_FAILED = "validation_gate_failed"
    AUTHORITY_CHECK = "authority_check"
    HITL_ESCALATION = "hitl_escalation"
    ROLLBACK_INITIATED = "rollback_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"


@dataclass
class AuditEvent:
    """Immutable audit event capturing the "Why", "What", and "Who".
    
    This is the forensic-grade record required by the SEC/FCA
    Explainability Mandate for every AI-driven action.
    """
    # Core identifiers
    event_id: str
    timestamp: datetime
    
    # THE "WHO" - Agent identity
    agent_id: str
    agent_authority: AgentAuthority
    human_supervisor: str
    
    # THE "WHAT" - Action taken
    event_type: AuditEventType
    saga_transaction_id: str
    step_name: Optional[str]
    action_taken: str
    
    # THE "WHY" - Reasoning trace
    reasoning_trace: str
    decision_factors: list[str]
    
    # State tracking
    input_state: dict
    output_state: dict
    
    # Validation records
    validation_results: list[dict]
    
    # System of Record linkage
    source_system_ids: dict
    metadata: dict
    
    @classmethod
    def create(
        cls,
        agent_id: str,
        agent_authority: AgentAuthority,
        human_supervisor: str,
        event_type: AuditEventType,
        saga_transaction_id: str,
        action_taken: str,
        reasoning_trace: str,
        step_name: Optional[str] = None,
        decision_factors: Optional[list[str]] = None,
        input_state: Optional[dict] = None,
        output_state: Optional[dict] = None,
        validation_results: Optional[list[ValidationResult]] = None,
        source_system_ids: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> "AuditEvent":
        """Factory method to create a new audit event."""
        return cls(
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            timestamp=datetime.now(),
            agent_id=agent_id,
            agent_authority=agent_authority,
            human_supervisor=human_supervisor,
            event_type=event_type,
            saga_transaction_id=saga_transaction_id,
            step_name=step_name,
            action_taken=action_taken,
            reasoning_trace=reasoning_trace,
            decision_factors=decision_factors or [],
            input_state=input_state or {},
            output_state=output_state or {},
            validation_results=[v.to_dict() for v in (validation_results or [])],
            source_system_ids=source_system_ids or {},
            metadata=metadata or {},
        )
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "agent_authority": self.agent_authority.value,
            "human_supervisor": self.human_supervisor,
            "event_type": self.event_type.value,
            "saga_transaction_id": self.saga_transaction_id,
            "step_name": self.step_name,
            "action_taken": self.action_taken,
            "reasoning_trace": self.reasoning_trace,
            "decision_factors": self.decision_factors,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "validation_results": self.validation_results,
            "source_system_ids": self.source_system_ids,
            "metadata": self.metadata,
        }


# =============================================================================
# 4. SYSTEM OF RECORD (Explainability Mandate)
# =============================================================================

@dataclass
class SystemOfRecordLink:
    """Links audit events to source systems for full traceability.
    
    This ensures every AI action is traceable to its origin data,
    satisfying the SEC's "System of Record" requirement.
    """
    link_id: str
    audit_event_id: str
    source_system: str        # "CUSTODIAN", "PORTFOLIO_DB", "TAX_ENGINE"
    record_id: str            # ID in source system
    record_type: str          # "TRADE", "POSITION", "TAX_LOT"
    snapshot_hash: str        # Hash of record state at time of action
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls,
        audit_event_id: str,
        source_system: str,
        record_id: str,
        record_type: str,
        record_data: Any
    ) -> "SystemOfRecordLink":
        """Create a link with computed snapshot hash."""
        snapshot = json.dumps(record_data, sort_keys=True, default=str)
        snapshot_hash = hashlib.sha256(snapshot.encode()).hexdigest()[:32]
        return cls(
            link_id=f"link_{uuid.uuid4().hex[:12]}",
            audit_event_id=audit_event_id,
            source_system=source_system,
            record_id=record_id,
            record_type=record_type,
            snapshot_hash=snapshot_hash,
        )
    
    def to_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "audit_event_id": self.audit_event_id,
            "source_system": self.source_system,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "snapshot_hash": self.snapshot_hash,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditReport:
    """Compliance report for regulators."""
    report_id: str
    generated_at: datetime
    start_date: datetime
    end_date: datetime
    total_events: int
    events_by_type: dict
    events_by_agent: dict
    validation_summary: dict
    events: list[dict]
    
    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "events_by_agent": self.events_by_agent,
            "validation_summary": self.validation_summary,
            "events": self.events,
        }


class AuditStore:
    """Append-only immutable store for audit events.
    
    This is the "black box recorder" of the AI system, essential
    for satisfying regulatory inquiries and internal audits.
    """
    
    def __init__(self):
        self._events: list[AuditEvent] = []
        self._source_links: list[SystemOfRecordLink] = []
        self._events_by_transaction: dict[str, list[AuditEvent]] = {}
    
    def log_event(self, event: AuditEvent) -> str:
        """Log an audit event (append-only, immutable)."""
        self._events.append(event)
        
        # Index by transaction ID
        if event.saga_transaction_id not in self._events_by_transaction:
            self._events_by_transaction[event.saga_transaction_id] = []
        self._events_by_transaction[event.saga_transaction_id].append(event)
        
        return event.event_id
    
    def get_transaction_trace(
        self, 
        transaction_id: str
    ) -> list[AuditEvent]:
        """Get full event trace for a transaction."""
        return self._events_by_transaction.get(transaction_id, [])
    
    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        agent_id: Optional[str] = None,
    ) -> list[AuditEvent]:
        """Query events with filters."""
        events = self._events
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
            
        return events
    
    def get_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> AuditReport:
        """Generate compliance report for date range."""
        events = self.get_events(start_date=start_date, end_date=end_date)
        
        # Aggregate by type
        events_by_type: dict[str, int] = {}
        for e in events:
            t = e.event_type.value
            events_by_type[t] = events_by_type.get(t, 0) + 1
        
        # Aggregate by agent
        events_by_agent: dict[str, int] = {}
        for e in events:
            events_by_agent[e.agent_id] = events_by_agent.get(e.agent_id, 0) + 1
        
        # Validation summary
        passed = sum(1 for e in events 
                    if e.event_type == AuditEventType.VALIDATION_GATE_PASSED)
        failed = sum(1 for e in events 
                    if e.event_type == AuditEventType.VALIDATION_GATE_FAILED)
        
        return AuditReport(
            report_id=f"rpt_{uuid.uuid4().hex[:12]}",
            generated_at=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            total_events=len(events),
            events_by_type=events_by_type,
            events_by_agent=events_by_agent,
            validation_summary={"passed": passed, "failed": failed},
            events=[e.to_dict() for e in events],
        )
    
    def link_to_source(
        self, 
        event_id: str, 
        links: list[SystemOfRecordLink]
    ):
        """Link an audit event to source system records."""
        for link in links:
            self._source_links.append(link)
    
    def trace_to_source(
        self, 
        event_id: str
    ) -> list[SystemOfRecordLink]:
        """Get all source system links for an event."""
        return [l for l in self._source_links if l.audit_event_id == event_id]
    
    def export_for_regulators(
        self, 
        transaction_id: str, 
        format: str = "json"
    ) -> str:
        """Export transaction trace for regulatory submission."""
        events = self.get_transaction_trace(transaction_id)
        
        if format == "json":
            return json.dumps([e.to_dict() for e in events], indent=2)
        elif format == "csv":
            if not events:
                return "No events found"
            headers = list(events[0].to_dict().keys())
            lines = [",".join(headers)]
            for e in events:
                d = e.to_dict()
                row = [str(d.get(h, "")).replace(",", ";") for h in headers]
                lines.append(",".join(row))
            return "\n".join(lines)
        else:
            return json.dumps([e.to_dict() for e in events])


# =============================================================================
# Pre-configured Agents (Demo)
# =============================================================================

# Global agent registry instance
_global_registry = AgentRegistry()

# Pre-register standard agents
TLH_AGENT = AgentIdentity.create(
    agent_type="TLH_AGENT",
    version="1.0.0",
    authority=AgentAuthority.TRADE_MEDIUM,
    owner="System",
    description="Tax Loss Harvesting Agent"
)

REBALANCE_AGENT = AgentIdentity.create(
    agent_type="REBALANCE_AGENT", 
    version="1.0.0",
    authority=AgentAuthority.TRADE_MEDIUM,
    owner="System",
    description="Portfolio Rebalancing Agent"
)

ANALYSIS_AGENT = AgentIdentity.create(
    agent_type="ANALYSIS_AGENT",
    version="1.0.0", 
    authority=AgentAuthority.READ_ONLY,
    owner="System",
    description="Read-only Analysis Agent"
)

# Register all agents
_global_registry.register_agent(TLH_AGENT)
_global_registry.register_agent(REBALANCE_AGENT)
_global_registry.register_agent(ANALYSIS_AGENT)


def get_global_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return _global_registry


# Global audit store instance
_global_audit_store = AuditStore()


def get_global_audit_store() -> AuditStore:
    """Get the global audit store instance."""
    return _global_audit_store
