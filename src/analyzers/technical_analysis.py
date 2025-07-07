"""
Technical Analysis Module for Day Trading Assistant

This module provides functions to calculate various technical indicators
including Simple Moving Averages (SMA) and Exponential Moving Averages (EMA).
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import date

# Add database import
from src.utils.database import db_manager

logger = logging.getLogger(__name__)


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average for a given period.
    
    Args:
        prices: List of prices (most recent price should be last)
        period: Number of periods for the moving average
        
    Returns:
        SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
    
    # Take the last 'period' prices and calculate average
    recent_prices = prices[-period:]
    return round(sum(recent_prices) / len(recent_prices), 2)


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average for a given period.
    
    Args:
        prices: List of prices (most recent price should be last)
        period: Number of periods for the moving average
        
    Returns:
        EMA value or None if insufficient data
    """
    if len(prices) < period:
        return None
    
    # Calculate smoothing factor (alpha)
    alpha = 2.0 / (period + 1)
    
    # Initialize EMA with first price
    ema = prices[0]
    
    # Calculate EMA iteratively
    for price in prices[1:]:
        ema = alpha * price + (1 - alpha) * ema
    
    return round(ema, 2)

def calculate_real_relative_strength_daily(market_data: List, target_date: date) -> Dict[str, Optional[float]]:
    """Calculate Real Relative Strength over multiple periods up to a target date. Compare with SPY as benchmark.
    
    Args:
        market_data: List of OHLC market data records (should be sorted by date ascending) with enough data for 20 trading days
        target_date: The date for which to calculate indicators
        
    Returns:
        Dictionary containing real relative strength for a 1 day period, 8 day period, 15 day period
    """
    try:
        if not market_data:
            logger.warning("No market data provided for RRS calculation")
            return {'rrs_1_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
        
        # Convert to pandas DataFrame for easier manipulation
        df = pd.DataFrame([{
            'date': record.date.isoformat(),
            'close': record.close,
            'open': record.open,
            'high': record.high,
            'low': record.low,
            'volume': record.volume
        } for record in market_data])
        
        # Ensure data is sorted by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Convert target_date to string for comparison
        target_date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        
        # Find the row for the target date
        target_row = df[df['date'] == target_date_str]
        if target_row.empty:
            logger.warning(f"No data found for target date {target_date_str}")
            return {'rrs_1_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
        
        target_index = target_row.index[0]
        
        # Get data up to and including the target date
        symbol_data = df.loc[:target_index].copy()
        
        # Need at least 20 days for the longest calculation (15 + some buffer)
        if len(symbol_data) < 20:
            logger.warning(f"Insufficient data for RRS calculation: {len(symbol_data)} days available, 20+ required")
            return {'rrs_1_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
        
        # Get SPY data from database
        import asyncio
        
        async def get_spy_data():
            return await db_manager.get_market_data_for_calculation_up_to_date("SPY", target_date, days=len(symbol_data))
        
        # Run async function - handle existing event loop
        try:
            # Try to get existing loop
            asyncio.get_running_loop()
            # If there's already a loop running, we need to create a task
            # But since we're in a sync function, we'll use run_until_complete
            # Create new loop for this operation
            spy_market_data = asyncio.run(get_spy_data())
        except RuntimeError:
            # No loop running, safe to create one
            spy_market_data = asyncio.run(get_spy_data())
            
        if not spy_market_data:
            logger.error("Could not retrieve SPY data for RRS calculation")
            return {'rrs_1_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
        
        # Convert SPY data to DataFrame
        spy_df = pd.DataFrame([{
            'date': record.date.isoformat(),
            'close': record.close,
            'open': record.open,
            'high': record.high,
            'low': record.low,
            'volume': record.volume
        } for record in spy_market_data])
        
        spy_df = spy_df.sort_values('date').reset_index(drop=True)
        
        # Align SPY data with symbol data by date
        spy_aligned = spy_df[spy_df['date'].isin(symbol_data['date'])].copy()
        spy_aligned = spy_aligned.sort_values('date').reset_index(drop=True)
        
        if len(spy_aligned) != len(symbol_data):
            logger.warning(f"SPY data length ({len(spy_aligned)}) doesn't match symbol data length ({len(symbol_data)})")
            # Try to proceed with available data
            min_length = min(len(spy_aligned), len(symbol_data))
            spy_aligned = spy_aligned.tail(min_length).reset_index(drop=True)
            symbol_data = symbol_data.tail(min_length).reset_index(drop=True)
        
        # Calculate RRS for each period
        results = {}
        periods = [1, 8, 15]
        
        for period in periods:
            rrs_value = _calculate_rrs_for_period(symbol_data, spy_aligned, period)
            results[f'rrs_{period}_day'] = rrs_value
            
        return results
        
    except Exception as e:
        logger.error(f"Error calculating Real Relative Strength: {e}")
        return {'rrs_1_day': None, 'rrs_8_day': None, 'rrs_15_day': None}


def _calculate_rrs_for_period(symbol_data: pd.DataFrame, spy_data: pd.DataFrame, period: int) -> Optional[float]:
    """Calculate RRS for a specific period following the ThinkScript logic."""
    try:
        if len(symbol_data) < period + 1 or len(spy_data) < period + 1:
            return None
            
        # Calculate rolling price changes
        symbol_rolling_move = symbol_data['close'].iloc[-1] - symbol_data['close'].iloc[-(period + 1)]
        spy_rolling_move = spy_data['close'].iloc[-1] - spy_data['close'].iloc[-(period + 1)]
        
        # Calculate True Range for both symbols
        symbol_tr = _calculate_true_range(symbol_data)
        spy_tr = _calculate_true_range(spy_data)
        
        # Calculate Wilder's Average (ATR) using the period
        symbol_atr = _calculate_wilders_average(symbol_tr, period)
        spy_atr = _calculate_wilders_average(spy_tr, period)
        
        if symbol_atr is None or spy_atr is None or spy_atr == 0 or symbol_atr == 0:
            return None
            
        # Calculate RRS components following ThinkScript logic
        power_index = spy_rolling_move / spy_atr
        expected_move = power_index * symbol_atr
        diff = symbol_rolling_move - expected_move
        rrs = diff / symbol_atr
        
        return round(rrs, 4)
        
    except Exception as e:
        logger.error(f"Error calculating RRS for period {period}: {e}")
        return None


def _calculate_true_range(data: pd.DataFrame) -> pd.Series:
    """Calculate True Range for OHLC data."""
    try:
        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Previous close (shift by 1)
        prev_close = close.shift(1)
        
        # Calculate the three components
        hl = high - low
        hc = np.abs(high - prev_close)
        lc = np.abs(low - prev_close)
        
        # True Range is the maximum of the three
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        
        return tr
        
    except Exception as e:
        logger.error(f"Error calculating True Range: {e}")
        return pd.Series()


def _calculate_wilders_average(data: pd.Series, period: int) -> Optional[float]:
    """Calculate Wilder's Average (smoothed moving average) for the given period."""
    try:
        if len(data) < period or data.isna().all():
            return None
            
        # Remove NaN values
        clean_data = data.dropna()
        
        if len(clean_data) < period:
            return None
            
        # Wilder's Average uses exponential smoothing with alpha = 1/period
        alpha = 1.0 / period
        
        # Initialize with simple average of first 'period' values
        initial_avg = clean_data.iloc[:period].mean()
        
        # Apply exponential smoothing for remaining values
        result = initial_avg
        for i in range(period, len(clean_data)):
            result = alpha * clean_data.iloc[i] + (1 - alpha) * result
            
        return result
        
    except Exception as e:
        logger.error(f"Error calculating Wilder's Average: {e}")
        return None

def calculate_all_indicators(market_data: List, target_date: date) -> Dict[str, Optional[float]]:
    """Calculate all required technical indicators for a given dataset.
    
    Args:
        market_data: List of market data records (should be sorted by date ascending)
        target_date: The date for which to calculate indicators
        
    Returns:
        Dictionary containing all calculated indicators
    """
    try:
        # Convert to pandas DataFrame for easier manipulation
        if not market_data:
            logger.warning("No market data provided for technical analysis")
            return _get_empty_indicators()
        
        # Create DataFrame from market data
        df = pd.DataFrame([{
            'date': record.date.isoformat(),
            'close': record.close,
            'open': record.open,
            'high': record.high,
            'low': record.low,
            'volume': record.volume
        } for record in market_data])
        
        # Ensure data is sorted by date
        df = df.sort_values('date').reset_index(drop=True)

        # Convert target_date to string for comparison (since dates are stored as ISO strings)
        target_date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)

        # Find the row for the target date
        target_row = df[df['date'] == target_date_str]

        if target_row.empty:
            logger.warning(f"No data found for target date {target_date_str}")
            return _get_empty_indicators()
        
        target_index = target_row.index[0]

        # Get prices up to and including the target date
        prices_up_to_target = df.loc[:target_index, 'close'].tolist()

        # Calculate all indicators
        indicators = {}
        
        # Simple Moving Averages
        indicators['sma_200'] = calculate_sma(prices_up_to_target, 200)
        indicators['sma_100'] = calculate_sma(prices_up_to_target, 100)
        indicators['sma_50'] = calculate_sma(prices_up_to_target, 50)
        
        # Exponential Moving Averages
        indicators['ema_15'] = calculate_ema(prices_up_to_target, 15)
        indicators['ema_8'] = calculate_ema(prices_up_to_target, 8)
        
        # Real Relative Strength indicators
        rrs_indicators = calculate_real_relative_strength_daily(market_data, target_date)
        indicators.update(rrs_indicators)
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {e}")
        return _get_empty_indicators()


def _get_empty_indicators() -> Dict[str, Optional[float]]:
    """Return empty indicators dictionary."""
    return {
        'sma_200': None,
        'sma_100': None,
        'sma_50': None,
        'ema_15': None,
        'ema_8': None,
        'rrs_1_day': None,
        'rrs_8_day': None,
        'rrs_15_day': None
    }


def validate_data_sufficiency(market_data: List, required_days: int = 200) -> bool:
    """Validate that we have sufficient data for technical analysis.
    
    Args:
        market_data: List of market data records
        required_days: Minimum number of days required
        
    Returns:
        True if sufficient data, False otherwise
    """
    if not market_data:
        return False
    
    if len(market_data) < required_days:
        logger.warning(f"Insufficient data: {len(market_data)} days available, "
                      f"{required_days} days required")
        return False
    
    return True


def get_technical_summary(indicators: Dict[str, Optional[float]], current_price: float) -> str:
    """Generate a human-readable summary of technical indicators.
    
    Args:
        indicators: Dictionary of calculated indicators
        current_price: Current stock price
        
    Returns:
        Formatted summary string
    """
    summary = f"Technical Analysis Summary (Current Price: ${current_price:.2f}):\n\n"
    
    summary += "📊 SIMPLE MOVING AVERAGES:\n"
    for period in [200, 100, 50]:
        key = f'sma_{period}'
        if indicators[key] is not None:
            value = indicators[key]
            diff = current_price - value
            percent_diff = (diff / value) * 100
            position = "above" if diff > 0 else "below"
            summary += f"• {period}-day SMA: ${value:.2f} "
            summary += f"(Price is {percent_diff:+.1f}% {position})\n"
        else:
            summary += f"• {period}-day SMA: N/A (insufficient data)\n"
    
    summary += "\n📈 EXPONENTIAL MOVING AVERAGES:\n"
    for period in [15, 8]:
        key = f'ema_{period}'
        if indicators[key] is not None:
            value = indicators[key]
            diff = current_price - value
            percent_diff = (diff / value) * 100
            position = "above" if diff > 0 else "below"
            summary += f"• {period}-day EMA: ${value:.2f} "
            summary += f"(Price is {percent_diff:+.1f}% {position})\n"
        else:
            summary += f"• {period}-day EMA: N/A (insufficient data)\n"
    
    summary += "\n📊 REAL RELATIVE STRENGTH (vs SPY):\n"
    for period in [1, 8, 15]:
        key = f'rrs_{period}_day'
        if indicators[key] is not None:
            value = indicators[key]
            strength = "Strong" if abs(value) > 2 else "Moderate" if abs(value) > 1 else "Weak"
            direction = "Outperforming" if value > 0 else "Underperforming"
            summary += f"• {period}-day RRS: {value:.4f} ({strength} {direction})\n"
        else:
            summary += f"• {period}-day RRS: N/A (insufficient data)\n"
    
    return summary 