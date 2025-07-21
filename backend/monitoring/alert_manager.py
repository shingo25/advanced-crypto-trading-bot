"""
統合アラートマネージャー

既存のアラートシステムと新しいRedis Pub/Subシステムを
統合する中央管理システム
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

from ..core.messaging import AlertMessageBroker, MessagePriority
from ..core.redis import get_redis_manager
from ..models.alerts import (
    AlertCategory,
    AlertLevel,
    AlertType,
    UnifiedAlert,
    create_performance_alert,
    create_risk_alert,
    create_system_alert,
)

logger = logging.getLogger(__name__)


class AlertConfigManager:
    """アラート設定管理"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join("config", "alerts.yml")
        self.config: Dict[str, Any] = {}
        self.last_loaded: Optional[datetime] = None
        self._load_config()

    def _load_config(self):
        """設定ファイルを読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                self.last_loaded = datetime.now(timezone.utc)
                logger.info(f"Alert config loaded from {self.config_path}")
            else:
                logger.warning(f"Alert config file not found: {self.config_path}")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Failed to load alert config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """デフォルト設定を作成"""
        self.config = {
            "alert_system": {"enabled": True},
            "notification_channels": {},
            "notification_rules": [],
            "filters": {},
        }

    def reload_config(self):
        """設定を再読み込み"""
        self._load_config()

    def is_enabled(self) -> bool:
        """アラートシステムが有効かチェック"""
        return self.config.get("alert_system", {}).get("enabled", True)

    def get_notification_rules(self) -> List[Dict[str, Any]]:
        """通知ルールを取得"""
        return self.config.get("notification_rules", [])

    def get_filters(self) -> Dict[str, Any]:
        """フィルター設定を取得"""
        return self.config.get("filters", {})

    def get_channel_config(self, channel_name: str) -> Dict[str, Any]:
        """チャネル設定を取得"""
        channels = self.config.get("notification_channels", {})
        return channels.get(channel_name, {})


class AlertThrottleManager:
    """アラート抑制管理"""

    def __init__(self):
        self._throttle_cache: Dict[str, datetime] = {}
        self._duplicate_cache: Dict[str, List[datetime]] = {}

    def should_throttle(self, alert: UnifiedAlert, window_minutes: int = 5) -> bool:
        """アラートを抑制すべきかチェック"""
        throttle_key = self._get_throttle_key(alert)
        now = datetime.now(timezone.utc)

        if throttle_key in self._throttle_cache:
            last_sent = self._throttle_cache[throttle_key]
            if (now - last_sent).total_seconds() < window_minutes * 60:
                return True

        self._throttle_cache[throttle_key] = now
        return False

    def _get_throttle_key(self, alert: UnifiedAlert) -> str:
        """抑制キーを生成"""
        components = [
            alert.category.value,
            alert.alert_type.value,
            alert.metadata.symbol if alert.metadata and alert.metadata.symbol else "",
            alert.metadata.strategy_name if alert.metadata and alert.metadata.strategy_name else "",
        ]
        return ":".join(filter(None, components))

    def check_duplicate(self, alert: UnifiedAlert, window_minutes: int = 5) -> bool:
        """重複アラートをチェック"""
        content_hash = alert.content_hash
        if not content_hash:
            return False

        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=window_minutes)

        if content_hash not in self._duplicate_cache:
            self._duplicate_cache[content_hash] = []

        # 古いエントリを削除
        self._duplicate_cache[content_hash] = [
            timestamp for timestamp in self._duplicate_cache[content_hash] if timestamp > cutoff_time
        ]

        # 重複チェック
        if self._duplicate_cache[content_hash]:
            return True

        # エントリを追加
        self._duplicate_cache[content_hash].append(now)
        return False

    def cleanup_old_entries(self):
        """古いエントリをクリーンアップ"""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=1)

        # スロットルキャッシュのクリーンアップ
        expired_keys = [key for key, timestamp in self._throttle_cache.items() if timestamp < cutoff_time]
        for key in expired_keys:
            del self._throttle_cache[key]

        # 重複キャッシュのクリーンアップ
        for content_hash in list(self._duplicate_cache.keys()):
            self._duplicate_cache[content_hash] = [
                timestamp for timestamp in self._duplicate_cache[content_hash] if timestamp > cutoff_time
            ]
            if not self._duplicate_cache[content_hash]:
                del self._duplicate_cache[content_hash]


class IntegratedAlertManager:
    """統合アラートマネージャー"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = AlertConfigManager(config_path)
        self.throttle_manager = AlertThrottleManager()
        self.message_broker: Optional[AlertMessageBroker] = None

        # 統計情報
        self.stats = {
            "total_alerts": 0,
            "sent_alerts": 0,
            "throttled_alerts": 0,
            "duplicate_alerts": 0,
            "failed_alerts": 0,
            "last_alert": None,
            "alerts_by_level": {level.value: 0 for level in AlertLevel},
            "alerts_by_category": {category.value: 0 for category in AlertCategory},
        }

        # クリーンアップタスク
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info("IntegratedAlertManager initialized")

    async def initialize(self):
        """アラートマネージャーを初期化"""
        try:
            # Redis接続確認
            redis_manager = await get_redis_manager()
            if not redis_manager.is_healthy:
                await redis_manager.initialize()

            # メッセージブローカー初期化
            self.message_broker = AlertMessageBroker()
            await self.message_broker.start()

            # クリーンアップタスクを開始
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

            logger.info("IntegratedAlertManager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize IntegratedAlertManager: {e}")
            return False

    async def shutdown(self):
        """アラートマネージャーを停止"""
        try:
            # クリーンアップタスクを停止
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # メッセージブローカーを停止
            if self.message_broker:
                await self.message_broker.stop()

            logger.info("IntegratedAlertManager shut down")

        except Exception as e:
            logger.error(f"Error during IntegratedAlertManager shutdown: {e}")

    async def send_alert(
        self,
        alert: UnifiedAlert,
        priority: int = MessagePriority.NORMAL,
        bypass_throttle: bool = False,
    ) -> bool:
        """アラートを送信"""
        try:
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_level"][alert.level.value] += 1
            self.stats["alerts_by_category"][alert.category.value] += 1
            self.stats["last_alert"] = datetime.now(timezone.utc)

            # システムが無効な場合
            if not self.config_manager.is_enabled():
                logger.debug("Alert system is disabled")
                return False

            # フィルターチェック
            if not self._passes_filters(alert):
                logger.debug(f"Alert {alert.id} filtered out")
                return False

            # 重複チェック
            if self.throttle_manager.check_duplicate(alert):
                self.stats["duplicate_alerts"] += 1
                logger.debug(f"Duplicate alert {alert.id} detected")
                return False

            # スロットルチェック
            if not bypass_throttle and self.throttle_manager.should_throttle(alert):
                self.stats["throttled_alerts"] += 1
                logger.debug(f"Alert {alert.id} throttled")
                return False

            # メッセージブローカー経由で送信
            if self.message_broker:
                success = await self.message_broker.publish(alert, priority)
                if success:
                    self.stats["sent_alerts"] += 1
                    logger.info(f"Alert {alert.id} sent successfully")
                else:
                    self.stats["failed_alerts"] += 1
                    logger.error(f"Failed to send alert {alert.id}")
                return success
            else:
                logger.error("Message broker not initialized")
                self.stats["failed_alerts"] += 1
                return False

        except Exception as e:
            logger.error(f"Error sending alert {alert.id}: {e}")
            self.stats["failed_alerts"] += 1
            return False

    def _passes_filters(self, alert: UnifiedAlert) -> bool:
        """フィルターをチェック"""
        filters = self.config_manager.get_filters()

        # 除外アラートタイプ
        excluded_types = filters.get("excluded_alert_types", [])
        if alert.alert_type.value in excluded_types:
            return False

        # 除外ソースコンポーネント
        excluded_sources = filters.get("excluded_sources", [])
        if alert.metadata and alert.metadata.source_component in excluded_sources:
            return False

        # 戦略フィルター
        strategy_filters = filters.get("strategy_filters", {})
        if alert.metadata and alert.metadata.strategy_name:
            strategy_config = strategy_filters.get(alert.metadata.strategy_name)
            if strategy_config and not strategy_config.get("enabled", True):
                return False

        # シンボルフィルター
        symbol_filters = filters.get("symbol_filters", {})
        if alert.metadata and alert.metadata.symbol:
            symbol_config = symbol_filters.get(alert.metadata.symbol)
            if symbol_config and not symbol_config.get("enabled", True):
                return False

        # 営業時間フィルター
        business_hours = filters.get("business_hours", {})
        if business_hours.get("enabled", False):
            if not self._is_business_hours(business_hours):
                return False

        return True

    def _is_business_hours(self, business_hours_config: Dict[str, Any]) -> bool:
        """営業時間内かチェック"""
        now = datetime.now(timezone.utc)

        # 曜日チェック
        if business_hours_config.get("weekdays_only", True):
            if now.weekday() >= 5:  # 土曜日=5, 日曜日=6
                return False

        # 時間チェック
        start_hour = business_hours_config.get("start_hour", 9)
        end_hour = business_hours_config.get("end_hour", 17)

        current_hour = now.hour
        return start_hour <= current_hour < end_hour

    async def _periodic_cleanup(self):
        """定期的なクリーンアップタスク"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1時間ごと
                self.throttle_manager.cleanup_old_entries()
                logger.debug("Periodic cleanup completed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    # 既存システム互換用のメソッド
    async def create_alert(
        self,
        alert_type: str,  # 文字列で受け取り、内部でEnumに変換
        level: str,
        title: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """既存システム互換用のアラート作成"""
        try:
            # 文字列をEnumに変換
            alert_level = AlertLevel(level.lower())

            # アラートタイプをマッピング
            type_mapping = {
                "price_change": AlertType.PRICE_CHANGE,
                "volume_spike": AlertType.VOLUME_SPIKE,
                "position_loss": AlertType.DAILY_LOSS,
                "system_error": AlertType.SYSTEM_ERROR,
                "strategy_performance": AlertType.STRATEGY_PERFORMANCE,
                "order_execution": AlertType.ORDER_EXECUTION,
                "balance_low": AlertType.BALANCE_LOW,
                "network_issue": AlertType.NETWORK_ISSUE,
                "var_breach": AlertType.VAR_BREACH,
                "drawdown": AlertType.DRAWDOWN,
                "volatility": AlertType.VOLATILITY,
                "concentration": AlertType.CONCENTRATION,
                "correlation": AlertType.CORRELATION,
                "daily_loss": AlertType.DAILY_LOSS,
            }

            alert_type_enum = type_mapping.get(alert_type, AlertType.SYSTEM_ERROR)

            # カテゴリを決定
            category_mapping = {
                AlertType.VAR_BREACH: AlertCategory.RISK,
                AlertType.DRAWDOWN: AlertCategory.RISK,
                AlertType.VOLATILITY: AlertCategory.RISK,
                AlertType.CONCENTRATION: AlertCategory.RISK,
                AlertType.CORRELATION: AlertCategory.RISK,
                AlertType.DAILY_LOSS: AlertCategory.RISK,
                AlertType.STRATEGY_PERFORMANCE: AlertCategory.PERFORMANCE,
                AlertType.LOW_SHARPE_RATIO: AlertCategory.PERFORMANCE,
                AlertType.HIGH_DRAWDOWN: AlertCategory.PERFORMANCE,
                AlertType.LOW_WIN_RATE: AlertCategory.PERFORMANCE,
                AlertType.ORDER_EXECUTION: AlertCategory.EXECUTION,
                AlertType.ORDER_FAILED: AlertCategory.EXECUTION,
                AlertType.SLIPPAGE_HIGH: AlertCategory.EXECUTION,
                AlertType.PRICE_CHANGE: AlertCategory.MARKET,
                AlertType.VOLUME_SPIKE: AlertCategory.MARKET,
                AlertType.MARKET_ANOMALY: AlertCategory.MARKET,
            }

            category = category_mapping.get(alert_type_enum, AlertCategory.SYSTEM)

            # UnifiedAlertを作成
            if category == AlertCategory.RISK:
                alert = create_risk_alert(
                    alert_type=alert_type_enum,
                    level=alert_level,
                    title=title,
                    message=message,
                    source_component="legacy_alert_manager",
                    symbol=symbol,
                    strategy_name=strategy_name,
                )
            elif category == AlertCategory.PERFORMANCE:
                alert = create_performance_alert(
                    alert_type=alert_type_enum,
                    level=alert_level,
                    title=title,
                    message=message,
                    strategy_name=strategy_name or "unknown",
                    metrics=data or {},
                )
            else:
                alert = create_system_alert(
                    alert_type=alert_type_enum,
                    level=alert_level,
                    title=title,
                    message=message,
                    source_component="legacy_alert_manager",
                    error_details=data,
                )

            # 追加データがある場合は設定
            if data and alert.metadata:
                alert.metadata.additional_data.update(data)

            return await self.send_alert(alert)

        except Exception as e:
            logger.error(f"Error creating legacy alert: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = dict(self.stats)
        stats["last_alert"] = self.stats["last_alert"].isoformat() if self.stats["last_alert"] else None
        stats["config_last_loaded"] = (
            self.config_manager.last_loaded.isoformat() if self.config_manager.last_loaded else None
        )
        stats["system_enabled"] = self.config_manager.is_enabled()
        return stats

    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            health = {
                "healthy": True,
                "components": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Redis接続チェック
            try:
                redis_manager = await get_redis_manager()
                redis_healthy = await redis_manager.health_check()
                health["components"]["redis"] = {
                    "healthy": redis_healthy,
                    "message": "OK" if redis_healthy else "Connection failed",
                }
            except Exception as e:
                health["components"]["redis"] = {"healthy": False, "message": str(e)}
                health["healthy"] = False

            # メッセージブローカーチェック
            if self.message_broker:
                broker_stats = self.message_broker.get_stats()
                health["components"]["message_broker"] = {
                    "healthy": broker_stats.get("started", False),
                    "message": "OK" if broker_stats.get("started", False) else "Not started",
                }
                if not broker_stats.get("started", False):
                    health["healthy"] = False
            else:
                health["components"]["message_broker"] = {
                    "healthy": False,
                    "message": "Not initialized",
                }
                health["healthy"] = False

            # 設定ファイルチェック
            health["components"]["config"] = {
                "healthy": self.config_manager.is_enabled(),
                "message": f"Config loaded: {bool(self.config_manager.last_loaded)}",
            }

            return health

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# グローバルインスタンス
_alert_manager: Optional[IntegratedAlertManager] = None


async def get_alert_manager() -> IntegratedAlertManager:
    """グローバルアラートマネージャーを取得"""
    global _alert_manager

    if _alert_manager is None:
        _alert_manager = IntegratedAlertManager()
        await _alert_manager.initialize()

    return _alert_manager


# 便利関数（既存システム互換性用）
async def create_alert(
    alert_type: str,
    level: str,
    title: str,
    message: str,
    symbol: Optional[str] = None,
    strategy_name: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """既存システム互換用のアラート作成関数"""
    manager = await get_alert_manager()
    return await manager.create_alert(alert_type, level, title, message, symbol, strategy_name, data)
