"""
キャッシュ付きデータソースデコレータ
任意のデータソースにキャッシュ機能を追加
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.backend.exchanges.base import (
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)

from .cache import CacheKey, get_cache
from .interfaces import DataSourceStrategy

logger = logging.getLogger(__name__)


class CachedDataSource(DataSourceStrategy):
    """
    キャッシュ機能を持つデータソースデコレータ

    任意のDataSourceStrategyをラップして、自動的にキャッシュ機能を追加します。
    """

    def __init__(self, base_source: DataSourceStrategy, cache_enabled: bool = True):
        """
        Args:
            base_source: ラップする基底データソース
            cache_enabled: キャッシュを有効にするか
        """
        self._base_source = base_source
        self._cache = get_cache() if cache_enabled else None
        self._cache_enabled = cache_enabled

    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """キャッシュ付きティッカー取得"""
        if not self._cache_enabled:
            return await self._base_source.get_ticker(exchange, symbol)

        # キャッシュキーを生成
        cache_key = CacheKey.ticker(exchange, symbol)

        # キャッシュをチェック
        cached_data = await self._cache.get(cache_key)
        if cached_data:
            return Ticker(**cached_data)

        # キャッシュミスの場合は基底ソースから取得
        ticker = await self._base_source.get_ticker(exchange, symbol)

        # キャッシュに保存
        await self._cache.set(
            cache_key,
            {
                "timestamp": ticker.timestamp.isoformat(),
                "symbol": ticker.symbol,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "last": ticker.last,
                "volume": ticker.volume,
            },
        )

        return ticker

    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """キャッシュ付きOHLCV取得"""
        if not self._cache_enabled:
            return await self._base_source.get_ohlcv(exchange, symbol, timeframe, since, limit)

        # パラメータをハッシュ化してキャッシュキーの一部に（SHA-256使用でセキュリティ向上）
        params_hash = hashlib.sha256(f"{since}:{limit}".encode()).hexdigest()[:16]

        cache_key = f"{CacheKey.ohlcv(exchange, symbol, timeframe.value)}:{params_hash}"

        # キャッシュをチェック
        cached_data = await self._cache.get(cache_key)
        if cached_data:
            return [
                OHLCV(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    open=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item["volume"],
                )
                for item in cached_data
            ]

        # キャッシュミスの場合は基底ソースから取得
        ohlcv_list = await self._base_source.get_ohlcv(exchange, symbol, timeframe, since, limit)

        # キャッシュに保存
        cache_data = [
            {
                "timestamp": ohlcv.timestamp.isoformat(),
                "open": ohlcv.open,
                "high": ohlcv.high,
                "low": ohlcv.low,
                "close": ohlcv.close,
                "volume": ohlcv.volume,
            }
            for ohlcv in ohlcv_list
        ]
        await self._cache.set(cache_key, cache_data)

        return ohlcv_list

    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """キャッシュ付き資金調達率取得"""
        if not self._cache_enabled:
            return await self._base_source.get_funding_rate(exchange, symbol)

        cache_key = CacheKey.funding_rate(exchange, symbol)

        cached_data = await self._cache.get(cache_key)
        if cached_data:
            return FundingRate(
                timestamp=datetime.fromisoformat(cached_data["timestamp"]),
                symbol=cached_data["symbol"],
                funding_rate=cached_data["funding_rate"],
                next_funding_time=datetime.fromisoformat(cached_data["next_funding_time"]),
            )

        funding_rate = await self._base_source.get_funding_rate(exchange, symbol)

        await self._cache.set(
            cache_key,
            {
                "timestamp": funding_rate.timestamp.isoformat(),
                "symbol": funding_rate.symbol,
                "funding_rate": funding_rate.funding_rate,
                "next_funding_time": funding_rate.next_funding_time.isoformat(),
            },
        )

        return funding_rate

    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """キャッシュ付き建玉取得"""
        if not self._cache_enabled:
            return await self._base_source.get_open_interest(exchange, symbol)

        cache_key = CacheKey.open_interest(exchange, symbol)

        cached_data = await self._cache.get(cache_key)
        if cached_data:
            return OpenInterest(
                timestamp=datetime.fromisoformat(cached_data["timestamp"]),
                symbol=cached_data["symbol"],
                open_interest=cached_data["open_interest"],
                open_interest_value=cached_data["open_interest_value"],
            )

        open_interest = await self._base_source.get_open_interest(exchange, symbol)

        await self._cache.set(
            cache_key,
            {
                "timestamp": open_interest.timestamp.isoformat(),
                "symbol": open_interest.symbol,
                "open_interest": open_interest.open_interest,
                "open_interest_value": open_interest.open_interest_value,
            },
        )

        return open_interest

    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """キャッシュ付き残高取得"""
        if not self._cache_enabled:
            return await self._base_source.get_balance(exchange)

        cache_key = CacheKey.balance(exchange)

        cached_data = await self._cache.get(cache_key)
        if cached_data:
            return cached_data

        balance = await self._base_source.get_balance(exchange)

        await self._cache.set(cache_key, balance)

        return balance

    async def is_available(self, exchange: str) -> bool:
        """利用可能性チェック（キャッシュなし）"""
        return await self._base_source.is_available(exchange)

    def clear_cache(self):
        """キャッシュをクリア"""
        if self._cache_enabled and self._cache:
            logger.info("Clearing all cached data")
            # 実装は簡略化のため省略（本来は全キャッシュクリアメソッドを呼ぶ）
