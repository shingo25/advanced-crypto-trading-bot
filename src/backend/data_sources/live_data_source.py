"""
実データソース実装
実際の取引所からリアルタイムデータを取得
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.backend.exchanges.base import (
    OHLCV,
    ExchangeError,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)
from src.backend.exchanges.factory import ExchangeFactory

from .interfaces import DataSourceStrategy

logger = logging.getLogger(__name__)


class LiveDataSource(DataSourceStrategy):
    """実データソースの実装"""

    def __init__(self):
        self._adapters: Dict[str, object] = {}
        self._sandbox_mode = False  # 本番APIを使用

    def _get_adapter(self, exchange: str):
        """取引所アダプタを取得（キャッシュ付き）"""
        if exchange not in self._adapters:
            try:
                adapter = ExchangeFactory.create_adapter(exchange, sandbox=self._sandbox_mode)
                self._adapters[exchange] = adapter
                logger.info(f"Created adapter for {exchange} (sandbox={self._sandbox_mode})")
            except Exception as e:
                logger.error(f"Failed to create adapter for {exchange}: {e}")
                raise ExchangeError(f"Exchange {exchange} not available: {e}")
        
        return self._adapters[exchange]

    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """実際のティッカーデータを取得"""
        adapter = self._get_adapter(exchange)
        
        try:
            ticker = await adapter.fetch_ticker(symbol)
            logger.debug(f"Fetched ticker for {symbol} from {exchange}: {ticker.last}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker from {exchange}: {e}")
            raise

    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """実際のOHLCVデータを取得"""
        adapter = self._get_adapter(exchange)
        
        try:
            ohlcv_list = await adapter.fetch_ohlcv(symbol, timeframe, since, limit)
            logger.debug(f"Fetched {len(ohlcv_list)} OHLCV records for {symbol} from {exchange}")
            return ohlcv_list
        except Exception as e:
            logger.error(f"Error fetching OHLCV from {exchange}: {e}")
            raise

    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """実際の資金調達率を取得"""
        adapter = self._get_adapter(exchange)
        
        try:
            funding_rate = await adapter.fetch_funding_rate(symbol)
            logger.debug(f"Fetched funding rate for {symbol} from {exchange}: {funding_rate.funding_rate}")
            return funding_rate
        except Exception as e:
            logger.error(f"Error fetching funding rate from {exchange}: {e}")
            raise

    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """実際の建玉データを取得"""
        adapter = self._get_adapter(exchange)
        
        try:
            open_interest = await adapter.fetch_open_interest(symbol)
            logger.debug(f"Fetched open interest for {symbol} from {exchange}: {open_interest.open_interest}")
            return open_interest
        except Exception as e:
            logger.error(f"Error fetching open interest from {exchange}: {e}")
            raise

    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """実際の残高を取得"""
        adapter = self._get_adapter(exchange)
        
        try:
            balance = await adapter.get_balance()
            logger.debug(f"Fetched balance from {exchange}: {len(balance)} assets")
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange}: {e}")
            raise

    async def is_available(self, exchange: str) -> bool:
        """取引所が利用可能かチェック"""
        try:
            adapter = self._get_adapter(exchange)
            return await adapter.health_check()
        except Exception as e:
            logger.warning(f"Exchange {exchange} is not available: {e}")
            return False

    async def close(self):
        """すべてのアダプタ接続を閉じる"""
        for exchange, adapter in self._adapters.items():
            try:
                if hasattr(adapter, 'close'):
                    await adapter.close()
                    logger.info(f"Closed connection for {exchange}")
            except Exception as e:
                logger.error(f"Error closing adapter for {exchange}: {e}")