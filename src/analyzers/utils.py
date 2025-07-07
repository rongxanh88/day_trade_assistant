from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


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
