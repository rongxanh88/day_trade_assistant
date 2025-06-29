from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Configuration
    tradier_api_key: str = Field(..., env="TRADIER_API_ACCESS_TOKEN")
    tradier_base_url: str = Field(
        default="https://api.tradier.com/v1",
        env="TRADIER_BASE_URL"
    )
    
    # LLM Configuration
    # openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    # anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    # default_model: str = Field(default="gpt-4-1106-preview", env="DEFAULT_MODEL")
    
    # Database Configuration
    # database_url: str = Field(
    #     default="sqlite:///./trading_assistant.db",
    #     env="DATABASE_URL"
    # )
    # redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Trading Configuration
    # default_watchlist: List[str] = Field(
    #     default=["SPY", "QQQ", "IWM", "TSLA", "AAPL", "NVDA", "MSFT"],
    #     env="DEFAULT_WATCHLIST"
    # )
    # max_concurrent_analysis: int = Field(default=10, env="MAX_CONCURRENT_ANALYSIS")
    # scan_interval_seconds: int = Field(default=30, env="SCAN_INTERVAL_SECONDS")
    
    # Risk Management
    # max_position_size_percent: float = Field(default=5.0, env="MAX_POSITION_SIZE_PERCENT")
    # max_daily_loss_percent: float = Field(default=2.0, env="MAX_DAILY_LOSS_PERCENT")
    # min_risk_reward_ratio: float = Field(default=2.0, env="MIN_RISK_REWARD_RATIO")
    
    # Market Hours (EST)
    # market_open_hour: int = Field(default=9, env="MARKET_OPEN_HOUR")
    # market_open_minute: int = Field(default=30, env="MARKET_OPEN_MINUTE")
    # market_close_hour: int = Field(default=16, env="MARKET_CLOSE_HOUR")
    # market_close_minute: int = Field(default=0, env="MARKET_CLOSE_MINUTE")
    
    # Alert Configuration
    # enable_email_alerts: bool = Field(default=False, env="ENABLE_EMAIL_ALERTS")
    # enable_webhook_alerts: bool = Field(default=True, env="ENABLE_WEBHOOK_ALERTS")
    # webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    
    # Technical Analysis Configuration
    # rsi_oversold_threshold: float = Field(default=30.0, env="RSI_OVERSOLD_THRESHOLD")
    # rsi_overbought_threshold: float = Field(default=70.0, env="RSI_OVERBOUGHT_THRESHOLD")
    # volume_spike_multiplier: float = Field(default=2.0, env="VOLUME_SPIKE_MULTIPLIER")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="trading_assistant.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# Trading-specific configurations
class TradingConfig:
    """Trading-specific configuration constants."""
    
    # Setup Types
    MOMENTUM_BREAKOUT = "momentum_breakout"
    GAP_PLAY = "gap_play"
    SWING_TRADE = "swing_trade"
    DAY_TRADE = "day_trade"
    
    SETUP_TYPES = [
        MOMENTUM_BREAKOUT,
        GAP_PLAY,
        SWING_TRADE,
        DAY_TRADE
    ]
    
    # Time Frames
    TIMEFRAMES = {
        "5min": "5min",
        "15min": "15min",
        "30min": "30min",
        "1hour": "1hour",
        "daily": "daily"
    }
    
    # Technical Indicators
    # DEFAULT_RSI_PERIOD = 14
    # DEFAULT_MACD_FAST = 12
    # DEFAULT_MACD_SLOW = 26
    # DEFAULT_MACD_SIGNAL = 9
    # DEFAULT_BB_PERIOD = 20
    # DEFAULT_BB_STD = 2.0
    
    # Volume Analysis
    # MIN_VOLUME_FOR_BREAKOUT = 1000000  # 1M shares
    # VOLUME_MA_PERIOD = 20
    
    # Price Movement Thresholds
    # MIN_BREAKOUT_PERCENT = 2.0  # 2% minimum breakout
    # MAX_DRAWDOWN_PERCENT = 5.0  # 5% max drawdown tolerance
    
    # Options Flow
    # MIN_OPTION_VOLUME = 1000
    # MIN_OPTION_OI_RATIO = 2.0  # Volume to OI ratio
    
    # Market Conditions
    # TREND_LOOKBACK_DAYS = 20
    # VOLATILITY_LOOKBACK_DAYS = 30


# Initialize trading config
trading_config = TradingConfig() 