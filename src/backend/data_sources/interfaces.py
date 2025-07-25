"""
データソース戦略のインターフェース定義
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from src.backend.exchanges.base import (
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
)


class DataSourceStrategy(ABC):
    """データソース戦略の抽象基底クラス"""

    @abstractmethod
    async def get_ticker(self, exchange: str, symbol: str) -> Ticker:
        """
        最新のティッカーデータを取得
        
        Args:
            exchange: 取引所名
            symbol: シンボル（例: BTC/USDT）
        
        Returns:
            Ticker: ティッカーデータ
        """
        pass

    @abstractmethod
    async def get_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """
        OHLCV（ローソク足）データを取得
        
        Args:
            exchange: 取引所名
            symbol: シンボル
            timeframe: 時間枠
            since: 開始時刻
            limit: 取得件数
        
        Returns:
            List[OHLCV]: OHLCVデータのリスト
        """
        pass

    @abstractmethod
    async def get_funding_rate(self, exchange: str, symbol: str) -> FundingRate:
        """
        資金調達率を取得
        
        Args:
            exchange: 取引所名
            symbol: シンボル
        
        Returns:
            FundingRate: 資金調達率データ
        """
        pass

    @abstractmethod
    async def get_open_interest(self, exchange: str, symbol: str) -> OpenInterest:
        """
        建玉データを取得
        
        Args:
            exchange: 取引所名
            symbol: シンボル
        
        Returns:
            OpenInterest: 建玉データ
        """
        pass

    @abstractmethod
    async def get_balance(self, exchange: str) -> Dict[str, float]:
        """
        残高を取得
        
        Args:
            exchange: 取引所名
        
        Returns:
            Dict[str, float]: 通貨別の残高
        """
        pass

    @abstractmethod
    async def is_available(self, exchange: str) -> bool:
        """
        データソースが利用可能かチェック
        
        Args:
            exchange: 取引所名
        
        Returns:
            bool: 利用可能な場合True
        """
        pass