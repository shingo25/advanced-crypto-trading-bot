from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class TimeFrame(Enum):
    """時間枠の定義"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_8 = "8h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


@dataclass
class OHLCV:
    """OHLCV データ構造"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class FundingRate:
    """資金調達率データ構造"""
    timestamp: datetime
    symbol: str
    funding_rate: float
    next_funding_time: datetime


@dataclass
class OpenInterest:
    """建玉データ構造"""
    timestamp: datetime
    symbol: str
    open_interest: float
    open_interest_value: float


@dataclass
class Ticker:
    """ティッカーデータ構造"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float


class ExchangeError(Exception):
    """取引所エラーの基底クラス"""
    pass


class RateLimitError(ExchangeError):
    """レート制限エラー"""
    pass


class APIError(ExchangeError):
    """API エラー"""
    pass


class AbstractExchangeAdapter(ABC):
    """取引所アダプタの抽象基底クラス"""
    
    def __init__(self, api_key: str, secret: str, sandbox: bool = False):
        self.api_key = api_key
        self.secret = secret
        self.sandbox = sandbox
        self.name = self.__class__.__name__.replace('Adapter', '').lower()
    
    @abstractmethod
    async def fetch_ohlcv(self, 
                         symbol: str, 
                         timeframe: TimeFrame,
                         since: Optional[datetime] = None,
                         limit: int = 1000) -> List[OHLCV]:
        """OHLCV データを取得"""
        pass
    
    @abstractmethod
    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        pass
    
    @abstractmethod
    async def fetch_open_interest(self, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        pass
    
    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """ティッカーデータを取得"""
        pass
    
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """利用可能なシンボル一覧を取得"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """残高を取得"""
        pass
    
    def to_dataframe(self, ohlcv_list: List[OHLCV]) -> pd.DataFrame:
        """OHLCV リストを DataFrame に変換"""
        if not ohlcv_list:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        data = []
        for ohlcv in ohlcv_list:
            data.append({
                'timestamp': ohlcv.timestamp,
                'open': ohlcv.open,
                'high': ohlcv.high,
                'low': ohlcv.low,
                'close': ohlcv.close,
                'volume': ohlcv.volume
            })
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        return df
    
    def normalize_symbol(self, symbol: str) -> str:
        """シンボルを正規化"""
        return symbol.upper().replace('/', '')
    
    def validate_timeframe(self, timeframe: TimeFrame) -> bool:
        """時間枠の有効性を検証"""
        return timeframe in TimeFrame
    
    async def health_check(self) -> bool:
        """接続状態を確認"""
        try:
            await self.get_symbols()
            return True
        except Exception:
            return False