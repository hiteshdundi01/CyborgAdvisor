"""
Cyborg Advisor - Main Entry Point

Demo script showing the Neurosymbolic Rebalancer in action:
1. Load a sample portfolio
2. Process a rebalance request
3. Show trade calculations (deterministic Python)
4. Demonstrate human-in-the-loop approval
5. Mock trade execution
"""

import os
from dotenv import load_dotenv

from src.state import (
    create_initial_state,
    SAMPLE_PORTFOLIO,
    DEFAULT_TARGET_ALLOCATION,
)
from src.graph import compile_graph
from src.nodes.financial_calculator import format_trades_summary


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("🤖 CYBORG ADVISOR - Neurosymbolic Rebalancer")
    print("=" * 60)
    print("\nSystem 1 (LLM): Intent parsing & response generation")
    print("System 2 (Python): All calculations & compliance checks")
    print("-" * 60)


def print_portfolio(portfolio: dict):
    """Print portfolio summary."""
    print("\n📊 Current Portfolio:")
    print(f"   Total Value: ${portfolio['total_value']:,.2f}")
    print("\n   Holdings:")
    for h in portfolio["holdings"]:
        pct = (h["value"] / portfolio["total_value"]) * 100
        print(f"   • {h['asset']:6} ({h['class']:12}): ${h['value']:>10,.2f} ({pct:>5.1f}%)")


def print_targets(targets: dict):
    """Print target allocation."""
    print("\n🎯 Target Allocation:")
    for asset_class, weight in targets.items():
        print(f"   • {asset_class:15}: {weight*100:>5.1f}%")


def run_demo():
    """Run the interactive demo."""
    # Load environment
    load_dotenv()
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n⚠️  Warning: GOOGLE_API_KEY not set in environment")
        print("   Copy .env.example to .env and add your API key")
        print("   Running in demo mode with mock responses...\n")
    
    print_banner()
    print_portfolio(SAMPLE_PORTFOLIO)
    print_targets(DEFAULT_TARGET_ALLOCATION)
    
    # Compile graph with checkpointer for HITL
    print("\n🔧 Initializing LangGraph state machine...")
    graph = compile_graph(checkpointer=True)
    
    # Create initial state
    thread_id = "demo-session-1"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Demo: Rebalance request
    print("\n" + "-" * 60)
    print("💬 User: Please rebalance my portfolio")
    print("-" * 60)
    
    initial_state = create_initial_state(
        user_input="Please rebalance my portfolio",
        portfolio_data=SAMPLE_PORTFOLIO,
        target_allocation=DEFAULT_TARGET_ALLOCATION,
    )
    
    try:
        # Run until human review interrupt
        print("\n⚙️  Processing (System 1: Intent → System 2: Calculate → Compliance)...")
        
        for event in graph.stream(initial_state, config):
            # Print node execution
            for node_name, output in event.items():
                print(f"   ✓ {node_name}")
                
                # Show trades if calculated
                if output.get("proposed_trades"):
                    print("\n" + format_trades_summary(output["proposed_trades"]))
        
        # Check current state
        state = graph.get_state(config)
        
        if state.values.get("proposed_trades"):
            print("\n" + "=" * 60)
            print("⏸️  HUMAN REVIEW CHECKPOINT")
            print("=" * 60)
            print("\nThe graph has paused for human approval.")
            
            # Simulate human approval
            approval = input("\nApprove trades? (yes/no): ").strip().lower()
            
            if approval in ["yes", "y", "approve"]:
                # Resume with approval
                print("\n✅ Resuming with approval...")
                resume_state = create_initial_state(
                    user_input="approve",
                    portfolio_data=SAMPLE_PORTFOLIO,
                    target_allocation=DEFAULT_TARGET_ALLOCATION,
                )
                resume_state["human_approval"] = True
                resume_state["proposed_trades"] = state.values.get("proposed_trades")
                
                for event in graph.stream(resume_state, config):
                    for node_name, output in event.items():
                        print(f"   ✓ {node_name}")
                        if output.get("response"):
                            print(f"\n{output['response']}")
            else:
                print("\n❌ Trades cancelled by user.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Installed dependencies: pip install -r requirements.txt")
        print("2. Set GOOGLE_API_KEY in .env file")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")


def run_simple_demo():
    """
    Run a simplified demo without LLM (for testing structure).
    
    This demonstrates the deterministic components:
    - Financial calculations
    - Compliance checks
    """
    from src.nodes.financial_calculator import calculate_rebalance
    from src.nodes.compliance_check import run_compliance_checks
    
    print_banner()
    print_portfolio(SAMPLE_PORTFOLIO)
    print_targets(DEFAULT_TARGET_ALLOCATION)
    
    print("\n" + "-" * 60)
    print("🧮 Running Deterministic Calculations (No LLM)")
    print("-" * 60)
    
    # Calculate rebalance
    print("\n📐 Financial Calculator (System 2):")
    trades = calculate_rebalance(SAMPLE_PORTFOLIO, DEFAULT_TARGET_ALLOCATION)
    print(format_trades_summary(trades))
    
    # Run compliance
    print("\n🛡️ Compliance Check (System 2):")
    passed, errors = run_compliance_checks(trades, SAMPLE_PORTFOLIO)
    
    if passed:
        print("   ✅ All compliance rules passed!")
    else:
        print("   ❌ Compliance failures:")
        for error in errors:
            print(f"      • {error}")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        # Run without LLM
        run_simple_demo()
    else:
        # Full demo with LLM
        run_demo()
