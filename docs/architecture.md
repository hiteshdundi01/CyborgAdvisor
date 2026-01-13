# Cyborg Advisor Architecture

## Detailed Technical Documentation

This document provides in-depth architectural diagrams and explanations for the Neurosymbolic Rebalancer.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph External["🌐 External"]
        USER[👤 User]
        GEMINI[🤖 Google Gemini API]
    end
    
    subgraph CyborgAdvisor["🧠 Cyborg Advisor"]
        subgraph LangGraph["LangGraph State Machine"]
            ENTRY[Entry Point]
            IP[Intent Parser]
            FC[Financial Calculator]
            CC[Compliance Check]
            HR[Human Review]
            ET[Execute Trades]
            CT[Cancel Trades]
            RG[Response Generator]
        end
        
        subgraph Core["Core Modules"]
            STATE[AgentState]
            CONFIG[Model Config]
        end
    end
    
    USER -->|message| ENTRY
    IP <-->|LLM calls| GEMINI
    RG <-->|LLM calls| GEMINI
    ENTRY --> IP
    IP --> FC
    FC --> CC
    CC --> HR
    HR --> ET
    HR --> CT
    
    STATE -.->|flows through| LangGraph
    CONFIG -.->|configures| IP
    CONFIG -.->|configures| RG
    
    style CyborgAdvisor fill:#f5f5f5,stroke:#333
    style LangGraph fill:#e8f5e9,stroke:#4caf50
    style Core fill:#fff3e0,stroke:#ff9800
```

---

## 2. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input
        A[User Message]
        B[Portfolio Data]
        C[Target Allocation]
    end
    
    subgraph Processing
        D{Intent<br/>Parser}
        E[Trades<br/>Calculation]
        F{Compliance<br/>Check}
        G{Human<br/>Approval}
    end
    
    subgraph Output
        H[Trade<br/>Execution]
        I[Response<br/>Message]
    end
    
    A --> D
    B --> E
    C --> E
    
    D -->|rebalance| E
    D -->|query| I
    
    E --> F
    F -->|pass| G
    F -->|fail| I
    
    G -->|yes| H
    G -->|no| I
    
    H --> I
    
    style D fill:#e8f5e9
    style E fill:#fff3e0
    style F fill:#fff3e0
    style G fill:#e3f2fd
```

---

## 3. State Transformations

Each node reads and writes specific state fields:

```mermaid
graph TD
    subgraph InitialState["Initial State"]
        S1[user_input: str]
        S2[portfolio_data: dict]
        S3[target_allocation: dict]
    end
    
    subgraph AfterIntentParser["After Intent Parser"]
        IP1[intent: rebalance/query/respond]
        IP2[messages: updated]
    end
    
    subgraph AfterCalculator["After Financial Calculator"]
        FC1[proposed_trades: list]
    end
    
    subgraph AfterCompliance["After Compliance Check"]
        CC1[compliance_status: bool]
        CC2[compliance_errors: list]
    end
    
    subgraph AfterHumanReview["After Human Review"]
        HR1[human_approval: bool]
    end
    
    subgraph FinalState["Final State"]
        FS1[response: str]
        FS2[messages: complete history]
    end
    
    InitialState --> AfterIntentParser
    AfterIntentParser --> AfterCalculator
    AfterCalculator --> AfterCompliance
    AfterCompliance --> AfterHumanReview
    AfterHumanReview --> FinalState
```

---

## 4. Component Responsibilities

### Node Responsibility Matrix

| Node | Input | Processing | Output | Uses LLM? |
|------|-------|------------|--------|-----------|
| **Intent Parser** | user_input | Classify intent, extract parameters | intent, target_allocation | ✅ Yes |
| **Financial Calculator** | portfolio_data, target_allocation | Calculate buy/sell orders | proposed_trades | ❌ No |
| **Compliance Check** | proposed_trades, portfolio_data | Apply rules | compliance_status, errors | ❌ No |
| **Human Review** | proposed_trades | Present for approval | human_approval | ❌ No |
| **Execute Trades** | proposed_trades | Mock execution | response | ❌ No |
| **Response Generator** | state context | Generate message | response | ✅ Yes |

---

## 5. Sequence Diagrams

### Rebalance Flow (Happy Path)

```mermaid
sequenceDiagram
    participant U as User
    participant IP as Intent Parser
    participant LLM as Gemini LLM
    participant FC as Financial Calculator
    participant CC as Compliance Check
    participant HR as Human Review
    participant ET as Execute Trades
    
    U->>IP: "Please rebalance my portfolio"
    IP->>LLM: Classify intent
    LLM-->>IP: {intent: "rebalance"}
    
    IP->>FC: State with intent=rebalance
    Note over FC: Pure Python/Pandas<br/>NO LLM CALLS
    FC->>FC: Calculate trades
    
    FC->>CC: State with proposed_trades
    Note over CC: Deterministic rules<br/>NO LLM CALLS
    CC->>CC: Apply Rule A (cash)
    CC->>CC: Apply Rule B (size)
    
    CC->>HR: State with compliance_status=true
    HR-->>U: Display trades for review
    
    U->>HR: "approve"
    HR->>ET: State with human_approval=true
    
    Note over ET: Mock execution<br/>(Broker API in production)
    ET-->>U: "Trades executed successfully!"
```

### Compliance Failure Flow

