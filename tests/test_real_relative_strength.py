import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.real_relative_strength import calculate_wilders_average, calculate_true_range


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 