# Test Instructions for Tradier Client

## Setup

1. **Install dependencies:**
   ```bash
   cd day_trade_assistant
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file in the `day_trade_assistant` directory with:
   ```
   TRADIER_API_ACCESS_TOKEN=your_actual_tradier_api_key
   TRADIER_BASE_URL=https://api.tradier.com/v1
   ```
   
   Get your API key from: https://developer.tradier.com/getting_started

## Running Tests

### Run all historical data tests:
```bash
pytest tests/test_tradier_client_historical.py -v
```

### Run specific test:
```bash
pytest tests/test_tradier_client_historical.py::TestTradierClientHistorical::test_get_historical_data_basic -v
```

### Run tests with VCR recording (first time):
```bash
# This will make real API calls and record them
pytest tests/test_tradier_client_historical.py -v --vcr-record=once
```

### Run tests with existing recordings (subsequent runs):
```bash
# This will use recorded responses, no API calls made
pytest tests/test_tradier_client_historical.py -v
```

## VCR Cassettes

The tests use VCR (Video Cassette Recorder) to record API interactions:

- **Location:** `tests/fixtures/vcr_cassettes/`
- **Purpose:** Record real API responses for repeatable testing
- **Benefits:** 
  - Tests run fast (no real API calls after first run)
  - Tests are deterministic
  - No API rate limiting issues
  - Tests work offline

### Managing Cassettes

**To re-record all cassettes:**
```bash
rm -rf tests/fixtures/vcr_cassettes/*.yaml
pytest tests/test_tradier_client_historical.py -v
```

**To record only specific test:**
```bash
rm tests/fixtures/vcr_cassettes/historical_data_basic.yaml
pytest tests/test_tradier_client_historical.py::TestTradierClientHistorical::test_get_historical_data_basic -v
```

## Test Coverage

The test suite covers:

- ✅ Basic historical data retrieval
- ✅ Date range filtering (start/end dates)
- ✅ Different time intervals (5min, 15min, 30min, 1hour, daily)
- ✅ Invalid symbol handling
- ✅ Weekend/non-trading day handling
- ✅ API error handling
- ✅ Malformed response handling
- ✅ Partial bad data handling

## Notes

🔧 **First Run:** On first run with a real API key, tests will make actual API calls to Tradier and record the responses. Subsequent runs will use the recorded responses.