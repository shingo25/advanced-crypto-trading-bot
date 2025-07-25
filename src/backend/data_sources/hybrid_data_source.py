"""
ハイブリッドデータソース実装
条件に応じてモックデータと実データを使い分け
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from src.backend.exchanges.base import (
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)

from .interfaces import DataSourceStrategy
from .live_data_source import LiveDataSource
from .mock_data_source import MockDataSource

logger = logging.getLogger(__name__)


class HybridDataSource(DataSourceStrategy):
    """
    ハイブリッドデータソースの実装
    
    以下の条件で自動的にデータソースを切り替え：
    - 指定された取引所がホワイトリストにある場合は実データ
    - API接続エラーが発生した場合はモックデータにフォールバック
    - 特定のシンボルのみ実データを使用する設定も可能
    """

    def __init__(
        self,
        live_exchanges: Optional[Set[str]] = None,
        live_symbols: Optional[Set[str]] = None,
        fallback_to_mock: bool = True,
    ):
        """
        Args:
            live_exchanges: 実データを使用する取引所のセット
            live_symbols: 実データを使用するシンボルのセット
            fallback_to_mock: エラー時にモックにフォールバックするか
        """
        self.mock_source = MockDataSource()
        self.live_source = LiveDataSource()
        
        # デフォルトは全てモック
        self.live_exchanges = live_exchanges or set()
        self.live_symbols = live_symbols or set()
        self.fallback_to_mock = fallback_to_mock
        
        # エラーカウンター（一定回数エラーが続いたら一時的にモックに切り替え）
        self._error_counts: Dict[str, int] = {}
        self._max_errors = 5

    def _should_use_live(self, exchange: str, symbol: str) -> bool:
        """実データを使用すべきか判定"""
        # エラーが多発している場合はモックを使用
        if self._error_counts.get(exchange, 0) >= self._max_errors:
            logger.warning(f"Too many errors for {exchange}, using mock data")
            return False
        
        # ホワイトリストチェック
        if self.live_exchanges and exchange in self.live_exchanges:
            return True
        
        if self.live_symbols and symbol in self.live_symbols:
            return True
        
        return False

    def _record_error(self, exchange: str):
        """エラーを記録"""
        self._error_counts[exchange] = self._error_counts.get(exchange, 0) + 1

    def _clear_error(self, exchange: str):
        """エラーカウントをクリア"""
        if exchange in self._error_counts:
            self._error_counts[exchange] = 0

    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """ティッカーデータを取得"""
        if self._should_use_live(exchange, symbol):
            try:
                result = await self.live_source.get_ticker(exchange, symbol)
                self._clear_error(exchange)
                logger.debug(f"Using live ticker for {symbol} from {exchange}")
                return result
            except Exception as e:
                self._record_error(exchange)
                logger.warning(f"Failed to get live ticker, falling back to mock: {e}")
                if not self.fallback_to_mock:
                    raise
        
        logger.debug(f"Using mock ticker for {symbol} from {exchange}")
        return await self.mock_source.get_ticker(exchange, symbol)

    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """OHLCVデータを取得"""
        if self._should_use_live(exchange, symbol):
            try:
                result = await self.live_source.get_ohlcv(exchange, symbol, timeframe, since, limit)
                self._clear_error(exchange)
                logger.debug(f"Using live OHLCV for {symbol} from {exchange}")
                return result
            except Exception as e:
                self._record_error(exchange)
                logger.warning(f"Failed to get live OHLCV, falling back to mock: {e}")
                if not self.fallback_to_mock:
                    raise
        
        logger.debug(f"Using mock OHLCV for {symbol} from {exchange}")
        return await self.mock_source.get_ohlcv(exchange, symbol, timeframe, since, limit)

    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        if self._should_use_live(exchange, symbol):
            try:
                result = await self.live_source.get_funding_rate(exchange, symbol)
                self._clear_error(exchange)
                logger.debug(f"Using live funding rate for {symbol} from {exchange}")
                return result
            except Exception as e:
                self._record_error(exchange)
                logger.warning(f"Failed to get live funding rate, falling back to mock: {e}")
                if not self.fallback_to_mock:
                    raise
        
        logger.debug(f"Using mock funding rate for {symbol} from {exchange}")
        return await self.mock_source.get_funding_rate(exchange, symbol)

    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        if self._should_use_live(exchange, symbol):
            try:
                result = await self.live_source.get_open_interest(exchange, symbol)
                self._clear_error(exchange)
                logger.debug(f"Using live open interest for {symbol} from {exchange}")
                return result
            except Exception as e:
                self._record_error(exchange)
                logger.warning(f"Failed to get live open interest, falling back to mock: {e}")
                if not self.fallback_to_mock:
                    raise
        
        logger.debug(f"Using mock open interest for {symbol} from {exchange}")
        return await self.mock_source.get_open_interest(exchange, symbol)

    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """残高を取得"""
        if self._should_use_live(exchange, ""):
            try:
                result = await self.live_source.get_balance(exchange)
                self._clear_error(exchange)
                logger.debug(f"Using live balance from {exchange}")
                return result
            except Exception as e:
                self._record_error(exchange)
                logger.warning(f"Failed to get live balance, falling back to mock: {e}")
                if not self.fallback_to_mock:
                    raise
        
        logger.debug(f"Using mock balance for {exchange}")
        return await self.mock_source.get_balance(exchange)

    async def is_available(self, exchange: str) -> bool:
        """利用可能かチェック"""
        # まず実データソースをチェック
        if exchange in self.live_exchanges:
            if await self.live_source.is_available(exchange):
                return True
        
        # モックデータソースは常に利用可能
        return await self.mock_source.is_available(exchange)

    def enable_live_exchange(self, exchange: str):
        """特定の取引所の実データを有効化"""
        self.live_exchanges.add(exchange)
        logger.info(f"Enabled live data for {exchange}")

    def disable_live_exchange(self, exchange: str):
        """特定の取引所の実データを無効化"""
        self.live_exchanges.discard(exchange)
        logger.info(f"Disabled live data for {exchange}")

    def reset_error_counts(self):
        """エラーカウントをリセット"""
        self._error_counts.clear()
        logger.info("Reset all error counts")