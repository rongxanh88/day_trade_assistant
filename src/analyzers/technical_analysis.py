"""
Technical Analysis Module for Day Trading Assistant

This module provides functions to calculate various technical indicators
including Simple Moving Averages (SMA) and Exponential Moving Averages (EMA).
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
from datetime import date
import numpy as np
import talib as ta

# Import RRS utility functions
from .real_relative_strength import calculate_real_relative_strength_daily
# Add database import for SPY data
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
    
    prices = np.array(prices)
    sma = ta.SMA(prices, timeperiod=period)
    return round(sma[-1], 2)


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
    
    prices = np.array(prices)
    ema = ta.EMA(prices, timeperiod=period)
    return round(ema[-1], 2)


def calculate_relative_volume(volumes: List[int], period: int = 20) -> Optional[float]:
    """Calculate Relative Volume for the current day against average volume.
    
    Args:
        volumes: List of volumes (most recent volume should be last)
        period: Number of periods to use for average calculation (default 20)
        
    Returns:
        Relative volume ratio or None if insufficient data
    """
    if len(volumes) < period + 1:  # Need period + 1 for current day + historical average
        return None
    
    # Current day volume (last in the list)
    current_volume = volumes[-1]
    
    # Previous 'period' days volumes (excluding current day)
    historical_volumes = volumes[-(period + 1):-1]
    
    # Calculate average of historical volumes
    average_volume = sum(historical_volumes) / len(historical_volumes)
    
    # Avoid division by zero
    if average_volume == 0:
        return None
    
    # Calculate relative volume ratio
    relative_volume = current_volume / average_volume
    
    return round(relative_volume, 2)


async def calculate_all_indicators(market_data: List, target_date: date) -> Dict[str, Optional[float]]:
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
            'date': record.date.isoformat() if hasattr(record.date, 'isoformat') else str(record.date),
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

        # Get prices and volumes up to and including the target date
        prices_up_to_target = df.loc[:target_index, 'close'].tolist()
        volumes_up_to_target = df.loc[:target_index, 'volume'].tolist()

        # Calculate all indicators
        indicators = {}
        
        # Simple Moving Averages
        indicators['sma_200'] = calculate_sma(prices_up_to_target, 200)
        indicators['sma_100'] = calculate_sma(prices_up_to_target, 100)
        indicators['sma_50'] = calculate_sma(prices_up_to_target, 50)
        
        # Exponential Moving Averages
        indicators['ema_15'] = calculate_ema(prices_up_to_target, 15)
        indicators['ema_8'] = calculate_ema(prices_up_to_target, 8)
        
        # Volume indicators
        indicators['relative_volume'] = calculate_relative_volume(volumes_up_to_target, 20)
        
        # Real Relative Strength indicators - fetch SPY data
        default_rrs_indicators = {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
        try:
            spy_data = await db_manager.get_market_data_for_calculation_up_to_date(
                "SPY", target_date, days=len(market_data)
            )
            
            if spy_data:
                rrs_indicators = calculate_real_relative_strength_daily(market_data, spy_data, target_date)
                indicators.update(rrs_indicators)
            else:
                logger.warning("Could not fetch SPY data for RRS calculation")
                indicators.update(default_rrs_indicators)
                
        except Exception as e:
            logger.error(f"Error fetching SPY data for RRS calculation: {e}")
            indicators.update(default_rrs_indicators)
        
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
        'rrs_3_day': None,
        'rrs_8_day': None,
        'rrs_15_day': None,
        'relative_volume': None
    }

