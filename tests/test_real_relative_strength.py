import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.real_relative_strength import calculate_wilders_average, calculate_true_range, calculate_rrs_for_period, calculate_real_relative_strength_daily
from src.data.models import OHLCV
from unittest.mock import patch
from datetime import date, timedelta


class TestCalculateTrueRange:
    """Test suite for calculate_true_range function."""
    
    def create_ohlc_dataframe(self, data_points: list) -> pd.DataFrame:
        """Helper method to create OHLC DataFrame from list of tuples.
        
        Args:
            data_points: List of tuples (high, low, close)
        """
        df_data = []
        for i, (high, low, close) in enumerate(data_points):
            df_data.append({
                'date': f'2024-01-{i+1:02d}',
                'high': high,
                'low': low, 
                'close': close,
                'open': close,  # Using close as open for simplicity
                'volume': 1000000
            })
        return pd.DataFrame(df_data)
    
    def test_calculate_true_range_normal_case(self):
        """Test True Range calculation with normal OHLC data."""
        # Create test data where we can manually verify True Range
        # Day 1: H=105, L=95, C=100
        # Day 2: H=110, L=98, C=108, Prev_C=100
        # Day 3: H=106, L=102, C=104, Prev_C=108
        data_points = [
            (105, 95, 100),  # TR = max(10, -, -) = 10 (first day, no prev close)
            (110, 98, 108),  # TR = max(12, 10, 2) = 12
            (106, 102, 104)  # TR = max(4, 2, 6) = 6
        ]
        
        df = self.create_ohlc_dataframe(data_points)
        tr_series = calculate_true_range(df)
        
        # First day should be high - low (no previous close)
        assert tr_series.iloc[0] == 10.0  # 105 - 95
        
        # Second day: max(110-98=12, abs(110-100)=10, abs(98-100)=2) = 12
        assert tr_series.iloc[1] == 12.0
        
        # Third day: max(106-102=4, abs(106-108)=2, abs(102-108)=6) = 6
        assert tr_series.iloc[2] == 6.0
    
    def test_calculate_true_range_single_point(self):
        """Test True Range with single data point."""
        data_points = [(105, 95, 100)]
        df = self.create_ohlc_dataframe(data_points)
        tr_series = calculate_true_range(df)
        
        # With single point, TR should be high - low
        assert len(tr_series) == 1
        assert tr_series.iloc[0] == 10.0  # 105 - 95
    
    def test_calculate_true_range_empty_dataframe(self):
        """Test True Range with empty DataFrame."""
        df = pd.DataFrame(columns=['high', 'low', 'close'])
        tr_series = calculate_true_range(df)
        
        assert len(tr_series) == 0
    
    def test_calculate_true_range_gaps_and_volatility(self):
        """Test True Range with price gaps and high volatility."""
        # Test case with large gap up and gap down
        data_points = [
            (100, 90, 95),   # Normal day
            (120, 115, 118), # Gap up: prev close 95, high 120
            (110, 85, 88)    # Gap down: prev close 118, low 85
        ]
        
        df = self.create_ohlc_dataframe(data_points)
        tr_series = calculate_true_range(df)
        
        # Day 1: high - low = 10
        assert tr_series.iloc[0] == 10.0
        
        # Day 2: max(120-115=5, abs(120-95)=25, abs(115-95)=20) = 25
        assert tr_series.iloc[1] == 25.0
        
        # Day 3: max(110-85=25, abs(110-118)=8, abs(85-118)=33) = 33
        assert tr_series.iloc[2] == 33.0
    

