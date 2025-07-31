import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlencode

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import aiohttp

from .base import (
    OHLCV,
    AbstractExchangeAdapter,
    APIError,
    ExchangeError,
    FundingRate,
    OpenInterest,
    RateLimitError,
    Ticker,
    TimeFrame,
)

logger = logging.getLogger(__name__)


class BackpackAdapter(AbstractExchangeAdapter):
    """BackPack Exchange取引所アダプタ（独自API）"""

    def __init__(self, api_key: str, secret: str, sandbox: bool = False):
        super().__init__(api_key, secret, sandbox)

        # BackPack API設定
        self.base_url = (
            "https://api.backpack.exchange" if not sandbox else "https://api.backpack.exchange"
        )  # テストネット未確認

        # セッション管理
        self.session: Optional[aiohttp.ClientSession] = None

        # 時間枠マッピング（BackPack形式）
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

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP セッションを取得"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"Content-Type": "application/json", "User-Agent": "crypto-bot/1.0"}
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session

    def _generate_signature(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """BackPack API署名を生成"""
        timestamp = str(int(time.time() * 1000))

        # 署名文字列を作成
        message = f"{method}{path}{body}{timestamp}"

        # HMAC-SHA256で署名
        signature = hmac.new(self.secret.encode("utf-8"), message.encode("utf-8"), digestmod="sha256").hexdigest()

        return {
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

    async def _make_request(self, path: str, method: str = "GET", data: Dict = None, auth: bool = False) -> Dict:
        """HTTP リクエストを実行"""
        session = await self._get_session()
        url = f"{self.base_url}{path}"

        headers = {}
        body = ""

        if auth:
            if data and method.upper() == "POST":
                body = json.dumps(data)
            elif data and method.upper() == "GET":
                query_string = urlencode(data)
                url += f"?{query_string}"

            auth_headers = self._generate_signature(method.upper(), path, body)
            headers.update(auth_headers)

        try:
            if method.upper() == "POST":
                if auth:
                    async with session.post(url, data=body, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
                else:
                    async with session.post(url, json=data, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
            else:
                async with session.get(url, params=data if not auth else None, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()

            return result
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                raise APIError(f"HTTP error {e.status}: {e.message}")
        except Exception as e:
            raise ExchangeError(f"Request failed: {e}")

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
            backpack_timeframe = self.timeframe_map[timeframe]

            # リクエストパラメータ
            params = {
                "symbol": normalized_symbol,
                "interval": backpack_timeframe,
                "limit": limit,
            }

            if since:
                params["startTime"] = int(since.timestamp() * 1000)

            # データを取得
            response = await self._make_request("/api/v1/klines", "GET", params)

            if not response:
                return []

            # OHLCV オブジェクトに変換
            ohlcv_list = []
            for candle in response:
                ohlcv = OHLCV(
                    timestamp=datetime.fromtimestamp(int(candle[0]) / 1000, tz=timezone.utc),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                )
                ohlcv_list.append(ohlcv)

            logger.info(f"Fetched {len(ohlcv_list)} OHLCV records for {symbol} from BackPack")
            return ohlcv_list

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch OHLCV: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        try:
            # BackPackの資金調達率エンドポイント（仮実装）
            logger.warning("Funding rate not implemented for BackPack (API endpoint unknown)")

            # デフォルト値を返す
            funding_rate = FundingRate(
                timestamp=datetime.now(timezone.utc),
                symbol=self.normalize_symbol(symbol),
                funding_rate=0.0,
                next_funding_time=datetime.now(timezone.utc),
            )

            return funding_rate

        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch funding rate: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_open_interest(self, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        try:
            # BackPackの建玉データエンドポイント（仮実装）
            logger.warning("Open interest not implemented for BackPack (API endpoint unknown)")

            # デフォルト値を返す
            open_interest = OpenInterest(
                timestamp=datetime.now(timezone.utc),
                symbol=self.normalize_symbol(symbol),
                open_interest=0.0,
                open_interest_value=0.0,
            )

            return open_interest

        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch open interest: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """ティッカーデータを取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            params = {"symbol": normalized_symbol}
            response = await self._make_request("/api/v1/ticker/24hr", "GET", params)

            if not response:
                raise ExchangeError(f"No ticker data for {normalized_symbol}")

            ticker = Ticker(
                timestamp=datetime.now(timezone.utc),
                symbol=normalized_symbol,
                bid=float(response.get("bidPrice", 0)),
                ask=float(response.get("askPrice", 0)),
                last=float(response.get("lastPrice", 0)),
                volume=float(response.get("volume", 0)),
            )

            return ticker

        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch ticker: {e}")

    async def get_symbols(self) -> List[str]:
        """利用可能なシンボル一覧を取得"""
        try:
            response = await self._make_request("/api/v1/exchangeInfo", "GET")

            symbols = []
            if "symbols" in response:
                symbols = [
                    symbol_info["symbol"]
                    for symbol_info in response["symbols"]
                    if symbol_info.get("status") == "TRADING"
                ]

            logger.info(f"Fetched {len(symbols)} symbols from BackPack")
            return symbols

        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise ExchangeError(f"Error fetching symbols: {e}")

    async def get_balance(self) -> Dict[str, float]:
        """残高を取得（認証が必要）"""
        try:
            response = await self._make_request("/api/v1/capital", "GET", auth=True)

            balance = {}
            if "balances" in response:
                balance = {
                    asset["asset"]: float(asset["free"]) for asset in response["balances"] if float(asset["free"]) > 0
                }

            logger.info(f"Fetched balance for {len(balance)} assets from BackPack")
            return balance

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise ExchangeError(f"Error fetching balance: {e}")

    def normalize_symbol(self, symbol: str) -> str:
        """BackPack用のシンボル正規化"""
        # BTC/USDT -> BTCUSDT
        return symbol.upper().replace("/", "")

    async def close(self):
        """接続を閉じる"""
        if self.session and not self.session.closed:
            await self.session.close()
