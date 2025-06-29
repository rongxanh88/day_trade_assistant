import pytest
import vcr
from datetime import datetime, date
from unittest.mock import AsyncMock, patch
import os
import sys

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.integrations.tradier_client import TradierClient
from src.data.models import OHLCV


# VCR configuration for recording API calls
my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/vcr_cassettes',
    record_mode='once',  # Record once, then replay
    match_on=['uri', 'method'],
    filter_headers=['authorization'],  # Don't record API keys
    decode_compressed_response=True,
)


class TestTradierClientHistorical:
    """Test suite for TradierClient get_historical_data method."""
    
    @pytest.fixture
    def client(self):
        """Create a TradierClient instance for testing."""
        # Use actual API key for testing
        return TradierClient()
    
    @pytest.mark.asyncio
    @my_vcr.use_cassette('historical_data_basic.yaml')
    async def test_get_historical_data_basic(self, client):
        """Test basic historical data retrieval for a popular symbol."""
        symbol = "AAPL"
        
        result = await client.get_historical_data(symbol)
        
        # Basic assertions
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check first bar structure
        first_bar = result[0]
        assert isinstance(first_bar, OHLCV)
        assert hasattr(first_bar, 'date')
        assert hasattr(first_bar, 'open')
        assert hasattr(first_bar, 'high')  
        assert hasattr(first_bar, 'low')
        assert hasattr(first_bar, 'close')
        assert hasattr(first_bar, 'volume')
        
        # Verify data types
        assert isinstance(first_bar.open, float)
        assert isinstance(first_bar.high, float)
        assert isinstance(first_bar.low, float)
        assert isinstance(first_bar.close, float)
        assert isinstance(first_bar.volume, int)
    
    @pytest.mark.asyncio
    @my_vcr.use_cassette('historical_data_with_dates.yaml')
    async def test_get_historical_data_with_dates(self, client):
        """Test historical data with specific start and end dates."""
        symbol = "MSFT"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        result = await client.get_historical_data(
            symbol=symbol,
            start=start_date,
            end=end_date
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify all bars are within the requested date range
        for bar in result:
            bar_date = datetime.fromisoformat(bar.date).date()
            
            assert start_date <= bar_date <= end_date
    
    @pytest.mark.asyncio  
    @my_vcr.use_cassette('historical_data_different_intervals.yaml')
    async def test_get_historical_data_different_intervals(self, client):
        """Test historical data with different time intervals."""
        symbol = "SPY"
        intervals = ["5min", "15min", "30min", "1hour", "daily"]
        
        for interval in intervals:
            result = await client.get_historical_data(
                symbol=symbol,
                interval=interval
            )
            
            assert isinstance(result, list)
            # Some intervals might not have data, but shouldn't error
            if len(result) > 0:
                first_bar = result[0]
                assert isinstance(first_bar, OHLCV)
    
    @pytest.mark.asyncio
    @my_vcr.use_cassette('historical_data_invalid_symbol.yaml')
    async def test_get_historical_data_invalid_symbol(self, client):
        """Test historical data with an invalid symbol."""
        symbol = "INVALIDTICKER123"
        
        result = await client.get_historical_data(symbol)
        
        # Should return empty list for invalid symbols
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    @my_vcr.use_cassette('historical_data_weekend_dates.yaml')
    async def test_get_historical_data_weekend_dates(self, client):
        """Test historical data over weekend (should skip non-trading days)."""
        symbol = "QQQ"
        # Pick a weekend date range
        start_date = date(2024, 1, 6)  # Saturday
        end_date = date(2024, 1, 7)    # Sunday
        
        result = await client.get_historical_data(
            symbol=symbol,
            start=start_date,
            end=end_date
        )
        
        # Should return empty list for weekend-only date range
        assert isinstance(result, list)
        assert len(result) == 0
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 