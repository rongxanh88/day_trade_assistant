"""
RRS Screener Tool for LangGraph-based trading assistant.
Provides interactive screening for stocks with relative strength indicators.
"""

import logging
from typing import Dict, List, Optional, Annotated
from typing_extensions import TypedDict
from datetime import datetime
from sqlalchemy import text

from langgraph.graph.message import add_messages
from src.utils.database import db_manager

logger = logging.getLogger(__name__)


class RRSScreeningState(TypedDict):
    """State for RRS screening workflow"""
    messages: Annotated[list, add_messages]
    
    # Screening Parameters
    rrs_timeframes: Optional[List[str]]  # ['1_day', '3_day', '8_day', '15_day']
    rrs_thresholds: Optional[Dict[str, float]]  # example: {'1_day': 0.5, '3_day': 0.3}
    
    # Additional Filters - TODO: Add these
    
    # Workflow State
    screening_status: Optional[str]  # 'pending_params', 'collecting', 'executing', 'completed', 'error'
    current_parameter: Optional[str]  # Which parameter we're currently collecting
    
    # Results
    screening_query: Optional[str]
    screening_results: Optional[List[Dict]]
    result_count: Optional[int]


class RRSScreenerTool:
    """Interactive RRS screening tool with human-in-the-loop parameter collection"""
    
    def __init__(self):
        self.default_thresholds = {
            '1_day': 0.0,
            '3_day': 0.0, 
            '8_day': 0.0,
            '15_day': 0.0
        }
        self.valid_timeframes = self.default_thresholds.keys()
    
    def get_tool_description(self) -> str:
        """Return tool description for LLM binding"""
        return """
        Screen stocks based on Real Relative Strength (RRS) indicators.
        This tool guides you through setting up screening criteria and executes
        SQL queries to find stocks with relative strength patterns.
        
        Available RRS timeframes:
        - 1_day: Very short-term momentum
        - 3_day: Short-term strength
        - 8_day: Medium-term strength  
        - 15_day: Longer-term strength
        """
    
    def collect_timeframes(self, state: RRSScreeningState) -> Dict:
        """Collect RRS timeframes from user"""
        return {
            "messages": [{
                "role": "assistant",
                "content": """
🎯 **RRS Stock Screener**

I'll help you find stocks with relative strength! Let's start by selecting timeframes.

**Available RRS Timeframes:**
• `1_day` - Very short-term momentum (intraday strength)
• `3_day` - Short-term strength (3-day trend)
• `8_day` - Medium-term strength (1-2 week trend)
• `15_day` - Longer-term strength (3-week trend)

**How to specify:**
• Single timeframe: `1_day` or `8_day`
• Multiple timeframes: `1_day,3_day,8_day`
• All timeframes: `all`

Which timeframes would you like to screen for?
                """
            }],
            "screening_status": "collecting",
            "current_parameter": "timeframes"
        }
    
    def collect_thresholds(self, state: RRSScreeningState) -> Dict:
        """Collect RRS thresholds from user"""
        timeframes_str = ', '.join(state['rrs_timeframes'])
        
        return {
            "messages": [{
                "role": "assistant", 
                "content": f"""
📊 **RRS Threshold Selection**

Selected timeframes: {timeframes_str}

**RRS Threshold Guide:**
• `0.0` - Any relative strength (outperforming market baseline)
• `0.5` - Moderate relative strength 
• `1.0` - Strong relative strength
• `2.0` - Very strong relative strength
• `3.0+` - Exceptional relative strength

**How to specify:**
• Same threshold for all: `1.0`
• Different per timeframe: `1_day:1.5,3_day:1.0,8_day:0.5`

What RRS threshold(s) would you like to use?
                """
            }],
            "screening_status": "collecting",
            "current_parameter": "thresholds"
        }
    
    
    def parse_user_input(self, user_input: str, parameter: str, state: RRSScreeningState) -> Dict:
        """Parse user input based on current parameter being collected"""
        
        try:
            if parameter == "timeframes":
                return self._parse_timeframes(user_input)
            elif parameter == "thresholds":
                return self._parse_thresholds(user_input, state['rrs_timeframes'])
            else:
                return {"error": f"Unknown parameter: {parameter}"}
                
        except Exception as e:
            logger.error(f"Error parsing user input for {parameter}: {e}")
            return {"error": f"Error parsing {parameter}: {str(e)}"}
    
    def _parse_timeframes(self, user_input: str) -> Dict:
        """Parse timeframe input"""
        user_input = user_input.strip().lower()
        
        if user_input == 'all':
            timeframes = self.valid_timeframes.copy()
        else:
            # Split by comma and clean up
            timeframes = [tf.strip() for tf in user_input.split(',')]
            
            # Validate timeframes
            invalid_timeframes = [tf for tf in timeframes if tf not in self.valid_timeframes]
            if invalid_timeframes:
                return {
                    "error": f"Invalid timeframes: {invalid_timeframes}. Valid options: {self.valid_timeframes}"
                }
        
        return {"rrs_timeframes": timeframes}
    
    def _parse_thresholds(self, user_input: str, timeframes: List[str]) -> Dict:
        """Parse threshold input"""
        user_input = user_input.strip()
        
        # Check if single threshold for all timeframes
        try:
            threshold = float(user_input)
            thresholds = {tf: threshold for tf in timeframes}
            return {"rrs_thresholds": thresholds}
        except ValueError:
            pass
        
        # Parse individual timeframe thresholds
        try:
            thresholds = {}
            pairs = user_input.split(',')
            
            for pair in pairs:
                if ':' in pair:
                    tf, threshold_str = pair.split(':', 1)
                    tf = tf.strip()
                    threshold = float(threshold_str.strip())
                    
                    if tf not in timeframes:
                        return {"error": f"Timeframe '{tf}' not in selected timeframes: {timeframes}"}
                    
                    thresholds[tf] = threshold
                else:
                    return {"error": "Invalid threshold format. Use 'timeframe:threshold' or single value"}
            
            # Fill missing timeframes with default - do not fill in missing timeframes
            # for tf in timeframes:
            #     if tf not in thresholds:
            #         thresholds[tf] = 0.0
            
            return {"rrs_thresholds": thresholds}
            
        except ValueError as e:
            return {"error": f"Invalid threshold value: {str(e)}"}
    
    def build_screening_query(self, state: RRSScreeningState) -> Dict:
        """Build SQL query based on screening parameters"""
        
        try:
            thresholds = state['rrs_thresholds']
            timeframes = thresholds.keys()
            logic = 'AND'
            
            # Base query
            base_query = """
            SELECT 
                t.symbol, 
                t.date,
                t.rrs_1_day, 
                t.rrs_3_day, 
                t.rrs_8_day, 
                t.rrs_15_day,
                m.close as current_price,
                t.relative_volume,
                t.sma_50,
                t.sma_100,
                t.sma_200,
                t.ema_15,
                t.ema_8,
            FROM technical_indicators t
            INNER JOIN daily_market_data m ON t.symbol = m.symbol AND t.date = m.date
            WHERE t.date = (
                SELECT MAX(date) 
                FROM technical_indicators 
                WHERE rrs_1_day IS NOT NULL
            )
            """
            
            # Build RRS conditions
            rrs_conditions = []
            for timeframe in timeframes:
                threshold = thresholds.get(timeframe, 0.0)
                rrs_field = f"t.rrs_{timeframe}"
                rrs_conditions.append(f"{rrs_field} > {threshold}")
            
            # Combine RRS conditions with AND/OR logic
            rrs_clause = f" {logic} ".join(rrs_conditions)
            
            # Additional filters
            additional_filters = [
                "t.rrs_1_day IS NOT NULL"  # Ensure we have data
            ]
            
            # Complete query
            final_query = f"""
            {base_query}
            AND ({rrs_clause})
            AND {' AND '.join(additional_filters)}
            ORDER BY t.rrs_1_day DESC
            """
            
            return {
                "screening_query": final_query.strip(),
                "screening_status": "query_built"
            }
            
        except Exception as e:
            logger.error(f"Error building screening query: {e}")
            return {
                "screening_status": "error",
                "error": f"Error building query: {str(e)}"
            }
    
    async def execute_screening(self, state: RRSScreeningState) -> Dict:
        """Execute the screening query and return results"""
        
        try:
            query = state['screening_query']
            logger.info(f"Executing RRS screening query: {query[:200]}...")
            
            async with db_manager.async_session() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                
                # Format results
                results = []
                for row in rows:
                    results.append({
                        "symbol": row.symbol,
                        "date": str(row.date),
                        "rrs_scores": {
                            "1_day": round(row.rrs_1_day or 0, 3),
                            "3_day": round(row.rrs_3_day or 0, 3),
                            "8_day": round(row.rrs_8_day or 0, 3),
                            "15_day": round(row.rrs_15_day or 0, 3)
                        },
                        "price_data": {
                            "current_price": round(row.current_price, 2),
                            "relative_volume": round(row.relative_volume or 0, 2)
                        },
                        "technical_status": {
                            "sma_50": round(row.sma_50 or 0, 2),
                            "sma_100": round(row.sma_100 or 0, 2),
                            "sma_200": round(row.sma_200 or 0, 2),
                            "ema_8": round(row.ema_8 or 0, 2),
                            "ema_15": round(row.ema_15 or 0, 2)
                        }
                    })
                
                return {
                    "screening_results": results,
                    "result_count": len(results),
                    "screening_status": "completed"
                }
                
        except Exception as e:
            logger.error(f"Error executing screening query: {e}")
            return {
                "screening_status": "error",
                "error": f"Database error: {str(e)}"
            }
    
    def format_results(self, state: RRSScreeningState) -> Dict:
        """Format screening results for display"""
        
        results = state.get('screening_results', [])
        result_count = state.get('result_count', 0)
        
        if result_count == 0:
            return {
                "messages": [{
                    "role": "assistant",
                    "content": """
🔍 **No Results Found**

No stocks matched your screening criteria. Consider:
• Lowering the RRS thresholds
• Checking different timeframes

Would you like to adjust your criteria and try again?
                    """
                }]
            }
        
        # Create summary message
        summary_msg = f"""
📈 **RRS Screening Results**

Found **{result_count}** stocks matching your criteria:

**Screening Parameters:**
• Timeframes: {', '.join(state['rrs_timeframes'])}
• Thresholds: {dict(state['rrs_thresholds'])}

**Top Results:**
"""
        
        # Add results table
        summary_msg += "\n| Symbol | RRS 1D | RRS 3D | RRS 8D | RRS 15D | Price | RelVol |\n"
        summary_msg += "|--------|--------|--------|--------|---------|-------|--------|\n"
        
        # Show top 15 results
        display_count = min(15, len(results))
        for i in range(display_count):
            stock = results[i]
            rrs = stock['rrs_scores']
            price = stock['price_data']
            
            summary_msg += f"| **{stock['symbol']}** | "
            summary_msg += f"{rrs['1_day']:.2f} | {rrs['3_day']:.2f} | "
            summary_msg += f"{rrs['8_day']:.2f} | {rrs['15_day']:.2f} | "
            summary_msg += f"${price['current_price']:.2f} | "
            summary_msg += f"{price['relative_volume']:.1f}x | "
        
        if result_count > display_count:
            summary_msg += f"\n*Showing top {display_count} of {result_count} total results*"
        
        summary_msg += "\n\n💡 **Next Steps:**\n"
        summary_msg += "• Review these stocks for potential setups\n"
        summary_msg += "• Check charts for entry/exit points\n" 
        summary_msg += "• Consider risk management for selected stocks\n"
        summary_msg += "• Run screening again with different parameters if needed"
        
        return {
            "messages": [{
                "role": "assistant",
                "content": summary_msg
            }]
        }


# Tool instance for use in LangGraph workflows
rrs_screener_tool = RRSScreenerTool()
