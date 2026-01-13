"""
Response Generator Node

Generates natural language responses using the LLM.
Used for query responses, trade confirmations, and error explanations.
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from ..config import get_llm
from ..state import AgentState
from .financial_calculator import format_trades_summary


RESPONSE_SYSTEM_PROMPT = """You are a helpful portfolio management assistant.

Your role is to:
1. Answer questions about portfolios and rebalancing clearly
2. Explain trade proposals in plain language
3. Provide helpful guidance on investment concepts
4. Respond to general conversation politely

Always be professional, concise, and helpful.
If you don't know something, say so rather than guessing.
"""


def response_generator(state: AgentState, model_name: str | None = None) -> dict:
    """
    Generate a response to the user based on current state.
    
    This node handles:
    - Query responses (portfolio questions)
    - Trade confirmations
    - Error explanations
    - General conversation
    
    Args:
        state: Current agent state
        model_name: Optional model override
        
    Returns:
        dict: State updates with response
    """
    # If there's already a response set (e.g., from error), use it
    if state.get("response"):
        return {"messages": [AIMessage(content=state["response"])]}
    
    # If there are proposed trades awaiting approval, summarize them
    trades = state.get("proposed_trades")
    if trades:
        summary = format_trades_summary(trades)
        response = (
            f"{summary}\n\n"
            "✋ **Awaiting your approval.** Reply 'approve' to execute these trades "
            "or 'cancel' to abort."
        )
        return {
            "response": response,
            "messages": [AIMessage(content=response)],
        }
    
    # Generate LLM response for queries or conversation
    llm = get_llm(model_name)
    
    context_parts = []
    
    # Add portfolio context if available
    if state.get("portfolio_data"):
        portfolio = state["portfolio_data"]
        context_parts.append(
            f"User's portfolio value: ${portfolio.get('total_value', 0):,.2f}"
        )
    
    # Add any errors
    if state.get("error"):
        context_parts.append(f"Error occurred: {state['error']}")
    
    context = "\n".join(context_parts) if context_parts else "No portfolio data loaded."
    
    messages = [
        SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
        SystemMessage(content=f"Context: {context}"),
        HumanMessage(content=state["user_input"]),
    ]
    
    try:
        response = llm.invoke(messages)
        return {
            "response": response.content,
            "messages": [AIMessage(content=response.content)],
        }
    except Exception as e:
        error_msg = f"I apologize, but I encountered an error: {str(e)}"
        return {
            "response": error_msg,
            "messages": [AIMessage(content=error_msg)],
        }
