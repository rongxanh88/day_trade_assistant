import logging

from langchain.chat_models import init_chat_model

from config.settings import settings
from src.data.models import TradingState
from src.agents.utils.tools import update_market_data

logger = logging.getLogger(__name__)

# LangGraph node functions
    
async def chatbot(state: TradingState) -> TradingState:
    """
    Chatbot agent that can answer questions about the market data using LangChain tools.
    """
    logger.info("Starting chatbot...")
    
    updated_state = state.copy()
    
    # Initialize LLM with tools
    llm = init_chat_model(
        model="google_genai:" + settings.default_model
    )
    
    # Bind the market data update tool to the LLM
    tools = [update_market_data]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get the latest message and generate a response
    if "agent_messages" in updated_state and updated_state["agent_messages"]:
        response = llm_with_tools.invoke(updated_state["agent_messages"])
        updated_state["agent_messages"].append(response)
        
        # Check if the LLM wants to call any tools
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                logger.info(f"LLM requested tool call: {tool_call['name']}")
                
                # Execute the tool (currently only update_market_data)
                if tool_call['name'] == 'update_market_data':
                    try:
                        tool_result = await update_market_data.ainvoke({})
                        
                        # Add tool result as a message
                        updated_state["agent_messages"].append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tool_call.get('id', 'unknown')
                        })
                        
                        # Let LLM process the tool result and generate final response
                        final_response = llm_with_tools.invoke(updated_state["agent_messages"])
                        updated_state["agent_messages"].append(final_response)
                        
                    except Exception as e:
                        error_msg = f"❌ Tool execution failed: {str(e)}"
                        logger.error(error_msg)
                        updated_state["agent_messages"].append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    return updated_state
