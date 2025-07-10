#!/usr/bin/env python3

import asyncio
import logging
import sys
from datetime import datetime
from typing import List

import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

# Add project paths
sys.path.append('.')
sys.path.append('src')

from src.integrations.fin_viz_screener import fetch_custom_universe
from src.utils.database import DatabaseManager, StockUniverse

logger = logging.getLogger(__name__)


class StockUniverseManager:
    """Manages the stock universe - fetches from finviz and stores in DB."""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    async def run(self):
        """Main entry point - fetch stocks and update database."""
        logger.info("Starting stock universe update...")
        
        try:
            # Create tables if they don't exist
            await self.db.create_tables()
            
            # Fetch stock data from finviz
            logger.info("Fetching stock data from finviz...")
            df = fetch_custom_universe()
            
            if df.empty:
                logger.warning("No stocks returned from finviz screener")
                return
            
            logger.info(f"Found {len(df)} stocks from finviz")
            
            # Clean and validate the data
            stocks = self._process_stock_data(df)
            
            if not stocks:
                logger.warning("No valid stocks after processing")
                return
            
            # Update database
            await self._update_stock_universe(stocks)
            
            logger.info(f"Stock universe update completed. {len(stocks)} stocks processed.")
            
        except Exception as e:
            logger.error(f"Failed to update stock universe: {e}")
            raise
        finally:
            await self.db.close()
    
    def _process_stock_data(self, df: pd.DataFrame) -> List[dict]:
        """Process the finviz DataFrame into clean stock records."""
        stocks = []
        
        # Required columns mapping (finviz -> our format)
        column_mapping = {
            'Ticker': 'symbol',
            'Company': 'name', 
            'Sector': 'sector',
            'Industry': 'industry',
            'Country': 'country'
        }
        
        # Check if all required columns exist
        missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            logger.info(f"Available columns: {df.columns.tolist()}")
            return []
        
        for _, row in df.iterrows():
            try:
                # Extract and clean the data
                stock = {}
                for finviz_col, our_col in column_mapping.items():
                    value = row.get(finviz_col, '')
                    if pd.isna(value):
                        value = ''
                    stock[our_col] = str(value).strip()
                
                # Basic validation
                if not stock['symbol'] or not stock['name']:
                    logger.warning(f"Skipping invalid stock record: {stock}")
                    continue
                
                # Ensure symbol is uppercase and clean
                stock['symbol'] = stock['symbol'].upper()
                # Replace dots with slashes (e.g., BRK.A -> BRK/A)
                stock['symbol'] = stock['symbol'].replace('.', '/')
                stock['symbol'] = stock['symbol'].replace('-', '/')
                
                # Truncate fields to fit database constraints
                stock['name'] = stock['name'][:255]
                stock['sector'] = stock['sector'][:255] 
                stock['industry'] = stock['industry'][:255]
                stock['country'] = stock['country'][:255]
                
                stocks.append(stock)
                
            except Exception as e:
                logger.warning(f"Error processing stock row: {e}")
                continue
        
        logger.info(f"Processed {len(stocks)} valid stocks from {len(df)} total")
        return stocks
    
    async def _update_stock_universe(self, stocks: List[dict]):
        """Update the stock universe table with new data."""
        async with self.db.async_session() as session:
            try:
                # Clear existing data - we want a fresh universe each time
                logger.info("Clearing existing stock universe...")
                await session.execute(delete(StockUniverse))
                
                # Batch insert new data
                if stocks:
                    logger.info(f"Inserting {len(stocks)} stocks...")
                    stmt = insert(StockUniverse).values(stocks)
                    await session.execute(stmt)
                
                await session.commit()
                logger.info("Stock universe table updated successfully")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update stock universe table: {e}")
                raise
    
    async def get_universe_symbols(self) -> List[str]:
        """Get all symbols from the current stock universe."""
        async with self.db.async_session() as session:
            try:
                result = await session.execute(
                    select(StockUniverse.symbol).order_by(StockUniverse.symbol)
                )
                symbols = [row[0] for row in result.fetchall()]
                logger.info(f"Retrieved {len(symbols)} symbols from stock universe")
                return symbols
                
            except Exception as e:
                logger.error(f"Failed to get universe symbols: {e}")
                raise


async def main():
    """CLI entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = StockUniverseManager()
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())
