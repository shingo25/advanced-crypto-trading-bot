"""
WebSocket接続管理システム
リアルタイム価格配信、取引データ、ニュースなどの配信を管理
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import WebSocket

from crypto_bot.core.security import decode_token

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocketメッセージタイプ"""

    PRICE_UPDATE = "price_update"
    TRADE_EXECUTION = "trade_execution"
    ORDER_UPDATE = "order_update"
    MARKET_NEWS = "market_news"
    SYSTEM_ALERT = "system_alert"
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"
    AUTH = "auth"


class ChannelType(Enum):
    """配信チャンネルタイプ"""

    PRICES = "prices"  # リアルタイム価格
    TRADES = "trades"  # 取引データ
    ORDERS = "orders"  # 注文状況
    NEWS = "news"  # ニュース
    ALERTS = "alerts"  # アラート
    PORTFOLIO = "portfolio"  # ポートフォリオ
    BACKTEST = "backtest"  # バックテスト進捗


@dataclass
class WebSocketMessage:
    """WebSocketメッセージ構造"""

    type: MessageType
    channel: ChannelType
    data: Any
    timestamp: str = None
    message_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(
            {
                "type": self.type.value,
                "channel": self.channel.value,
                "data": self.data,
                "timestamp": self.timestamp,
                "message_id": self.message_id,
            }
        )


@dataclass
class ClientConnection:
    """クライアント接続情報"""

    websocket: WebSocket
    client_id: str
    user_id: Optional[str] = None
    subscriptions: Set[str] = None
    connected_at: datetime = None
    last_heartbeat: datetime = None
    rate_limit_count: int = 0
    rate_limit_reset: datetime = None

    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()
        if self.connected_at is None:
            self.connected_at = datetime.now(timezone.utc)
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now(timezone.utc)
        if self.rate_limit_reset is None:
            self.rate_limit_reset = datetime.now(timezone.utc)


