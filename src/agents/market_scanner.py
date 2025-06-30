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
from datetime import datetime, date, timedelta
from typing import Dict, List, Any

from langgraph.graph import StateGraph, END, START
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model

from src.data.models import (
    TradingState,
    SetupType, 
    # TimeFrame, 
    # AlertLevel,
    MarketCondition,
    # Quote
)
from src.integrations.tradier_client import tradier_client
from src.utils.database import db_manager
from config.sp500_symbols import get_sp500_symbols
from config.settings import settings


logger = logging.getLogger(__name__)


# LangGraph node functions
async def update_daily_market_data(state: TradingState) -> TradingState:
    """
    Update daily market data for watchlist symbols.
    
    Checks database for missing data in the past year and fetches from Tradier API if needed.
    """
    logger.info("Starting daily market data update...")
    
    # Get complete S&P 500 symbols list
    sp500_symbols = get_sp500_symbols()
    
    if not sp500_symbols:
        logger.error("No S&P 500 symbols found in configuration")
        updated_state = state.copy()
        updated_state["workflow_status"] = "error"
        updated_state["last_error"] = "No S&P 500 symbols found in configuration"
        updated_state["messages"].append({
            "timestamp": datetime.now(),
            "type": "error",
            "message": "No S&P 500 symbols found in configuration"
        })
        return updated_state
    
    logger.info(f"Loaded {len(sp500_symbols)} S&P 500 symbols for market data update")
    
    # Calculate date range for the past year
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    updated_state = state.copy()
    updated_state["workflow_status"] = "updating_market_data"
    updated_state["messages"].append({
        "timestamp": datetime.now(),
        "type": "info",
        "message": f"Starting market data update for {len(sp500_symbols)} S&P 500 symbols"
    })
    
    try:
        symbols_updated = 0
        total_records_fetched = 0
        
        for idx, symbol in enumerate(sp500_symbols, 1):
            try:
                logger.info(f"[{idx}/{len(sp500_symbols)}] Checking market data for {symbol}...")
                
                # Get existing data dates from database
                existing_dates = await db_manager.get_existing_data_dates(symbol, start_date, end_date)
                logger.info(f"{symbol}: Found {len(existing_dates)} existing records in database")
                
                # Generate all trading days in the range (excluding weekends)
                all_dates = []
                current_date = start_date
                while current_date <= end_date:
                    # Skip weekends (Monday=0, Sunday=6)
                    if current_date.weekday() < 5:  # Monday to Friday
                        all_dates.append(current_date)
                    current_date += timedelta(days=1)
                
                # Find missing dates
                existing_date_set = set(existing_dates)
                missing_dates = [d for d in all_dates if d not in existing_date_set]
                
                if missing_dates:
                    logger.info(f"{symbol}: Found {len(missing_dates)} missing dates, fetching from API...")
                    
                    # Fetch missing data from Tradier API
                    # We'll fetch in chunks to avoid overwhelming the API
                    missing_start = min(missing_dates)
                    missing_end = max(missing_dates)
                    
                    market_data = await tradier_client.get_historical_data(
                        symbol=symbol,
                        interval="daily",
                        start=missing_start,
                        end=missing_end
                    )
                    
                    if market_data:
                        # Filter to only include the actual missing dates
                        filtered_data = []
                        for data in market_data:
                            data_date = data.date
                            if isinstance(data_date, str):
                                data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
                            if data_date in missing_dates:
                                filtered_data.append(data)
                        
                        if filtered_data:
                            await db_manager.insert_market_data(filtered_data, symbol)
                            total_records_fetched += len(filtered_data)
                            logger.info(f"{symbol}: Successfully inserted {len(filtered_data)} new records")
                        else:
                            logger.info(f"{symbol}: No new data to insert after filtering")
                    else:
                        logger.warning(f"{symbol}: No data returned from API")
                else:
                    logger.info(f"{symbol}: Database is up to date")
                
                symbols_updated += 1
                
                # Add progress update every 50 symbols
                if idx % 50 == 0:
                    progress_message = f"Progress: {idx}/{len(sp500_symbols)} symbols processed ({symbols_updated} updated, {total_records_fetched} records fetched)"
                    logger.info(progress_message)
                    updated_state["messages"].append({
                        "timestamp": datetime.now(),
                        "type": "info",
                        "message": progress_message
                    })
                
            except Exception as e:
                logger.error(f"Failed to update market data for {symbol}: {e}")
                updated_state["messages"].append({
                    "timestamp": datetime.now(),
                    "type": "error",
                    "message": f"Failed to update {symbol}: {str(e)}"
                })
                # Continue with other symbols instead of failing completely
                continue
        
        # Update state with results
        updated_state["workflow_status"] = "market_data_updated"
        updated_state["last_scan_time"] = datetime.now()
        updated_state["messages"].append({
            "timestamp": datetime.now(),
            "type": "success",
            "message": f"S&P 500 market data update completed. {symbols_updated}/{len(sp500_symbols)} symbols processed, {total_records_fetched} new records fetched."
        })
        
        logger.info(f"S&P 500 market data update completed successfully. {symbols_updated}/{len(sp500_symbols)} symbols processed, {total_records_fetched} new records fetched.")
        return updated_state
        
    except Exception as e:
        logger.error(f"Market data update failed: {e}")
        updated_state["workflow_status"] = "error"
        updated_state["last_error"] = str(e)
        updated_state["messages"].append({
            "timestamp": datetime.now(),
            "type": "error",
            "message": f"Market data update failed: {str(e)}"
        })
        return updated_state
    
