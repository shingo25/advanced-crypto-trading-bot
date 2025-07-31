"""
WebSocket APIルート
リアルタイムデータ配信のためのWebSocketエンドポイント
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from src.backend.core.security import get_current_user
from src.backend.websocket.manager import (
    ChannelType,
    MessageType,
    WebSocketMessage,
    websocket_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None, description="クライアントID（オプション）"),
):
    """
    メインWebSocketエンドポイント

    接続例:
    - ws://localhost:8000/websocket/ws
    - ws://localhost:8000/websocket/ws?client_id=custom_client_id
    """
    actual_client_id = None

    try:
        # 接続を確立
        actual_client_id = await websocket_manager.connect(websocket, client_id)
        logger.info(f"WebSocket接続開始: {actual_client_id}")

        # メッセージループ
        while True:
            try:
                # クライアントからのメッセージを受信
                raw_message = await websocket.receive_text()

                # メッセージを処理
                await websocket_manager.handle_message(actual_client_id, raw_message)

            except WebSocketDisconnect:
                logger.info(f"クライアントが接続を切断: {actual_client_id}")
                break
            except Exception as e:
                logger.error(f"メッセージ処理エラー: {e}")
                # エラーをクライアントに通知
                await websocket_manager.send_to_client(
                    actual_client_id,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        channel=ChannelType.ALERTS,
                        data={"error": f"メッセージ処理エラー: {str(e)}"},
                    ),
                )

    except Exception as e:
        logger.error(f"WebSocket接続エラー: {e}")

    finally:
        # 接続を切断
        if actual_client_id:
            await websocket_manager.disconnect(actual_client_id)


@router.websocket("/ws/prices")
async def price_stream_endpoint(
    websocket: WebSocket,
    symbols: Optional[str] = Query(None, description="購読するシンボル (例: BTC,ETH)"),
):
    """
    価格データ専用WebSocketエンドポイント

    接続例:
    - ws://localhost:8000/websocket/ws/prices
    - ws://localhost:8000/websocket/ws/prices?symbols=BTC,ETH,SOL
    """
    client_id = None

    try:
        # 接続を確立
        client_id = await websocket_manager.connect(websocket)

        # 価格チャンネルに自動購読
        await websocket_manager._subscribe_to_channel(client_id, ChannelType.PRICES.value)

        # 特定のシンボルが指定された場合は個別チャンネルも購読
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            for symbol in symbol_list:
                await websocket_manager._subscribe_to_channel(client_id, f"{ChannelType.PRICES.value}:{symbol}")

        # 購読完了通知
        await websocket_manager.send_to_client(
            client_id,
            WebSocketMessage(
                type=MessageType.SYSTEM_ALERT,
                channel=ChannelType.ALERTS,
                data={
                    "message": "価格データストリームに接続しました",
                    "subscribed_symbols": symbols.split(",") if symbols else ["ALL"],
                },
            ),
        )

        # 接続を維持
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info(f"価格ストリーム接続切断: {client_id}")
    except Exception as e:
        logger.error(f"価格ストリーム接続エラー: {e}")
    finally:
        if client_id:
            await websocket_manager.disconnect(client_id)


@router.websocket("/ws/trades")
async def trade_stream_endpoint(websocket: WebSocket):
    """
    取引データ専用WebSocketエンドポイント
    """
    client_id = None

    try:
        client_id = await websocket_manager.connect(websocket)

        # 取引チャンネルに自動購読
        await websocket_manager._subscribe_to_channel(client_id, ChannelType.TRADES.value)

        await websocket_manager.send_to_client(
            client_id,
            WebSocketMessage(
                type=MessageType.SYSTEM_ALERT,
                channel=ChannelType.ALERTS,
                data={"message": "取引データストリームに接続しました"},
            ),
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info(f"取引ストリーム接続切断: {client_id}")
    except Exception as e:
        logger.error(f"取引ストリーム接続エラー: {e}")
    finally:
        if client_id:
            await websocket_manager.disconnect(client_id)


@router.get("/connections")
async def get_connection_stats(current_user: dict = Depends(get_current_user)):
    """
    WebSocket接続統計を取得
    """
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

    stats = websocket_manager.get_connection_stats()
    return {"status": "success", "data": stats}


@router.post("/broadcast")
async def broadcast_message(
    message_data: dict,
    channel: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    管理者用ブロードキャスト機能
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

    try:
        message = WebSocketMessage(type=MessageType.SYSTEM_ALERT, channel=ChannelType.ALERTS, data=message_data)

        if channel:
            await websocket_manager.broadcast_to_channel(channel, message)
        else:
            await websocket_manager.broadcast_to_all(message)

        return {"status": "success", "message": "メッセージが配信されました"}

    except Exception as e:
        logger.error(f"ブロードキャストエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_message_to_client(client_id: str, message_data: dict, current_user: dict = Depends(get_current_user)):
    """
    特定のクライアントにメッセージを送信
    """
    if current_user.get("role") not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="権限が不足しています")

    try:
        message = WebSocketMessage(type=MessageType.SYSTEM_ALERT, channel=ChannelType.ALERTS, data=message_data)

        success = await websocket_manager.send_to_client(client_id, message)

        if success:
            return {
                "status": "success",
                "message": f"クライアント {client_id} にメッセージを送信しました",
            }
        else:
            raise HTTPException(status_code=404, detail="クライアントが見つかりません")

    except Exception as e:
        logger.error(f"メッセージ送信エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connections/{client_id}")
async def disconnect_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """
    特定のクライアント接続を強制切断
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

    try:
        await websocket_manager.disconnect(client_id)
        return {
            "status": "success",
            "message": f"クライアント {client_id} を切断しました",
        }

    except Exception as e:
        logger.error(f"クライアント切断エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def websocket_health_check():
    """
    WebSocketサービスのヘルスチェック
    """
    stats = websocket_manager.get_connection_stats()

    return {
        "status": "healthy",
        "service": "websocket",
        "connections": stats["total_connections"],
        "authenticated": stats["authenticated_connections"],
        "channels": stats["active_channels"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
