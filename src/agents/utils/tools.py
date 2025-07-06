import logging
from datetime import datetime, date, timedelta
from typing import List
from langchain_core.tools import tool

from config.sp500_symbols import get_sp500_symbols
from src.integrations.tradier_client import tradier_client
from src.utils.database import db_manager
from config.sp500_symbols import get_sp500_symbols
from src.analyzers.technical_analysis import calculate_all_indicators, validate_data_sufficiency, get_technical_summary

logger = logging.getLogger(__name__)


@tool
async def update_market_data() -> str:
    """Update S&P 500 market data by fetching missing daily data from the past year.
    
    This tool checks the database for missing market data and fetches it from the Tradier API.
    It processes all S&P 500 symbols and can take several minutes to complete.
    
    Returns:
        A summary message indicating the results of the update operation.
    """
    logger.info("Starting daily market data update via tool...")
    
    # Get complete S&P 500 symbols list
    sp500_symbols = get_sp500_symbols()
    
    if not sp500_symbols:
        error_msg = "No S&P 500 symbols found in configuration"
        logger.error(error_msg)
        return f"❌ {error_msg}"
    
    logger.info(f"Loaded {len(sp500_symbols)} S&P 500 symbols for market data update")
    
    # Calculate date range for the past year
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
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

                    logger.info(f"Fetching data for {symbol} from {missing_start} to {missing_end}")
                    
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
                
                # Log progress every 50 symbols
                if idx % 50 == 0:
                    progress_message = f"Progress: {idx}/{len(sp500_symbols)} symbols processed ({symbols_updated} updated, {total_records_fetched} records fetched)"
                    logger.info(progress_message)
                
            except Exception as e:
                logger.error(f"Failed to update market data for {symbol}: {e}")
                # Continue with other symbols instead of failing completely
                continue
        
        success_msg = f"✅ S&P 500 market data update completed successfully! Processed {symbols_updated}/{len(sp500_symbols)} symbols and fetched {total_records_fetched} new records."
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        error_msg = f"❌ Market data update failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
async def get_symbol_data(symbol: str, days: int = 50) -> str:
    """Retrieve recent market data for a specific stock symbol.
    
    This tool gets the most recent daily OHLCV (Open, High, Low, Close, Volume) data
    for a specific stock symbol from our database. Use this when the user asks about
    a specific stock or wants to analyze price movements, trends, or performance.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        days: Number of recent trading days to retrieve (default: 50, max: 252)
        
    Returns:
        Formatted string containing the market data and basic analysis summary
    """
    logger.info(f"Retrieving market data for {symbol} ({days} days)")
    
    # Clean and validate symbol
    symbol = symbol.upper().strip()
    
    # Limit days to reasonable range
    days = max(1, min(days, 252))  # 1 day to 1 year of trading days
    
    # Validate symbol is in our supported list
    sp500_symbols = get_sp500_symbols()
    if symbol not in sp500_symbols:
        return f"❌ Symbol '{symbol}' is not found in our S&P 500 database. Available symbols include major stocks like AAPL, MSFT, TSLA, etc."
    
    try:
        # Get market data from database
        market_data = await db_manager.get_recent_market_data(symbol, days)
        
        if not market_data:
            return f"❌ No market data found for {symbol}. Try running a market data update first."
        
        # Format the data for LLM context
        formatted_data = _format_market_data_for_context(market_data, symbol, days)
        
        logger.info(f"Successfully retrieved and formatted {len(market_data)} records for {symbol}")
        return formatted_data
        
    except Exception as e:
        error_msg = f"❌ Failed to retrieve data for {symbol}: {str(e)}"
        logger.error(error_msg)
        return error_msg