async def chatbot(state: TradingState) -> TradingState:
    """
    Chatbot agent that can answer questions about the market data and handle market data updates.
    """
    logger.info("Starting chatbot...")
    
    updated_state = state.copy()
    
    # Check if user is asking for market data update
    if "agent_messages" in updated_state and updated_state["agent_messages"]:
        latest_user_message = updated_state["agent_messages"][-1]
        user_content = ""
        
        if isinstance(latest_user_message, dict) and 'content' in latest_user_message:
            user_content = latest_user_message['content'].lower()
        elif hasattr(latest_user_message, 'content'):
            user_content = latest_user_message.content.lower()
        
        # Check if user is requesting market data update
        update_keywords = ['update market data', 'refresh market data', 'update data', 'fetch market data', 'download market data']
        if any(keyword in user_content for keyword in update_keywords):
            logger.info("User requested market data update, executing...")
            
            # Add notification that update is starting
            updated_state["agent_messages"].append({
                "role": "assistant", 
                "content": "🚀 Starting S&P 500 market data update... This may take a few minutes."
            })
            
            # Run the market data update
            updated_state = await update_daily_market_data(updated_state)
            
            # Add completion message
            if updated_state.get("workflow_status") == "market_data_updated":
                completion_msg = "✅ Market data update completed successfully! You can now ask questions about the latest market data."
            else:
                completion_msg = f"❌ Market data update failed: {updated_state.get('last_error', 'Unknown error')}"
            
            updated_state["agent_messages"].append({
                "role": "assistant", 
                "content": completion_msg
            })
            
            return updated_state
    
    # Regular chatbot functionality
    llm = init_chat_model(
        model="google_genai:" + settings.default_model
    )
    
    # Get the latest message and generate a response
    if "agent_messages" in updated_state and updated_state["agent_messages"]:
        response = llm.invoke(updated_state["agent_messages"])
        updated_state["agent_messages"].append(response)
    
    return updated_state


# Build the LangGraph workflow
def create_market_scanner_graph() -> StateGraph:
    """Create the market scanner LangGraph workflow."""
    
    # Initialize the graph with our state schema
    workflow = StateGraph(TradingState)
    
    # Add nodes (these are the workflow steps)
    workflow.add_node("update_daily_market_data", update_daily_market_data)
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
        print("Ask me about market conditions, trading strategies, or say 'update market data' to refresh data.")
        print("Type 'quit' to exit.\n")
        
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