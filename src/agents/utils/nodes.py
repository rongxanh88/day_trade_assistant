import logging

from langchain.agents import create_react_agent

from config.settings import settings
from src.data.models import TradingState
from src.agents.utils.tools import update_market_data, get_symbol_data

logger = logging.getLogger(__name__)

async def chatbot(state: TradingState) -> TradingState:
    """React agent that handles market data queries with automatic tool selection."""
    
    updated_state = state.copy()
    
    if not updated_state.get("agent_messages"):
        return updated_state
        
    # Get the latest user message
    latest_message = updated_state["agent_messages"][-1]
    if not isinstance(latest_message, dict) or latest_message.get("role") != "user":
        return updated_state
    
    try:
        tools = [update_market_data, get_symbol_data]
        
        # Create react agent
        agent = create_react_agent(
            model="google_genai:" + settings.default_model,
            tools=[update_market_data, get_symbol_data],
            prompt="You are an expert stock and option trading assistant. Use the available tools to help users analyze market data. Be concise and helpful.",
        )
        
        # Execute agent
        result = await agent.invoke({"messages": [{"role": "user", "content": latest_message["content"]}]})
        
        # Add response to messages
        updated_state["agent_messages"].append({
            "role": "assistant", 
            "content": result["output"]
        })
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        updated_state["agent_messages"].append({
            "role": "assistant",
            "content": f"❌ Something went wrong: {str(e)}"
        })
    
    return updated_state
