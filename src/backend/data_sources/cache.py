"""
データキャッシュレイヤー
高頻度アクセスデータの効率的なキャッシング
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheKey:
    """キャッシュキーの生成ヘルパー"""

    @staticmethod
    def ticker(exchange: str, symbol: str) -> str:
        return f"ticker:{exchange}:{symbol}"

    @staticmethod
    def ohlcv(exchange: str, symbol: str, timeframe: str, page: int = 0) -> str:
        return f"ohlcv:{exchange}:{symbol}:{timeframe}:{page}"

    @staticmethod
    def funding_rate(exchange: str, symbol: str) -> str:
        return f"funding:{exchange}:{symbol}"

    @staticmethod
    def open_interest(exchange: str, symbol: str) -> str:
        return f"oi:{exchange}:{symbol}"

    @staticmethod
    def balance(exchange: str) -> str:
        return f"balance:{exchange}"


class DataCache:
    """
    多層キャッシュシステム
    
    Layer 1: インメモリキャッシュ（高速・短期）
    Layer 2: Redis（中速・中期）
    """

    def __init__(self, redis_url: Optional[str] = None):
        # Layer 1: インメモリキャッシュ
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_ttl = {
            "ticker": 1,  # 1秒
            "ohlcv": 60,  # 1分
            "funding": 300,  # 5分
            "oi": 60,  # 1分
            "balance": 10,  # 10秒
        }
        
        # Layer 2: Redis
        self._redis_client: Optional[redis.Redis] = None
        self._redis_url = redis_url or "redis://localhost:6379/0"
        self._redis_ttl = {
            "ticker": 5,  # 5秒
            "ohlcv": 3600,  # 1時間
            "funding": 3600,  # 1時間
            "oi": 300,  # 5分
            "balance": 60,  # 1分
        }
        
        # バックグラウンドでRedis接続を初期化
        asyncio.create_task(self._init_redis())

    async def _init_redis(self):
        """Redis接続を初期化"""
        try:
            self._redis_client = await redis.from_url(self._redis_url)
            await self._redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}")
            self._redis_client = None

    def _get_ttl(self, key: str, layer: str = "memory") -> int:
        """キーに基づいてTTLを取得"""
        prefix = key.split(":")[0]
        ttl_map = self._memory_ttl if layer == "memory" else self._redis_ttl
        return ttl_map.get(prefix, 60)  # デフォルト60秒

    async def get(self, key: str) -> Optional[Any]:
        """キャッシュからデータを取得"""
        # Layer 1: メモリキャッシュをチェック
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if datetime.now() < entry["expires"]:
                logger.debug(f"Memory cache hit: {key}")
                return entry["data"]
            else:
                # 期限切れのエントリを削除
                del self._memory_cache[key]
        
        # Layer 2: Redisをチェック
        if self._redis_client:
            try:
                data = await self._redis_client.get(key)
                if data:
                    logger.debug(f"Redis cache hit: {key}")
                    decoded = json.loads(data)
                    
                    # メモリキャッシュにも保存
                    await self._set_memory(key, decoded)
                    
                    return decoded
            except (RedisError, json.JSONDecodeError) as e:
                logger.error(f"Redis cache error: {e}")
        
        logger.debug(f"Cache miss: {key}")
        return None

    async def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """データをキャッシュに保存"""
        # Layer 1: メモリキャッシュに保存
        await self._set_memory(key, data, ttl)
        
        # Layer 2: Redisに保存
        if self._redis_client:
            try:
                redis_ttl = ttl or self._get_ttl(key, "redis")
                serialized = json.dumps(data, default=str)
                await self._redis_client.setex(key, redis_ttl, serialized)
                logger.debug(f"Cached to Redis: {key} (TTL: {redis_ttl}s)")
            except (RedisError, json.JSONEncodeError) as e:
                logger.error(f"Redis cache set error: {e}")

    async def _set_memory(self, key: str, data: Any, ttl: Optional[int] = None):
        """メモリキャッシュにデータを保存"""
        memory_ttl = ttl or self._get_ttl(key, "memory")
        self._memory_cache[key] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=memory_ttl)
        }
        logger.debug(f"Cached to memory: {key} (TTL: {memory_ttl}s)")

    async def delete(self, key: str):
        """キャッシュからデータを削除"""
        # Layer 1: メモリキャッシュから削除
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        # Layer 2: Redisから削除
        if self._redis_client:
            try:
                await self._redis_client.delete(key)
            except RedisError as e:
                logger.error(f"Redis cache delete error: {e}")

    async def clear_pattern(self, pattern: str):
        """パターンに一致するキャッシュをクリア"""
        # Layer 1: メモリキャッシュ
        keys_to_delete = [k for k in self._memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self._memory_cache[key]
        
        # Layer 2: Redis
        if self._redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis_client.scan(
                        cursor, match=f"*{pattern}*"
                    )
                    if keys:
                        await self._redis_client.delete(*keys)
                    if cursor == 0:
                        break
            except RedisError as e:
                logger.error(f"Redis cache clear pattern error: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得"""
        stats = {
            "memory_cache_size": len(self._memory_cache),
            "redis_available": self._redis_client is not None,
        }
        
        if self._redis_client:
            try:
                info = await self._redis_client.info()
                stats.update({
                    "redis_memory_used": info.get("used_memory_human", "N/A"),
                    "redis_keys": await self._redis_client.dbsize(),
                })
            except RedisError:
                pass
        
        return stats

    async def close(self):
        """接続をクリーンアップ"""
        if self._redis_client:
            await self._redis_client.close()


# グローバルキャッシュインスタンス
_cache_instance: Optional[DataCache] = None


def get_cache() -> DataCache:
    """キャッシュインスタンスを取得"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache()
    return _cache_instance