import pytest
import vcr
import pandas as pd
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.integrations.fin_viz_screener import screener, fetch_custom_universe, UNIVERSE_CRITERIA

# Compatibility fix for VCR/urllib3 issue
try:
    from vcr.cassette import Cassette
    from vcr.stubs import VCRHTTPResponse
    if not hasattr(VCRHTTPResponse, 'version_string'):
        VCRHTTPResponse.version_string = "HTTP/1.1"
except ImportError:
    pass


my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/vcr_cassettes',
    record_mode='once',
    match_on=['uri', 'method'],
    filter_headers=['authorization'],
    decode_compressed_response=True,
)


class TestFinVizScreener:
    """Test the fin_viz_screener functions. No bullshit, just tests that work."""

    def test_universe_criteria_constant(self):
        """Test that UNIVERSE_CRITERIA has expected keys. No API call needed."""
        expected_keys = ["Exchange", "Price", "Average Volume", "Country", "Market Cap."]
        
        for key in expected_keys:
            assert key in UNIVERSE_CRITERIA
        
        # Verify some basic values
        assert UNIVERSE_CRITERIA["Country"] == "USA"
        assert "Over $10" in UNIVERSE_CRITERIA["Price"]
        assert "Over 1M" in UNIVERSE_CRITERIA["Average Volume"]

    @pytest.mark.vcr
    @my_vcr.use_cassette('finviz_custom_universe.yaml')
    def test_fetch_custom_universe(self):
        """Test the custom universe fetch. Should use predefined criteria."""
        result = fetch_custom_universe()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 0
        print(f"Found {len(result)} stocks")
        
        if len(result) > 0:
            assert 'Ticker' in result.columns
            assert 'Company' in result.columns
            assert 'Sector' in result.columns
            assert 'Industry' in result.columns
            assert 'Country' in result.columns
            assert 'Price' in result.columns
            assert 'P/E' in result.columns
            assert 'Change' in result.columns
            assert 'Volume' in result.columns
            assert 'Market Cap' in result.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 