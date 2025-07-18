import ccxt
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import logging

from .base import (
    AbstractExchangeAdapter,
    OHLCV,
    FundingRate,
    OpenInterest,
    Ticker,
    TimeFrame,
    ExchangeError,
    RateLimitError,
    APIError,
)

logger = logging.getLogger(__name__)


class BybitAdapter(AbstractExchangeAdapter):
    """Bybit取引所アダプタ"""

    def __init__(self, api_key: str, secret: str, sandbox: bool = False):
        super().__init__(api_key, secret, sandbox)

        # CCXT設定
        self.exchange = ccxt.bybit(
            {
                "apiKey": api_key,
                "secret": secret,
                "sandbox": sandbox,
                "enableRateLimit": True,
                "timeout": 30000,
            }
        )

        # 時間枠マッピング
        self.timeframe_map = {
            TimeFrame.MINUTE_1: "1m",
            TimeFrame.MINUTE_5: "5m",
            TimeFrame.MINUTE_15: "15m",
            TimeFrame.MINUTE_30: "30m",
            TimeFrame.HOUR_1: "1h",
            TimeFrame.HOUR_2: "2h",
            TimeFrame.HOUR_4: "4h",
            TimeFrame.HOUR_8: "8h",
            TimeFrame.DAY_1: "1d",
            TimeFrame.WEEK_1: "1w",
            TimeFrame.MONTH_1: "1M",
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """OHLCV データを取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            ccxt_timeframe = self.timeframe_map[timeframe]

            # since を timestamp に変換
            since_timestamp = None
            if since:
                since_timestamp = int(since.timestamp() * 1000)

            # 非同期でデータを取得
            ohlcv_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.exchange.fetch_ohlcv(
                    normalized_symbol, ccxt_timeframe, since_timestamp, limit
                ),
            )

            # OHLCV オブジェクトに変換
            ohlcv_list = []
            for data in ohlcv_data:
                ohlcv = OHLCV(
                    timestamp=datetime.fromtimestamp(data[0] / 1000, tz=timezone.utc),
                    open=float(data[1]),
                    high=float(data[2]),
                    low=float(data[3]),
                    close=float(data[4]),
                    volume=float(data[5]),
                )
                ohlcv_list.append(ohlcv)

            logger.info(f"Fetched {len(ohlcv_list)} OHLCV records for {symbol}")
            return ohlcv_list

        except ccxt.RateLimitExceeded as e:
            logger.warning(f"Rate limit exceeded for {symbol}: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}")
        except ccxt.BaseError as e:
            logger.error(f"CCXT error for {symbol}: {e}")
            raise APIError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching OHLCV for {symbol}: {e}")
            raise ExchangeError(f"Unexpected error: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            # Bybitの先物用エンドポイントを使用
            funding_info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_funding_rate(normalized_symbol)
            )

            funding_rate = FundingRate(
                timestamp=datetime.fromtimestamp(
                    funding_info["timestamp"] / 1000, tz=timezone.utc
                ),
                symbol=normalized_symbol,
                funding_rate=float(funding_info["fundingRate"]),
                next_funding_time=datetime.fromtimestamp(
                    funding_info["fundingTimestamp"] / 1000, tz=timezone.utc
                ),
            )

            logger.info(
                f"Fetched funding rate for {symbol}: {funding_rate.funding_rate}"
            )
            return funding_rate

        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}")
        except ccxt.BaseError as e:
            raise APIError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            raise ExchangeError(f"Unexpected error: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_open_interest(self, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            # Bybitの建玉情報を取得
            oi_info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_open_interest(normalized_symbol)
            )

            open_interest = OpenInterest(
                timestamp=datetime.fromtimestamp(
                    oi_info["timestamp"] / 1000, tz=timezone.utc
                ),
                symbol=normalized_symbol,
                open_interest=float(oi_info["openInterestAmount"]),
                open_interest_value=float(oi_info["openInterestValue"]),
            )

            logger.info(
                f"Fetched open interest for {symbol}: {open_interest.open_interest}"
            )
            return open_interest

        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}")
        except ccxt.BaseError as e:
            raise APIError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            raise ExchangeError(f"Unexpected error: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """ティッカーデータを取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            ticker_data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_ticker(normalized_symbol)
            )

            ticker = Ticker(
                timestamp=datetime.fromtimestamp(
                    ticker_data["timestamp"] / 1000, tz=timezone.utc
                ),
                symbol=normalized_symbol,
                bid=float(ticker_data["bid"]),
                ask=float(ticker_data["ask"]),
                last=float(ticker_data["last"]),
                volume=float(ticker_data["baseVolume"]),
            )

            return ticker

        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}")
        except ccxt.BaseError as e:
            raise APIError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise ExchangeError(f"Unexpected error: {e}")

    async def get_symbols(self) -> List[str]:
        """利用可能なシンボル一覧を取得"""
        try:
            markets = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.load_markets()
            )

            symbols = list(markets.keys())
            logger.info(f"Fetched {len(symbols)} symbols from Bybit")
            return symbols

        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise ExchangeError(f"Error fetching symbols: {e}")

    async def get_balance(self) -> Dict[str, float]:
        """残高を取得"""
        try:
            balance = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_balance()
            )

            # フリー残高のみを返す
            free_balance = {
                asset: float(info["free"])
                for asset, info in balance.items()
                if isinstance(info, dict) and "free" in info and float(info["free"]) > 0
            }

            logger.info(f"Fetched balance for {len(free_balance)} assets")
            return free_balance

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise ExchangeError(f"Error fetching balance: {e}")

    def normalize_symbol(self, symbol: str) -> str:
        """Bybit用のシンボル正規化"""
        # BTC/USDT -> BTCUSDT (Bybitでは/区切りを使用)
        return symbol.upper()

    async def close(self):
        """接続を閉じる"""
        if self.exchange:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.close()
            )
