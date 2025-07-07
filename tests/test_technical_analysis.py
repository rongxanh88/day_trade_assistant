import pytest
import os
import sys
from datetime import date, timedelta
from unittest.mock import patch


# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.technical_analysis import (
    calculate_sma,
    calculate_ema,
    calculate_all_indicators,
    _get_empty_indicators
)
from src.data.models import OHLCV


class TestTechnicalAnalysis:
    """Test suite for technical analysis calculations."""
    
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

    def test_calculate_sma_basic(self):
        """Test basic SMA calculation."""
        prices = [100.0, 102.0, 101.0, 103.0, 104.0]
        
        # Test 3-period SMA
        result = calculate_sma(prices, 3)
        expected = (101.0 + 103.0 + 104.0) / 3  # Last 3 prices
        assert result == round(expected, 2)
        
        # Test 5-period SMA
        result = calculate_sma(prices, 5)
        expected = sum(prices) / 5
        assert result == round(expected, 2)

    def test_calculate_sma_insufficient_data(self):
        """Test SMA calculation with insufficient data."""
        prices = [100.0, 102.0]
        
        # Request 5-period SMA with only 2 data points
        result = calculate_sma(prices, 5)
        assert result is None

    def test_calculate_sma_empty_data(self):
        """Test SMA calculation with empty data."""
        prices = []
        result = calculate_sma(prices, 5)
        assert result is None

    def test_calculate_sma_200_days(self):
        """Test 200-day SMA calculation."""
        # Create 250 days of data to ensure we have enough
        test_data = self.create_test_data(250, start_price=100.0, trend="uptrend")
        prices = [record.close for record in test_data]
        
        result = calculate_sma(prices, 200)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_sma_100_days(self):
        """Test 100-day SMA calculation."""
        test_data = self.create_test_data(150, start_price=100.0, trend="neutral")
        prices = [record.close for record in test_data]
        
        result = calculate_sma(prices, 100)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_sma_50_days(self):
        """Test 50-day SMA calculation."""
        test_data = self.create_test_data(75, start_price=1000.0, trend="downtrend")
        prices = [record.close for record in test_data]
        
        result = calculate_sma(prices, 50)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_ema_basic(self):
        """Test basic EMA calculation."""
        prices = [100.0, 102.0, 101.0, 103.0, 104.0]
        
        # Test 3-period EMA
        result = calculate_ema(prices, 3)
        assert result is not None
        assert isinstance(result, float)
        
        # EMA should be different from SMA
        sma_result = calculate_sma(prices, 3)
        assert result != sma_result

    def test_calculate_ema_insufficient_data(self):
        """Test EMA calculation with insufficient data."""
        prices = [100.0, 102.0]
        
        # Request 5-period EMA with only 2 data points
        result = calculate_ema(prices, 5)
        assert result is None

    def test_calculate_ema_empty_data(self):
        """Test EMA calculation with empty data."""
        prices = []
        result = calculate_ema(prices, 5)
        assert result is None

    def test_calculate_ema_15_days(self):
        """Test 15-day EMA calculation."""
        test_data = self.create_test_data(30, start_price=100.0, trend="uptrend")
        prices = [record.close for record in test_data]
        
        result = calculate_ema(prices, 15)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_ema_8_days(self):
        """Test 8-day EMA calculation."""
        test_data = self.create_test_data(20, start_price=100.0, trend="neutral")
        prices = [record.close for record in test_data]
        
        result = calculate_ema(prices, 8)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_ema_responsiveness(self):
        """Test that EMA is more responsive to recent price changes than SMA."""
        # Create data with a recent price spike
        prices = [100.0] * 10 + [110.0] * 5  # 10 days at 100, then 5 days at 110
        
        ema_result = calculate_ema(prices, 10)
        sma_result = calculate_sma(prices, 10)
        
        # EMA should be closer to the recent higher prices
        assert ema_result > sma_result
        assert sma_result == 105.0

    def test_calculate_all_indicators_complete(self):
        """Test calculating all indicators with sufficient data."""
        # Create 250 days of data to ensure all indicators can be calculated
        test_data = self.create_test_data(365, start_price=100.0, trend="uptrend")
        target_date = date(2024, 12, 30)  # Well within our test data range
        
        result = calculate_all_indicators(test_data, target_date)

        # Check that all indicators are calculated
        assert result['sma_200'] is not None
        assert result['sma_100'] is not None
        assert result['sma_50'] is not None
        assert result['ema_15'] is not None
        assert result['ema_8'] is not None
        assert result['rrs_1_day'] is not None
        assert result['rrs_8_day'] is not None
        assert result['rrs_15_day'] is not None
        
        # # Check that values are reasonable
        assert all(isinstance(val, float) for val in result.values())
        assert all(val > 0 for val in result.values())

    def test_calculate_all_indicators_no_data(self):
        """Test calculating indicators with no data."""
        result = calculate_all_indicators([], date(2024, 1, 1))
        
        expected = _get_empty_indicators()
        assert result == expected

    def test_calculate_all_indicators_target_date_not_found(self):
        """Test calculating indicators when target date is not in data."""
        test_data = self.create_test_data(50, start_price=100.0, trend="neutral")
        target_date = date(2025, 1, 1)  # Date not in our test data
        
        result = calculate_all_indicators(test_data, target_date)
        
        expected = _get_empty_indicators()
        assert result == expected

    def test_sma_vs_ema_characteristics(self):
        """Test that SMA and EMA have expected characteristics."""
        # Create data with a trend change
        stable_prices = [100.0] * 20
        trending_prices = [100.0 + i for i in range(1, 11)]  # Uptrend
        prices = stable_prices + trending_prices
        
        sma_result = calculate_sma(prices, 20)
        ema_result = calculate_ema(prices, 20)
        
        # EMA should be more responsive to recent trend
        # Since recent prices are higher, EMA should be higher than SMA
        assert ema_result > sma_result


    @patch('src.analyzers.technical_analysis.logger')
    def test_calculate_all_indicators_error_handling(self, mock_logger):
        """Test error handling in calculate_all_indicators."""
        # Create invalid data that might cause an exception
        invalid_data = [None, "invalid", 123]  # Not OHLCV objects
        
        result = calculate_all_indicators(invalid_data, date(2024, 1, 1))
        
        # Should return empty indicators and log error
        expected = _get_empty_indicators()
        assert result == expected
        mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 