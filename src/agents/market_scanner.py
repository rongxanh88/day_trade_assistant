import asyncio
import logging
from typing import List

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from config.settings import settings
from src.agents.utils.tools import update_market_data, get_symbol_data
from src.utils.database import db_manager

logger = logging.getLogger(__name__)


def create_market_scanner():
    # Initialize Google Gemini model
    llm = init_chat_model(f"google_genai:{settings.default_model}")
    
    # Define available tools
    tools = [update_market_data, get_symbol_data]
    
    # Create react agent (returns compiled graph)
    agent = create_react_agent(
        llm, 
        tools,
        prompt="""You are an expert stock and option trading assistant. 
        
        You have access to tools to:
        - Update S&P 500 market data from Tradier API
        - Get recent market data for specific symbols
        
        Use these tools to help users analyze market data, identify trends, and answer trading questions.
        Be concise, helpful, and data-driven in your responses.
        
        When users ask about specific stocks, use the get_symbol_data tool to provide current information.
        If users want to refresh the database, use the update_market_data tool.
        """
    )
    
    return agent


# Example usage function
async def run_market_chatbot():
    # Ensure database tables exist
    await db_manager.create_tables()

    # Create the agent
    agent = create_market_scanner()
    
    try:
        print("🤖 Market Scanner Chat Bot Ready!")
        print("I can help you with:")
        print("• Analyze specific stocks (e.g., 'How has AAPL performed recently?')")
        print("• Update market data from Tradier API")
        print("• Answer trading and market questions")
        print("• Compare stocks and identify trends")
        print("The AI will automatically use tools when needed. Type 'quit' to exit.\n")
        
        # Chat loop
        while True:
            try:
                user_input = input("User: ")
                if user_input.lower() in ["q", "quit", "exit"]:
                    print("Exiting chat...")
                    break
                
                # Run agent with user input
                result = await agent.ainvoke({
                    "messages": [{"role": "user", "content": user_input}]
                })
                
                # Display response
                if result["messages"]:
                    # Get the last AI message
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        print("Assistant:", last_message.content)
                    else:
                        print("Assistant:", str(last_message))
                
            except KeyboardInterrupt:
                print("\nExiting chat...")
                break
            except Exception as e:
                print(f"Error during chat: {e}")
                logger.error(f"Chat error: {e}")
                
    except Exception as e:
        logger.error(f"Market scanner failed: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_market_chatbot()) 