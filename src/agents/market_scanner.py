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
# from config.settings import settings


logger = logging.getLogger(__name__)


# LangGraph node functions
async def update_daily_market_data(state: TradingState) -> TradingState:
    """
    Update daily market data for watchlist symbols.
    
    Checks database for missing data in the past year and fetches from Tradier API if needed.
    """
    logger.info("Starting daily market data update...")
    
    # Default watchlist - in production this would come from user preferences
    default_watchlist = ["SPY", "QQQ", "IWM", "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    
    # Calculate date range for the past year
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    updated_state = state.copy()
    updated_state["workflow_status"] = "updating_market_data"
    updated_state["messages"].append({
        "timestamp": datetime.now(),
        "type": "info",
        "message": f"Starting market data update for {len(default_watchlist)} symbols"
    })
    
    try:
        symbols_updated = 0
        total_records_fetched = 0
        
        for symbol in default_watchlist:
            try:
                logger.info(f"Checking market data for {symbol}...")
                
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
            "message": f"Market data update completed. {symbols_updated} symbols processed, {total_records_fetched} new records fetched."
        })
        
        logger.info(f"Market data update completed successfully. {total_records_fetched} new records fetched.")
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


async def notify_user(state: TradingState) -> TradingState:
    """
    Notify user of workflow completion and results.
    """
    logger.info("Notifying user of workflow completion...")
    
    updated_state = state.copy()
    
    # Create summary message
    if state["workflow_status"] == "market_data_updated":
        summary = "✅ Market data update completed successfully!"
        if state["messages"]:
            latest_message = state["messages"][-1]
            if latest_message.get("type") == "success":
                summary += f"\n{latest_message['message']}"
    else:
        summary = "❌ Market data update encountered issues."
        if state.get("last_error"):
            summary += f"\nError: {state['last_error']}"
    
    updated_state["workflow_status"] = "completed"
    updated_state["messages"].append({
        "timestamp": datetime.now(),
        "type": "notification",
        "message": summary
    })
    
    # In a real application, this would send notifications via:
    # - Email
    # - Slack/Discord webhook
    # - Push notifications
    # - WebSocket to frontend
    logger.info(f"User notification: {summary}")
    
    return updated_state


# Conditional routing functions
# def should_continue_scanning(state: TradingState) -> str:
#     """Decide whether to continue based on market hours."""
#     if state.get("workflow_status") == "market_closed":
#         return "wait"
#     elif state.get("last_error"):
#         return "error"
#     else:
#         return "scan"


# def route_after_scan(state: TradingState) -> str:
#     """Route based on scan results."""
#     status = state.get("workflow_status")
#     if status == "setups_found":
#         return "review"
#     elif status == "no_setups":
#         return "complete"
#     else:
#         return "error"


# def route_after_review(state: TradingState) -> str:
#     """Route based on review results."""
#     status = state.get("workflow_status")
#     if status == "setups_approved":
#         return "alert"
#     elif status == "no_review_needed":
#         return "complete"
#     else:
#         return "wait_for_human"


# Build the LangGraph workflow
def create_market_scanner_graph() -> StateGraph:
    """Create the market scanner LangGraph workflow."""
    
    # Initialize the graph with our state schema
    workflow = StateGraph(TradingState)
    
    # Add nodes (these are the workflow steps)
    workflow.add_node("update_daily_market_data", update_daily_market_data)
    workflow.add_node("notify_user", notify_user)
    # workflow.add_node("check_market", check_market_hours)
    # workflow.add_node("fetch_data", fetch_watchlist_data)
    # workflow.add_node("scan_setups", scan_for_setups)
    # workflow.add_node("review_setups", review_setups)
    # workflow.add_node("send_alerts", send_alerts)
    
    # Add edges (workflow routing)
    workflow.add_edge(START, "update_daily_market_data")
    
    # Conditional routing from market check
    # workflow.add_conditional_edges(
    #     "check_market",
    #     should_continue_scanning,
    #     {
    #         "scan": "fetch_data",
    #         "wait": END,
    #         "error": END
    #     }
    # )
    
    # Linear flow through scanning
    # workflow.add_edge("fetch_data", "scan_setups")
    
    # Conditional routing after scan
    # workflow.add_conditional_edges(
    #     "scan_setups",
    #     route_after_scan,
    #     {
    #         "review": "review_setups",
    #         "complete": END,
    #         "error": END
    #     }
    # )
    
    # Conditional routing after review
    # workflow.add_conditional_edges(
    #     "review_setups", 
    #     route_after_review,
    #     {
    #         "alert": "send_alerts",
    #         "complete": END,
    #         "wait_for_human": END  # In real app, this would pause
    #     }
    # )
    
    # End after alerts
    workflow.add_edge("notify_user", END)
    # workflow.add_edge("send_alerts", END)
    
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
        "last_error": None
    }
    
    return graph, initial_state


# Example usage function
async def run_market_scan_example():
    # Ensure database tables exist
    await db_manager.create_tables()

    """Example of how to run the market scanner."""
    logger.info("Starting market scanner example...")
    
    # Create the graph and initial state
    graph, initial_state = create_market_scanner()
    
    # Compile the graph
    app = graph.compile()
    
    try:
        # Run the workflow
        result = await app.ainvoke(initial_state)
        
        # # Print results
        # print("\n" + "="*50)
        # print("MARKET SCAN RESULTS")
        # print("="*50)
        
        # print(f"Workflow Status: {result['workflow_status']}")
        # print(f"Symbols Scanned: {', '.join(result['watchlist'])}")
        # print(f"Setups Found: {len(result['active_setups'])}")
        # print(f"Alerts Sent: {len(result['alerts_sent'])}")
        
        # if result['active_setups']:
        #     print("\nSETUPS FOUND:")
        #     for setup in result['active_setups']:
        #         print(f"  • {setup.symbol}: {setup.confidence_score:.1f}% confidence")
        #         print(f"    Entry: ${setup.entry_price:.2f} | Target: ${setup.target_price:.2f} | Stop: ${setup.stop_loss:.2f}")
        #         print(f"    Reasoning: {setup.reasoning}")
        #         print()
        
        # if result['alerts_sent']:
        #     print("ALERTS SENT:")
        #     for alert in result['alerts_sent']:
        #         print(f"  📱 {alert.symbol} - {alert.alert_level.value.upper()}")
        
        # print("="*50)
        return result
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_market_scan_example()) 