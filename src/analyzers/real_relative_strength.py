"""
Real Relative Strength (RRS) Calculation Module

This module provides the Real Relative Strength calculation functionality
that compares a symbol's performance against SPY (S&P 500 ETF) benchmark.
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import date

logger = logging.getLogger(__name__)


def calculate_real_relative_strength_daily(
    market_data: List, 
    spy_data: List, 
    target_date: date
) -> Dict[str, Optional[float]]:
    """Calculate Real Relative Strength over multiple periods up to a target date. Compare with SPY as benchmark.
    
    Args:
        market_data: List of OHLC market data records for the symbol (sorted by date ascending)
        spy_data: List of OHLC market data records for SPY (sorted by date ascending)
        target_date: The date for which to calculate indicators
        
    Returns:
        Dictionary containing real relative strength for 1 day, 8 day, and 15 day periods
    """
    default_rrs_values = {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}

    try:

        if not market_data:
            logger.warning("No market data provided for RRS calculation")
            return default_rrs_values
        
        if not spy_data:
            logger.warning("No SPY data provided for RRS calculation")
            return default_rrs_values
        
        # Convert to pandas DataFrames for easier manipulation
        symbol_df = _convert_to_dataframe(market_data)
        spy_df = _convert_to_dataframe(spy_data)
        
        # Ensure data is sorted by date
        symbol_df = symbol_df.sort_values('date').reset_index(drop=True)
        spy_df = spy_df.sort_values('date').reset_index(drop=True)
        
        # Convert target_date to string for comparison
        target_date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
        
        # Find the row for the target date in symbol data
        target_row = symbol_df[symbol_df['date'] == target_date_str]
        if target_row.empty:
            logger.warning(f"No data found for target date {target_date_str}")
            return default_rrs_values
        
        target_index = target_row.index[0]
        
        # Get data up to and including the target date
        symbol_data = symbol_df.loc[:target_index].copy()
        
        # Need at least 20 days for the longest calculation (15 + some buffer)
        if len(symbol_data) < 20:
            logger.warning(f"Insufficient symbol data for RRS calculation: {len(symbol_data)} days available, 20+ required")
            return default_rrs_values
        
        # Align SPY data with symbol data by date
        spy_aligned = spy_df[spy_df['date'].isin(symbol_data['date'])].copy()
        spy_aligned = spy_aligned.sort_values('date').reset_index(drop=True)
        
        if len(spy_aligned) < 20:
            logger.warning(f"Insufficient SPY data for RRS calculation: {len(spy_aligned)} days available, 20+ required")
            return default_rrs_values
        
        # Ensure both datasets have the same length by taking the overlap
        min_length = min(len(spy_aligned), len(symbol_data))
        if min_length < 20:
            logger.warning(f"Insufficient overlapping data for RRS calculation: {min_length} days available")
            return default_rrs_values
        
        spy_aligned = spy_aligned.tail(min_length).reset_index(drop=True)
        symbol_data = symbol_data.tail(min_length).reset_index(drop=True)
        
        # Calculate RRS for each period
        results = {}
        periods = [1, 3, 8, 15]
        
        for period in periods:
            rrs_value = calculate_rrs_for_period(symbol_data, spy_aligned, period)
            results[f'rrs_{period}_day'] = rrs_value
            
        return results
        
    except Exception as e:
        logger.error(f"Error calculating Real Relative Strength: {e}")
        return default_rrs_values


def _convert_to_dataframe(market_data: List) -> pd.DataFrame:
    """Convert market data list to pandas DataFrame."""
    return pd.DataFrame([{
        'date': record.date.isoformat() if hasattr(record.date, 'isoformat') else str(record.date),
        'close': record.close,
        'open': record.open,
        'high': record.high,
        'low': record.low,
        'volume': record.volume
    } for record in market_data])


def calculate_rrs_for_period(symbol_data: pd.DataFrame, spy_data: pd.DataFrame, period: int) -> Optional[float]:
    """Calculate RRS for a specific period following the ThinkScript logic."""
    try:
        # Always use 14 days for ATR calculation, but need enough data for both price changes and ATR
        atr_period = 14
        min_required_days = max(period + 1, atr_period + 1)
        
        if len(symbol_data) < min_required_days or len(spy_data) < min_required_days:
            return None
            
        # Calculate rolling price changes using the specified period
        symbol_rolling_move = symbol_data['close'].iloc[-1] - symbol_data['close'].iloc[-(period + 1)]
        spy_rolling_move = spy_data['close'].iloc[-1] - spy_data['close'].iloc[-(period + 1)]
        
        # Calculate True Range for both symbols
        symbol_tr = calculate_true_range(symbol_data)
        spy_tr = calculate_true_range(spy_data)
        
        # Calculate Wilder's Average (ATR) using fixed 14-day period
        symbol_atr = calculate_wilders_average(symbol_tr, atr_period)
        spy_atr = calculate_wilders_average(spy_tr, atr_period)
        
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


def calculate_true_range(data: pd.DataFrame) -> pd.Series:
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


def calculate_wilders_average(data: pd.Series, period: int) -> Optional[float]:
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