# TODO: Change the format of the data to be more accurate and useful for the LLM
def _format_market_data_for_context(market_data: List, symbol: str, requested_days: int) -> str:
    """Format market data for LLM context in a readable and analysis-friendly way."""
    
    if not market_data:
        return f"No data available for {symbol}"
    
    # Sort by date ascending for chronological analysis
    sorted_data = sorted(market_data, key=lambda x: x.date)
    latest_data = sorted_data[-1]  # Most recent
    oldest_data = sorted_data[0]   # Oldest in range
    
    # Calculate basic metrics
    latest_price = latest_data.close
    period_start_price = oldest_data.close
    price_change = latest_price - period_start_price
    price_change_pct = (price_change / period_start_price) * 100
    
    # Find period high/low
    period_high = max(data.high for data in market_data)
    period_low = min(data.low for data in market_data)
    
    # Calculate average volume
    avg_volume = sum(data.volume for data in market_data) / len(market_data)
    
    # Start building the formatted context
    context = f"""
📊 MARKET DATA FOR {symbol}
Period: {oldest_data.date} to {latest_data.date} ({len(market_data)} trading days)

💰 PRICE SUMMARY:
• Current Price: ${latest_price:.2f}
• Period Start: ${period_start_price:.2f}
• Change: ${price_change:+.2f} ({price_change_pct:+.1f}%)
• Period High: ${period_high:.2f}
• Period Low: ${period_low:.2f}
• Average Volume: {avg_volume:,.0f}

📈 RECENT DAILY DATA (Last 10 days):"""
    
    # Add last 10 days of detailed data
    recent_data = sorted_data[-10:]
    for data in reversed(recent_data):  # Most recent first
        daily_change = data.close - data.open
        daily_change_pct = (daily_change / data.open) * 100 if data.open != 0 else 0
        
        context += f"""
{data.date}: Open ${data.open:.2f} | High ${data.high:.2f} | Low ${data.low:.2f} | Close ${data.close:.2f} | Vol {data.volume:,} | Daily {daily_change:+.2f} ({daily_change_pct:+.1f}%)"""
    
    # Add analysis hints for the LLM
    context += f"""

🔍 KEY INSIGHTS:
• Volatility: Period range of ${period_high - period_low:.2f} ({((period_high - period_low) / period_low) * 100:.1f}% of low)
• Trend Direction: {'📈 Upward' if price_change > 0 else '📉 Downward' if price_change < 0 else '➡️ Sideways'}
• Recent Performance: {price_change_pct:+.1f}% over {len(market_data)} days

This data can be used to analyze trends, calculate technical indicators, assess volatility, and answer questions about {symbol}'s recent performance.
"""
    
    return context


