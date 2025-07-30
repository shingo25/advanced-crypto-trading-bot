"""
通知チャネルベースクラス

すべての通知チャネルが実装する必要がある
抽象基底クラスとインターフェース
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ...models.alerts import UnifiedAlert

logger = logging.getLogger(__name__)


class NotificationStatus(Enum):
    """通知ステータス"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class NotificationResult:
    """通知結果"""

    status: NotificationStatus
    message: str
    channel_name: str
    alert_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_data: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    retry_count: int = 0
    execution_time_ms: Optional[float] = None

    @property
    def is_success(self) -> bool:
        """成功かどうか"""
        return self.status == NotificationStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """失敗かどうか"""
        return self.status in [NotificationStatus.FAILED, NotificationStatus.TIMEOUT]

    @property
    def should_retry(self) -> bool:
        """リトライすべきかどうか"""
        return self.status == NotificationStatus.RETRY


class NotificationError(Exception):
    """通知エラー"""

    def __init__(
        self,
        message: str,
        channel_name: str,
        alert_id: str,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.channel_name = channel_name
        self.alert_id = alert_id
        self.error_code = error_code
        self.response_data = response_data


@dataclass
class NotificationConfig:
    """通知設定の基底クラス"""

    enabled: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    max_concurrent: int = 5
    rate_limit_per_minute: Optional[int] = None

    # テンプレート設定
    use_template: bool = True
    template_format: str = "default"  # "default", "compact", "detailed"

    # フィルター設定
    min_level: Optional[str] = None
    allowed_categories: Optional[List[str]] = None
    excluded_alert_types: Optional[List[str]] = None


class NotificationChannel(ABC):
    """通知チャネル抽象基底クラス"""

    def __init__(self, name: str, config: NotificationConfig):
        self.name = name
        self.config = config
        self._stats = {
            "total_sent": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_retries": 0,
            "last_sent": None,
            "average_response_time": 0.0,
        }
        self._rate_limiter = self._create_rate_limiter()
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        logger.info(f"Initialized notification channel: {name}")

    def _create_rate_limiter(self):
        """レート制限器を作成"""
        if self.config.rate_limit_per_minute:
            # 簡易レート制限器（実際の実装では redis-py-cluster などを使用）
            return {"requests": [], "limit": self.config.rate_limit_per_minute}
        return None

    async def _check_rate_limit(self) -> bool:
        """レート制限をチェック"""
        if not self._rate_limiter:
            return True

        now = datetime.now(timezone.utc)
        minute_ago = now.replace(second=0, microsecond=0).timestamp() - 60

        # 1分前より古いリクエストを除去
        self._rate_limiter["requests"] = [
            req_time for req_time in self._rate_limiter["requests"] if req_time > minute_ago
        ]

        # レート制限チェック
        if len(self._rate_limiter["requests"]) >= self._rate_limiter["limit"]:
            return False

        self._rate_limiter["requests"].append(now.timestamp())
        return True

    def _should_send_alert(self, alert: UnifiedAlert) -> bool:
        """アラートを送信すべきかフィルターチェック"""
        config = self.config

        # レベルフィルター
        if config.min_level:
            level_order = {"info": 1, "warning": 2, "error": 3, "critical": 4}
            if level_order.get(alert.level.value, 0) < level_order.get(config.min_level, 0):
                return False

        # カテゴリフィルター
        if config.allowed_categories:
            if alert.category.value not in config.allowed_categories:
                return False

        # アラートタイプ除外
        if config.excluded_alert_types:
            if alert.alert_type.value in config.excluded_alert_types:
                return False

        return True

    @abstractmethod
    async def _send_notification(self, alert: UnifiedAlert, formatted_message: str) -> NotificationResult:
        """実際の通知送信処理（サブクラスで実装）"""
        pass

    @abstractmethod
    def _format_message(self, alert: UnifiedAlert) -> str:
        """メッセージをフォーマット（サブクラスで実装）"""
        pass

    def _get_default_template(self, alert: UnifiedAlert) -> str:
        """デフォルトメッセージテンプレート"""
        template_format = self.config.template_format

        if template_format == "compact":
            return self._get_compact_template(alert)
        elif template_format == "detailed":
            return self._get_detailed_template(alert)
        else:
            return self._get_standard_template(alert)

    def _get_standard_template(self, alert: UnifiedAlert) -> str:
        """標準テンプレート"""
        level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}

        emoji = level_emoji.get(alert.level.value, "")

        lines = [
            f"{emoji} **{alert.title}**",
            f"**Level:** {alert.level.value.upper()}",
            f"**Category:** {alert.category.value}",
            f"**Message:** {alert.message}",
            f"**Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]

        if alert.metadata and alert.metadata.symbol:
            lines.append(f"**Symbol:** {alert.metadata.symbol}")

        if alert.metadata and alert.metadata.strategy_name:
            lines.append(f"**Strategy:** {alert.metadata.strategy_name}")

        if alert.recommended_actions:
            actions = ", ".join([action.description for action in alert.recommended_actions])
            lines.append(f"**Recommended Actions:** {actions}")

        return "\n".join(lines)

    def _get_compact_template(self, alert: UnifiedAlert) -> str:
        """コンパクトテンプレート"""
        level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}

        emoji = level_emoji.get(alert.level.value, "")
        symbol_str = f" [{alert.metadata.symbol}]" if alert.metadata and alert.metadata.symbol else ""

        return f"{emoji} {alert.level.value.upper()}{symbol_str}: {alert.message}"

    def _get_detailed_template(self, alert: UnifiedAlert) -> str:
        """詳細テンプレート"""
        template = self._get_standard_template(alert)

        # メタデータの詳細を追加
        if alert.metadata:
            metadata_lines = []

            if alert.metadata.current_value is not None:
                metadata_lines.append(f"**Current Value:** {alert.metadata.current_value}")

            if alert.metadata.threshold_value is not None:
                metadata_lines.append(f"**Threshold:** {alert.metadata.threshold_value}")

            if alert.metadata.additional_data:
                for key, value in alert.metadata.additional_data.items():
                    metadata_lines.append(f"**{key.title()}:** {value}")

            if metadata_lines:
                template += "\n\n**Additional Details:**\n" + "\n".join(metadata_lines)

        # アラートIDとハッシュを追加
        template += f"\n\n**Alert ID:** `{alert.id}`"
        if alert.content_hash:
            template += f"\n**Hash:** `{alert.content_hash[:8]}...`"

        return template

    async def send_alert(self, alert: UnifiedAlert) -> NotificationResult:
        """アラートを送信"""
        start_time = datetime.now(timezone.utc)

        try:
            # チャネルが無効な場合
            if not self.config.enabled:
                return NotificationResult(
                    status=NotificationStatus.CANCELLED,
                    message="Channel is disabled",
                    channel_name=self.name,
                    alert_id=alert.id,
                )

            # フィルターチェック
            if not self._should_send_alert(alert):
                return NotificationResult(
                    status=NotificationStatus.CANCELLED,
                    message="Alert filtered out",
                    channel_name=self.name,
                    alert_id=alert.id,
                )

            # レート制限チェック
            if not await self._check_rate_limit():
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    message="Rate limit exceeded",
                    channel_name=self.name,
                    alert_id=alert.id,
                )

            # 同時実行制限
            async with self._semaphore:
                # メッセージフォーマット
                formatted_message = self._format_message(alert)

                # リトライロジック
                last_result = None
                for attempt in range(self.config.retry_attempts + 1):
                    try:
                        # 通知送信
                        result = await asyncio.wait_for(
                            self._send_notification(alert, formatted_message),
                            timeout=self.config.timeout_seconds,
                        )

                        result.retry_count = attempt

                        # 成功時の統計更新
                        if result.is_success:
                            self._update_stats(True, start_time)
                            return result

                        # リトライが必要な場合
                        if result.should_retry and attempt < self.config.retry_attempts:
                            await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                            last_result = result
                            continue

                        # 失敗時の統計更新
                        self._update_stats(False, start_time)
                        return result

                    except asyncio.TimeoutError:
                        result = NotificationResult(
                            status=NotificationStatus.TIMEOUT,
                            message=f"Timeout after {self.config.timeout_seconds}s",
                            channel_name=self.name,
                            alert_id=alert.id,
                            retry_count=attempt,
                        )

                        if attempt < self.config.retry_attempts:
                            await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                            last_result = result
                            continue

                        self._update_stats(False, start_time)
                        return result

                    except Exception as e:
                        result = NotificationResult(
                            status=NotificationStatus.FAILED,
                            message=f"Unexpected error: {str(e)}",
                            channel_name=self.name,
                            alert_id=alert.id,
                            error_details=str(e),
                            retry_count=attempt,
                        )

                        if attempt < self.config.retry_attempts:
                            await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                            last_result = result
                            continue

                        self._update_stats(False, start_time)
                        return result

                # すべてのリトライが失敗した場合
                self._update_stats(False, start_time)
                return last_result or NotificationResult(
                    status=NotificationStatus.FAILED,
                    message="All retry attempts failed",
                    channel_name=self.name,
                    alert_id=alert.id,
                )

        except Exception as e:
            logger.error(f"Unexpected error in {self.name} channel: {e}")
            self._update_stats(False, start_time)
            return NotificationResult(
                status=NotificationStatus.FAILED,
                message=f"Channel error: {str(e)}",
                channel_name=self.name,
                alert_id=alert.id,
                error_details=str(e),
            )

    def _update_stats(self, success: bool, start_time: datetime):
        """統計を更新"""
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds() * 1000

        self._stats["total_sent"] += 1

        if success:
            self._stats["total_success"] += 1
        else:
            self._stats["total_failed"] += 1

        self._stats["last_sent"] = end_time

        # 移動平均で応答時間を更新
        if self._stats["average_response_time"] == 0:
            self._stats["average_response_time"] = execution_time
        else:
            self._stats["average_response_time"] = self._stats["average_response_time"] * 0.9 + execution_time * 0.1

    async def send_bulk_alerts(self, alerts: List[UnifiedAlert]) -> List[NotificationResult]:
        """複数のアラートを一括送信"""
        tasks = [self.send_alert(alert) for alert in alerts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外を結果に変換
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    NotificationResult(
                        status=NotificationStatus.FAILED,
                        message=f"Bulk send error: {str(result)}",
                        channel_name=self.name,
                        alert_id=alerts[i].id if i < len(alerts) else "unknown",
                        error_details=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = dict(self._stats)
        stats["success_rate"] = self._stats["total_success"] / max(self._stats["total_sent"], 1)
        stats["last_sent"] = self._stats["last_sent"].isoformat() if self._stats["last_sent"] else None
        return stats

    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            # サブクラスでオーバーライド可能
            result = await self._perform_health_check()
            return {
                "channel": self.name,
                "healthy": result.get("healthy", True),
                "message": result.get("message", "OK"),
                "details": result.get("details", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "channel": self.name,
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _perform_health_check(self) -> Dict[str, Any]:
        """ヘルスチェック実装（サブクラスでオーバーライド）"""
        return {"healthy": True, "message": "Base health check OK"}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.config.enabled})"

    def __repr__(self) -> str:
        return self.__str__()
