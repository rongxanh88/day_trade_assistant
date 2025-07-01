import logging
from datetime import datetime, date, timedelta
from langchain_core.tools import tool

from config.sp500_symbols import get_sp500_symbols
from src.integrations.tradier_client import tradier_client
from src.utils.database import db_manager

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