class TestCalculateWildersAverage:
    """Test suite for calculate_wilders_average function."""
    
    def test_calculate_wilders_average_normal_case(self):
        """Test Wilder's Average with normal data."""
        # Create test data: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        period = 4
        
        result = calculate_wilders_average(data, period)
        
        # Manual calculation:
        # Initial average of first 4 values: (1+2+3+4)/4 = 2.5
        # alpha = 1/4 = 0.25
        # Step 1: 0.25*5 + 0.75*2.5 = 1.25 + 1.875 = 3.125
        # Step 2: 0.25*6 + 0.75*3.125 = 1.5 + 2.34375 = 3.84375
        # Step 3: 0.25*7 + 0.75*3.84375 = 1.75 + 2.8828125 = 4.6328125
        # Step 4: 0.25*8 + 0.75*4.6328125 = 2 + 3.474609375 = 5.474609375
        # Step 5: 0.25*9 + 0.75*5.474609375 = 2.25 + 4.10595703125 = 6.35595703125
        # Step 6: 0.25*10 + 0.75*6.35595703125 = 2.5 + 4.7669677734375 = 7.2669677734375
        
        expected = 7.2669677734375
        assert abs(result - expected) < 1e-10
    
    def test_calculate_wilders_average_exact_period_length(self):
        """Test Wilder's Average when data length equals period."""
        data = pd.Series([10, 20, 30, 40])
        period = 4
        
        result = calculate_wilders_average(data, period)
        
        # Should return the simple average since no exponential smoothing is applied
        expected = (10 + 20 + 30 + 40) / 4
        assert result == expected
    
    def test_calculate_wilders_average_insufficient_data(self):
        """Test Wilder's Average with insufficient data."""
        data = pd.Series([1, 2])
        period = 5
        
        result = calculate_wilders_average(data, period)
        
        assert result is None
    
    def test_calculate_wilders_average_empty_series(self):
        """Test Wilder's Average with empty Series."""
        data = pd.Series([])
        period = 4
        
        result = calculate_wilders_average(data, period)
        
        assert result is None
    
    def test_calculate_wilders_average_with_nan_values(self):
        """Test Wilder's Average with NaN values in data."""
        # Series with NaN values
        data = pd.Series([1, np.nan, 3, 4, 5, 6])
        period = 4
        
        result = calculate_wilders_average(data, period)
        
        # Should work with clean data after dropping NaN: [1, 3, 4, 5, 6]
        # Initial average: (1+3+4+5)/4 = 3.25
        # alpha = 0.25
        # Final: 0.25*6 + 0.75*3.25 = 1.5 + 2.4375 = 3.9375
        
        expected = 3.9375
        assert abs(result - expected) < 1e-10
    
    def test_calculate_wilders_average_all_nan(self):
        """Test Wilder's Average with all NaN values."""
        data = pd.Series([np.nan, np.nan, np.nan, np.nan])
        period = 2
        
        result = calculate_wilders_average(data, period)
        
        assert result is None
    
    def test_calculate_wilders_average_insufficient_after_nan_removal(self):
        """Test when insufficient data remains after NaN removal."""
        data = pd.Series([1, np.nan, np.nan, np.nan, 2])
        period = 4
        
        result = calculate_wilders_average(data, period)
        
        # Only 2 values remain after NaN removal, but period is 4
        assert result is None
    
    def test_calculate_wilders_average_period_one(self):
        """Test Wilder's Average with period = 1."""
        data = pd.Series([5, 10, 15, 20])
        period = 1
        
        result = calculate_wilders_average(data, period)
        
        # With period 1, alpha = 1, so result should be last value
        assert result == 20
    
    def test_calculate_wilders_average_large_dataset(self):
        """Test Wilder's Average with larger dataset for consistency."""
        # Create a dataset with known pattern
        data = pd.Series(range(1, 101))  # 1 to 100
        period = 14
        
        result = calculate_wilders_average(data, period)
        
        # Result should be a positive number between initial average and final values
        initial_avg = sum(range(1, 15)) / 14  # Average of first 14 numbers
        assert result > initial_avg
        assert result < 100  # Should be less than the maximum value
        assert isinstance(result, float)
    
    def test_calculate_wilders_average_consistent_values(self):
        """Test Wilder's Average with all same values."""
        data = pd.Series([50, 50, 50, 50, 50, 50])
        period = 3
        
        result = calculate_wilders_average(data, period)
        
        # When all values are the same, result should be that value
        assert result == 50.0


