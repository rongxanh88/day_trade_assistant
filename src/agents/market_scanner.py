"""
Market Scanner Agent - Your first LangGraph workflow!

This agent demonstrates core LangGraph concepts:
- State management with TradingState
- Tool integration (Tradier API)
- Conditional routing based on market conditions
- Human-in-the-loop for setup review
- Error handling and recovery
"""

import asyncio
import logging
from typing import List

from langgraph.graph import StateGraph, END, START

from src.data.models import (
    TradingState,
    SetupType, 
    # TimeFrame, 
    # AlertLevel,
    MarketCondition,
    # Quote
)
from src.utils.database import db_manager
from src.agents.utils.nodes import chatbot

logger = logging.getLogger(__name__)


# Build the LangGraph workflow
def create_market_scanner_graph() -> StateGraph:
    """Create the market scanner LangGraph workflow."""
    
    # Initialize the graph with our state schema
    workflow = StateGraph(TradingState)
    
    # Add nodes (these are the workflow steps)
    workflow.add_node("chatbot", chatbot)
    
    # Add edges (workflow routing)
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    # End after alerts
    
    return workflow


# Factory function to create and configure the scanner
def create_market_scanner(watchlist: List[str] = None) -> StateGraph:
    """Create a configured market scanner instance."""
    
    graph = create_market_scanner_graph()
    
    # Create initial state
    initial_state: TradingState = {
        # Market Data
        "market_condition": MarketCondition.NEUTRAL,
        
        # Analysis Results
        "latest_quotes": {},
        "technical_indicators": {},
        
        # Current Symbol Context
        "current_symbol": None,
        "current_symbol_data": None,

        # User Preferences
        "risk_tolerance": 1.0,
        "preferred_strategies": [SetupType.SWING_TRADE],
        "account_size": 25000.0,
        
        # Workflow Control
        "scan_frequency": 30,
        "last_scan_time": None,
        "alerts_sent": [],
        "is_scanning_active": True,
        
        # Analysis Settings
        "min_confidence_threshold": 70.0,
        "min_risk_reward_ratio": 2.0,
        "max_concurrent_setups": 5,
        
        # Messages and Logs
        "messages": [],
        "workflow_status": "initializing",
        "last_error": None,
        
        # Chat Messages for LLM
        "agent_messages": []
    }
    
    return graph, initial_state


# Example usage function
async def run_market_scan_example():
    """Example of how to run the market scanner."""
    # Ensure database tables exist
    await db_manager.create_tables()
    
    logger.info("Starting market scanner example...")
    
    # Create the graph and initial state
    graph, initial_state = create_market_scanner()
    
    # Compile the graph
    app = graph.compile()
    
    try:
        print("🤖 Market Scanner Chat Bot Ready!")
        print("I can help you with:")
        print("• Analyze specific stocks (e.g., 'How has AAPL performed recently?')")
        print("• Update market data from Tradier API")
        print("• Answer trading and market questions")
        print("• Compare stocks and identify trends")
        print("The AI will automatically use tools when needed. Type 'quit' to exit.\n")
        
        current_state = initial_state
        
        # Chat loop
        while True:
            try:
                user_input = input("User: ")
                if user_input.lower() in ["q", "quit", "exit"]:
                    print("Exiting chat...")
                    break
                
                # Add user message to state
                current_state["agent_messages"].append({"role": "user", "content": user_input})
                
                # Run workflow
                current_state = await app.ainvoke(current_state)
                
                # Display response(s) - there might be multiple messages from market data updates
                if current_state["agent_messages"]:
                    # Get all new messages (everything after the user message we just added)
                    new_messages = current_state["agent_messages"][-(len(current_state["agent_messages"]) - len(initial_state.get("agent_messages", []))):]
                    
                    for message in new_messages:
                        if isinstance(message, dict) and message.get("role") == "assistant":
                            print("Assistant:", message["content"])
                        elif hasattr(message, 'content') and hasattr(message, 'type'):
                            print("Assistant:", message.content)
                
            except KeyboardInterrupt:
                print("\nExiting chat...")
                break
            except Exception as e:
                print(f"Error during chat: {e}")
                # Try with a default message to test the system
                user_input = "What can you help me with?"
                print(f"Trying with default message: {user_input}")
                current_state["agent_messages"].append({"role": "user", "content": user_input})
                current_state = await app.ainvoke(current_state)
                if current_state["agent_messages"]:
                    last_message = current_state["agent_messages"][-1]
                    if hasattr(last_message, 'content'):
                        print("Assistant:", last_message.content)
                    elif isinstance(last_message, dict) and 'content' in last_message:
                        print("Assistant:", last_message['content'])
                    else:
                        print("Assistant:", str(last_message))
                break
        
        return current_state
        
    except Exception as e:
        logger.error(f"Market scanner failed: {e}")
        raise

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_market_scan_example()) 