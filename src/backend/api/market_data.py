"""
Market Data API endpoints
マーケットデータ（価格情報など）のAPIエンドポイント
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import cachetools
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.supabase_db import get_supabase_client

logger = logging.getLogger(__name__)

# ルーター作成
router = APIRouter()

# インメモリキャッシュ（TTL: 60秒）
cache = cachetools.TTLCache(maxsize=1000, ttl=60)


class OHLCVResponse(BaseModel):
    """OHLCV レスポンスモデル"""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVParams(BaseModel):
    """OHLCV パラメータモデル"""

    exchange: str = Field(default="binance", description="取引所名")
    symbol: str = Field(..., description="シンボル（例: BTCUSDT）")
    timeframe: str = Field(default="1h", description="時間足（例: 1m, 5m, 15m, 1h, 4h, 1d）")
    limit: int = Field(default=100, le=1000, description="取得件数（最大1000件）")
    start_time: Optional[datetime] = Field(default=None, description="開始時刻")
    end_time: Optional[datetime] = Field(default=None, description="終了時刻")


class MarketDataCache:
    """マーケットデータキャッシュクラス"""

    def __init__(self):
        self.cache = cachetools.TTLCache(maxsize=1000, ttl=60)
        self._lock = asyncio.Lock()

    def _generate_cache_key(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
    ) -> str:
        """キャッシュキーを生成"""
        key_parts = [exchange, symbol, timeframe, str(limit)]
        if start_time:
            key_parts.append(start_time.isoformat())
        if end_time:
            key_parts.append(end_time.isoformat())
        return ":".join(key_parts)

    async def get(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
    ) -> Optional[List[Dict[str, Any]]]:
        """キャッシュからデータを取得"""
        cache_key = self._generate_cache_key(exchange, symbol, timeframe, start_time, end_time, limit)
        async with self._lock:
            return self.cache.get(cache_key)

    async def set(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
        data: List[Dict[str, Any]],
    ):
        """キャッシュにデータを保存"""
        cache_key = self._generate_cache_key(exchange, symbol, timeframe, start_time, end_time, limit)
        async with self._lock:
            self.cache[cache_key] = data


# グローバルキャッシュインスタンス
market_data_cache = MarketDataCache()


async def get_ohlcv_from_db(
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Supabaseからデータを取得"""

    # キャッシュから取得を試行
    cached_data = await market_data_cache.get(exchange, symbol, timeframe, start_time, end_time, limit)
    if cached_data is not None:
        logger.info(f"Cache hit for {exchange}:{symbol}:{timeframe}")
        return cached_data

    try:
        supabase = get_supabase_client()

        # クエリを構築
        query = (
            supabase.table("price_data")
            .select("*")
            .eq("exchange", exchange)
            .eq("symbol", symbol)
            .eq("timeframe", timeframe)
            .order("timestamp", desc=True)
            .limit(limit)
        )

        # 時間範囲指定
        if start_time:
            query = query.gte("timestamp", start_time.isoformat())
        if end_time:
            query = query.lte("timestamp", end_time.isoformat())

        # クエリ実行
        response = query.execute()

        if not response.data:
            logger.warning(f"No data found for {exchange}:{symbol}:{timeframe}")
            return []

        # データ変換（新しい順→古い順に並び替え）
        ohlcv_data = []
        for row in reversed(response.data):  # 時系列順に並び替え
            ohlcv_data.append(
                {
                    "timestamp": row["timestamp"],
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": float(row["close_price"]),
                    "volume": float(row["volume"]),
                }
            )

        # キャッシュに保存
        await market_data_cache.set(exchange, symbol, timeframe, start_time, end_time, limit, ohlcv_data)

        logger.info(f"Retrieved {len(ohlcv_data)} OHLCV records from database for {exchange}:{symbol}:{timeframe}")
        return ohlcv_data

    except Exception as e:
        logger.error(f"Error retrieving OHLCV data: {e}")
        raise HTTPException(status_code=500, detail=f"データ取得エラー: {str(e)}")