@tool
async def update_technical_indicators() -> str:
    """Calculate and update technical indicators for all stocks with sufficient data.
    
    This tool checks for existing technical indicators for today's date and calculates
    them if they don't exist. It processes stocks that have at least 200 days of data
    and calculates: 200-day SMA, 100-day SMA, 50-day SMA, 15-day EMA, and 8-day EMA.
    
    Returns:
        A summary message indicating the results of the technical analysis update.
    """
    logger.info("Starting technical indicators update...")
    
    today = date.today()
    
    try:
        # Get all symbols with sufficient data (at least 200 days)
        symbols_with_data = await db_manager.get_symbols_with_sufficient_data(min_days=200)
        
        if not symbols_with_data:
            return "❌ No symbols found with sufficient data (200+ days) for technical analysis."
        
        logger.info(f"Found {len(symbols_with_data)} symbols with sufficient data")
        
        symbols_processed = 0
        symbols_updated = 0
        symbols_skipped = 0
        
        for idx, symbol in enumerate(symbols_with_data, 1):
            try:
                logger.info(f"[{idx}/{len(symbols_with_data)}] Processing {symbol}...")
                
                # Check if technical indicators already exist for today
                existing_indicators = await db_manager.get_existing_technical_indicators(symbol, today)
                
                if existing_indicators:
                    logger.info(f"{symbol}: Technical indicators already exist for {today}")
                    symbols_skipped += 1
                    continue
                
                # Get market data for calculation (need extra days for 200-day SMA)
                market_data = await db_manager.get_market_data_for_calculation(symbol, days=250)
                
                if not validate_data_sufficiency(market_data, required_days=200):
                    logger.warning(f"{symbol}: Insufficient data for technical analysis")
                    continue
                
                # Calculate technical indicators
                indicators = calculate_all_indicators(market_data, today)
                
                # Only save if we have at least some indicators calculated
                if any(value is not None for value in indicators.values()):
                    await db_manager.insert_technical_indicators(symbol, today, indicators)
                    symbols_updated += 1
                    logger.info(f"{symbol}: Technical indicators calculated and saved")
                else:
                    logger.warning(f"{symbol}: No indicators could be calculated")
                
                symbols_processed += 1
                
                # Log progress every 50 symbols
                if idx % 50 == 0:
                    progress_msg = f"Progress: {idx}/{len(symbols_with_data)} symbols processed ({symbols_updated} updated, {symbols_skipped} skipped)"
                    logger.info(progress_msg)
                
            except Exception as e:
                logger.error(f"Failed to process technical indicators for {symbol}: {e}")
                continue
        
        success_msg = f"✅ Technical indicators update completed! Processed {symbols_processed} symbols: {symbols_updated} updated, {symbols_skipped} already current."
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        error_msg = f"❌ Technical indicators update failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
async def get_technical_analysis(symbol: str) -> str:
    """Get technical analysis for a specific stock symbol.
    
    This tool retrieves the latest technical indicators for a stock and provides
    a formatted analysis including moving averages and their relationship to the
    current price.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        
    Returns:
        Formatted technical analysis summary
    """
    logger.info(f"Getting technical analysis for {symbol}")
    
    # Clean and validate symbol
    symbol = symbol.upper().strip()
    
    try:
        # Get the most recent technical indicators
        today = date.today()
        technical_data = await db_manager.get_existing_technical_indicators(symbol, today)
        
        if not technical_data:
            # Try previous trading day
            yesterday = today - timedelta(days=1)
            technical_data = await db_manager.get_existing_technical_indicators(symbol, yesterday)
            
            if not technical_data:
                return f"❌ No technical indicators found for {symbol}. Run the technical indicators update first."
        
        # Get current price from recent market data
        recent_data = await db_manager.get_recent_market_data(symbol, days=1)
        if not recent_data:
            return f"❌ No recent market data found for {symbol}."
        
        current_price = recent_data[0].close
        
        # Create indicators dictionary
        indicators = {
            'sma_200': technical_data.sma_200,
            'sma_100': technical_data.sma_100,
            'sma_50': technical_data.sma_50,
            'ema_15': technical_data.ema_15,
            'ema_8': technical_data.ema_8
        }
        
        # Generate technical summary
        summary = f"📊 TECHNICAL ANALYSIS FOR {symbol}\n"
        summary += f"Analysis Date: {technical_data.date}\n\n"
        summary += get_technical_summary(indicators, current_price)
        
        # Add trend analysis
        summary += "\n🔍 TREND ANALYSIS:\n"
        if indicators['sma_200'] and indicators['sma_100'] and indicators['sma_50']:
            if current_price > indicators['sma_200']:
                summary += "• Long-term trend: 📈 BULLISH (above 200-day SMA)\n"
            else:
                summary += "• Long-term trend: 📉 BEARISH (below 200-day SMA)\n"
            
            if indicators['sma_50'] > indicators['sma_100'] > indicators['sma_200']:
                summary += "• Moving average alignment: 📈 BULLISH (50 > 100 > 200)\n"
            elif indicators['sma_50'] < indicators['sma_100'] < indicators['sma_200']:
                summary += "• Moving average alignment: 📉 BEARISH (50 < 100 < 200)\n"
            else:
                summary += "• Moving average alignment: ⚡ MIXED\n"
        
        if indicators['ema_15'] and indicators['ema_8']:
            if current_price > indicators['ema_15'] and indicators['ema_8'] > indicators['ema_15']:
                summary += "• Short-term momentum: 📈 BULLISH (price above EMAs, 8 > 15)\n"
            elif current_price < indicators['ema_15'] and indicators['ema_8'] < indicators['ema_15']:
                summary += "• Short-term momentum: 📉 BEARISH (price below EMAs, 8 < 15)\n"
            else:
                summary += "• Short-term momentum: ⚡ MIXED\n"
        
        logger.info(f"Successfully generated technical analysis for {symbol}")
        return summary
        
    except Exception as e:
        error_msg = f"❌ Failed to get technical analysis for {symbol}: {str(e)}"
        logger.error(error_msg)
        return error_msg
