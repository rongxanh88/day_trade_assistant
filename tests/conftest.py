import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Set up test environment variables if not already set
if "TRADIER_API_ACCESS_TOKEN" not in os.environ:
    os.environ["TRADIER_API_ACCESS_TOKEN"] = "test_api_key_for_vcr"

# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers and other settings."""
    config.addinivalue_line(
        "markers", "vcr: mark test as using VCR for API recording"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


@pytest.fixture(scope="session")
def vcr_config():
    """Default VCR configuration for all tests."""
    return {
        "cassette_library_dir": "tests/fixtures/vcr_cassettes",
        "record_mode": "once",
        "match_on": ["uri", "method"],
        "filter_headers": ["authorization"],
        "decode_compressed_response": True,
    }