@router.get("/ohlcv", response_model=List[OHLCVResponse])
async def get_ohlcv(
    exchange: str = Query(default="binance", description="取引所名"),
    symbol: str = Query(..., description="シンボル（例: BTCUSDT）"),
    timeframe: str = Query(default="1h", description="時間足"),
    limit: int = Query(default=100, le=1000, description="取得件数"),
    start_time: Optional[datetime] = Query(default=None, description="開始時刻（ISO 8601形式）"),
    end_time: Optional[datetime] = Query(default=None, description="終了時刻（ISO 8601形式）"),
):
    """
    OHLCV価格データを取得

    - **exchange**: 取引所名（デフォルト: binance）
    - **symbol**: 取引ペア（例: BTCUSDT）
    - **timeframe**: 時間足（1m, 5m, 15m, 1h, 4h, 1d）
    - **limit**: 取得件数（最大1000件）
    - **start_time**: 開始時刻（オプション）
    - **end_time**: 終了時刻（オプション）
    """

    # パラメータバリデーション
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limitは1から1000の範囲で指定してください")

    # 有効な時間足をチェック
    valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    if timeframe not in valid_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"無効な時間足です。有効な値: {', '.join(valid_timeframes)}",
        )

    # シンボル正規化（スラッシュ除去）
    normalized_symbol = symbol.replace("/", "").upper()

    try:
        # データベースからデータを取得
        ohlcv_data = await get_ohlcv_from_db(
            exchange=exchange.lower(),
            symbol=normalized_symbol,
            timeframe=timeframe,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

        # レスポンス形式に変換
        response_data = []
        for item in ohlcv_data:
            response_data.append(
                OHLCVResponse(
                    timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                    open=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item["volume"],
                )
            )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_ohlcv: {e}")
        raise HTTPException(status_code=500, detail="内部サーバーエラー")


@router.get("/symbols")
async def get_available_symbols(
    exchange: str = Query(default="binance", description="取引所名"),
):
    """
    利用可能なシンボル一覧を取得
    """
    try:
        supabase = get_supabase_client()

        # ユニークなシンボル一覧を取得
        response = supabase.table("price_data").select("symbol").eq("exchange", exchange.lower()).execute()

        if not response.data:
            return {"symbols": []}

        # 重複を除去
        symbols = list(set(row["symbol"] for row in response.data))
        symbols.sort()

        return {"symbols": symbols}

    except Exception as e:
        logger.error(f"Error retrieving symbols: {e}")
        raise HTTPException(status_code=500, detail=f"シンボル取得エラー: {str(e)}")


@router.get("/timeframes")
async def get_available_timeframes(
    exchange: str = Query(default="binance", description="取引所名"),
    symbol: str = Query(None, description="シンボル（オプション）"),
):
    """
    利用可能な時間足一覧を取得
    """
    try:
        supabase = get_supabase_client()

        # ベースクエリ
        query = supabase.table("price_data").select("timeframe").eq("exchange", exchange.lower())

        # シンボル指定がある場合
        if symbol:
            normalized_symbol = symbol.replace("/", "").upper()
            query = query.eq("symbol", normalized_symbol)

        response = query.execute()

        if not response.data:
            return {"timeframes": []}

        # 重複を除去してソート
        timeframes = list(set(row["timeframe"] for row in response.data))

        # 時間足を適切な順序でソート
        timeframe_order = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        sorted_timeframes = [tf for tf in timeframe_order if tf in timeframes]

        # 不明な時間足も追加
        for tf in timeframes:
            if tf not in sorted_timeframes:
                sorted_timeframes.append(tf)

        return {"timeframes": sorted_timeframes}

    except Exception as e:
        logger.error(f"Error retrieving timeframes: {e}")
        raise HTTPException(status_code=500, detail=f"時間足取得エラー: {str(e)}")


@router.get("/latest")
async def get_latest_prices(
    exchange: str = Query(default="binance", description="取引所名"),
    symbols: Optional[str] = Query(default=None, description="シンボル（カンマ区切り、未指定で全シンボル）"),
    timeframe: str = Query(default="1h", description="時間足"),
):
    """
    最新価格を取得
    """
    try:
        supabase = get_supabase_client()

        # ベースクエリ
        query = (
            supabase.table("price_data")
            .select("*")
            .eq("exchange", exchange.lower())
            .eq("timeframe", timeframe)
            .order("timestamp", desc=True)
        )

        # シンボル指定がある場合
        if symbols:
            symbol_list = [s.strip().replace("/", "").upper() for s in symbols.split(",")]
            query = query.in_("symbol", symbol_list)

        response = query.execute()

        if not response.data:
            return {"latest_prices": []}

        # 各シンボルの最新価格を取得
        latest_prices = {}
        for row in response.data:
            symbol = row["symbol"]
            if symbol not in latest_prices:
                latest_prices[symbol] = {
                    "symbol": symbol,
                    "timestamp": row["timestamp"],
                    "open": float(row["open_price"]),
                    "high": float(row["high_price"]),
                    "low": float(row["low_price"]),
                    "close": float(row["close_price"]),
                    "volume": float(row["volume"]),
                }

        return {"latest_prices": list(latest_prices.values())}

    except Exception as e:
        logger.error(f"Error retrieving latest prices: {e}")
        raise HTTPException(status_code=500, detail=f"最新価格取得エラー: {str(e)}")


@router.get("/health")
async def market_data_health():
    """
    Market Data APIのヘルスチェック
    """
    try:
        # Supabase接続テスト
        supabase = get_supabase_client()
        response = supabase.table("price_data").select("count", count="exact").limit(1).execute()

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connection": "ok",
            "total_records": response.count if response.count else 0,
            "cache_size": len(market_data_cache.cache),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"サービス利用不可: {str(e)}")
