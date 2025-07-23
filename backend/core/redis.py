"""
Redis接続管理システム

アラート・通知システムのために使用される
Redis Pub/Sub およびキャッシュ機能を提供
"""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis設定クラス"""

    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD")
        self.username = os.getenv("REDIS_USERNAME")
        self.ssl = os.getenv("REDIS_SSL", "false").lower() == "true"

        # 接続プール設定
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 10))
        self.retry_on_timeout = True
        self.socket_connect_timeout = 5
        self.socket_timeout = 5

        # Pub/Sub設定
        self.pubsub_timeout = 1.0
        self.max_retries = 3
        self.retry_delay = 1.0

    def get_connection_params(self) -> Dict[str, Any]:
        """接続パラメータを取得"""
        params = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_timeout": self.socket_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "max_connections": self.max_connections,
            "ssl": self.ssl,
        }

        if self.password:
            params["password"] = self.password
        if self.username:
            params["username"] = self.username

        return params


class RedisManager:
    """Redis接続管理クラス（シングルトン）"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.config = RedisConfig()
            self._redis_pool: Optional[Redis] = None
            self._pubsub_connections: Dict[str, Any] = {}
            self._subscribers: Dict[str, List[Callable]] = {}
            self._running_tasks: List[asyncio.Task] = []
            self._connection_healthy = False
            RedisManager._initialized = True
            logger.info("RedisManager initialized")

    async def initialize(self) -> bool:
        """Redis接続を初期化"""
        try:
            connection_params = self.config.get_connection_params()
            self._redis_pool = redis.Redis(**connection_params)

            # 接続テスト
            await self._redis_pool.ping()
            self._connection_healthy = True

            logger.info(f"Redis connection established: {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._connection_healthy = False
            return False

    async def close(self):
        """接続を閉じる"""
        try:
            # 実行中のタスクをキャンセル
            for task in self._running_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Pub/Sub接続を閉じる
            for channel, pubsub in self._pubsub_connections.items():
                try:
                    await pubsub.close()
                except Exception as e:
                    logger.warning(f"Error closing pubsub for channel {channel}: {e}")

            # メイン接続を閉じる
            if self._redis_pool:
                await self._redis_pool.close()

            self._connection_healthy = False
            logger.info("Redis connections closed")

        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    @property
    def is_healthy(self) -> bool:
        """接続が健全かチェック"""
        return self._connection_healthy

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            if not self._redis_pool:
                return False

            await self._redis_pool.ping()
            self._connection_healthy = True
            return True

        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._connection_healthy = False
            return False

    async def get_redis(self) -> Redis:
        """Redis接続を取得"""
        if not self._redis_pool:
            await self.initialize()

        if not self._connection_healthy:
            raise ConnectionError("Redis connection is not healthy")

        return self._redis_pool

    # Pub/Sub関連メソッド
    async def publish(self, channel: str, message: Any, serialize: bool = True) -> bool:
        """メッセージを発行"""
        try:
            redis_client = await self.get_redis()

            if serialize:
                if isinstance(message, dict):
                    message = json.dumps(message, default=str)
                elif not isinstance(message, (str, bytes)):
                    message = str(message)

            result = await redis_client.publish(channel, message)
            logger.debug(f"Published message to {channel}: {result} subscribers")
            return result > 0

        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            return False

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str, Any], None],
        deserialize: bool = True,
    ) -> bool:
        """チャンネルに購読"""
        try:
            if channel not in self._subscribers:
                self._subscribers[channel] = []

            self._subscribers[channel].append(callback)

            # 新しいチャンネルの場合、Pub/Sub接続を作成
            if channel not in self._pubsub_connections:
                await self._create_pubsub_connection(channel, deserialize)

            logger.info(f"Subscribed to channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False

    async def _create_pubsub_connection(self, channel: str, deserialize: bool = True):
        """Pub/Sub接続を作成"""
        try:
            redis_client = await self.get_redis()
            pubsub = redis_client.pubsub()

            await pubsub.subscribe(channel)
            self._pubsub_connections[channel] = pubsub

            # リスナータスクを開始
            task = asyncio.create_task(self._listen_for_messages(channel, pubsub, deserialize))
            self._running_tasks.append(task)

            logger.info(f"Created pubsub connection for channel: {channel}")

        except Exception as e:
            logger.error(f"Failed to create pubsub connection for {channel}: {e}")
            raise

    async def _listen_for_messages(self, channel: str, pubsub, deserialize: bool = True):
        """メッセージリスナー"""
        logger.info(f"Started listening for messages on channel: {channel}")

        retry_count = 0
        max_retries = self.config.max_retries

        while retry_count < max_retries:
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = message["data"]

                            if deserialize and isinstance(data, (str, bytes)):
                                if isinstance(data, bytes):
                                    data = data.decode("utf-8")
                                try:
                                    data = json.loads(data)
                                except json.JSONDecodeError:
                                    # JSON形式でない場合はそのまま使用
                                    pass

                            # 購読者のコールバックを呼び出し
                            if channel in self._subscribers:
                                for callback in self._subscribers[channel]:
                                    try:
                                        if asyncio.iscoroutinefunction(callback):
                                            await callback(channel, data)
                                        else:
                                            callback(channel, data)
                                    except Exception as e:
                                        logger.error(f"Error in subscriber callback: {e}")

                        except Exception as e:
                            logger.error(f"Error processing message from {channel}: {e}")

                # 正常な終了
                break

            except (ConnectionError, TimeoutError) as e:
                retry_count += 1
                logger.warning(f"Connection error on channel {channel}, retry {retry_count}/{max_retries}: {e}")

                if retry_count < max_retries:
                    await asyncio.sleep(self.config.retry_delay * retry_count)
                    try:
                        # 再接続を試行
                        await self._create_pubsub_connection(channel, deserialize)
                        retry_count = 0  # 成功したらリセット
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed for {channel}: {reconnect_error}")
                else:
                    logger.error(f"Max retries reached for channel {channel}")
                    break

            except asyncio.CancelledError:
                logger.info(f"Message listener for {channel} cancelled")
                break

            except Exception as e:
                logger.error(f"Unexpected error in message listener for {channel}: {e}")
                break

        logger.info(f"Stopped listening for messages on channel: {channel}")

    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None) -> bool:
        """チャンネルから購読解除"""
        try:
            if channel in self._subscribers:
                if callback:
                    # 特定のコールバックのみ削除
                    if callback in self._subscribers[channel]:
                        self._subscribers[channel].remove(callback)
                else:
                    # すべてのコールバックを削除
                    self._subscribers[channel].clear()

                # コールバックがなくなった場合、Pub/Sub接続を閉じる
                if not self._subscribers[channel]:
                    if channel in self._pubsub_connections:
                        pubsub = self._pubsub_connections[channel]
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                        del self._pubsub_connections[channel]

                    del self._subscribers[channel]

            logger.info(f"Unsubscribed from channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe from {channel}: {e}")
            return False

    # キャッシュ関連メソッド
    async def set_cache(
        self,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None,
        serialize: bool = True,
    ) -> bool:
        """キャッシュに値を設定"""
        try:
            redis_client = await self.get_redis()

            if serialize and not isinstance(value, (str, bytes)):
                value = json.dumps(value, default=str)

            if expire_seconds:
                await redis_client.setex(key, expire_seconds, value)
            else:
                await redis_client.set(key, value)

            return True

        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def get_cache(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """キャッシュから値を取得"""
        try:
            redis_client = await self.get_redis()
            value = await redis_client.get(key)

            if value is None:
                return None

            if isinstance(value, bytes):
                value = value.decode("utf-8")

            if deserialize:
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    # JSON形式でない場合はそのまま返す
                    pass

            return value

        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        """キャッシュから値を削除"""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    async def exists_cache(self, key: str) -> bool:
        """キーが存在するかチェック"""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.exists(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to check existence of cache key {key}: {e}")
            return False

    # 統計・監視メソッド
    async def get_channel_stats(self) -> Dict[str, Any]:
        """チャンネル統計を取得"""
        try:
            redis_client = await self.get_redis()
            pubsub_channels = await redis_client.pubsub_channels()

            stats = {
                "active_channels": len(self._pubsub_connections),
                "subscribed_channels": list(self._subscribers.keys()),
                "redis_pubsub_channels": [ch.decode() if isinstance(ch, bytes) else ch for ch in pubsub_channels],
                "running_tasks": len(self._running_tasks),
                "connection_healthy": self._connection_healthy,
                "config": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db,
                },
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get channel stats: {e}")
            return {"error": str(e)}


# グローバルインスタンス
redis_manager = RedisManager()


# 便利関数
async def get_redis_manager() -> RedisManager:
    """RedisManagerインスタンスを取得"""
    if not redis_manager.is_healthy:
        await redis_manager.initialize()
    return redis_manager


async def publish_alert(alert_data: Dict[str, Any], channel: str = "alerts") -> bool:
    """アラートを発行（便利関数）"""
    manager = await get_redis_manager()
    return await manager.publish(channel, alert_data)


async def subscribe_to_alerts(callback: Callable[[str, Any], None], channel: str = "alerts") -> bool:
    """アラートに購読（便利関数）"""
    manager = await get_redis_manager()
    return await manager.subscribe(channel, callback)
