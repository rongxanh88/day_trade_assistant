"""
Database utilities for PostgreSQL operations.
"""

import logging
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from config.settings import settings
from src.data.models import OHLCV
import asyncpg

logger = logging.getLogger(__name__)

# Database base model
Base = declarative_base()

class DailyMarketData(Base):
    """Database model for daily market data."""
    __tablename__ = "daily_market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    
    # Ensure unique symbol-date combinations and add index on symbol for fast lookups
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='_symbol_date_uc'),
        Index('idx_symbol', 'symbol'),
    )


class TechnicalIndicators(Base):
    """Database model for technical indicators."""
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    
    # Moving Averages
    sma_200 = Column(Float, nullable=True)
    sma_100 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    ema_15 = Column(Float, nullable=True)
    ema_8 = Column(Float, nullable=True)
    
    # Real Relative Strength
    rrs_1_day = Column(Float, nullable=True)
    rrs_3_day = Column(Float, nullable=True)
    rrs_8_day = Column(Float, nullable=True)
    rrs_15_day = Column(Float, nullable=True)
    
    # Volume indicators
    relative_volume = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    
    # Ensure unique symbol-date combinations and add index on symbol for fast lookups
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='_tech_symbol_date_uc'),
        Index('idx_tech_symbol', 'symbol'),
        Index('idx_tech_date', 'date'),
    )

class StockUniverse(Base):
    """Database model for the stock universe."""
    __tablename__ = "stock_universe"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    sector = Column(String(255), nullable=False)
    industry = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now())


