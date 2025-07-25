"""
通知ワーカーシステム

Redis Pub/Subからアラートを受信し、
設定に基づいて適切な通知チャネルに配信
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml

from ..core.messaging import AlertChannels, AlertSubscriber
from ..core.redis import get_redis_manager
from ..models.alerts import UnifiedAlert
from .channels.base import NotificationChannel, NotificationResult
from .channels.email import EmailChannel, EmailConfig
from .channels.slack import SlackChannel, SlackConfig
from .channels.webhook import WebhookChannel, WebhookConfig

logger = logging.getLogger(__name__)


@dataclass
class NotificationRule:
    """通知ルール"""

    name: str
    priority: int
    enabled: bool
    conditions: Dict[str, Any]
    channels: List[str]
    throttle: Dict[str, Any] = field(default_factory=dict)
    batch: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchedAlert:
    """バッチ化されたアラート"""

    alerts: List[UnifiedAlert] = field(default_factory=list)
    first_alert_time: Optional[datetime] = None
    last_alert_time: Optional[datetime] = None
    rule_name: str = ""
    channels: List[str] = field(default_factory=list)


class NotificationChannelFactory:
    """通知チャネルファクトリー"""

    @staticmethod
    def create_channel(channel_type: str, config: Dict[str, Any]) -> Optional[NotificationChannel]:
        """チャネルを作成"""
        try:
            if channel_type == "email":
                email_config = EmailConfig(
                    smtp_server=config.get("smtp_server", ""),
                    smtp_port=config.get("smtp_port", 587),
                    username=config.get("username", ""),
                    password=config.get("password", ""),
                    from_email=config.get("from_email", ""),
                    to_emails=config.get("to_emails", []),
                    use_tls=config.get("use_tls", True),
                    use_ssl=config.get("use_ssl", False),
                    enabled=config.get("enabled", False),
                    timeout_seconds=config.get("timeout_seconds", 30),
                    retry_attempts=config.get("retry_attempts", 3),
                    html_format=config.get("html_format", True),
                    subject_prefix=config.get("subject_prefix", "[CryptoBot Alert]"),
                )
                return EmailChannel(email_config)

            elif channel_type == "slack":
                slack_config = SlackConfig(
                    webhook_url=config.get("webhook_url", ""),
                    channel=config.get("channel", "#alerts"),
                    username=config.get("username", "CryptoBot"),
                    icon_emoji=config.get("icon_emoji", ":warning:"),
                    enabled=config.get("enabled", False),
                    timeout_seconds=config.get("timeout_seconds", 30),
                    retry_attempts=config.get("retry_attempts", 3),
                    use_attachments=config.get("use_attachments", True),
                    color_coding=config.get("color_coding", True),
                )
                return SlackChannel(slack_config)

            elif channel_type == "webhook":
                webhook_config = WebhookConfig(
                    url=config.get("url", ""),
                    method=config.get("method", "POST"),
                    headers=config.get("headers", {}),
                    enabled=config.get("enabled", False),
                    timeout_seconds=config.get("timeout_seconds", 30),
                    retry_attempts=config.get("retry_attempts", 3),
                    auth_type=config.get("auth_type"),
                    auth_token=config.get("auth_token"),
                    payload_format=config.get("payload_format", "json"),
                    verify_ssl=config.get("verify_ssl", True),
                    include_metadata=config.get("include_metadata", True),
                )
                return WebhookChannel(webhook_config)

            else:
                logger.error(f"Unknown channel type: {channel_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create {channel_type} channel: {e}")
            return None


class NotificationRuleEngine:
    """通知ルールエンジン"""

    def __init__(self, rules: List[NotificationRule]):
        self.rules = sorted(rules, key=lambda x: x.priority)

    def find_matching_rules(self, alert: UnifiedAlert) -> List[NotificationRule]:
        """アラートにマッチするルールを検索"""
        matching_rules = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if self._rule_matches(rule, alert):
                matching_rules.append(rule)

        return matching_rules

    def _rule_matches(self, rule: NotificationRule, alert: UnifiedAlert) -> bool:
        """ルールがアラートにマッチするかチェック"""
        conditions = rule.conditions

        # カテゴリ条件
        if "category" in conditions:
            category_filter = conditions["category"]
            if isinstance(category_filter, str):
                if alert.category.value != category_filter:
                    return False
            elif isinstance(category_filter, list):
                if alert.category.value not in category_filter:
                    return False

        # レベル条件
        if "level" in conditions:
            level_filter = conditions["level"]
            if isinstance(level_filter, str):
                if alert.level.value != level_filter:
                    return False
            elif isinstance(level_filter, list):
                if alert.level.value not in level_filter:
                    return False

        # アラートタイプ条件
        if "alert_type" in conditions:
            type_filter = conditions["alert_type"]
            if isinstance(type_filter, str):
                if alert.alert_type.value != type_filter:
                    return False
            elif isinstance(type_filter, list):
                if alert.alert_type.value not in type_filter:
                    return False

        # シンボル条件
        if "symbol" in conditions:
            symbol_filter = conditions["symbol"]
            alert_symbol = alert.metadata.symbol if alert.metadata else None
            if isinstance(symbol_filter, str):
                if alert_symbol != symbol_filter:
                    return False
            elif isinstance(symbol_filter, list):
                if alert_symbol not in symbol_filter:
                    return False

        # 戦略条件
        if "strategy" in conditions:
            strategy_filter = conditions["strategy"]
            alert_strategy = alert.metadata.strategy_name if alert.metadata else None
            if isinstance(strategy_filter, str):
                if alert_strategy != strategy_filter:
                    return False
            elif isinstance(strategy_filter, list):
                if alert_strategy not in strategy_filter:
                    return False

        return True


class NotificationWorker:
    """通知ワーカー"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join("config", "alerts.yml")
        self.config: Dict[str, Any] = {}
        self.channels: Dict[str, NotificationChannel] = {}
        self.rule_engine: Optional[NotificationRuleEngine] = None
        self.subscriber: Optional[AlertSubscriber] = None

        # バッチ処理用
        self.batched_alerts: Dict[str, BatchedAlert] = {}
        self.batch_task: Optional[asyncio.Task] = None

        # 統計情報
        self.stats = {
            "alerts_received": 0,
            "notifications_sent": 0,
            "notifications_failed": 0,
            "batched_alerts": 0,
            "last_alert": None,
            "last_notification": None,
            "channel_stats": {},
        }

        self._running = False
        self._load_config()

    def _load_config(self):
        """設定ファイルを読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"Notification worker config loaded from {self.config_path}")
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                self.config = {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

    async def initialize(self):
        """ワーカーを初期化"""
        try:
            # 通知チャネルを初期化
            await self._initialize_channels()

            # ルールエンジンを初期化
            self._initialize_rule_engine()

            # Subscriberを初期化
            self.subscriber = AlertSubscriber()

            # Redis接続確認
            redis_manager = await get_redis_manager()
            if not redis_manager.is_healthy:
                await redis_manager.initialize()

            logger.info("NotificationWorker initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize NotificationWorker: {e}")
            return False

    async def _initialize_channels(self):
        """通知チャネルを初期化"""
        channel_configs = self.config.get("notification_channels", {})

        for channel_name, channel_config in channel_configs.items():
            if channel_config.get("enabled", False):
                channel = NotificationChannelFactory.create_channel(channel_name, channel_config)
                if channel:
                    self.channels[channel_name] = channel
                    logger.info(f"Initialized {channel_name} channel")
                else:
                    logger.error(f"Failed to initialize {channel_name} channel")

    def _initialize_rule_engine(self):
        """ルールエンジンを初期化"""
        rules_config = self.config.get("notification_rules", [])
        rules = []

        for rule_config in rules_config:
            rule = NotificationRule(
                name=rule_config.get("name", ""),
                priority=rule_config.get("priority", 999),
                enabled=rule_config.get("enabled", True),
                conditions=rule_config.get("conditions", {}),
                channels=rule_config.get("channels", []),
                throttle=rule_config.get("throttle", {}),
                batch=rule_config.get("batch", {}),
            )
            rules.append(rule)

        self.rule_engine = NotificationRuleEngine(rules)
        logger.info(f"Initialized rule engine with {len(rules)} rules")

    async def start(self):
        """ワーカーを開始"""
        if self._running:
            logger.warning("Worker is already running")
            return

        try:
            self._running = True

            # アラート購読を開始
            if self.subscriber:
                await self.subscriber.subscribe_to_alerts(self._handle_alert, channels=[AlertChannels.ALERTS])

            # バッチ処理タスクを開始
            self.batch_task = asyncio.create_task(self._batch_processor())

            logger.info("NotificationWorker started")

        except Exception as e:
            logger.error(f"Failed to start NotificationWorker: {e}")
            self._running = False
            raise

    async def stop(self):
        """ワーカーを停止"""
        try:
            self._running = False

            # バッチ処理タスクを停止
            if self.batch_task and not self.batch_task.done():
                self.batch_task.cancel()
                try:
                    await self.batch_task
                except asyncio.CancelledError:
                    pass

            # 残りのバッチアラートを処理
            await self._flush_batched_alerts()

            logger.info("NotificationWorker stopped")

        except Exception as e:
            logger.error(f"Error stopping NotificationWorker: {e}")

    async def _handle_alert(self, alert: UnifiedAlert):
        """アラートを処理"""
        try:
            self.stats["alerts_received"] += 1
            self.stats["last_alert"] = datetime.now(timezone.utc)

            if not self.rule_engine:
                logger.warning("Rule engine not initialized")
                return

            # マッチするルールを検索
            matching_rules = self.rule_engine.find_matching_rules(alert)

            if not matching_rules:
                logger.debug(f"No matching rules for alert {alert.id}")
                return

            # ルールに基づいて処理
            for rule in matching_rules:
                await self._process_rule(rule, alert)

        except Exception as e:
            logger.error(f"Error handling alert {alert.id}: {e}")

    async def _process_rule(self, rule: NotificationRule, alert: UnifiedAlert):
        """ルールに基づいてアラートを処理"""
        try:
            # バッチ処理が有効な場合
            if rule.batch.get("enabled", False):
                await self._add_to_batch(rule, alert)
            else:
                # 即座に通知
                await self._send_notifications(rule.channels, [alert])

        except Exception as e:
            logger.error(f"Error processing rule {rule.name} for alert {alert.id}: {e}")

    async def _add_to_batch(self, rule: NotificationRule, alert: UnifiedAlert):
        """アラートをバッチに追加"""
        rule_name = rule.name
        now = datetime.now(timezone.utc)

        if rule_name not in self.batched_alerts:
            self.batched_alerts[rule_name] = BatchedAlert(
                rule_name=rule_name, channels=rule.channels, first_alert_time=now
            )

        batch = self.batched_alerts[rule_name]
        batch.alerts.append(alert)
        batch.last_alert_time = now

        self.stats["batched_alerts"] += 1

        # バッチサイズ制限チェック
        batch_window_minutes = rule.batch.get("batch_window_minutes", 15)
        max_batch_size = rule.batch.get("max_batch_size", 50)

        if len(batch.alerts) >= max_batch_size or (
            batch.first_alert_time and (now - batch.first_alert_time).total_seconds() >= batch_window_minutes * 60
        ):
            await self._flush_batch(rule_name)

    async def _flush_batch(self, rule_name: str):
        """バッチを送信"""
        if rule_name not in self.batched_alerts:
            return

        batch = self.batched_alerts[rule_name]
        if not batch.alerts:
            return

        try:
            await self._send_notifications(batch.channels, batch.alerts)
            logger.info(f"Flushed batch {rule_name} with {len(batch.alerts)} alerts")
        except Exception as e:
            logger.error(f"Failed to flush batch {rule_name}: {e}")
        finally:
            del self.batched_alerts[rule_name]

    async def _flush_batched_alerts(self):
        """すべてのバッチアラートを送信"""
        for rule_name in list(self.batched_alerts.keys()):
            await self._flush_batch(rule_name)

    async def _batch_processor(self):
        """バッチ処理定期実行"""
        while self._running:
            try:
                await asyncio.sleep(30)  # 30秒ごとにチェック

                now = datetime.now(timezone.utc)
                expired_batches = []

                for rule_name, batch in self.batched_alerts.items():
                    if batch.first_alert_time and (now - batch.first_alert_time).total_seconds() >= 900:  # 15分
                        expired_batches.append(rule_name)

                for rule_name in expired_batches:
                    await self._flush_batch(rule_name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")

    async def _send_notifications(self, channel_names: List[str], alerts: List[UnifiedAlert]):
        """通知を送信"""
        for channel_name in channel_names:
            if channel_name in self.channels:
                channel = self.channels[channel_name]

                try:
                    if len(alerts) == 1:
                        result = await channel.send_alert(alerts[0])
                        await self._record_result(channel_name, result)
                    else:
                        results = await channel.send_bulk_alerts(alerts)
                        for result in results:
                            await self._record_result(channel_name, result)

                except Exception as e:
                    logger.error(f"Error sending to {channel_name}: {e}")
                    self.stats["notifications_failed"] += 1
            else:
                logger.warning(f"Channel {channel_name} not found")

    async def _record_result(self, channel_name: str, result: NotificationResult):
        """通知結果を記録"""
        self.stats["last_notification"] = datetime.now(timezone.utc)

        if channel_name not in self.stats["channel_stats"]:
            self.stats["channel_stats"][channel_name] = {
                "sent": 0,
                "failed": 0,
                "last_sent": None,
            }

        channel_stats = self.stats["channel_stats"][channel_name]

        if result.is_success:
            self.stats["notifications_sent"] += 1
            channel_stats["sent"] += 1
            channel_stats["last_sent"] = result.timestamp
        else:
            self.stats["notifications_failed"] += 1
            channel_stats["failed"] += 1

        logger.debug(f"Notification result for {channel_name}: {result.status.value}")

    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            health = {
                "healthy": True,
                "running": self._running,
                "components": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # チャネルヘルスチェック
            for channel_name, channel in self.channels.items():
                try:
                    channel_health = await channel.health_check()
                    health["components"][f"channel_{channel_name}"] = channel_health
                    if not channel_health.get("healthy", False):
                        health["healthy"] = False
                except Exception as e:
                    health["components"][f"channel_{channel_name}"] = {
                        "healthy": False,
                        "message": str(e),
                    }
                    health["healthy"] = False

            # ルールエンジンチェック
            health["components"]["rule_engine"] = {
                "healthy": self.rule_engine is not None,
                "rules_count": len(self.rule_engine.rules) if self.rule_engine else 0,
            }

            # Subscriberチェック
            health["components"]["subscriber"] = {
                "healthy": self.subscriber is not None,
                "subscriptions": len(self.subscriber._subscriptions) if self.subscriber else 0,
            }

            return health

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = dict(self.stats)
        stats["last_alert"] = self.stats["last_alert"].isoformat() if self.stats["last_alert"] else None
        stats["last_notification"] = (
            self.stats["last_notification"].isoformat() if self.stats["last_notification"] else None
        )
        stats["running"] = self._running
        stats["active_batches"] = len(self.batched_alerts)
        stats["channels_count"] = len(self.channels)
        return stats


# グローバルインスタンス
_notification_worker: Optional[NotificationWorker] = None


async def get_notification_worker() -> NotificationWorker:
    """グローバル通知ワーカーを取得"""
    global _notification_worker

    if _notification_worker is None:
        _notification_worker = NotificationWorker()
        await _notification_worker.initialize()

    return _notification_worker


async def start_notification_worker():
    """通知ワーカーを開始"""
    worker = await get_notification_worker()
    await worker.start()


async def stop_notification_worker():
    """通知ワーカーを停止"""
    global _notification_worker
    if _notification_worker:
        await _notification_worker.stop()
