"""
Cyborg Advisor - Streamlit UI

Interactive web application for the Neurosymbolic Portfolio Rebalancer.
Visualizes the System 1 (LLM) vs System 2 (Python) architecture.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Cyborg Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Cards */
    .css-1r6slb0, .css-12w0qpk {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00d4ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #00d4ff;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #7c3aed, #00d4ff);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 30px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
    }
    
    /* System badges */
    .system1-badge {
        background: linear-gradient(90deg, #10b981, #34d399);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: 600;
        display: inline-block;
    }
    
    .system2-badge {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Trade cards */
    .trade-buy {
        background: rgba(16, 185, 129, 0.2);
        border-left: 4px solid #10b981;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .trade-sell {
        background: rgba(239, 68, 68, 0.2);
        border-left: 4px solid #ef4444;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Saga step visualization */
    .saga-step {
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .saga-step-pending {
        background: rgba(148, 163, 184, 0.2);
        border-left: 4px solid #94a3b8;
    }
    
    .saga-step-running {
        background: rgba(59, 130, 246, 0.2);
        border-left: 4px solid #3b82f6;
        animation: pulse 1.5s infinite;
    }
    
    .saga-step-success {
        background: rgba(16, 185, 129, 0.2);
        border-left: 4px solid #10b981;
    }
    
    .saga-step-failed {
        background: rgba(239, 68, 68, 0.2);
        border-left: 4px solid #ef4444;
    }
    
    .saga-step-compensated {
        background: rgba(251, 191, 36, 0.2);
        border-left: 4px solid #fbbf24;
    }
    
    .saga-transaction-id {
        font-family: monospace;
        background: rgba(0, 212, 255, 0.1);
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid rgba(0, 212, 255, 0.3);
        color: #00d4ff;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {
        "holdings": [
            {"asset": "AAPL", "class": "stocks", "value": 25000},
            {"asset": "MSFT", "class": "stocks", "value": 20000},
            {"asset": "GOOGL", "class": "stocks", "value": 15000},
            {"asset": "BND", "class": "bonds", "value": 20000},
            {"asset": "TLT", "class": "bonds", "value": 10000},
            {"asset": "CASH", "class": "cash", "value": 8000},
            {"asset": "GLD", "class": "alternatives", "value": 2000},
        ],
        "total_value": 100000,
    }

if "target_allocation" not in st.session_state:
    st.session_state.target_allocation = {
        "stocks": 0.60,
        "bonds": 0.30,
        "cash": 0.05,
        "alternatives": 0.05,
    }

if "proposed_trades" not in st.session_state:
    st.session_state.proposed_trades = None

if "compliance_status" not in st.session_state:
    st.session_state.compliance_status = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "processing_stage" not in st.session_state:
    st.session_state.processing_stage = None

# Saga execution state
if "saga_logs" not in st.session_state:
    st.session_state.saga_logs = None

if "saga_status" not in st.session_state:
    st.session_state.saga_status = None

if "saga_transaction_id" not in st.session_state:
    st.session_state.saga_transaction_id = None


def get_current_allocation(portfolio: dict) -> dict:
    """Calculate current allocation percentages."""
    total = portfolio["total_value"]
    holdings = portfolio["holdings"]
    
    allocation = {}
    for holding in holdings:
        asset_class = holding["class"]
        allocation[asset_class] = allocation.get(asset_class, 0) + holding["value"]
    
    return {k: v / total for k, v in allocation.items()}


def calculate_trades(portfolio: dict, targets: dict) -> list:
    """Calculate rebalancing trades (System 2 - deterministic)."""
    from src.nodes.financial_calculator import calculate_rebalance
    return calculate_rebalance(portfolio, targets)


def check_compliance(trades: list, portfolio: dict) -> tuple:
    """Run compliance checks (System 2 - deterministic)."""
    from src.nodes.compliance_check import run_compliance_checks
    return run_compliance_checks(trades, portfolio)


# Sidebar
with st.sidebar:
    st.markdown("# 🤖 Cyborg Advisor")
    st.markdown("### Neurosymbolic Rebalancer")
    
    st.divider()
    
    # Model configuration
    st.markdown("#### 🧠 LLM Model")
    model_name = st.selectbox(
        "Select Model",
        ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"],
        index=0,
    )
    
    # API Key status
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ Set GOOGLE_API_KEY in .env")
    
    st.divider()
    
    # Target allocation editor
    st.markdown("#### 🎯 Target Allocation")
    
    stocks_pct = st.slider("Stocks %", 0, 100, int(st.session_state.target_allocation["stocks"] * 100))
    bonds_pct = st.slider("Bonds %", 0, 100, int(st.session_state.target_allocation["bonds"] * 100))
    cash_pct = st.slider("Cash %", 0, 100, int(st.session_state.target_allocation["cash"] * 100))
    alt_pct = st.slider("Alternatives %", 0, 100, int(st.session_state.target_allocation["alternatives"] * 100))
    
    total_pct = stocks_pct + bonds_pct + cash_pct + alt_pct
    if total_pct != 100:
        st.error(f"⚠️ Total: {total_pct}% (must equal 100%)")
    else:
        st.success(f"✅ Total: {total_pct}%")
        st.session_state.target_allocation = {
            "stocks": stocks_pct / 100,
            "bonds": bonds_pct / 100,
            "cash": cash_pct / 100,
            "alternatives": alt_pct / 100,
        }
    
    st.divider()
    
    # Architecture info
    st.markdown("#### 📐 Architecture")
    st.markdown('<span class="system1-badge">System 1: LLM</span>', unsafe_allow_html=True)
    st.caption("Intent parsing, responses")
    st.markdown('<span class="system2-badge">System 2: Python</span>', unsafe_allow_html=True)
    st.caption("Calculations, compliance")


# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("## 📊 Portfolio Overview")
    
    # Portfolio metrics
    portfolio = st.session_state.portfolio
    current_alloc = get_current_allocation(portfolio)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Value", f"${portfolio['total_value']:,.0f}")
    with m2:
        st.metric("Stocks", f"{current_alloc.get('stocks', 0)*100:.1f}%")
    with m3:
        st.metric("Bonds", f"{current_alloc.get('bonds', 0)*100:.1f}%")
    with m4:
        st.metric("Cash", f"{current_alloc.get('cash', 0)*100:.1f}%")

with col2:
    st.markdown("## 🎯 Target vs Current")
    
    # Comparison chart
    targets = st.session_state.target_allocation
    
    comparison_data = []
    for asset_class in targets:
        comparison_data.append({
            "Asset Class": asset_class.title(),
            "Type": "Current",
            "Weight": current_alloc.get(asset_class, 0) * 100,
        })
        comparison_data.append({
            "Asset Class": asset_class.title(),
            "Type": "Target",
            "Weight": targets[asset_class] * 100,
        })
    
    df_compare = pd.DataFrame(comparison_data)
    
    fig = px.bar(
        df_compare,
        x="Asset Class",
        y="Weight",
        color="Type",
        barmode="group",
        color_discrete_map={"Current": "#7c3aed", "Target": "#00d4ff"},
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


# Holdings table with editor
st.markdown("## 📋 Current Holdings")

# Portfolio editing mode toggle
col_edit1, col_edit2 = st.columns([3, 1])
with col_edit2:
    edit_mode = st.toggle("✏️ Edit Portfolio", key="edit_mode")

if edit_mode:
    st.markdown("### 📝 Portfolio Editor")
    
    # Show editable dataframe
    holdings_data = st.session_state.portfolio["holdings"]
    
    # Convert to DataFrame for editing
    edit_df = pd.DataFrame(holdings_data)
    
    # Add new holding form
    st.markdown("#### ➕ Add New Holding")
    add_col1, add_col2, add_col3, add_col4 = st.columns([2, 2, 2, 1])
    
    with add_col1:
        new_asset = st.text_input("Asset Symbol", placeholder="e.g., NVDA")
    with add_col2:
        new_class = st.selectbox(
            "Asset Class",
            ["stocks", "bonds", "cash", "alternatives"],
            key="new_class"
        )
    with add_col3:
        new_value = st.number_input("Value ($)", min_value=0.0, step=1000.0)
    with add_col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_holding"):
            if new_asset and new_value > 0:
                new_holding = {
                    "asset": new_asset.upper(),
                    "class": new_class,
                    "value": float(new_value)
                }
                st.session_state.portfolio["holdings"].append(new_holding)
                # Recalculate total
                st.session_state.portfolio["total_value"] = sum(
                    h["value"] for h in st.session_state.portfolio["holdings"]
                )
                st.rerun()
            else:
                st.warning("Enter asset symbol and value > 0")
    
    st.markdown("#### 📊 Edit Existing Holdings")
    st.caption("Modify values directly and click 'Apply Changes'")
    
    # Create editable dataframe
    edited_df = st.data_editor(
        edit_df,
        column_config={
            "asset": st.column_config.TextColumn("Asset", width="medium"),
            "class": st.column_config.SelectboxColumn(
                "Class",
                options=["stocks", "bonds", "cash", "alternatives"],
                width="medium"
            ),
            "value": st.column_config.NumberColumn(
                "Value ($)",
                min_value=0,
                format="$%.0f",
                width="medium"
            ),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",  # Allow adding/removing rows
    )
    
    # Apply changes button
    col_apply1, col_apply2, col_apply3 = st.columns([1, 1, 2])
    with col_apply1:
        if st.button("✅ Apply Changes", type="primary"):
            # Update portfolio from edited dataframe
            new_holdings = edited_df.to_dict('records')
            # Filter out empty rows
            new_holdings = [h for h in new_holdings if h.get("asset") and h.get("value", 0) > 0]
            st.session_state.portfolio["holdings"] = new_holdings
            st.session_state.portfolio["total_value"] = sum(
                h["value"] for h in new_holdings
            )
            st.success("Portfolio updated!")
            st.rerun()
    
    with col_apply2:
        if st.button("🔄 Reset to Sample"):
            st.session_state.portfolio = {
                "holdings": [
                    {"asset": "AAPL", "class": "stocks", "value": 25000},
                    {"asset": "MSFT", "class": "stocks", "value": 20000},
                    {"asset": "GOOGL", "class": "stocks", "value": 15000},
                    {"asset": "BND", "class": "bonds", "value": 20000},
                    {"asset": "TLT", "class": "bonds", "value": 10000},
                    {"asset": "CASH", "class": "cash", "value": 8000},
                    {"asset": "GLD", "class": "alternatives", "value": 2000},
                ],
                "total_value": 100000,
            }
            st.rerun()

else:
    # Read-only display
    holdings_df = pd.DataFrame(portfolio["holdings"])
    holdings_df["Weight"] = holdings_df["value"] / portfolio["total_value"] * 100
    holdings_df.columns = ["Asset", "Class", "Value ($)", "Weight (%)"]
    holdings_df["Value ($)"] = holdings_df["Value ($)"].apply(lambda x: f"${x:,.0f}")
    holdings_df["Weight (%)"] = holdings_df["Weight (%)"].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        holdings_df,
        use_container_width=True,
        hide_index=True,
    )


# Rebalancing section
st.markdown("---")
st.markdown("## 🔄 Rebalancing")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("🚀 Calculate Rebalance", use_container_width=True):
        # Processing animation
        with st.spinner(""):
            progress = st.progress(0)
            status = st.empty()
            
            # System 1: Intent (simulated)
            status.markdown("### 🧠 System 1: Parsing Intent...")
            for i in range(30):
                progress.progress(i)
                time.sleep(0.02)
            
            # System 2: Calculate
            status.markdown("### 🔢 System 2: Calculating Trades...")
            for i in range(30, 60):
                progress.progress(i)
                time.sleep(0.02)
            
            try:
                trades = calculate_trades(portfolio, targets)
                st.session_state.proposed_trades = trades
            except Exception as e:
                st.error(f"Calculation error: {e}")
                st.session_state.proposed_trades = None
            
            # System 2: Compliance
            status.markdown("### 🛡️ System 2: Checking Compliance...")
            for i in range(60, 100):
                progress.progress(i)
                time.sleep(0.02)
            
            if st.session_state.proposed_trades:
                passed, errors = check_compliance(
                    st.session_state.proposed_trades, 
                    portfolio
                )
                st.session_state.compliance_status = (passed, errors)
            
            progress.progress(100)
            status.empty()


# Display proposed trades
if st.session_state.proposed_trades:
    trades = st.session_state.proposed_trades
    compliance = st.session_state.compliance_status
    
    st.markdown("### 📝 Proposed Trades")
    
    if not trades:
        st.info("✅ Portfolio is already balanced. No trades needed.")
    else:
        # Trade cards
        for trade in trades:
            if trade["action"] == "BUY":
                st.markdown(f"""
                <div class="trade-buy">
                    <strong>🟢 BUY</strong> ${trade['amount']:,.2f} of <strong>{trade['asset']}</strong><br>
                    <small>{trade['current_weight']*100:.1f}% → {trade['target_weight']*100:.1f}% | {trade['reason']}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="trade-sell">
                    <strong>🔴 SELL</strong> ${trade['amount']:,.2f} of <strong>{trade['asset']}</strong><br>
                    <small>{trade['current_weight']*100:.1f}% → {trade['target_weight']*100:.1f}% | {trade['reason']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Compliance status
        st.markdown("### 🛡️ Compliance Check")
        
        if compliance and compliance[0]:
            st.success("✅ All compliance rules passed!")
            
            # Human approval
            st.markdown("### ✋ Human Approval Required")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("✅ Approve & Execute", type="primary"):
                    # Execute using Saga Pattern
                    from src.sagas import RebalanceSaga
                    from src.sagas.core import SagaContext, SagaStatus
                    
                    # Build saga context
                    ctx: SagaContext = {
                        "transaction_id": "",
                        "portfolio_data": portfolio,
                        "proposed_trades": trades,
                        "executed_steps": [],
                        "logs": [],
                        "error": None,
                    }
                    
                    # Show execution panel
                    st.markdown("### 🔄 Saga Execution")
                    
                    # Execute saga
                    saga = RebalanceSaga()
                    result = saga.run(ctx)
                    
                    # Store in session state
                    st.session_state.saga_logs = [log.to_dict() for log in result.logs]
                    st.session_state.saga_status = result.status.value
                    st.session_state.saga_transaction_id = result.transaction_id
                    
                    # Display transaction ID
                    st.markdown(f"""
                    <div class="saga-transaction-id">
                        🔑 Transaction ID: {result.transaction_id}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display step logs
                    for log in result.logs:
                        status_class = {
                            "success": "saga-step-success",
                            "failed": "saga-step-failed",
                            "compensated": "saga-step-compensated",
                            "compensating": "saga-step-compensated",
                            "running": "saga-step-running",
                            "pending": "saga-step-pending",
                            "skipped": "saga-step-pending",
                        }.get(log.status.value, "saga-step-pending")
                        
                        status_emoji = {
                            "success": "✅",
                            "failed": "❌",
                            "compensated": "🔄",
                            "compensating": "🔄",
                            "running": "⏳",
                            "pending": "⏸️",
                            "skipped": "⏭️",
                        }.get(log.status.value, "•")
                        
                        st.markdown(f"""
                        <div class="saga-step {status_class}">
                            <span>{status_emoji}</span>
                            <strong>{log.step_name}</strong>
                            <span style="opacity: 0.7;">— {log.message}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Final status
                    if result.status == SagaStatus.SUCCESS:
                        st.balloons()
                        st.success("🎉 **Saga Complete!** Portfolio rebalanced successfully.")
                        st.session_state.proposed_trades = None
                        st.session_state.compliance_status = None
                    elif result.status == SagaStatus.ROLLED_BACK:
                        st.warning(f"⚠️ **Saga Rolled Back**: {result.error}")
                        st.info("No changes were made to your portfolio.")
                    else:
                        st.error(f"❌ **Saga Failed**: {result.error}")
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.proposed_trades = None
                    st.session_state.compliance_status = None
                    st.session_state.saga_logs = None
                    st.session_state.saga_status = None
                    st.session_state.saga_transaction_id = None
                    st.rerun()
        
        elif compliance:
            st.error("❌ Compliance Check Failed")
            for error in compliance[1]:
                st.warning(error)


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; opacity: 0.7;">
    <p>🤖 <strong>Cyborg Advisor</strong> | System 1 (LLM) + System 2 (Python) = Neurosymbolic AI</p>
    <p><small>Built with LangGraph • Streamlit • Google Gemini</small></p>
</div>
""", unsafe_allow_html=True)
