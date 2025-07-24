"""
リアルタイム価格配信API
価格ストリーミングシステムの制御とステータス管理
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from backend.core.security import get_current_user
from backend.streaming.price_streamer import price_stream_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class SymbolSubscriptionRequest(BaseModel):
    """シンボル購読リクエスト"""

    symbols: List[str]


class SymbolSubscriptionResponse(BaseModel):
    """シンボル購読レスポンス"""

    status: str
    message: str
    subscribed_symbols: List[str]
    failed_symbols: List[str] = []


class PriceStreamStats(BaseModel):
    """価格配信統計"""

    is_running: bool
    total_symbols: int
    active_connections: int
    cached_prices: int
    binance_stats: Dict[str, Any]


@router.post("/start")
async def start_price_streaming(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    価格配信システムを開始
    管理者またはアナリストのみ実行可能
    """
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="権限が不足しています")

    try:
        # バックグラウンドで開始
        background_tasks.add_task(price_stream_manager.start)

        return {
            "status": "success",
            "message": "価格配信システムの開始処理を実行中です",
        }

    except Exception as e:
        logger.error(f"Failed to start price streaming: {e}")
        raise HTTPException(status_code=500, detail=f"開始に失敗しました: {e}")


@router.post("/stop")
async def stop_price_streaming(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    価格配信システムを停止
    管理者のみ実行可能
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

    try:
        # バックグラウンドで停止
        background_tasks.add_task(price_stream_manager.stop)

        return {
            "status": "success",
            "message": "価格配信システムの停止処理を実行中です",
        }

    except Exception as e:
        logger.error(f"Failed to stop price streaming: {e}")
        raise HTTPException(status_code=500, detail=f"停止に失敗しました: {e}")


@router.get("/status", response_model=PriceStreamStats)
async def get_streaming_status(current_user: dict = Depends(get_current_user)):
    """
    価格配信システムのステータスを取得
    """
    try:
        stats = price_stream_manager.get_stats()

        return PriceStreamStats(
            is_running=stats["manager_running"],
            total_symbols=stats["total_symbols"],
            active_connections=stats["binance"]["active_connections"],
            cached_prices=stats["cached_prices"],
            binance_stats=stats["binance"],
        )

    except Exception as e:
        logger.error(f"Failed to get streaming status: {e}")
        raise HTTPException(status_code=500, detail=f"ステータス取得に失敗しました: {e}")


@router.get("/prices")
async def get_all_prices(current_user: dict = Depends(get_current_user)):
    """
    キャッシュされた全価格データを取得
    """
    try:
        prices = price_stream_manager.get_all_prices()

        return {
            "status": "success",
            "count": len(prices),
            "prices": prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get prices: {e}")
        raise HTTPException(status_code=500, detail=f"価格データ取得に失敗しました: {e}")


@router.get("/prices/{symbol}")
async def get_symbol_price(symbol: str, current_user: dict = Depends(get_current_user)):
    """
    特定シンボルの価格データを取得
    """
    try:
        symbol = symbol.upper()
        prices = price_stream_manager.get_all_prices()

        if symbol not in prices:
            raise HTTPException(status_code=404, detail=f"シンボル {symbol} が見つかりません")

        return {"status": "success", "symbol": symbol, "data": prices[symbol]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"価格データ取得に失敗しました: {e}")


@router.post("/subscribe", response_model=SymbolSubscriptionResponse)
async def subscribe_symbols(request: SymbolSubscriptionRequest, current_user: dict = Depends(get_current_user)):
    """
    シンボルを購読
    """
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="権限が不足しています")

    try:
        subscribed = []
        failed = []

        for symbol in request.symbols:
            try:
                await price_stream_manager.subscribe_symbol(symbol.upper())
                subscribed.append(symbol.upper())
            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")
                failed.append(symbol.upper())

        return SymbolSubscriptionResponse(
            status="success",
            message=f"{len(subscribed)}個のシンボルを購読しました",
            subscribed_symbols=subscribed,
            failed_symbols=failed,
        )

    except Exception as e:
        logger.error(f"Failed to subscribe symbols: {e}")
        raise HTTPException(status_code=500, detail=f"購読処理に失敗しました: {e}")


@router.delete("/subscribe/{symbol}")
async def unsubscribe_symbol(symbol: str, current_user: dict = Depends(get_current_user)):
    """
    シンボルの購読を解除
    """
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="権限が不足しています")

    try:
        symbol = symbol.upper()
        await price_stream_manager.unsubscribe_symbol(symbol)

        return {
            "status": "success",
            "message": f"シンボル {symbol} の購読を解除しました",
        }

    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"購読解除に失敗しました: {e}")


@router.get("/symbols")
async def get_subscribed_symbols(current_user: dict = Depends(get_current_user)):
    """
    購読中のシンボル一覧を取得
    """
    try:
        symbols = price_stream_manager.binance_streamer.get_subscribed_symbols()

        return {"status": "success", "count": len(symbols), "symbols": symbols}

    except Exception as e:
        logger.error(f"Failed to get subscribed symbols: {e}")
        raise HTTPException(status_code=500, detail=f"シンボル一覧取得に失敗しました: {e}")


@router.post("/restart")
async def restart_price_streaming(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    価格配信システムを再起動
    管理者のみ実行可能
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

    try:

        async def restart_task():
            await price_stream_manager.stop()
            await asyncio.sleep(2)  # 少し待機
            await price_stream_manager.start()

        background_tasks.add_task(restart_task)

        return {
            "status": "success",
            "message": "価格配信システムの再起動処理を実行中です",
        }

    except Exception as e:
        logger.error(f"Failed to restart price streaming: {e}")
        raise HTTPException(status_code=500, detail=f"再起動に失敗しました: {e}")


@router.get("/health")
async def health_check():
    """
    価格配信システムのヘルスチェック
    """
    try:
        stats = price_stream_manager.get_stats()

        # ヘルスチェック基準
        is_healthy = stats["manager_running"] and stats["total_symbols"] > 0 and stats["binance"]["is_running"]

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "price_streaming",
            "is_running": stats["manager_running"],
            "symbols_count": stats["total_symbols"],
            "connections": stats["binance"]["active_connections"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "price_streaming",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