class TestCalculateRrsForPeriod:
    """Test suite for calculate_rrs_for_period function."""
    
    def create_market_dataframe(self, prices: list, start_date: str = "2024-01-01") -> pd.DataFrame:
        """Helper method to create market data DataFrame from list of closing prices.
        
        Args:
            prices: List of closing prices
            start_date: Starting date in YYYY-MM-DD format
        """
        from datetime import datetime, timedelta
        
        df_data = []
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        for i, close_price in enumerate(prices):
            # Create realistic OHLC data with some volatility
            volatility = 0.02  # 2% daily volatility
            daily_range = close_price * volatility
            
            open_price = close_price + np.random.uniform(-daily_range/2, daily_range/2)
            high_price = max(open_price, close_price) + abs(np.random.uniform(0, daily_range/2))
            low_price = min(open_price, close_price) - abs(np.random.uniform(0, daily_range/2))
            
            df_data.append({
                'date': (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': 1000000 + i * 10000
            })
        
        return pd.DataFrame(df_data)
    
    def create_test_scenario_data(self, days: int = 20) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create test data for both symbol and SPY with predictable patterns."""
        # Create SPY data with modest uptrend
        spy_base_price = 400.0
        spy_prices = []
        for i in range(days):
            # SPY gains 0.1% per day on average
            spy_price = spy_base_price * (1.001 ** i)
            spy_prices.append(spy_price)
        
        # Create symbol data that outperforms SPY
        symbol_base_price = 100.0
        symbol_prices = []
        for i in range(days):
            # Symbol gains 0.2% per day on average (outperforming SPY)
            symbol_price = symbol_base_price * (1.002 ** i)
            symbol_prices.append(symbol_price)
        
        spy_data = self.create_market_dataframe(spy_prices)
        symbol_data = self.create_market_dataframe(symbol_prices)
        
        return symbol_data, spy_data
    
    def test_calculate_rrs_for_period_normal_case(self):
        """Test RRS calculation with normal data and different periods."""
        symbol_data, spy_data = self.create_test_scenario_data(20)
        
        # Test different periods
        for period in [1, 8, 15]:
            result = calculate_rrs_for_period(symbol_data, spy_data, period)
            # Result should be a number (symbol outperforms SPY, so positive RRS expected)
            assert result is not None
            assert isinstance(result, float)
            assert result > 0  # Symbol should outperform SPY in our test scenario
    
    def test_calculate_rrs_for_period_insufficient_data_for_atr(self):
        """Test RRS with insufficient data for 14-day ATR calculation."""
        # Only 10 days of data, less than 15 required for 14-day ATR + 1
        symbol_data, spy_data = self.create_test_scenario_data(10)
        
        result = calculate_rrs_for_period(symbol_data, spy_data, 1)
        
        assert result is None
    
    def test_calculate_rrs_for_period_insufficient_data_for_price_change(self):
        """Test RRS when there's enough data for ATR but not for price changes."""
        # 15 days: enough for 14-day ATR but need 16+ for 15-day price change
        symbol_data, spy_data = self.create_test_scenario_data(15)
        
        # Should work for 1-day and 8-day periods
        result_1day = calculate_rrs_for_period(symbol_data, spy_data, 1)
        result_8day = calculate_rrs_for_period(symbol_data, spy_data, 8)
        
        assert result_1day is not None
        assert result_8day is not None
        
        # Should fail for 15-day period (need 16 days minimum)
        result_15day = calculate_rrs_for_period(symbol_data, spy_data, 15)
        assert result_15day is None
    
    def test_calculate_rrs_for_period_symbol_outperforms(self):
        """Test RRS when symbol significantly outperforms SPY."""
        days = 20
        
        # SPY flat
        spy_prices = [400.0] * days
        
        # Symbol up 2% over the period
        symbol_base = 100.0
        symbol_prices = []
        for i in range(days):
            symbol_prices.append(symbol_base + (i * 0.1))  # Linear increase
        
        spy_data = self.create_market_dataframe(spy_prices)
        symbol_data = self.create_market_dataframe(symbol_prices)
        
        result = calculate_rrs_for_period(symbol_data, spy_data, 8)
        
        assert result is not None
        assert result > 0.4  # Symbol outperforms flat SPY
    
    def test_calculate_rrs_for_period_symbol_underperforms(self):
        """Test RRS when symbol underperforms SPY."""
        days = 20
        
        # SPY up significantly
        spy_base = 400.0
        spy_prices = []
        for i in range(days):
            spy_prices.append(spy_base + (i * 0.5))  # Strong uptrend
        
        # Symbol flat
        symbol_prices = [100.0] * days
        
        spy_data = self.create_market_dataframe(spy_prices)
        symbol_data = self.create_market_dataframe(symbol_prices)
        
        result = calculate_rrs_for_period(symbol_data, spy_data, 8)
        
        assert result is not None
        assert result < -0.5  # Symbol underperforms rising SPY
    
    def test_calculate_rrs_for_period_zero_atr_case(self):
        """Test RRS when ATR is zero (no volatility)."""
        days = 20
        
        # Both symbol and SPY completely flat (no True Range)
        spy_prices = [400.0] * days
        symbol_prices = [100.0] * days
        
        # Create DataFrames with no volatility (high = low = close)
        spy_data = pd.DataFrame([{
            'date': f'2024-01-{i+1:02d}',
            'open': 400.0,
            'high': 400.0,
            'low': 400.0,
            'close': 400.0,
            'volume': 1000000
        } for i in range(days)])
        
        symbol_data = pd.DataFrame([{
            'date': f'2024-01-{i+1:02d}',
            'open': 100.0,
            'high': 100.0,
            'low': 100.0,
            'close': 100.0,
            'volume': 1000000
        } for i in range(days)])
        
        result = calculate_rrs_for_period(symbol_data, spy_data, 8)
        
        # Should return None when ATR is zero
        assert result is None
    
    def test_calculate_rrs_for_period_different_periods_use_same_atr(self):
        """Test that different periods use the same 14-day ATR calculation."""
        symbol_data, spy_data = self.create_test_scenario_data(25)
        
        # Get results for different periods
        results = {}
        for period in [1, 8, 15]:
            results[period] = calculate_rrs_for_period(symbol_data, spy_data, period)
        
        # All should return valid results
        for period, result in results.items():
            assert result is not None, f"Period {period} returned None"
            assert isinstance(result, float), f"Period {period} returned non-float"
        
        # Results should be different (different price change periods)
        assert results[1] != results[8]
        assert results[8] != results[15]
        assert results[1] != results[15]
    
    def test_calculate_rrs_for_period_minimum_data_requirement(self):
        """Test the minimum data requirement logic."""
        # Test with exactly 15 days (minimum for 14-day ATR + 1)
        symbol_data, spy_data = self.create_test_scenario_data(15)
        
        # Should work for 1-day period (needs 2 days minimum, have 15)
        result_1day = calculate_rrs_for_period(symbol_data, spy_data, 1)
        assert result_1day is not None
        
        # Should work for 8-day period (needs 9 days minimum, have 15)
        result_8day = calculate_rrs_for_period(symbol_data, spy_data, 8)
        assert result_8day is not None
        
        # Should not work for 15-day period (needs 16 days minimum, have 15)
        result_15day = calculate_rrs_for_period(symbol_data, spy_data, 15)
        assert result_15day is None
    
    def test_calculate_rrs_for_period_with_realistic_data(self):
        """Test RRS with realistic market-like data patterns."""
        days = 30
        
        # Create more realistic price movements
        np.random.seed(42)  # For reproducible tests
        
        # SPY with random walk
        spy_prices = [400.0]
        for i in range(1, days):
            change = np.random.normal(0, 0.01)  # 1% daily volatility
            new_price = spy_prices[-1] * (1 + change)
            spy_prices.append(max(new_price, 1.0))  # Prevent negative prices
        
        # Symbol with slightly higher volatility and bias
        symbol_prices = [100.0]
        for i in range(1, days):
            change = np.random.normal(0.001, 0.015)  # Slight positive bias, higher vol
            new_price = symbol_prices[-1] * (1 + change)
            symbol_prices.append(max(new_price, 1.0))  # Prevent negative prices
        
        spy_data = self.create_market_dataframe(spy_prices)
        symbol_data = self.create_market_dataframe(symbol_prices)
        
        result = calculate_rrs_for_period(symbol_data, spy_data, 8)
        
        assert result is not None
        assert isinstance(result, float)
        # With our random seed and bias, result should be reasonable
        assert -5.0 < result < 5.0  # Reasonable RRS range


class TestCalculateRealRelativeStrengthDaily:
    """Test suite for calculate_real_relative_strength_daily function."""
    
    def create_ohlcv_data(self, prices: list, start_date: date = date(2024, 1, 1)) -> list[OHLCV]:
        """Create OHLCV test data from a list of prices."""
        data = []
        for i, price in enumerate(prices):
            current_date = start_date + timedelta(days=i)
            # Create realistic OHLC from close price
            high = price * 1.02  # 2% higher than close
            low = price * 0.98   # 2% lower than close
            open_price = price * 1.005  # Slightly higher than close
            
            data.append(OHLCV(
                date=current_date.isoformat(),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(price, 2),
                volume=int(10000 + i * 100)  # Varying volume
            ))
        
        return data
    
    def create_spy_mock_data(self, prices: list, start_date: date = date(2024, 1, 1)) -> list[OHLCV]:
        """Create SPY mock data for testing."""
        return self.create_ohlcv_data(prices, start_date)
    
    def test_calculate_real_relative_strength_daily_normal_case(self):
        """Test RRS calculation with normal data for all periods."""
        # Setup test data
        days = 25
        target_date = date(2024, 1, 20)
        
        # Create symbol data that outperforms
        symbol_prices = [100 + i * 0.2 for i in range(days)]  # Uptrending
        symbol_data = self.create_ohlcv_data(symbol_prices)
        
        # Create SPY data that's flatter
        spy_prices = [400 + i * 0.1 for i in range(days)]  # Slower uptrend
        spy_data = self.create_spy_mock_data(spy_prices)
        
        # Call the function with SPY data
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Verify structure
        assert isinstance(result, dict)
        assert 'rrs_1_day' in result
        assert 'rrs_3_day' in result
        assert 'rrs_8_day' in result
        assert 'rrs_15_day' in result
        
        # All values should be calculated (not None)
        assert result['rrs_1_day'] is not None
        assert result['rrs_3_day'] is not None
        assert result['rrs_8_day'] is not None
        assert result['rrs_15_day'] is not None
        
        # All should be positive (symbol outperforms SPY)
        assert result['rrs_1_day'] > 0
        assert result['rrs_3_day'] > 0
        assert result['rrs_8_day'] > 0
        assert result['rrs_15_day'] > 0
    
    def test_calculate_real_relative_strength_daily_no_market_data(self):
        """Test RRS when no market data is provided."""
        target_date = date(2024, 1, 15)
        spy_data = self.create_spy_mock_data([400, 401, 402])
        
        result = calculate_real_relative_strength_daily([], spy_data, target_date)
        
        # Should return None values for all periods
        assert result == {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
    
    def test_calculate_real_relative_strength_daily_no_spy_data(self):
        """Test RRS when no SPY data is provided."""
        symbol_data = self.create_ohlcv_data([100 + i * 0.1 for i in range(25)])
        target_date = date(2024, 1, 20)
        
        result = calculate_real_relative_strength_daily(symbol_data, [], target_date)
        
        # Should return None values due to missing SPY data
        assert result == {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
    
    def test_calculate_real_relative_strength_daily_target_date_not_found(self):
        """Test RRS when target date is not in the data."""
        # Create data for different dates
        symbol_data = self.create_ohlcv_data([100, 101, 102], date(2024, 1, 1))
        spy_data = self.create_spy_mock_data([400, 401, 402], date(2024, 1, 1))
        target_date = date(2024, 2, 15)  # Date not in the data
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Should return None values
        assert result == {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
    
    def test_calculate_real_relative_strength_daily_insufficient_data(self):
        """Test RRS with insufficient data (less than 20 days)."""
        # Only 10 days of data
        symbol_data = self.create_ohlcv_data([100 + i for i in range(10)])
        spy_data = self.create_spy_mock_data([400 + i for i in range(10)])
        target_date = date(2024, 1, 10)
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Should return None values due to insufficient data
        assert result == {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
    
    def test_calculate_real_relative_strength_daily_mismatched_spy_data(self):
        """Test RRS when SPY data length doesn't match symbol data."""
        # Setup symbol data
        symbol_data = self.create_ohlcv_data([100 + i * 0.1 for i in range(25)])
        target_date = date(2024, 1, 20)
        
        # SPY data with different length - but should still work due to alignment
        spy_data = self.create_spy_mock_data([400 + i * 0.05 for i in range(30)])  # Longer
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Should still work
        assert isinstance(result, dict)
        assert 'rrs_1_day' in result
        assert 'rrs_3_day' in result
        assert 'rrs_8_day' in result
        assert 'rrs_15_day' in result
    
    def test_calculate_real_relative_strength_daily_symbol_underperforms(self):
        """Test RRS when symbol underperforms SPY."""
        days = 25
        target_date = date(2024, 1, 20)
        
        # Create symbol data that's flat
        symbol_data = self.create_ohlcv_data([100] * days)
        
        # Create SPY data that's strongly trending up
        spy_prices = [400 + i * 0.5 for i in range(days)]  # Strong uptrend
        spy_data = self.create_spy_mock_data(spy_prices)
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # All values should be calculated
        assert result['rrs_1_day'] is not None
        assert result['rrs_3_day'] is not None
        assert result['rrs_8_day'] is not None
        assert result['rrs_15_day'] is not None
        
        # All should be negative (symbol underperforms SPY)
        assert result['rrs_8_day'] < 0
        assert result['rrs_15_day'] < 0
    
    def test_calculate_real_relative_strength_daily_edge_case_minimum_data(self):
        """Test RRS with exactly minimum required data."""
        # Exactly 20 days of data (minimum required)
        days = 20
        symbol_data = self.create_ohlcv_data([100 + i * 0.1 for i in range(days)])
        spy_data = self.create_spy_mock_data([400 + i * 0.05 for i in range(days)])
        target_date = date(2024, 1, 20)
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        assert result['rrs_1_day'] is not None
        assert result['rrs_3_day'] is not None
        assert result['rrs_8_day'] is not None
        assert result['rrs_15_day'] is not None
    
    def test_calculate_real_relative_strength_daily_exception_handling(self):
        """Test RRS exception handling."""
        # Setup data that might cause calculation errors - use invalid data types
        symbol_data = "invalid_data"  # Wrong type
        spy_data = self.create_spy_mock_data([400 + i * 0.05 for i in range(25)])
        target_date = date(2024, 1, 20)
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Should return None values when exception occurs
        assert result == {'rrs_1_day': None, 'rrs_3_day': None, 'rrs_8_day': None, 'rrs_15_day': None}
    
    def test_calculate_real_relative_strength_daily_realistic_scenario(self):
        """Test RRS with realistic market scenario."""
        days = 30
        target_date = date(2024, 1, 25)
        
        # Create realistic symbol data with some volatility
        np.random.seed(123)  # For reproducible test
        symbol_prices = [100.0]
        for i in range(1, days):
            change = np.random.normal(0.002, 0.015)  # 0.2% daily return, 1.5% volatility
            new_price = symbol_prices[-1] * (1 + change)
            symbol_prices.append(max(new_price, 1.0))
        
        symbol_data = self.create_ohlcv_data(symbol_prices)
        
        # Create SPY data with lower volatility
        spy_prices = [400.0]
        np.random.seed(456)  # Different seed for SPY
        for i in range(1, days):
            change = np.random.normal(0.001, 0.010)  # 0.1% daily return, 1.0% volatility
            new_price = spy_prices[-1] * (1 + change)
            spy_prices.append(max(new_price, 1.0))
        
        spy_data = self.create_spy_mock_data(spy_prices)
        
        result = calculate_real_relative_strength_daily(symbol_data, spy_data, target_date)
        
        # Should get realistic results
        assert isinstance(result, dict)
        assert all(key in result for key in ['rrs_1_day', 'rrs_3_day', 'rrs_8_day', 'rrs_15_day'])
        
        # Values should be calculated (not None)
        assert all(value is not None for value in result.values())
        
        # Should be reasonable values (not extreme)
        for value in result.values():
            assert -10 < value < 10  # Reasonable range for RRS


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 