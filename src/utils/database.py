"""
Database utilities for PostgreSQL operations.
"""

import logging
from datetime import datetime, date
from typing import List
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, UniqueConstraint, Index, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import ProgrammingError
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
    
    async def close(self):
        """Close the database engine."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager() 