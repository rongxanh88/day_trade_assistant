import logging

from langchain.chat_models import init_chat_model

from config.settings import settings
from src.data.models import TradingState
from src.agents.utils.tools import update_market_data, get_symbol_data

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
    
    # Bind the tools to the LLM
    tools = [update_market_data, get_symbol_data]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get the latest message and generate a response
    if "agent_messages" in updated_state and updated_state["agent_messages"]:
        response = llm_with_tools.invoke(updated_state["agent_messages"])
        updated_state["agent_messages"].append(response)
        
        # Check if the LLM wants to call any tools
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                logger.info(f"LLM requested tool call: {tool_call['name']}")
                
                try:
                    # Execute the appropriate tool
                    if tool_call['name'] == 'update_market_data':
                        tool_result = await update_market_data.ainvoke({})
                    elif tool_call['name'] == 'get_symbol_data':
                        # Extract arguments from tool call
                        args = tool_call.get('args', {})
                        tool_result = await get_symbol_data.ainvoke(args)
                        
                        # Update state with current symbol context
                        if 'symbol' in args:
                            updated_state["current_symbol"] = args['symbol'].upper()
                            updated_state["current_symbol_data"] = tool_result
                    else:
                        tool_result = f"❌ Unknown tool: {tool_call['name']}"
                    
                    # Add tool result as a message
                    updated_state["agent_messages"].append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call.get('id', 'unknown')
                    })
                    
                except Exception as e:
                    error_msg = f"❌ Tool execution failed: {str(e)}"
                    logger.error(error_msg)
                    updated_state["agent_messages"].append({
                        "role": "tool",
                        "content": error_msg,
                        "tool_call_id": tool_call.get('id', 'unknown')
                    })
            
            # Let LLM process all tool results and generate final response
            try:
                final_response = llm_with_tools.invoke(updated_state["agent_messages"])
                updated_state["agent_messages"].append(final_response)
            except Exception as e:
                error_msg = f"❌ Failed to process tool results: {str(e)}"
                logger.error(error_msg)
                updated_state["agent_messages"].append({
                    "role": "assistant",
                    "content": error_msg
                })
    
    return updated_state
