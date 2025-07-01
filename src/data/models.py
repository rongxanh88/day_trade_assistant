from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict
from enum import Enum
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from typing import Annotated


# Enums for various trading concepts
class SetupType(str, Enum):
    """Types of trading setups the assistant can identify."""
    DOJI_SANDWICH = "doji_sandwich"
    GAP_PLAY = "gap_play"
    SWING_TRADE = "swing_trade"
    DAY_TRADE = "day_trade"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketCondition(str, Enum):
    """Overall market condition assessment."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


class TimeFrame(str, Enum):
    """Chart timeframes for analysis."""
    FIVE_MIN = "5min"
    FIFTEEN_MIN = "15min"
    THIRTY_MIN = "30min"
    ONE_HOUR = "1hour"
    DAILY = "daily"


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
    
    # Volume Indicators
    volume_ratio: Optional[float] = None


# class TradingSetup(BaseModel):
#     """A potential trading opportunity identified by the system."""
#     id: str = Field(default_factory=lambda: f"setup_{datetime.now().timestamp()}")
#     symbol: str
#     setup_type: SetupType
#     timeframe: TimeFrame
    
#     # Setup Details
#     entry_price: float
#     stop_loss: float
#     target_price: float
#     risk_reward_ratio: float
    
#     # Market Data
#     current_price: float
#     volume: int
#     volatility: float
    
#     # Analysis
#     confidence_score: float = Field(ge=0, le=100)
#     reasoning: str
#     technical_indicators: TechnicalIndicators
    
#     # Metadata
#     created_at: datetime = Field(default_factory=datetime.now)
#     expires_at: Optional[datetime] = None
#     alert_level: AlertLevel = AlertLevel.MEDIUM
    
#     # Status
#     is_active: bool = True
#     is_alerted: bool = False
    
    
class SuggestedPosition(BaseModel):
    """Current position information."""
    symbol: str
    quantity: int
    limit_price: float
    side: str  # "long" or "short"
    
    
class Alert(BaseModel):
    """Alert notification model."""
    id: str = Field(default_factory=lambda: f"alert_{datetime.now().timestamp()}")
    setup_id: str
    symbol: str
    alert_level: AlertLevel
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    is_sent: bool = False
    
    
# class RiskMetrics(BaseModel):
#     """Portfolio and position risk metrics."""
#     total_portfolio_value: float
#     total_unrealized_pnl: float
#     daily_pnl: float
#     max_drawdown: float
#     current_exposure: float
#     available_buying_power: float
    
#     # Risk Ratios
#     portfolio_beta: Optional[float] = None
#     sharpe_ratio: Optional[float] = None
#     max_position_size: float
    
    
# class MarketHours(BaseModel):
#     """Market session information."""
#     is_market_open: bool
#     is_pre_market: bool
#     is_after_hours: bool
#     next_open: Optional[datetime] = None
#     next_close: Optional[datetime] = None
    
    
# class PastTrade(BaseModel):
#     """Historical trade for performance tracking."""
#     symbol: str
#     setup_type: SetupType
#     entry_price: float
#     exit_price: float
#     quantity: int
#     pnl: float
#     duration_minutes: int
#     was_profitable: bool
#     confidence_score: float
#     actual_risk_reward: float
    
#     entry_time: datetime
#     exit_time: datetime


# LangGraph State Schema
class TradingState(TypedDict):
    """Main state schema for LangGraph workflows."""

    # Agent State
    agent_messages: Annotated[List, add_messages]
    
    # Market Data
    market_condition: MarketCondition
    
    # Analysis Results
    latest_quotes: Dict[str, Quote]
    technical_indicators: Dict[str, TechnicalIndicators]
    
    # Current Symbol Context
    current_symbol: Optional[str]  # Currently analyzed symbol
    current_symbol_data: Optional[str]  # Formatted market data context
    
    # User Preferences
    risk_tolerance: float
    preferred_strategies: List[SetupType]
    account_size: float
    
    # Workflow Control
    scan_frequency: int
    last_scan_time: Optional[datetime]
    alerts_sent: List[Alert]
    is_scanning_active: bool
    
    # Analysis Settings
    min_confidence_threshold: float
    min_risk_reward_ratio: float
    max_concurrent_setups: int
    
    # Messages and Logs
    messages: List[Dict[str, Any]]
    workflow_status: str
    last_error: Optional[str]


# Response Models for API
# class SetupResponse(BaseModel):
#     """Response model for setup recommendations."""
#     setup: TradingSetup
#     market_context: str
#     risk_assessment: str
#     action_required: bool
    

# class ScanResults(BaseModel):
#     """Results from a market scan."""
#     timestamp: datetime
#     symbols_scanned: List[str]
#     setups_found: List[TradingSetup]
#     market_condition: MarketCondition
#     scan_duration_seconds: float
    

# class PerformanceMetrics(BaseModel):
#     """Performance analytics."""
#     total_trades: int
#     winning_trades: int
#     losing_trades: int
#     win_rate: float
#     average_profit: float
#     average_loss: float
#     profit_factor: float
#     max_drawdown: float
#     total_pnl: float
    
    
# Workflow-specific models
# class AnalysisRequest(BaseModel):
#     """Request for symbol analysis."""
#     symbol: str
#     timeframes: List[TimeFrame] = [TimeFrame.FIVE_MIN, TimeFrame.FIFTEEN_MIN]
#     include_options: bool = False
#     force_refresh: bool = False


# class AlertConfig(BaseModel):
#     """Alert configuration for user preferences."""
#     enable_push_notifications: bool = True
#     enable_email: bool = False
#     enable_webhook: bool = True
#     min_alert_level: AlertLevel = AlertLevel.MEDIUM
#     quiet_hours_start: Optional[str] = None  # "22:00"
#     quiet_hours_end: Optional[str] = None    # "06:00"
#     max_alerts_per_hour: int = 10 