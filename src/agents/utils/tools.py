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
async def update_technical_indicators(target_date: str = None, num_days: int = 1) -> str:
    """Calculate and update technical indicators for all stocks with sufficient data.
    
    This tool checks for existing technical indicators for the specified date(s) and calculates
    them if they don't exist. It processes stocks that have at least 200 days of data
    and calculates: 200-day SMA, 100-day SMA, 50-day SMA, 15-day EMA, and 8-day EMA.
    
    Args:
        target_date: Target date in YYYY-MM-DD format. If None, uses today's date.
        num_days: Number of preceding days to calculate indicators for (default: 1)
                  For example, if target_date is 2025-07-01 and num_days is 5,
                  it will calculate for the 5 trading days ending on 2025-07-01.
    
    Returns:
        A summary message indicating the results of the technical analysis update.
    """
    logger.info(f"Starting technical indicators update for target_date={target_date}, num_days={num_days}")
    
    # Parse and validate target_date
    if target_date is None:
        end_date = date.today()
    else:
        try:
            end_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return f"❌ Invalid date format. Please use YYYY-MM-DD format (e.g., '2025-07-01')."
    
    # Validate num_days
    if num_days < 1:
        return "❌ num_days must be at least 1."
    if num_days > 252:  # Limit to about 1 year of trading days
        return "❌ num_days cannot exceed 252 (about 1 year of trading days)."
    
    # Generate list of target dates (working backwards from end_date)
    target_dates = []
    current_date = end_date
    days_added = 0
    
    while days_added < num_days:
        # Only include weekdays (Monday=0, Sunday=6)
        if current_date.weekday() < 5:  # Monday to Friday
            target_dates.append(current_date)
            days_added += 1
        current_date -= timedelta(days=1)
    
    # Reverse to process chronologically (oldest first)
    target_dates.reverse()
    
    logger.info(f"Will calculate indicators for {len(target_dates)} dates: {target_dates[0]} to {target_dates[-1]}")

    try:
        # Get all symbols with sufficient data (at least 200 days)
        symbols_with_data = await db_manager.get_symbols_with_sufficient_data(min_days=200)
        
        if not symbols_with_data:
            return "❌ No symbols found with sufficient data (200+ days) for technical analysis."
        
        logger.info(f"Found {len(symbols_with_data)} symbols with sufficient data")
        
        symbols_processed = 0
        total_indicators_calculated = 0
        total_indicators_skipped = 0
        
        for idx, symbol in enumerate(symbols_with_data, 1):
            try:
                logger.info(f"[{idx}/{len(symbols_with_data)}] Processing {symbol}...")
                
                symbol_indicators_calculated = 0
                symbol_indicators_skipped = 0
                
                # Process each target date for this symbol
                for calc_date in target_dates:
                    try:
                        # Check if technical indicators already exist for this date
                        existing_indicators = await db_manager.get_existing_technical_indicators(symbol, calc_date)
                        
                        if existing_indicators:
                            logger.debug(f"{symbol}: Technical indicators already exist for {calc_date}")
                            symbol_indicators_skipped += 1
                            continue
                        
                        # Get market data for calculation (need extra days for 200-day SMA)
                        # We need data up to the calculation date, so get historical data
                        market_data = await db_manager.get_market_data_for_calculation_up_to_date(symbol, calc_date, days=250)
                        
                        if not validate_data_sufficiency(market_data, required_days=200):
                            logger.warning(f"{symbol}: Insufficient data for technical analysis on {calc_date}")
                            continue
                        
                        # Calculate technical indicators for this specific date
                        indicators = calculate_all_indicators(market_data, calc_date)
                        
                        # Only save if we have at least some indicators calculated
                        if any(value is not None for value in indicators.values()):
                            await db_manager.insert_technical_indicators(symbol, calc_date, indicators)
                            symbol_indicators_calculated += 1
                            logger.debug(f"{symbol}: Technical indicators calculated and saved for {calc_date}")
                        else:
                            logger.warning(f"{symbol}: No indicators could be calculated for {calc_date}")
                            
                    except Exception as e:
                        logger.error(f"Failed to process {symbol} for date {calc_date}: {e}")
                        continue
                
                total_indicators_calculated += symbol_indicators_calculated
                total_indicators_skipped += symbol_indicators_skipped
                
                logger.info(f"{symbol}: {symbol_indicators_calculated} calculated, {symbol_indicators_skipped} skipped")
                symbols_processed += 1
                
                # Log progress every 50 symbols
                if idx % 50 == 0:
                    progress_msg = f"Progress: {idx}/{len(symbols_with_data)} symbols processed"
                    logger.info(progress_msg)
                
            except Exception as e:
                logger.error(f"Failed to process technical indicators for {symbol}: {e}")
                continue
        
        success_msg = f"✅ Technical indicators update completed! Processed {symbols_processed} symbols across {len(target_dates)} dates. Calculated: {total_indicators_calculated}, Already existed: {total_indicators_skipped}."
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        error_msg = f"❌ Technical indicators update failed: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
async def get_technical_analysis(symbol: str, analysis_date: str = None) -> str:
    """Get technical analysis for a specific stock symbol.
    
    This tool retrieves technical indicators for a stock and provides
    a formatted analysis including moving averages and their relationship to the
    price on the specified date.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        analysis_date: Date for analysis in YYYY-MM-DD format. If None, uses today's date.
        
    Returns:
        Formatted technical analysis summary
    """
    logger.info(f"Getting technical analysis for {symbol} on date={analysis_date}")
    
    # Clean and validate symbol
    symbol = symbol.upper().strip()
    
    # Parse and validate analysis_date
    if analysis_date is None:
        target_date = date.today()
    else:
        try:
            target_date = datetime.strptime(analysis_date, "%Y-%m-%d").date()
        except ValueError:
            return f"❌ Invalid date format. Please use YYYY-MM-DD format (e.g., '2025-07-01')."
    
    try:
        # Get technical indicators for the specified date
        technical_data = await db_manager.get_existing_technical_indicators(symbol, target_date)
        
        if not technical_data:
            # Try previous trading day if it's a weekend or holiday
            check_date = target_date - timedelta(days=1)
            days_checked = 1
            
            # Look back up to 5 days to find the most recent technical data
            while not technical_data and days_checked <= 5:
                if check_date.weekday() < 5:  # Only check weekdays
                    technical_data = await db_manager.get_existing_technical_indicators(symbol, check_date)
                
                if not technical_data:
                    check_date -= timedelta(days=1)
                    days_checked += 1
            
            if not technical_data:
                return f"❌ No technical indicators found for {symbol} around {target_date}. Run the technical indicators update first for that date period."
        
        # Get market data for the analysis date to get the price
        # We need to find the market data for the exact date the technical indicators were calculated
        indicator_date = technical_data.date
        
        # Get market data around the indicator date
        market_data_list = await db_manager.get_market_data_for_calculation_up_to_date(symbol, indicator_date, days=5)
        
        if not market_data_list:
            return f"❌ No market data found for {symbol} around {indicator_date}."
        
        # Find the market data for the exact indicator date
        price_data = None
        for data in market_data_list:
            if data.date == indicator_date:
                price_data = data
                break
        
        if not price_data:
            # If we can't find exact date, use the most recent data
            price_data = market_data_list[-1]  # Most recent since list is ascending
        
        analysis_price = price_data.close
        
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
        summary += f"Analysis Date: {technical_data.date}\n"
        summary += f"Price on Analysis Date: ${round(analysis_price, 2)}\n\n"
        summary += get_technical_summary(indicators, analysis_price)
        
        # Add trend analysis
        summary += "\n🔍 TREND ANALYSIS:\n"
        if indicators['sma_200'] and indicators['sma_100'] and indicators['sma_50']:
            if analysis_price > indicators['sma_200']:
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
            if analysis_price > indicators['ema_15'] and indicators['ema_8'] > indicators['ema_15']:
                summary += "• Short-term momentum: 📈 BULLISH (price above EMAs, 8 > 15)\n"
            elif analysis_price < indicators['ema_15'] and indicators['ema_8'] < indicators['ema_15']:
                summary += "• Short-term momentum: 📉 BEARISH (price below EMAs, 8 < 15)\n"
            else:
                summary += "• Short-term momentum: ⚡ MIXED\n"
        
        # Add note if using data from a different date than requested
        if analysis_date is not None and technical_data.date != target_date:
            summary += f"\n📅 Note: Using technical indicators from {technical_data.date} "
            summary += f"(closest available data to requested date {target_date})\n"
        
        logger.info(f"Successfully generated technical analysis for {symbol} on {technical_data.date}")
        return summary
        
    except Exception as e:
        error_msg = f"❌ Failed to get technical analysis for {symbol}: {str(e)}"
        logger.error(error_msg)
        return error_msg
