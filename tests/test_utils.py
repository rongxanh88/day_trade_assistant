import pytest
import os
import sys


# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.utils import validate_data_sufficiency, get_technical_summary
from src.data.models import OHLCV
from datetime import date, timedelta

class TestUtils:
    """Test suite for supporting util calculations."""
    def create_test_data(self, num_days: int, start_price: float = 100.0, trend: str = "neutral") -> list[OHLCV]:
        """Create test market data with predictable patterns."""
        data = []
        current_price = start_price
        base_date = date(2024, 1, 1)
        
        for i in range(num_days):
            # Create predictable price movement based on trend
            if trend == "uptrend":
                daily_change = 0.5 + (i * 0.1)  # Gradually increasing
            elif trend == "downtrend":
                daily_change = -0.5 - (i * 0.1)  # Gradually decreasing
            else:  # neutral
                daily_change = 0.2 * ((-1) ** i)  # Alternating small changes
                
            current_price += daily_change
            
            # Create OHLC data with some variation
            open_price = current_price
            high_price = current_price + abs(daily_change) * 0.5
            low_price = current_price - abs(daily_change) * 0.5
            close_price = current_price
            
            data.append(OHLCV(
                date=(base_date + timedelta(days=i)).isoformat(),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=1000000 + i * 10000
            ))
        
        return data

    def test_validate_data_sufficiency_sufficient(self):
        """Test validation with sufficient data."""
        test_data = self.create_test_data(250, start_price=100.0, trend="neutral")
        
        result = validate_data_sufficiency(test_data, 200)
        assert result is True

    def test_validate_data_sufficiency_insufficient(self):
        """Test validation with insufficient data."""
        test_data = self.create_test_data(100, start_price=100.0, trend="neutral")
        
        result = validate_data_sufficiency(test_data, 200)
        assert result is False

    def test_validate_data_sufficiency_no_data(self):
        """Test validation with no data."""
        result = validate_data_sufficiency([], 200)
        assert result is False

    def test_get_technical_summary(self):
        """Test technical summary generation."""
        # Create sample indicators
        indicators = {
            'sma_200': 95.0,
            'sma_100': 98.0,
            'sma_50': 102.0,
            'ema_15': 105.0,
            'ema_8': 107.0,
            'rrs_1_day': 1.0,
            'rrs_8_day': 1.0,
            'rrs_15_day': 1.0
        }
        current_price = 100.0
        
        summary = get_technical_summary(indicators, current_price)
        
        # Check that summary contains expected elements
        assert "Technical Analysis Summary" in summary
        assert "SIMPLE MOVING AVERAGES" in summary
        assert "EXPONENTIAL MOVING AVERAGES" in summary
        assert "$100.00" in summary  # Current price
        assert "$95.00" in summary  # SMA 200
        assert "$107.00" in summary  # EMA 8
        
        # Check that it shows position relative to moving averages
        assert "above" in summary  # Price above some MAs
        assert "below" in summary  # Price below some MAs

        # check that RRS is included
        assert "REAL RELATIVE STRENGTH" in summary
        assert "1-day RRS" in summary
        assert "8-day RRS" in summary
        assert "15-day RRS" in summary

    def test_get_technical_summary_with_none_values(self):
        """Test technical summary with some None values."""
        indicators = {
            'sma_200': None,  # Insufficient data
            'sma_100': 98.0,
            'sma_50': 102.0,
            'ema_15': None,  # Insufficient data
            'ema_8': 107.0,
            'rrs_1_day': None, # Insufficient data
            'rrs_8_day': None, # Insufficient data
            'rrs_15_day': None # Insufficient data
        }
        current_price = 100.0
        
        summary = get_technical_summary(indicators, current_price)
        
        # Check that None values are handled properly
        assert "N/A (insufficient data)" in summary
        assert "$98.00" in summary  # Available SMA 100
        assert "$102.00" in summary  # Available SMA 50
        assert "$107.00" in summary  # Available EMA 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 

