from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# Core trading data models
class Quote(BaseModel):
    """Real-time quote data."""
    symbol: str
    description: str
    last: float
    open: float
    close: float
    high: float
    low: float
    bid: float
    ask: float
    volume: int
    change: float
    change_percent: float
    average_volume: int
    
    
class OHLCV(BaseModel):
    """OHLC + Volume bar data."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators for a symbol."""
    symbol: str
    timestamp: datetime
    
    # Trend Indicators
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_8: Optional[float] = None
    ema_15: Optional[float] = None

    # Real Relative Strength Indicators
    rrs_1_day: Optional[float] = None
    rrs_3_day: Optional[float] = None
    rrs_8_day: Optional[float] = None
    rrs_15_day: Optional[float] = None
    
    # Volume Indicators
    relative_volume: Optional[float] = None
    
