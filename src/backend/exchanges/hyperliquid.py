import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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


class HyperliquidAdapter(AbstractExchangeAdapter):
    """Hyperliquid取引所アダプタ（公式SDK使用）"""

    def __init__(self, api_key: str, secret: str, sandbox: bool = False):
        super().__init__(api_key, secret, sandbox)

        # Hyperliquid SDK設定
        self.base_url = constants.TESTNET_API_URL if sandbox else constants.MAINNET_API_URL

        # アカウント設定（eth_accountを使用）
        try:
            # secret_keyは0xプレフィックス付きの16進数文字列として提供される想定
            self.account = Account.from_key(secret)
            self.address = self.account.address
        except Exception as e:
            logger.error(f"Failed to initialize account: {e}")
            raise ExchangeError(f"Invalid private key format: {e}")

        # Info APIクライアント（読み取り専用）
        self.info = Info(self.base_url, skip_ws=True)

        # Exchange APIクライアント（取引実行用）
        self.exchange = Exchange(self.account, self.base_url, skip_ws=True)

        # 時間枠マッピング（Hyperliquid形式）
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
            hyperliquid_timeframe = self.timeframe_map[timeframe]

            # SDKを使用してキャンドルデータを取得
            # 注: SDKのcandle_snapshotメソッドは同期的
            candles = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.info.candle_snapshot(
                    coin=normalized_symbol,
                    interval=hyperliquid_timeframe,
                    startTime=int(since.timestamp() * 1000) if since else None,
                    endTime=int(datetime.now().timestamp() * 1000),
                ),
            )

            if not candles:
                return []

            # OHLCV オブジェクトに変換
            ohlcv_list = []
            for candle in candles[-limit:]:  # 最新limit件を取得
                ohlcv = OHLCV(
                    timestamp=datetime.fromtimestamp(candle["t"] / 1000, tz=timezone.utc),
                    open=float(candle["o"]),
                    high=float(candle["h"]),
                    low=float(candle["l"]),
                    close=float(candle["c"]),
                    volume=float(candle["v"]),
                )
                ohlcv_list.append(ohlcv)

            logger.info(f"Fetched {len(ohlcv_list)} OHLCV records for {symbol} from Hyperliquid")
            return ohlcv_list

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded: {e}")
            raise ExchangeError(f"Failed to fetch OHLCV: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        """資金調達率を取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            # メタ情報を取得
            meta = await asyncio.get_event_loop().run_in_executor(None, lambda: self.info.meta())

            # シンボル情報から資金調達率を検索
            universe = meta.get("universe", [])
            for asset_info in universe:
                if asset_info["name"] == normalized_symbol:
                    funding_rate = FundingRate(
                        timestamp=datetime.now(timezone.utc),
                        symbol=normalized_symbol,
                        funding_rate=float(asset_info.get("fundingRate", 0)),
                        next_funding_time=datetime.now(timezone.utc),  # Hyperliquidは8時間おき
                    )

                    logger.info(f"Fetched funding rate for {symbol} from Hyperliquid: {funding_rate.funding_rate}")
                    return funding_rate

            raise ExchangeError(f"Symbol {normalized_symbol} not found")

        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded: {e}")
            raise ExchangeError(f"Failed to fetch funding rate: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((RateLimitError, APIError)),
    )
    async def fetch_open_interest(self, symbol: str) -> OpenInterest:
        """建玉データを取得"""
        try:
            normalized_symbol = self.normalize_symbol(symbol)

            # メタ情報を取得
            meta = await asyncio.get_event_loop().run_in_executor(None, lambda: self.info.meta())

            # シンボル情報から建玉データを検索
            universe = meta.get("universe", [])
            for asset_info in universe:
                if asset_info["name"] == normalized_symbol:
                    open_interest = OpenInterest(
                        timestamp=datetime.now(timezone.utc),
                        symbol=normalized_symbol,
                        open_interest=float(asset_info.get("openInterest", 0)),
                        open_interest_value=float(asset_info.get("openInterest", 0)),  # USD換算は別途計算
                    )

                    logger.info(f"Fetched open interest for {symbol} from Hyperliquid: {open_interest.open_interest}")
                    return open_interest

            raise ExchangeError(f"Symbol {normalized_symbol} not found")

        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded: {e}")
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

            # 全コインの中間価格を取得
            mids = await asyncio.get_event_loop().run_in_executor(None, lambda: self.info.all_mids())

            if normalized_symbol in mids:
                mid_price = float(mids[normalized_symbol])

                # L2オーダーブックから詳細な価格情報を取得
                try:
                    l2_data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.info.l2_snapshot(normalized_symbol)
                    )

                    if l2_data and "levels" in l2_data:
                        levels = l2_data["levels"]
                        if levels:
                            bid = float(levels[0]["px"]) if levels[0]["side"] == "B" else mid_price * 0.999
                            ask = float(levels[0]["px"]) if levels[0]["side"] == "A" else mid_price * 1.001
                        else:
                            bid = mid_price * 0.999
                            ask = mid_price * 1.001
                    else:
                        bid = mid_price * 0.999
                        ask = mid_price * 1.001

                except Exception:
                    # L2データ取得に失敗した場合は近似値を使用
                    bid = mid_price * 0.999
                    ask = mid_price * 1.001

                ticker = Ticker(
                    timestamp=datetime.now(timezone.utc),
                    symbol=normalized_symbol,
                    bid=bid,
                    ask=ask,
                    last=mid_price,
                    volume=0.0,  # Volume情報は別のエンドポイントが必要
                )

                return ticker

            raise ExchangeError(f"Symbol {normalized_symbol} not found")

        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            if "rate limit" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded: {e}")
            raise ExchangeError(f"Failed to fetch ticker: {e}")

    async def get_symbols(self) -> List[str]:
        """利用可能なシンボル一覧を取得"""
        try:
            meta = await asyncio.get_event_loop().run_in_executor(None, lambda: self.info.meta())

            universe = meta.get("universe", [])
            symbols = [asset["name"] for asset in universe]

            logger.info(f"Fetched {len(symbols)} symbols from Hyperliquid")
            return symbols

        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise ExchangeError(f"Error fetching symbols: {e}")

    async def get_balance(self) -> Dict[str, float]:
        """残高を取得"""
        try:
            # ユーザー状態を取得
            user_state = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.info.user_state(self.address)
            )

            if not user_state:
                return {}

            # 各アセットの残高を集計
            balance = {}

            # クロスマージンの残高
            if "crossMarginSummary" in user_state:
                margin_summary = user_state["crossMarginSummary"]
                # USDCベースの証拠金
                account_value = float(margin_summary.get("accountValue", 0))
                if account_value > 0:
                    balance["USDC"] = account_value

            # 各ポジションの残高（未実現損益含む）
            if "assetPositions" in user_state:
                for position in user_state["assetPositions"]:
                    coin = position["position"]["coin"]
                    size = float(position["position"]["szi"])
                    if abs(size) > 0:
                        balance[coin] = size

            logger.info(f"Fetched balance for {len(balance)} assets from Hyperliquid")
            return balance

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise ExchangeError(f"Error fetching balance: {e}")

    def normalize_symbol(self, symbol: str) -> str:
        """Hyperliquid用のシンボル正規化"""
        # BTC/USDT -> BTC (Hyperliquidはベース通貨のみ使用)
        if "/" in symbol:
            return symbol.split("/")[0].upper()
        return symbol.upper()

    async def close(self):
        """接続を閉じる（SDKは接続管理を内部で行うため特に処理なし）"""
        pass
