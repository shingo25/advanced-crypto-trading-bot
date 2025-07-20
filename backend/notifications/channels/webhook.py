"""
Webhook通知チャネル

汎用的なWebhook APIを使用したアラート通知
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import aiohttp

from .base import (
    NotificationChannel,
    NotificationConfig,
    NotificationResult,
    NotificationStatus,
)
from ...models.alerts import UnifiedAlert

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig(NotificationConfig):
    """Webhook設定"""

    url: str = ""
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)

    # 認証設定
    auth_type: Optional[str] = None  # "bearer", "basic", "apikey", "custom"
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_header_name: Optional[str] = None

    # ペイロード設定
    payload_format: str = "json"  # "json", "form", "custom"
    custom_payload_template: Optional[str] = None
    include_metadata: bool = True
    include_alert_id: bool = True

    # 証明書設定
    verify_ssl: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    # レスポンス設定
    success_status_codes: List[int] = field(
        default_factory=lambda: [200, 201, 202, 204]
    )
    retry_status_codes: List[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )

    # カスタムフィールド
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class WebhookChannel(NotificationChannel):
    """Webhook通知チャネル"""

    def __init__(self, config: WebhookConfig):
        super().__init__("webhook", config)
        self.webhook_config = config

        if not config.url:
            raise ValueError("Webhook URL is required")

        # ヘッダーを準備
        self._prepare_headers()

    def _prepare_headers(self):
        """認証ヘッダーを準備"""
        config = self.webhook_config
        headers = dict(config.headers)

        # Content-Typeの設定
        if config.payload_format == "json":
            headers["Content-Type"] = "application/json"
        elif config.payload_format == "form":
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # 認証ヘッダーの設定
        if config.auth_type == "bearer" and config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
        elif (
            config.auth_type == "apikey"
            and config.auth_token
            and config.auth_header_name
        ):
            headers[config.auth_header_name] = config.auth_token
        elif (
            config.auth_type == "custom"
            and config.auth_header_name
            and config.auth_token
        ):
            headers[config.auth_header_name] = config.auth_token

        config.headers = headers

    def _format_message(self, alert: UnifiedAlert) -> str:
        """Webhook用にメッセージをフォーマット"""
        if self.webhook_config.custom_payload_template:
            return self._apply_custom_template(alert)
        else:
            return self._get_default_template(alert)

    def _apply_custom_template(self, alert: UnifiedAlert) -> str:
        """カスタムテンプレートを適用"""
        template = self.webhook_config.custom_payload_template

        # 基本的な変数置換
        replacements = {
            "{alert_id}": alert.id,
            "{title}": alert.title,
            "{message}": alert.message,
            "{level}": alert.level.value,
            "{category}": alert.category.value,
            "{alert_type}": alert.alert_type.value,
            "{timestamp}": alert.timestamp.isoformat(),
            "{symbol}": alert.metadata.symbol
            if alert.metadata and alert.metadata.symbol
            else "",
            "{strategy}": alert.metadata.strategy_name
            if alert.metadata and alert.metadata.strategy_name
            else "",
            "{current_value}": str(alert.metadata.current_value)
            if alert.metadata and alert.metadata.current_value is not None
            else "",
            "{threshold_value}": str(alert.metadata.threshold_value)
            if alert.metadata and alert.metadata.threshold_value is not None
            else "",
        }

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        return template

    def _create_webhook_payload(
        self, alert: UnifiedAlert, formatted_message: str
    ) -> Any:
        """Webhook送信用ペイロードを作成"""
        config = self.webhook_config

        if config.payload_format == "custom":
            # カスタムペイロード（文字列をそのまま使用）
            return formatted_message

        # 基本ペイロード構造
        payload = {
            "title": alert.title,
            "message": alert.message,
            "level": alert.level.value,
            "category": alert.category.value,
            "alert_type": alert.alert_type.value,
            "timestamp": alert.timestamp.isoformat(),
        }

        # Alert ID を含める
        if config.include_alert_id:
            payload["alert_id"] = alert.id
            payload["content_hash"] = alert.content_hash

        # メタデータを含める
        if config.include_metadata and alert.metadata:
            metadata = {}

            if alert.metadata.symbol:
                metadata["symbol"] = alert.metadata.symbol

            if alert.metadata.strategy_name:
                metadata["strategy_name"] = alert.metadata.strategy_name

            if alert.metadata.position_id:
                metadata["position_id"] = alert.metadata.position_id

            if alert.metadata.order_id:
                metadata["order_id"] = alert.metadata.order_id

            if alert.metadata.current_value is not None:
                metadata["current_value"] = alert.metadata.current_value

            if alert.metadata.threshold_value is not None:
                metadata["threshold_value"] = alert.metadata.threshold_value

            if alert.metadata.change_percent is not None:
                metadata["change_percent"] = alert.metadata.change_percent

            if alert.metadata.additional_data:
                metadata["additional_data"] = alert.metadata.additional_data

            if metadata:
                payload["metadata"] = metadata

        # 推奨アクションを含める
        if alert.recommended_actions:
            payload["recommended_actions"] = [
                {
                    "action_type": action.action_type,
                    "description": action.description,
                    "urgency": action.urgency,
                    "automated": action.automated,
                    "parameters": action.parameters,
                }
                for action in alert.recommended_actions
            ]

        # 処理状況を含める
        payload["status"] = {
            "acknowledged": alert.acknowledged,
            "acknowledged_at": alert.acknowledged_at.isoformat()
            if alert.acknowledged_at
            else None,
            "acknowledged_by": alert.acknowledged_by,
            "resolved": alert.resolved,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }

        # カスタムフィールドを追加
        if config.custom_fields:
            payload.update(config.custom_fields)

        return payload

    async def _send_notification(
        self, alert: UnifiedAlert, formatted_message: str
    ) -> NotificationResult:
        """Webhook通知を送信"""
        try:
            config = self.webhook_config
            payload = self._create_webhook_payload(alert, formatted_message)

            # SSL設定
            ssl_context = None
            if not config.verify_ssl:
                ssl_context = False
            elif config.ssl_cert_path and config.ssl_key_path:
                import ssl

                ssl_context = ssl.create_default_context()
                ssl_context.load_cert_chain(config.ssl_cert_path, config.ssl_key_path)

            # Basic認証設定
            auth = None
            if (
                config.auth_type == "basic"
                and config.auth_username
                and config.auth_password
            ):
                auth = aiohttp.BasicAuth(config.auth_username, config.auth_password)

            # リクエストデータの準備
            if config.payload_format == "json":
                request_data = {"json": payload}
            elif config.payload_format == "form":
                # フォームデータに変換
                form_data = (
                    self._flatten_dict(payload)
                    if isinstance(payload, dict)
                    else {"data": str(payload)}
                )
                request_data = {"data": form_data}
            else:
                # カスタム形式
                request_data = {"data": payload}

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=config.method,
                    url=config.url,
                    headers=config.headers,
                    auth=auth,
                    ssl=ssl_context,
                    **request_data,
                ) as response:
                    response_text = await response.text()
                    response_data = {
                        "status_code": response.status,
                        "response": response_text[:500],  # レスポンスを制限
                        "headers": dict(response.headers),
                    }

                    if response.status in config.success_status_codes:
                        return NotificationResult(
                            status=NotificationStatus.SUCCESS,
                            message="Webhook notification sent successfully",
                            channel_name=self.name,
                            alert_id=alert.id,
                            response_data=response_data,
                        )
                    elif response.status in config.retry_status_codes:
                        return NotificationResult(
                            status=NotificationStatus.RETRY,
                            message=f"HTTP {response.status}: {response_text}",
                            channel_name=self.name,
                            alert_id=alert.id,
                            response_data=response_data,
                        )
                    else:
                        return NotificationResult(
                            status=NotificationStatus.FAILED,
                            message=f"HTTP {response.status}: {response_text}",
                            channel_name=self.name,
                            alert_id=alert.id,
                            response_data=response_data,
                        )

        except aiohttp.ClientError as e:
            return NotificationResult(
                status=NotificationStatus.RETRY,
                message=f"Network error: {str(e)}",
                channel_name=self.name,
                alert_id=alert.id,
                error_details=str(e),
            )

        except Exception as e:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                message=f"Unexpected error: {str(e)}",
                channel_name=self.name,
                alert_id=alert.id,
                error_details=str(e),
            )

    def _flatten_dict(
        self, d: Dict[str, Any], parent_key: str = "", sep: str = "_"
    ) -> Dict[str, str]:
        """辞書をフラット化（フォームデータ用）"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(
                            self._flatten_dict(
                                item, f"{new_key}{sep}{i}", sep=sep
                            ).items()
                        )
                    else:
                        items.append((f"{new_key}{sep}{i}", str(item)))
            else:
                items.append((new_key, str(v)))
        return dict(items)

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Webhookヘルスチェック"""
        try:
            config = self.webhook_config

            # 最小限のテストペイロード
            test_payload = {
                "test": True,
                "message": "Health check test",
                "timestamp": "2024-01-01T00:00:00Z",
                "source": "crypto-bot-health-check",
            }

            # SSL設定
            ssl_context = None
            if not config.verify_ssl:
                ssl_context = False

            # Basic認証設定
            auth = None
            if (
                config.auth_type == "basic"
                and config.auth_username
                and config.auth_password
            ):
                auth = aiohttp.BasicAuth(config.auth_username, config.auth_password)

            # リクエストデータの準備
            if config.payload_format == "json":
                request_data = {"json": test_payload}
            elif config.payload_format == "form":
                request_data = {"data": self._flatten_dict(test_payload)}
            else:
                request_data = {"data": test_payload}

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=config.method,
                    url=config.url,
                    headers=config.headers,
                    auth=auth,
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(
                        total=10
                    ),  # ヘルスチェック用短いタイムアウト
                    **request_data,
                ) as response:
                    response_text = await response.text()

                    if response.status in config.success_status_codes:
                        return {
                            "healthy": True,
                            "message": "Webhook endpoint is accessible",
                            "details": {
                                "status_code": response.status,
                                "url": config.url,
                                "method": config.method,
                                "response_length": len(response_text),
                            },
                        }
                    else:
                        return {
                            "healthy": False,
                            "message": f"Webhook returned HTTP {response.status}",
                            "details": {
                                "status_code": response.status,
                                "response": response_text[:200],
                            },
                        }

        except aiohttp.ClientTimeout:
            return {
                "healthy": False,
                "message": "Webhook endpoint timeout",
                "details": {"error": "timeout"},
            }

        except aiohttp.ClientError as e:
            return {
                "healthy": False,
                "message": f"Network error: {str(e)}",
                "details": {"error": str(e)},
            }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "details": {"error": str(e)},
            }

    async def test_notification(
        self, test_message: str = "Test notification"
    ) -> NotificationResult:
        """テスト通知を送信"""
        from ...models.alerts import create_system_alert, AlertType, AlertLevel

        test_alert = create_system_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            level=AlertLevel.INFO,
            title="Test Notification",
            message=test_message,
            source_component="webhook_test",
        )

        return await self.send_alert(test_alert)

    def get_config_info(self) -> Dict[str, Any]:
        """設定情報を取得（機密情報を除く）"""
        config = self.webhook_config

        # 機密情報をマスク
        masked_headers = {}
        for key, value in config.headers.items():
            if any(
                sensitive in key.lower()
                for sensitive in ["auth", "token", "key", "secret", "password"]
            ):
                masked_headers[key] = "***masked***"
            else:
                masked_headers[key] = value

        return {
            "url": config.url,
            "method": config.method,
            "headers": masked_headers,
            "payload_format": config.payload_format,
            "auth_type": config.auth_type,
            "verify_ssl": config.verify_ssl,
            "success_status_codes": config.success_status_codes,
            "retry_status_codes": config.retry_status_codes,
            "include_metadata": config.include_metadata,
            "include_alert_id": config.include_alert_id,
            "custom_fields": config.custom_fields,
            "enabled": config.enabled,
            "timeout_seconds": config.timeout_seconds,
            "retry_attempts": config.retry_attempts,
        }
