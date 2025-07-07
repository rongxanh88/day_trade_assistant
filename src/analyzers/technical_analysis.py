"""
Technical Analysis Module for Day Trading Assistant

This module provides functions to calculate various technical indicators
including Simple Moving Averages (SMA) and Exponential Moving Averages (EMA).
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
from datetime import date

# Add database import
from src.utils.database import db_manager
# Import RRS utility functions
from .real_relative_strength import calculate_real_relative_strength_daily

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