```mermaid
sequenceDiagram
    participant FC as Financial Calculator
    participant CC as Compliance Check
    participant RG as Response Generator
    participant U as User
    
    FC->>CC: proposed_trades (large trade)
    
    Note over CC: Rule B Check:<br/>Trade > 10% of portfolio
    CC->>CC: FAIL - Trade too large
    
    CC->>RG: compliance_status=false
    Note over RG: Generate error explanation
    
    RG-->>U: "Compliance Check Failed:<br/>Trade exceeds 10% limit"
```

---

## 6. Compliance Rules Specification

### Rule A: Cash Position Rule

```
┌─────────────────────────────────────────────────────┐
│ RULE: Resulting cash position must remain positive  │
├─────────────────────────────────────────────────────┤
│ Threshold:  Minimum 2% of total portfolio value     │
│                                                     │
│ Calculation:                                        │
│   resulting_cash = current_cash + net_trade_effect  │
│   min_required = total_portfolio * 0.02             │
│                                                     │
│ Validation:                                         │
│   IF resulting_cash < 0:                            │
│       FAIL "Negative cash position"                 │
│   IF resulting_cash < min_required:                 │
│       FAIL "Below 2% minimum"                       │
│   ELSE:                                             │
│       PASS                                          │
└─────────────────────────────────────────────────────┘
```

### Rule B: Trade Size Rule

```
┌─────────────────────────────────────────────────────┐
│ RULE: No single trade > 10% of portfolio value      │
├─────────────────────────────────────────────────────┤
│ Threshold:  Maximum 10% per trade                   │
│                                                     │
│ Calculation:                                        │
│   max_trade = total_portfolio * 0.10                │
│                                                     │
│ Validation:                                         │
│   FOR EACH trade IN proposed_trades:                │
│       IF trade.amount > max_trade:                  │
│           FAIL "Trade exceeds limit"                │
│   PASS                                              │
└─────────────────────────────────────────────────────┘
```

---

## 7. Model Configuration Architecture

```mermaid
graph TD
    subgraph Environment
        ENV[.env file]
        ENVVAR[Environment Variables]
    end
    
    subgraph Config["config.py"]
        MC[ModelConfig Class]
        FACTORY[get_llm Factory]
    end
    
    subgraph Models["Google Gemini Models"]
        M1[gemini-2.0-flash]
        M2[gemini-2.5-pro]
        M3[gemini-2.5-flash]
        M4[Future models...]
    end
    
    subgraph Nodes["LLM Nodes"]
        IP[Intent Parser]
        RG[Response Generator]
    end
    
    ENV --> MC
    ENVVAR --> MC
    MC --> FACTORY
    FACTORY --> M1
    FACTORY --> M2
    FACTORY --> M3
    FACTORY -.-> M4
    
    FACTORY --> IP
    FACTORY --> RG
    
    style Config fill:#fff3e0,stroke:#ff9800
    style Models fill:#e8f5e9,stroke:#4caf50
```

### Switching Models at Runtime

```python
# Default (from .env)
from src.config import get_llm
llm = get_llm()  # Uses MODEL_NAME from environment

# Override for specific use case
llm = get_llm("gemini-2.5-pro")  # Use most capable model

# Create new config entirely
from src.config import ModelConfig
config = ModelConfig(
    model_name="gemini-2.5-flash",
    temperature=0.3,
    max_tokens=8192
)
llm = config.get_llm()
```

---

## 8. Error Handling Flow

```mermaid
flowchart TD
    A[Start] --> B{Data Valid?}
    B -->|No| C[CalculationError]
    C --> D[Return error to user]
    
    B -->|Yes| E[Calculate Trades]
    E --> F{Any Trades?}
    F -->|No| G[Portfolio balanced]
    
    F -->|Yes| H{Compliance Pass?}
    H -->|No| I[Clear trades]
    I --> J[Return violation details]
    
    H -->|Yes| K{Human Approves?}
    K -->|No| L[Cancel trades]
    K -->|Yes| M[Execute trades]
    
    G --> N[End]
    J --> N
    L --> N
    M --> N
    D --> N
    
    style C fill:#ffcdd2
    style I fill:#ffcdd2
    style L fill:#ffcdd2
    style M fill:#c8e6c9
    style G fill:#c8e6c9
```

---

## 9. Future Enhancements

### Planned Extensions

1. **Broker Integration**: Connect to real trading APIs
2. **Multi-Asset Rebalancing**: Support for individual securities
3. **Tax-Loss Harvesting**: Add tax optimization node
4. **Risk Assessment**: Pre-trade risk analysis node
5. **Audit Logging**: Complete decision trail

### Architecture for Extensions

```mermaid
graph TD
    subgraph Current["Current Implementation"]
        IP[Intent Parser]
        FC[Financial Calculator]
        CC[Compliance Check]
    end
    
    subgraph Future["Future Nodes"]
        RA[Risk Assessment]
        TLH[Tax-Loss Harvesting]
        BROKER[Broker Integration]
        AUDIT[Audit Logger]
    end
    
    FC --> RA
    RA --> CC
    CC --> TLH
    TLH --> BROKER
    
    IP -.-> AUDIT
    FC -.-> AUDIT
    CC -.-> AUDIT
    
    style Future fill:#e3f2fd,stroke:#2196f3,stroke-dasharray: 5 5
```
