"""
メッセージングシステム

Redis Pub/Subを使用したアラート・通知システムの
メッセージング基盤を提供
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone

from .redis import RedisManager, get_redis_manager
from ..models.alerts import UnifiedAlert, AlertLevel, AlertCategory

logger = logging.getLogger(__name__)


class AlertChannels:
    """アラート関連のチャンネル定数"""

    # メインチャンネル
    ALERTS = "alerts"
    ALERTS_HIGH_PRIORITY = "alerts:high_priority"
    ALERTS_CRITICAL = "alerts:critical"

    # カテゴリ別チャンネル
    ALERTS_RISK = "alerts:risk"
    ALERTS_PERFORMANCE = "alerts:performance"
    ALERTS_EXECUTION = "alerts:execution"
    ALERTS_SYSTEM = "alerts:system"
    ALERTS_MARKET = "alerts:market"

    # 処理状況チャンネル
    ALERTS_ACKNOWLEDGED = "alerts:acknowledged"
    ALERTS_RESOLVED = "alerts:resolved"

    # 統計・監視チャンネル
    ALERTS_STATS = "alerts:stats"
    SYSTEM_HEALTH = "system:health"

    # 通知状況チャンネル
    NOTIFICATIONS_SENT = "notifications:sent"
    NOTIFICATIONS_FAILED = "notifications:failed"


class MessagePriority:
    """メッセージ優先度"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AlertMessage:
    """アラートメッセージ包装クラス"""

    def __init__(
        self,
        alert: UnifiedAlert,
        priority: int = MessagePriority.NORMAL,
        routing_key: Optional[str] = None,
    ):
        self.alert = alert
        self.priority = priority
        self.routing_key = routing_key or self._determine_routing_key()
        self.created_at = datetime.now(timezone.utc)
        self.message_id = f"msg_{alert.id}"

    def _determine_routing_key(self) -> str:
        """アラートの内容に基づいてルーティングキーを決定"""
        if self.alert.level == AlertLevel.CRITICAL:
            return AlertChannels.ALERTS_CRITICAL
        elif self.alert.level == AlertLevel.ERROR:
            return AlertChannels.ALERTS_HIGH_PRIORITY
        else:
            # カテゴリ別にルーティング
            category_channels = {
                AlertCategory.RISK: AlertChannels.ALERTS_RISK,
                AlertCategory.PERFORMANCE: AlertChannels.ALERTS_PERFORMANCE,
                AlertCategory.EXECUTION: AlertChannels.ALERTS_EXECUTION,
                AlertCategory.SYSTEM: AlertChannels.ALERTS_SYSTEM,
                AlertCategory.MARKET: AlertChannels.ALERTS_MARKET,
            }
            return category_channels.get(self.alert.category, AlertChannels.ALERTS)

    def to_dict(self) -> Dict[str, Any]:
        """メッセージを辞書形式に変換"""
        return {
            "message_id": self.message_id,
            "priority": self.priority,
            "routing_key": self.routing_key,
            "created_at": self.created_at.isoformat(),
            "alert": self.alert.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertMessage":
        """辞書からメッセージを復元"""
        alert = UnifiedAlert.from_dict(data["alert"])
        message = cls(
            alert=alert,
            priority=data.get("priority", MessagePriority.NORMAL),
            routing_key=data.get("routing_key"),
        )
        message.message_id = data.get("message_id", f"msg_{alert.id}")
        if "created_at" in data:
            message.created_at = datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            )
        return message