class DatabaseManager:
    """Async database manager for PostgreSQL operations."""
    
    def __init__(self):
        self.database_url = settings.database_url
        self.engine = None
        self.async_session = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the database engine and session maker."""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def _parse_database_url(self, url: str) -> dict:
        """Parse database URL to extract connection components."""
        # Example: postgres://user:password@host:port/database
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        return {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') if parsed.path else None
        }
    
    async def ensure_database_exists(self):
        """Create the database if it doesn't exist."""
        db_config = self._parse_database_url(self.database_url)
        target_database = db_config['database']
        
        if not target_database:
            logger.warning("No database specified in URL, skipping database creation")
            return
        
        # Connect to default 'postgres' database to create our target database
        try:
            conn = await asyncpg.connect(
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                port=db_config['port'],
                database='postgres'  # Connect to default database
            )
            
            # Check if database exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                target_database
            )
            
            if not result:
                logger.info(f"Database '{target_database}' does not exist, creating it...")
                
                # Create the database
                await conn.execute(f'CREATE DATABASE "{target_database}"')
                logger.info(f"Database '{target_database}' created successfully")
            else:
                logger.info(f"Database '{target_database}' already exists")
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Failed to ensure database exists: {e}")
            raise
    
    async def create_tables(self):
        """Create all database tables."""
        try:
            # Ensure database exists first
            await self.ensure_database_exists()
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def get_existing_data_dates(self, symbol: str, start_date: date, end_date: date) -> List[date]:
        """Get list of dates that already exist in the database for a symbol within the date range."""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(DailyMarketData.date)
                    .where(
                        and_(
                            DailyMarketData.symbol == symbol,
                            DailyMarketData.date >= start_date,
                            DailyMarketData.date <= end_date
                        )
                    )
                )
                existing_dates = [row[0] for row in result.fetchall()]
                return existing_dates
            except Exception as e:
                logger.error(f"Failed to query existing data dates for {symbol}: {e}")
                raise
    
    async def insert_market_data(self, market_data: List[OHLCV], symbol: str):
        """Insert market data into the database using batch operations."""
        async with self.async_session() as session:
            try:
                # Prepare data for batch upsert
                records_data = []
                for data in market_data:
                    # Convert date string to date object if needed
                    data_date = data.date
                    if isinstance(data_date, str):
                        data_date = datetime.strptime(data_date, "%Y-%m-%d").date()
                    
                    record_dict = {
                        'symbol': symbol,
                        'date': data_date,
                        'open': data.open,
                        'high': data.high,
                        'low': data.low,
                        'close': data.close,
                        'volume': data.volume,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                    records_data.append(record_dict)
                
                if records_data:
                    
                    stmt = insert(DailyMarketData).values(records_data)
                    stmt = stmt.on_conflict_do_update(
                        constraint='_symbol_date_uc',  # Our unique constraint
                        set_={
                            'open': stmt.excluded.open,
                            'high': stmt.excluded.high,
                            'low': stmt.excluded.low,
                            'close': stmt.excluded.close,
                            'volume': stmt.excluded.volume,
                            'updated_at': datetime.now()
                        }
                    )
                    
                    await session.execute(stmt)
                    await session.commit()
                    logger.info(f"Batch inserted/updated {len(records_data)} market data records for {symbol}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to batch insert market data for {symbol}: {e}")
                raise
    
    async def get_recent_market_data(self, symbol: str, days: int = 50) -> List[DailyMarketData]:
        """Get recent market data for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            days: Number of recent trading days to retrieve
            
        Returns:
            List of DailyMarketData records, ordered by date descending (most recent first)
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(DailyMarketData)
                    .where(DailyMarketData.symbol == symbol.upper())
                    .order_by(DailyMarketData.date.desc())
                    .limit(days)
                )
                records = result.scalars().all()
                logger.info(f"Retrieved {len(records)} records for {symbol}")
                return list(records)
            except Exception as e:
                logger.error(f"Failed to retrieve market data for {symbol}: {e}")
                raise

    async def close(self):
        """Close the database engine."""
        await self.engine.dispose()

    async def get_symbols_with_sufficient_data(self, min_days: int = 200) -> List[str]:
        """Get symbols that have at least min_days of market data.
        
        Args:
            min_days: Minimum number of days of data required
            
        Returns:
            List of symbols with sufficient data
        """
        async with self.async_session() as session:
            try:
                # Count records per symbol and filter by minimum days
                from sqlalchemy import func
                
                result = await session.execute(
                    select(DailyMarketData.symbol)
                    .group_by(DailyMarketData.symbol)
                    .having(func.count(DailyMarketData.id) >= min_days)
                )
                symbols = [row[0] for row in result.fetchall()]
                logger.info(f"Found {len(symbols)} symbols with at least {min_days} days of data")
                return symbols
            except Exception as e:
                logger.error(f"Failed to get symbols with sufficient data: {e}")
                raise

    async def get_existing_technical_indicators(self, symbol: str, target_date: date) -> Optional[TechnicalIndicators]:
        """Check if technical indicators exist for a symbol and date.
        
        Args:
            symbol: Stock ticker symbol
            target_date: Date to check for
            
        Returns:
            TechnicalIndicators record if exists, None otherwise
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(TechnicalIndicators)
                    .where(
                        and_(
                            TechnicalIndicators.symbol == symbol,
                            TechnicalIndicators.date == target_date
                        )
                    )
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to check existing technical indicators for {symbol}: {e}")
                raise

    async def insert_technical_indicators(self, symbol: str, target_date: date, indicators: dict):
        """Insert or update technical indicators for a symbol and date.
        
        Args:
            symbol: Stock ticker symbol
            target_date: Date of the indicators
            indicators: Dictionary containing indicator values
        """
        async with self.async_session() as session:
            try:
                # Prepare the data for upsert
                indicator_data = {
                    'symbol': symbol,
                    'date': target_date,
                    'sma_200': indicators.get('sma_200'),
                    'sma_100': indicators.get('sma_100'),
                    'sma_50': indicators.get('sma_50'),
                    'ema_15': indicators.get('ema_15'),
                    'ema_8': indicators.get('ema_8'),
                    'rrs_1_day': indicators.get('rrs_1_day'),
                    'rrs_3_day': indicators.get('rrs_3_day'),
                    'rrs_8_day': indicators.get('rrs_8_day'),
                    'rrs_15_day': indicators.get('rrs_15_day'),
                    'relative_volume': indicators.get('relative_volume'),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                # Use PostgreSQL upsert (INSERT ... ON CONFLICT DO UPDATE)
                stmt = insert(TechnicalIndicators).values(indicator_data)
                stmt = stmt.on_conflict_do_update(
                    constraint='_tech_symbol_date_uc',
                    set_={
                        'sma_200': stmt.excluded.sma_200,
                        'sma_100': stmt.excluded.sma_100,
                        'sma_50': stmt.excluded.sma_50,
                        'ema_15': stmt.excluded.ema_15,
                        'ema_8': stmt.excluded.ema_8,
                        'rrs_1_day': stmt.excluded.rrs_1_day,
                        'rrs_3_day': stmt.excluded.rrs_3_day,
                        'rrs_8_day': stmt.excluded.rrs_8_day,
                        'rrs_15_day': stmt.excluded.rrs_15_day,
                        'relative_volume': stmt.excluded.relative_volume,
                        'updated_at': datetime.now()
                    }
                )
                
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Inserted/updated technical indicators for {symbol} on {target_date}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to insert technical indicators for {symbol}: {e}")
                raise

    async def get_market_data_for_calculation(self, symbol: str, days: int) -> List[DailyMarketData]:
        """Get market data for technical indicator calculation.
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to retrieve (should be enough for longest indicator)
            
        Returns:
            List of DailyMarketData records, ordered by date ascending
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(DailyMarketData)
                    .where(DailyMarketData.symbol == symbol.upper())
                    .order_by(DailyMarketData.date.desc())
                    .limit(days)
                )
                records = result.scalars().all()
                return list(records)
            except Exception as e:
                logger.error(f"Failed to get market data for calculation for {symbol}: {e}")
                raise

    async def get_market_data_for_calculation_up_to_date(self, symbol: str, end_date: date, days: int) -> List[DailyMarketData]:
        """Get market data for technical indicator calculation up to a specific date.
        
        Args:
            symbol: Stock ticker symbol
            end_date: The end date (inclusive) for the data range
            days: Number of days to retrieve before the end date
            
        Returns:
            List of DailyMarketData records up to end_date, ordered by date ascending
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(DailyMarketData)
                    .where(
                        and_(
                            DailyMarketData.symbol == symbol.upper(),
                            DailyMarketData.date <= end_date
                        )
                    )
                    .order_by(DailyMarketData.date.desc())
                    .limit(days)
                )
                records = result.scalars().all()
                # Return in ascending order (oldest first) for technical analysis
                return list(reversed(records))
            except Exception as e:
                logger.error(f"Failed to get market data for calculation up to {end_date} for {symbol}: {e}")
                raise

    async def get_all_stock_universe_symbols(self) -> List[str]:
        """Get all symbols from the stock_universe table.
        
        Returns:
            List of stock symbols from the stock universe
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(StockUniverse.symbol)
                    .order_by(StockUniverse.symbol)
                )
                symbols = [row[0] for row in result.fetchall()]
                logger.info(f"Retrieved {len(symbols)} symbols from stock universe")
                return symbols
            except Exception as e:
                logger.error(f"Failed to get symbols from stock universe: {e}")
                raise


# Global database manager instance
db_manager = DatabaseManager() 