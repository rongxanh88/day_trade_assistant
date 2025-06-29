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
from datetime import datetime
from typing import Dict, List, Any

from langgraph.graph import StateGraph, END, START
from langchain_core.tools import tool

from src.data.models import (
    TradingState,
    SetupType, 
    TimeFrame, 
    AlertLevel,
    MarketCondition,
    Quote
)
from src.integrations.tradier_client import tradier_client
from config.settings import settings


logger = logging.getLogger(__name__)


# Tools for the LangGraph workflow
@tool
async def fetch_market_quotes(symbols: List[str]) -> Dict[str, Quote]:
    """Fetch real-time quotes for multiple symbols."""
    try:
        quotes = await tradier_client.get_quotes(symbols)
        logger.info(f"Fetched quotes for {len(quotes)} symbols")
        return quotes
    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")
        return {}


    """Get current market hours and status."""
    try:
        market_hours = await tradier_client.get_market_status()
        logger.info(f"Market status: open={market_hours.is_market_open}")
        return market_hours
    except Exception as e:
        logger.error(f"Failed to get market status: {e}")
        return None


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
    # workflow.add_node("check_market", check_market_hours)
    # workflow.add_node("fetch_data", fetch_watchlist_data)
    # workflow.add_node("scan_setups", scan_for_setups)
    # workflow.add_node("review_setups", review_setups)
    # workflow.add_node("send_alerts", send_alerts)
    
    # Add edges (workflow routing)
    # workflow.add_edge(START, "check_market")
    
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
        "preferred_strategies": [SetupType.MOMENTUM_BREAKOUT],
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