class AlertPublisher:
    """アラート発行者"""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager
        self._stats = {"published_count": 0, "failed_count": 0, "last_published": None}

    async def _get_redis_manager(self) -> RedisManager:
        """RedisManagerを取得"""
        if not self.redis_manager:
            self.redis_manager = await get_redis_manager()
        return self.redis_manager

    async def publish_alert(
        self,
        alert: UnifiedAlert,
        priority: int = MessagePriority.NORMAL,
        specific_channel: Optional[str] = None,
    ) -> bool:
        """アラートを発行"""
        try:
            redis_manager = await self._get_redis_manager()

            # アラートメッセージを作成
            message = AlertMessage(alert, priority, specific_channel)

            # メインチャンネルに発行
            main_channel = specific_channel or message.routing_key
            success_main = await redis_manager.publish(main_channel, message.to_dict())

            # 全体チャンネルにも発行（統計・監視用）
            success_all = await redis_manager.publish(
                AlertChannels.ALERTS, message.to_dict()
            )

            # 優先度別チャンネルにも発行
            if priority >= MessagePriority.HIGH:
                await redis_manager.publish(
                    AlertChannels.ALERTS_HIGH_PRIORITY, message.to_dict()
                )

            if alert.level == AlertLevel.CRITICAL:
                await redis_manager.publish(
                    AlertChannels.ALERTS_CRITICAL, message.to_dict()
                )

            if success_main or success_all:
                self._stats["published_count"] += 1
                self._stats["last_published"] = datetime.now(timezone.utc)
                logger.debug(f"Published alert {alert.id} to channels: {main_channel}")
                return True
            else:
                self._stats["failed_count"] += 1
                logger.warning(f"No subscribers for alert {alert.id}")
                return False

        except Exception as e:
            self._stats["failed_count"] += 1
            logger.error(f"Failed to publish alert {alert.id}: {e}")
            return False

    async def publish_bulk_alerts(
        self, alerts: List[UnifiedAlert], priority: int = MessagePriority.NORMAL
    ) -> Dict[str, int]:
        """複数のアラートを一括発行"""
        results = {"success": 0, "failed": 0}

        for alert in alerts:
            success = await self.publish_alert(alert, priority)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Bulk publish completed: {results}")
        return results

    async def publish_status_update(
        self,
        alert_id: str,
        status: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """アラートステータス更新を発行"""
        try:
            redis_manager = await self._get_redis_manager()

            status_message = {
                "alert_id": alert_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": additional_data or {},
            }

            channel = {
                "acknowledged": AlertChannels.ALERTS_ACKNOWLEDGED,
                "resolved": AlertChannels.ALERTS_RESOLVED,
            }.get(status, AlertChannels.ALERTS)

            return await redis_manager.publish(channel, status_message)

        except Exception as e:
            logger.error(f"Failed to publish status update for {alert_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """発行統計を取得"""
        return {
            **self._stats,
            "last_published": self._stats["last_published"].isoformat()
            if self._stats["last_published"]
            else None,
        }


class AlertSubscriber:
    """アラート購読者"""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._stats = {
            "received_count": 0,
            "processed_count": 0,
            "failed_count": 0,
            "last_received": None,
        }

    async def _get_redis_manager(self) -> RedisManager:
        """RedisManagerを取得"""
        if not self.redis_manager:
            self.redis_manager = await get_redis_manager()
        return self.redis_manager

    async def subscribe_to_alerts(
        self,
        callback: Callable[[UnifiedAlert], None],
        channels: Optional[List[str]] = None,
        alert_levels: Optional[List[AlertLevel]] = None,
        alert_categories: Optional[List[AlertCategory]] = None,
    ) -> bool:
        """アラートに購読"""
        try:
            redis_manager = await self._get_redis_manager()

            # デフォルトチャンネル
            if not channels:
                channels = [AlertChannels.ALERTS]

            # フィルター付きコールバックを作成
            filtered_callback = self._create_filtered_callback(
                callback, alert_levels, alert_categories
            )

            # 各チャンネルに購読
            for channel in channels:
                success = await redis_manager.subscribe(channel, filtered_callback)

                if success:
                    if channel not in self._subscriptions:
                        self._subscriptions[channel] = []
                    self._subscriptions[channel].append(callback)
                    logger.info(f"Subscribed to channel: {channel}")
                else:
                    logger.error(f"Failed to subscribe to channel: {channel}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to alerts: {e}")
            return False

    def _create_filtered_callback(
        self,
        original_callback: Callable[[UnifiedAlert], None],
        alert_levels: Optional[List[AlertLevel]] = None,
        alert_categories: Optional[List[AlertCategory]] = None,
    ) -> Callable[[str, Any], None]:
        """フィルター付きコールバックを作成"""

        async def filtered_callback(channel: str, message_data: Any):
            try:
                self._stats["received_count"] += 1
                self._stats["last_received"] = datetime.now(timezone.utc)

                # メッセージを解析
                if isinstance(message_data, dict):
                    if "alert" in message_data:
                        # AlertMessage形式
                        alert_message = AlertMessage.from_dict(message_data)
                        alert = alert_message.alert
                    else:
                        # 直接Alert形式
                        alert = UnifiedAlert.from_dict(message_data)
                else:
                    logger.warning(
                        f"Invalid message format from {channel}: {type(message_data)}"
                    )
                    return

                # フィルター適用
                if alert_levels and alert.level not in alert_levels:
                    return

                if alert_categories and alert.category not in alert_categories:
                    return

                # コールバック実行
                if asyncio.iscoroutinefunction(original_callback):
                    await original_callback(alert)
                else:
                    original_callback(alert)

                self._stats["processed_count"] += 1

            except Exception as e:
                self._stats["failed_count"] += 1
                logger.error(f"Error in alert callback for channel {channel}: {e}")

        return filtered_callback

    async def subscribe_to_critical_alerts(
        self, callback: Callable[[UnifiedAlert], None]
    ) -> bool:
        """クリティカルアラート専用購読"""
        return await self.subscribe_to_alerts(
            callback,
            channels=[AlertChannels.ALERTS_CRITICAL],
            alert_levels=[AlertLevel.CRITICAL],
        )

    async def subscribe_to_risk_alerts(
        self, callback: Callable[[UnifiedAlert], None]
    ) -> bool:
        """リスクアラート専用購読"""
        return await self.subscribe_to_alerts(
            callback,
            channels=[AlertChannels.ALERTS_RISK],
            alert_categories=[AlertCategory.RISK],
        )

    async def subscribe_to_status_updates(
        self, callback: Callable[[str, str, Dict[str, Any]], None]
    ) -> bool:
        """ステータス更新に購読"""
        try:
            redis_manager = await self._get_redis_manager()

            async def status_callback(channel: str, message_data: Any):
                try:
                    if isinstance(message_data, dict):
                        alert_id = message_data.get("alert_id")
                        status = message_data.get("status")
                        data = message_data.get("data", {})

                        if asyncio.iscoroutinefunction(callback):
                            await callback(alert_id, status, data)
                        else:
                            callback(alert_id, status, data)

                except Exception as e:
                    logger.error(f"Error in status update callback: {e}")

            channels = [
                AlertChannels.ALERTS_ACKNOWLEDGED,
                AlertChannels.ALERTS_RESOLVED,
            ]

            for channel in channels:
                await redis_manager.subscribe(channel, status_callback)

            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to status updates: {e}")
            return False

    async def unsubscribe(
        self, channel: str, callback: Optional[Callable] = None
    ) -> bool:
        """購読解除"""
        try:
            redis_manager = await self._get_redis_manager()

            if channel in self._subscriptions:
                if callback and callback in self._subscriptions[channel]:
                    self._subscriptions[channel].remove(callback)
                else:
                    self._subscriptions[channel].clear()

                if not self._subscriptions[channel]:
                    del self._subscriptions[channel]

            return await redis_manager.unsubscribe(channel, callback)

        except Exception as e:
            logger.error(f"Failed to unsubscribe from {channel}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """購読統計を取得"""
        return {
            **self._stats,
            "active_subscriptions": len(self._subscriptions),
            "subscribed_channels": list(self._subscriptions.keys()),
            "last_received": self._stats["last_received"].isoformat()
            if self._stats["last_received"]
            else None,
        }


class AlertMessageBroker:
    """アラートメッセージブローカー（発行と購読の統合）"""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.publisher = AlertPublisher(redis_manager)
        self.subscriber = AlertSubscriber(redis_manager)
        self._started = False

    async def start(self) -> bool:
        """ブローカーを開始"""
        try:
            # Redis接続確認
            redis_manager = await get_redis_manager()
            if not redis_manager.is_healthy:
                await redis_manager.initialize()

            self._started = True
            logger.info("AlertMessageBroker started")
            return True

        except Exception as e:
            logger.error(f"Failed to start AlertMessageBroker: {e}")
            return False

    async def stop(self):
        """ブローカーを停止"""
        try:
            # 購読を全て解除
            for channel in list(self.subscriber._subscriptions.keys()):
                await self.subscriber.unsubscribe(channel)

            self._started = False
            logger.info("AlertMessageBroker stopped")

        except Exception as e:
            logger.error(f"Error stopping AlertMessageBroker: {e}")

    async def publish(
        self, alert: UnifiedAlert, priority: int = MessagePriority.NORMAL
    ) -> bool:
        """アラートを発行"""
        if not self._started:
            logger.warning("MessageBroker not started, attempting to start...")
            await self.start()

        return await self.publisher.publish_alert(alert, priority)

    async def subscribe(
        self,
        callback: Callable[[UnifiedAlert], None],
        channels: Optional[List[str]] = None,
        **filter_kwargs,
    ) -> bool:
        """アラートに購読"""
        if not self._started:
            logger.warning("MessageBroker not started, attempting to start...")
            await self.start()

        return await self.subscriber.subscribe_to_alerts(
            callback, channels, **filter_kwargs
        )

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "started": self._started,
            "publisher_stats": self.publisher.get_stats(),
            "subscriber_stats": self.subscriber.get_stats(),
        }


# グローバルインスタンス
alert_broker = AlertMessageBroker()


# 便利関数
async def publish_alert(
    alert: UnifiedAlert, priority: int = MessagePriority.NORMAL
) -> bool:
    """アラートを発行（便利関数）"""
    return await alert_broker.publish(alert, priority)


async def subscribe_to_alerts(
    callback: Callable[[UnifiedAlert], None],
    channels: Optional[List[str]] = None,
    **filter_kwargs,
) -> bool:
    """アラートに購読（便利関数）"""
    return await alert_broker.subscribe(callback, channels, **filter_kwargs)


async def get_messaging_stats() -> Dict[str, Any]:
    """メッセージング統計を取得"""
    redis_manager = await get_redis_manager()
    redis_stats = await redis_manager.get_channel_stats()
    broker_stats = alert_broker.get_stats()

    return {
        "redis": redis_stats,
        "broker": broker_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
