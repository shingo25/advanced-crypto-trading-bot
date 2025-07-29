"""
データソースマネージャー
環境変数に基づいて適切なデータソース戦略を選択・管理
"""

import logging
import os
from enum import Enum
from typing import Dict, List, Optional, Set

from src.backend.core.config import settings
from src.backend.exchanges.base import (
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)

from .hybrid_data_source import HybridDataSource
from .interfaces import DataSourceStrategy
from .live_data_source import LiveDataSource
from .mock_data_source import MockDataSource

logger = logging.getLogger(__name__)


class DataSourceMode(Enum):
    """データソースモード"""

    MOCK = "mock"
    LIVE = "live"
    HYBRID = "hybrid"


class DataSourceManager:
    """
    データソースの管理と切り替えを行うマネージャー

    環境変数やランタイム設定に基づいて、適切なデータソース戦略を選択します。
    """

    def __init__(self):
        self._mode = self._get_mode_from_env()
        self._strategy = self._create_strategy()

        logger.info(f"DataSourceManager initialized with mode: {self._mode.value}")

    def _get_mode_from_env(self) -> DataSourceMode:
        """環境変数からデータソースモードを取得"""
        mode_str = os.getenv("DATA_SOURCE_MODE", "mock").lower()

        # USE_MOCK_DATA環境変数も考慮（後方互換性）
        if os.getenv("USE_MOCK_DATA", "true").lower() == "false":
            mode_str = "live"

        try:
            return DataSourceMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid DATA_SOURCE_MODE: {mode_str}, defaulting to MOCK")
            return DataSourceMode.MOCK

    def _create_strategy(self) -> DataSourceStrategy:
        """現在のモードに基づいて戦略を作成"""
        if self._mode == DataSourceMode.MOCK:
            logger.info("Using MOCK data source")
            return MockDataSource()

        elif self._mode == DataSourceMode.LIVE:
            logger.info("Using LIVE data source")
            return LiveDataSource()

        elif self._mode == DataSourceMode.HYBRID:
            # ハイブリッドモードの設定を環境変数から読み込み
            live_exchanges = self._parse_exchange_list(os.getenv("HYBRID_LIVE_EXCHANGES", ""))
            live_symbols = self._parse_symbol_list(os.getenv("HYBRID_LIVE_SYMBOLS", ""))

            logger.info(f"Using HYBRID data source with live exchanges: {live_exchanges}, live symbols: {live_symbols}")

            return HybridDataSource(live_exchanges=live_exchanges, live_symbols=live_symbols, fallback_to_mock=True)

        else:
            raise ValueError(f"Unknown data source mode: {self._mode}")

    def _parse_exchange_list(self, exchanges_str: str) -> Set[str]:
        """カンマ区切りの取引所リストをパース"""
        if not exchanges_str:
            return set()
        return {ex.strip().lower() for ex in exchanges_str.split(",") if ex.strip()}

    def _parse_symbol_list(self, symbols_str: str) -> Set[str]:
        """カンマ区切りのシンボルリストをパース"""
        if not symbols_str:
            return set()
        return {sym.strip().upper() for sym in symbols_str.split(",") if sym.strip()}

    @property
    def mode(self) -> DataSourceMode:
        """現在のデータソースモード"""
        return self._mode

    @property
    def strategy(self) -> DataSourceStrategy:
        """現在のデータソース戦略"""
        return self._strategy

    def set_mode(self, mode: DataSourceMode):
        """データソースモードを変更"""
        if mode != self._mode:
            logger.info(f"Changing data source mode from {self._mode.value} to {mode.value}")
            self._mode = mode
            self._strategy = self._create_strategy()

    def set_strategy(self, strategy: DataSourceStrategy):
        """カスタム戦略を設定"""
        logger.info(f"Setting custom data source strategy: {type(strategy).__name__}")
        self._strategy = strategy

    # データソース戦略へのプロキシメソッド
    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """ティッカーデータを取得"""
        return await self._strategy.get_ticker(exchange, symbol)

    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """OHLCVデータを取得"""
        return await self._strategy.get_ohlcv(exchange, symbol, timeframe, since, limit)

    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        return await self._strategy.get_funding_rate(exchange, symbol)

    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        return await self._strategy.get_open_interest(exchange, symbol)

    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """残高を取得"""
        return await self._strategy.get_balance(exchange)

    async def is_available(self, exchange: str) -> bool:
        """データソースが利用可能かチェック"""
        return await self._strategy.is_available(exchange)

    def get_status(self) -> Dict[str, any]:
        """現在のステータスを取得"""
        status = {
            "mode": self._mode.value,
            "strategy": type(self._strategy).__name__,
            "is_live": self._mode == DataSourceMode.LIVE,
            "is_mock": self._mode == DataSourceMode.MOCK,
            "is_hybrid": self._mode == DataSourceMode.HYBRID,
        }

        # ハイブリッドモードの場合は追加情報
        if isinstance(self._strategy, HybridDataSource):
            status.update(
                {
                    "live_exchanges": list(self._strategy.live_exchanges),
                    "live_symbols": list(self._strategy.live_symbols),
                }
            )

        return status


# シングルトンインスタンス
data_source_manager = DataSourceManager()
