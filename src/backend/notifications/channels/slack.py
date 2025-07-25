"""
Slack通知チャネル

Slack Webhook APIを使用したアラート通知
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

from ...models.alerts import AlertLevel, UnifiedAlert
from .base import (
    NotificationChannel,
    NotificationConfig,
    NotificationResult,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig(NotificationConfig):
    """Slack設定"""

    webhook_url: str = ""
    channel: str = "#alerts"
    username: str = "CryptoBot"
    icon_emoji: str = ":warning:"
    icon_url: Optional[str] = None
    link_names: bool = True
    unfurl_links: bool = False
    unfurl_media: bool = False

    # Slack固有設定
    use_threads: bool = False
    thread_broadcast: bool = False
    mention_users: Optional[list] = None  # ["@here", "@channel", "@user"]
    color_coding: bool = True

    # メッセージ制限
    max_message_length: int = 4000
    truncate_long_messages: bool = True

    # 添付ファイル設定
    use_attachments: bool = True
    include_fields: bool = True
    include_actions: bool = False


class SlackChannel(NotificationChannel):
    """Slack通知チャネル"""

    def __init__(self, config: SlackConfig):
        super().__init__("slack", config)
        self.slack_config = config

        if not config.webhook_url:
            raise ValueError("Slack webhook URL is required")

        # 色設定
        self.level_colors = {
            AlertLevel.INFO: "#36a64f",  # 緑
            AlertLevel.WARNING: "#ff9900",  # オレンジ
            AlertLevel.ERROR: "#ff0000",  # 赤
            AlertLevel.CRITICAL: "#800080",  # 紫
        }

        # 絵文字設定
        self.level_emojis = {
            AlertLevel.INFO: ":information_source:",
            AlertLevel.WARNING: ":warning:",
            AlertLevel.ERROR: ":x:",
            AlertLevel.CRITICAL: ":rotating_light:",
        }

    def _format_message(self, alert: UnifiedAlert) -> str:
        """Slack用にメッセージをフォーマット"""
        if self.slack_config.use_template:
            return self._get_slack_template(alert)
        else:
            return self._get_default_template(alert)

    def _get_slack_template(self, alert: UnifiedAlert) -> str:
        """Slack専用テンプレート"""
        template_format = self.config.template_format

        if template_format == "compact":
            return self._get_slack_compact_template(alert)
        elif template_format == "detailed":
            return self._get_slack_detailed_template(alert)
        else:
            return self._get_slack_standard_template(alert)

    def _get_slack_compact_template(self, alert: UnifiedAlert) -> str:
        """Slackコンパクトテンプレート"""
        emoji = self.level_emojis.get(alert.level, ":warning:")
        symbol_str = f" [{alert.metadata.symbol}]" if alert.metadata and alert.metadata.symbol else ""

        message = f"{emoji} *{alert.level.value.upper()}*{symbol_str}: {alert.message}"

        # メンション追加
        if self.slack_config.mention_users and alert.level in [
            AlertLevel.ERROR,
            AlertLevel.CRITICAL,
        ]:
            mentions = " ".join(self.slack_config.mention_users)
            message = f"{mentions}\n{message}"

        return message

    def _get_slack_standard_template(self, alert: UnifiedAlert) -> str:
        """Slack標準テンプレート"""
        emoji = self.level_emojis.get(alert.level, ":warning:")

        lines = [
            f"{emoji} *{alert.title}*",
            f"*Level:* {alert.level.value.upper()}",
            f"*Category:* {alert.category.value}",
            f"*Message:* {alert.message}",
            f"*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]

        if alert.metadata and alert.metadata.symbol:
            lines.append(f"*Symbol:* `{alert.metadata.symbol}`")

        if alert.metadata and alert.metadata.strategy_name:
            lines.append(f"*Strategy:* `{alert.metadata.strategy_name}`")

        if alert.recommended_actions:
            actions = ", ".join([action.description for action in alert.recommended_actions])
            lines.append(f"*Actions:* {actions}")

        message = "\n".join(lines)

        # メンション追加
        if self.slack_config.mention_users and alert.level in [
            AlertLevel.ERROR,
            AlertLevel.CRITICAL,
        ]:
            mentions = " ".join(self.slack_config.mention_users)
            message = f"{mentions}\n{message}"

        return message

    def _get_slack_detailed_template(self, alert: UnifiedAlert) -> str:
        """Slack詳細テンプレート"""
        # 標準テンプレートから開始
        message = self._get_slack_standard_template(alert)

        # メタデータの詳細を追加
        if alert.metadata:
            details = []

            if alert.metadata.current_value is not None:
                details.append(f"*Current:* {alert.metadata.current_value}")

            if alert.metadata.threshold_value is not None:
                details.append(f"*Threshold:* {alert.metadata.threshold_value}")

            if alert.metadata.additional_data:
                for key, value in alert.metadata.additional_data.items():
                    details.append(f"*{key.title()}:* {value}")

            if details:
                message += "\n\n*Details:*\n" + "\n".join(details)

        # Alert ID追加
        message += f"\n\n*ID:* `{alert.id}`"

        return message

    def _create_slack_payload(self, alert: UnifiedAlert, formatted_message: str) -> Dict[str, Any]:
        """Slack送信用ペイロードを作成"""
        config = self.slack_config

        # 基本ペイロード
        payload = {
            "channel": config.channel,
            "username": config.username,
            "link_names": config.link_names,
            "unfurl_links": config.unfurl_links,
            "unfurl_media": config.unfurl_media,
        }

        # アイコン設定
        if config.icon_url:
            payload["icon_url"] = config.icon_url
        else:
            payload["icon_emoji"] = config.icon_emoji

        # メッセージ長制限
        if len(formatted_message) > config.max_message_length:
            if config.truncate_long_messages:
                formatted_message = formatted_message[: config.max_message_length - 100] + "\n\n... (truncated)"
            else:
                # 長すぎる場合は添付ファイルに移動
                payload[
                    "text"
                ] = f"{self.level_emojis.get(alert.level, ':warning:')} Alert message too long, see attachment"
                config.use_attachments = True

        if config.use_attachments:
            # 添付ファイル形式
            attachment = self._create_attachment(alert, formatted_message)
            payload["attachments"] = [attachment]
        else:
            # テキストのみ
            payload["text"] = formatted_message

        return payload

    def _create_attachment(self, alert: UnifiedAlert, message: str) -> Dict[str, Any]:
        """Slack添付ファイルを作成"""
        config = self.slack_config

        attachment = {
            "color": self.level_colors.get(alert.level, "#cccccc") if config.color_coding else None,
            "title": alert.title,
            "text": message,
            "ts": int(alert.timestamp.timestamp()),
            "footer": "CryptoBot Alert System",
            "mrkdwn_in": ["text", "fields"],
        }

        # フィールド追加
        if config.include_fields:
            fields = []

            fields.append({"title": "Level", "value": alert.level.value.upper(), "short": True})

            fields.append({"title": "Category", "value": alert.category.value, "short": True})

            if alert.metadata and alert.metadata.symbol:
                fields.append({"title": "Symbol", "value": alert.metadata.symbol, "short": True})

            if alert.metadata and alert.metadata.strategy_name:
                fields.append(
                    {
                        "title": "Strategy",
                        "value": alert.metadata.strategy_name,
                        "short": True,
                    }
                )

            if alert.metadata and alert.metadata.current_value is not None:
                fields.append(
                    {
                        "title": "Current Value",
                        "value": str(alert.metadata.current_value),
                        "short": True,
                    }
                )

            if alert.metadata and alert.metadata.threshold_value is not None:
                fields.append(
                    {
                        "title": "Threshold",
                        "value": str(alert.metadata.threshold_value),
                        "short": True,
                    }
                )

            attachment["fields"] = fields

        # アクション追加（将来の拡張用）
        if config.include_actions:
            attachment["actions"] = [
                {
                    "type": "button",
                    "text": "Acknowledge",
                    "value": f"ack:{alert.id}",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": "Resolve",
                    "value": f"resolve:{alert.id}",
                    "style": "danger",
                },
            ]

        return attachment

    async def _send_notification(self, alert: UnifiedAlert, formatted_message: str) -> NotificationResult:
        """Slack通知を送信"""
        try:
            payload = self._create_slack_payload(alert, formatted_message)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_config.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        if response_text == "ok":
                            return NotificationResult(
                                status=NotificationStatus.SUCCESS,
                                message="Message sent successfully",
                                channel_name=self.name,
                                alert_id=alert.id,
                                response_data={"status_code": response.status},
                            )
                        else:
                            return NotificationResult(
                                status=NotificationStatus.FAILED,
                                message=f"Slack returned: {response_text}",
                                channel_name=self.name,
                                alert_id=alert.id,
                                response_data={
                                    "status_code": response.status,
                                    "response": response_text,
                                },
                            )
                    else:
                        # リトライ可能なエラー
                        if response.status in [429, 500, 502, 503, 504]:
                            return NotificationResult(
                                status=NotificationStatus.RETRY,
                                message=f"HTTP {response.status}: {response_text}",
                                channel_name=self.name,
                                alert_id=alert.id,
                                response_data={
                                    "status_code": response.status,
                                    "response": response_text,
                                },
                            )
                        else:
                            return NotificationResult(
                                status=NotificationStatus.FAILED,
                                message=f"HTTP {response.status}: {response_text}",
                                channel_name=self.name,
                                alert_id=alert.id,
                                response_data={
                                    "status_code": response.status,
                                    "response": response_text,
                                },
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

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Slackヘルスチェック"""
        try:
            # 簡単なテストメッセージ
            test_payload = {
                "channel": self.slack_config.channel,
                "username": self.slack_config.username,
                "text": "Health check test",
                "icon_emoji": ":white_check_mark:",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_config.webhook_url,
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        if response_text == "ok":
                            return {
                                "healthy": True,
                                "message": "Webhook is accessible",
                                "details": {
                                    "status_code": response.status,
                                    "channel": self.slack_config.channel,
                                },
                            }
                        else:
                            return {
                                "healthy": False,
                                "message": f"Webhook error: {response_text}",
                                "details": {"status_code": response.status},
                            }
                    else:
                        return {
                            "healthy": False,
                            "message": f"HTTP error: {response.status}",
                            "details": {"status_code": response.status},
                        }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "details": {"error": str(e)},
            }

    def get_config_info(self) -> Dict[str, Any]:
        """設定情報を取得（機密情報を除く）"""
        return {
            "channel": self.slack_config.channel,
            "username": self.slack_config.username,
            "use_attachments": self.slack_config.use_attachments,
            "color_coding": self.slack_config.color_coding,
            "mention_users": self.slack_config.mention_users,
            "template_format": self.slack_config.template_format,
            "enabled": self.slack_config.enabled,
            "webhook_configured": bool(self.slack_config.webhook_url),
        }
