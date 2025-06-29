import logging
from datetime import datetime, date
from typing import List, Dict, Any
import httpx
from config.settings import settings
from src.data.models import Quote, OHLCV, Position, MarketHours


logger = logging.getLogger(__name__)


class TradierClient:
    """Async client for Tradier API integration."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.tradier_api_key
        self.base_url = settings.tradier_base_url
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict[Any, Any]:
        """Make an async HTTP request to Tradier API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    data=data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                raise
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        params = {"symbols": symbol}
        data = await self._make_request("GET", "/markets/quotes", params=params)
        
        if "quotes" not in data or not data["quotes"]["quote"]:
            raise ValueError(f"No quote data for symbol {symbol}")
        
        quote_data = data["quotes"]["quote"]
        if isinstance(quote_data, list):
            quote_data = quote_data[0]
        
        return Quote(
            symbol=quote_data["symbol"],
            price=float(quote_data["last"]),
            bid=float(quote_data["bid"]),
            ask=float(quote_data["ask"]),
            volume=int(quote_data["volume"]),
            timestamp=datetime.now(),
            change=float(quote_data["change"]),
            change_percent=float(quote_data["change_percentage"])
        )
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes for multiple symbols."""
        if not symbols:
            return {}
        
        symbol_str = ",".join(symbols)
        params = {"symbols": symbol_str}
        data = await self._make_request("GET", "/markets/quotes", params=params)
        
        quotes = {}
        if "quotes" in data and data["quotes"]["quote"]:
            quote_list = data["quotes"]["quote"]
            if not isinstance(quote_list, list):
                quote_list = [quote_list]
            
            for quote_data in quote_list:
                try:
                    quote = Quote(
                        symbol=quote_data["symbol"],
                        price=float(quote_data["last"]),
                        bid=float(quote_data["bid"]),
                        ask=float(quote_data["ask"]),
                        volume=int(quote_data["volume"]),
                        timestamp=datetime.now(),
                        change=float(quote_data["change"]),
                        change_percent=float(quote_data["change_percentage"])
                    )
                    quotes[quote.symbol] = quote
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse quote for {quote_data.get('symbol', 'unknown')}: {e}")
        
        return quotes
    
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: str = "15min", 
        start: date = None, 
        end: date = None
    ) -> List[OHLCV]:
        """Get historical OHLCV data for a symbol."""
        params = {
            "symbol": symbol,
            "interval": interval
        }
        
        if start:
            params["start"] = start.strftime("%Y-%m-%d")
        if end:
            params["end"] = end.strftime("%Y-%m-%d")
        
        data = await self._make_request("GET", "/markets/history", params=params)
        
        if "history" not in data or not data["history"]:
            return []
        
        history_data = data["history"]["day"] if "day" in data["history"] else []
        if not isinstance(history_data, list):
            history_data = [history_data]
        
        ohlcv_data = []
        for bar in history_data:
            try:
                ohlcv = OHLCV(
                    timestamp=datetime.fromisoformat(bar["date"]),
                    open=float(bar["open"]),
                    high=float(bar["high"]),
                    low=float(bar["low"]),
                    close=float(bar["close"]),
                    volume=int(bar["volume"])
                )
                ohlcv_data.append(ohlcv)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse OHLCV data: {e}")
        
        return ohlcv_data


# Singleton instance for easy access
tradier_client = TradierClient() 