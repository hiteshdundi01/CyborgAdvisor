"""
Intent Parser Node (System 1 - LLM)

This node uses the LLM to classify user intent and extract parameters.
It acts as the "fast thinking" component that routes to appropriate handlers.

IMPORTANT: This is the ONLY node that uses the LLM for decision making.
All calculations are handled by deterministic Python functions.
"""

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..config import get_llm
from ..state import AgentState


class IntentClassification(BaseModel):
    """Structured output for intent classification."""
    intent: Literal["rebalance", "query", "respond"] = Field(
        description="The classified intent of the user message"
    )
    target_allocation: dict | None = Field(
        default=None,
        description="If rebalance intent, any specific target allocations mentioned"
    )
    query_topic: str | None = Field(
        default=None,
        description="If query intent, what the user is asking about"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0"
    )


INTENT_SYSTEM_PROMPT = """You are an intent classifier for a portfolio management system.

Your job is to classify user messages into one of three intents:
1. "rebalance" - User wants to rebalance their portfolio to target allocations
2. "query" - User is asking a question about their portfolio or the system
3. "respond" - General conversation that doesn't require portfolio actions

Examples:
- "Please rebalance my portfolio" -> rebalance
- "Rebalance to 70% stocks and 30% bonds" -> rebalance (with target_allocation)
- "What is my current allocation?" -> query
- "How does rebalancing work?" -> query
- "Hello, how are you?" -> respond
- "Thanks for your help" -> respond

If the user specifies target allocations during a rebalance request, extract them.
Allocations should be expressed as decimals (e.g., 0.70 for 70%).

Respond ONLY with valid JSON matching this schema:
{
    "intent": "rebalance" | "query" | "respond",
    "target_allocation": {"asset_class": weight} | null,
    "query_topic": "string" | null,
    "confidence": 0.0-1.0
}
"""


def intent_parser(state: AgentState, model_name: str | None = None) -> dict:
    """
    Parse user intent using the LLM (System 1 - fast thinking).
    
    This node:
    1. Takes the user's message
    2. Uses the LLM to classify intent
    3. Extracts any parameters (target allocations, query topics)
    4. Updates state with routing information
    
    Args:
        state: Current agent state
        model_name: Optional model override (supports any Google model)
        
    Returns:
        dict: State updates with intent and extracted parameters
    """
    llm = get_llm(model_name)
    parser = JsonOutputParser(pydantic_object=IntentClassification)
    
    messages = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=f"Classify this message: {state['user_input']}")
    ]
    
    try:
        response = llm.invoke(messages)
        result = parser.parse(response.content)
        
        # Extract target allocation if provided, otherwise use existing
        target_allocation = result.get("target_allocation") or state.get("target_allocation")
        
        return {
            "intent": result["intent"],
            "target_allocation": target_allocation,
            "messages": [HumanMessage(content=state["user_input"])],
        }
        
    except Exception as e:
        # On parse error, default to respond intent
        return {
            "intent": "respond",
            "error": f"Intent parsing failed: {str(e)}",
            "messages": [HumanMessage(content=state["user_input"])],
        }


def route_by_intent(state: AgentState) -> str:
    """
    Route to the appropriate node based on classified intent.
    
    This is a conditional edge function for LangGraph.
    
    Args:
        state: Current agent state
        
    Returns:
        str: Name of the next node to route to
    """
    intent = state.get("intent", "respond")
    
    if intent == "rebalance":
        # Route to deterministic financial calculator (System 2)
        return "financial_calculator"
    elif intent == "query":
        # Route to query handler
        return "response_generator"
    else:
        # Default: generate a conversational response
        return "response_generator"