class WebSocketManager:
    """WebSocket接続管理システム"""

    def __init__(self):
        # 接続管理
        self.connections: Dict[str, ClientConnection] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {}

        # レート制限設定
        self.rate_limit_requests = 100  # 1分間のリクエスト制限
        self.rate_limit_window = 60  # 制限時間（秒）

        # ハートビート設定
        self.heartbeat_interval = 30  # ハートビート間隔（秒）
        self.heartbeat_timeout = 60  # タイムアウト時間（秒）

        # メッセージハンドラー
        self.message_handlers: Dict[MessageType, Callable] = {
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            MessageType.AUTH: self._handle_auth,
            MessageType.HEARTBEAT: self._handle_heartbeat,
        }

        # バックグラウンドタスク
        self._background_tasks: List[asyncio.Task] = []

        logger.info("WebSocket管理システムが初期化されました")

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """WebSocket接続を確立"""
        try:
            await websocket.accept()

            if client_id is None:
                client_id = str(uuid.uuid4())

            connection = ClientConnection(websocket=websocket, client_id=client_id)

            self.connections[client_id] = connection

            logger.info(f"WebSocket接続確立: {client_id} (総接続数: {len(self.connections)})")

            # ハートビートタスクを開始
            heartbeat_task = asyncio.create_task(self._heartbeat_task(client_id))
            self._background_tasks.append(heartbeat_task)

            # 接続確認メッセージを送信
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.SYSTEM_ALERT,
                    channel=ChannelType.ALERTS,
                    data={"message": "接続が確立されました", "client_id": client_id},
                ),
            )

            return client_id

        except Exception as e:
            logger.error(f"WebSocket接続エラー: {e}")
            raise

    async def disconnect(self, client_id: str):
        """WebSocket接続を切断"""
        if client_id not in self.connections:
            return

        connection = self.connections[client_id]

        # 全ての購読を解除
        for channel in list(connection.subscriptions):
            await self._unsubscribe_from_channel(client_id, channel)

        # 接続を削除
        del self.connections[client_id]

        # バックグラウンドタスクをクリーンアップ
        self._cleanup_background_tasks(client_id)

        logger.info(f"WebSocket接続切断: {client_id} (残り接続数: {len(self.connections)})")

    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """特定のクライアントにメッセージを送信"""
        if client_id not in self.connections:
            logger.warning(f"存在しないクライアント: {client_id}")
            return False

        connection = self.connections[client_id]

        try:
            await connection.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.error(f"メッセージ送信エラー (client: {client_id}): {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage):
        """チャンネル購読者全員にブロードキャスト"""
        if channel not in self.channel_subscribers:
            return

        subscribers = list(self.channel_subscribers[channel])
        success_count = 0

        for client_id in subscribers:
            if await self.send_to_client(client_id, message):
                success_count += 1

        logger.debug(f"チャンネル '{channel}' に配信: {success_count}/{len(subscribers)} 成功")

    async def broadcast_to_all(self, message: WebSocketMessage):
        """全てのクライアントにブロードキャスト"""
        client_ids = list(self.connections.keys())
        success_count = 0

        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                success_count += 1

        logger.info(f"全体配信: {success_count}/{len(client_ids)} 成功")

    async def handle_message(self, client_id: str, raw_message: str):
        """クライアントからのメッセージを処理"""
        try:
            # レート制限チェック
            if not await self._check_rate_limit(client_id):
                await self.send_to_client(
                    client_id,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        channel=ChannelType.ALERTS,
                        data={"error": "レート制限に達しました"},
                    ),
                )
                return

            # メッセージをパース
            try:
                message_data = json.loads(raw_message)
                message_type = MessageType(message_data.get("type"))
            except (json.JSONDecodeError, ValueError) as e:
                await self.send_to_client(
                    client_id,
                    WebSocketMessage(
                        type=MessageType.ERROR,
                        channel=ChannelType.ALERTS,
                        data={"error": f"無効なメッセージ形式: {e}"},
                    ),
                )
                return

            # メッセージハンドラーを実行
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](client_id, message_data)
            else:
                logger.warning(f"未知のメッセージタイプ: {message_type}")

        except Exception as e:
            logger.error(f"メッセージ処理エラー (client: {client_id}): {e}")
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    channel=ChannelType.ALERTS,
                    data={"error": "メッセージ処理中にエラーが発生しました"},
                ),
            )

    async def _handle_subscribe(self, client_id: str, message_data: dict):
        """チャンネル購読処理"""
        channel = message_data.get("channel")
        if not channel:
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    channel=ChannelType.ALERTS,
                    data={"error": "チャンネルが指定されていません"},
                ),
            )
            return

        await self._subscribe_to_channel(client_id, channel)

        await self.send_to_client(
            client_id,
            WebSocketMessage(
                type=MessageType.SYSTEM_ALERT,
                channel=ChannelType.ALERTS,
                data={
                    "message": f"チャンネル '{channel}' を購読しました",
                    "channel": channel,
                },
            ),
        )

    async def _handle_unsubscribe(self, client_id: str, message_data: dict):
        """チャンネル購読解除処理"""
        channel = message_data.get("channel")
        if not channel:
            return

        await self._unsubscribe_from_channel(client_id, channel)

        await self.send_to_client(
            client_id,
            WebSocketMessage(
                type=MessageType.SYSTEM_ALERT,
                channel=ChannelType.ALERTS,
                data={
                    "message": f"チャンネル '{channel}' の購読を解除しました",
                    "channel": channel,
                },
            ),
        )

    async def _handle_auth(self, client_id: str, message_data: dict):
        """認証処理"""
        token = message_data.get("token")
        if not token:
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    channel=ChannelType.ALERTS,
                    data={"error": "認証トークンが必要です"},
                ),
            )
            return

        try:
            # トークンを検証
            user_info = decode_token(token)
            connection = self.connections[client_id]
            connection.user_id = user_info.get("user_id")

            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.SYSTEM_ALERT,
                    channel=ChannelType.ALERTS,
                    data={
                        "message": "認証が完了しました",
                        "user_id": connection.user_id,
                    },
                ),
            )

        except Exception as e:
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.ERROR,
                    channel=ChannelType.ALERTS,
                    data={"error": f"認証に失敗しました: {e}"},
                ),
            )

    async def _handle_heartbeat(self, client_id: str, message_data: dict):
        """ハートビート処理"""
        if client_id in self.connections:
            self.connections[client_id].last_heartbeat = datetime.now(timezone.utc)

            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    channel=ChannelType.ALERTS,
                    data={"status": "alive"},
                ),
            )

    async def _subscribe_to_channel(self, client_id: str, channel: str):
        """チャンネル購読"""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(client_id)

        if client_id in self.connections:
            self.connections[client_id].subscriptions.add(channel)

        logger.debug(f"チャンネル購読: {client_id} -> {channel}")

    async def _unsubscribe_from_channel(self, client_id: str, channel: str):
        """チャンネル購読解除"""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(client_id)

            # 購読者がいなくなった場合はチャンネルを削除
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]

        if client_id in self.connections:
            self.connections[client_id].subscriptions.discard(channel)

        logger.debug(f"チャンネル購読解除: {client_id} -> {channel}")

    async def _check_rate_limit(self, client_id: str) -> bool:
        """レート制限チェック"""
        if client_id not in self.connections:
            return False

        connection = self.connections[client_id]
        now = datetime.now(timezone.utc)

        # リセット時間を過ぎた場合はカウンターをリセット
        if (now - connection.rate_limit_reset).total_seconds() >= self.rate_limit_window:
            connection.rate_limit_count = 0
            connection.rate_limit_reset = now

        # レート制限チェック
        if connection.rate_limit_count >= self.rate_limit_requests:
            return False

        connection.rate_limit_count += 1
        return True

    async def _heartbeat_task(self, client_id: str):
        """ハートビートタスク"""
        try:
            while client_id in self.connections:
                await asyncio.sleep(self.heartbeat_interval)

                if client_id not in self.connections:
                    break

                connection = self.connections[client_id]
                now = datetime.now(timezone.utc)

                # タイムアウトチェック
                if (now - connection.last_heartbeat).total_seconds() > self.heartbeat_timeout:
                    logger.warning(f"ハートビートタイムアウト: {client_id}")
                    await self.disconnect(client_id)
                    break

        except Exception as e:
            logger.error(f"ハートビートタスクエラー: {e}")

    def _cleanup_background_tasks(self, client_id: str):
        """バックグラウンドタスクのクリーンアップ"""
        for task in self._background_tasks[:]:
            if task.done() or task.cancelled():
                self._background_tasks.remove(task)

    def get_connection_stats(self) -> dict:
        """接続統計を取得"""
        total_connections = len(self.connections)
        authenticated_connections = len([c for c in self.connections.values() if c.user_id])

        channel_stats = {channel: len(subscribers) for channel, subscribers in self.channel_subscribers.items()}

        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "channel_subscribers": channel_stats,
            "active_channels": len(self.channel_subscribers),
        }

    async def shutdown(self):
        """システムシャットダウン"""
        logger.info("WebSocket管理システムをシャットダウン中...")

        # 全ての接続を切断
        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            await self.disconnect(client_id)

        # バックグラウンドタスクを停止
        for task in self._background_tasks:
            task.cancel()

        logger.info("WebSocket管理システムのシャットダウンが完了しました")


# グローバルWebSocket管理インスタンス
websocket_manager = WebSocketManager()
