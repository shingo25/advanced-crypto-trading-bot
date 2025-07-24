"""
メール通知チャネル

SMTP経由でのメール通知機能
"""

import asyncio
import logging
import smtplib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from ...models.alerts import AlertLevel, UnifiedAlert
from .base import (
    NotificationChannel,
    NotificationConfig,
    NotificationResult,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig(NotificationConfig):
    """メール設定"""

    smtp_server: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    to_emails: List[str] = field(default_factory=list)

    # セキュリティ設定
    use_tls: bool = True
    use_ssl: bool = False

    # メール設定
    subject_prefix: str = "[CryptoBot Alert]"
    html_format: bool = True
    include_attachments: bool = False

    # 送信制限
    max_recipients: int = 50
    batch_size: int = 10
    batch_delay_seconds: float = 1.0

    # テンプレート設定
    email_template: str = "standard"  # "standard", "html", "plain"

    # 優先度別設定
    critical_recipients: Optional[List[str]] = None
    high_priority_recipients: Optional[List[str]] = None


class EmailChannel(NotificationChannel):
    """メール通知チャネル"""

    def __init__(self, config: EmailConfig):
        super().__init__("email", config)
        self.email_config = config

        if not config.smtp_server:
            raise ValueError("SMTP server is required")

        if not config.to_emails:
            raise ValueError("At least one recipient email is required")

        # スレッドプール（SMTP接続は同期的なため）
        self.thread_pool = ThreadPoolExecutor(max_workers=3)

    def _format_message(self, alert: UnifiedAlert) -> str:
        """メール用にメッセージをフォーマット"""
        if self.email_config.html_format:
            return self._get_html_template(alert)
        else:
            return self._get_plain_template(alert)

    def _get_plain_template(self, alert: UnifiedAlert) -> str:
        """プレーンテキストテンプレート"""
        template_format = self.config.template_format

        if template_format == "compact":
            return self._get_plain_compact_template(alert)
        elif template_format == "detailed":
            return self._get_plain_detailed_template(alert)
        else:
            return self._get_plain_standard_template(alert)

    def _get_plain_compact_template(self, alert: UnifiedAlert) -> str:
        """プレーンテキストコンパクトテンプレート"""
        symbol_str = f" [{alert.metadata.symbol}]" if alert.metadata and alert.metadata.symbol else ""
        return f"{alert.level.value.upper()}{symbol_str}: {alert.message}"

    def _get_plain_standard_template(self, alert: UnifiedAlert) -> str:
        """プレーンテキスト標準テンプレート"""
        lines = [
            "CRYPTO BOT ALERT",
            f"{'=' * 50}",
            "",
            f"Title: {alert.title}",
            f"Level: {alert.level.value.upper()}",
            f"Category: {alert.category.value}",
            f"Alert Type: {alert.alert_type.value}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "Message:",
            f"{alert.message}",
            "",
        ]

        if alert.metadata and alert.metadata.symbol:
            lines.append(f"Symbol: {alert.metadata.symbol}")

        if alert.metadata and alert.metadata.strategy_name:
            lines.append(f"Strategy: {alert.metadata.strategy_name}")

        if alert.metadata and alert.metadata.current_value is not None:
            lines.append(f"Current Value: {alert.metadata.current_value}")

        if alert.metadata and alert.metadata.threshold_value is not None:
            lines.append(f"Threshold: {alert.metadata.threshold_value}")

        if alert.recommended_actions:
            lines.append("")
            lines.append("Recommended Actions:")
            for action in alert.recommended_actions:
                lines.append(f"- {action.description}")

        lines.extend(
            [
                "",
                f"Alert ID: {alert.id}",
                "",
                "This is an automated message from CryptoBot Alert System.",
            ]
        )

        return "\n".join(lines)

    def _get_plain_detailed_template(self, alert: UnifiedAlert) -> str:
        """プレーンテキスト詳細テンプレート"""
        # 標準テンプレートから開始
        message = self._get_plain_standard_template(alert)

        # 詳細情報を追加
        if alert.metadata and alert.metadata.additional_data:
            message += "\n\nAdditional Details:\n"
            for key, value in alert.metadata.additional_data.items():
                message += f"{key.title()}: {value}\n"

        # 処理状況を追加
        message += "\nProcessing Status:\n"
        message += f"Acknowledged: {'Yes' if alert.acknowledged else 'No'}\n"
        if alert.acknowledged_at:
            message += f"Acknowledged At: {alert.acknowledged_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        message += f"Resolved: {'Yes' if alert.resolved else 'No'}\n"
        if alert.resolved_at:
            message += f"Resolved At: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

        return message

    def _get_html_template(self, alert: UnifiedAlert) -> str:
        """HTMLテンプレート"""
        level_colors = {
            AlertLevel.INFO: "#007bff",  # 青
            AlertLevel.WARNING: "#ffc107",  # 黄色
            AlertLevel.ERROR: "#dc3545",  # 赤
            AlertLevel.CRITICAL: "#6f42c1",  # 紫
        }

        level_icons = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }

        color = level_colors.get(alert.level, "#6c757d")
        icon = level_icons.get(alert.level, "📢")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CryptoBot Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 20px; }}
                .alert-info {{ background-color: #f8f9fa; border-left: 4px solid {color}; padding: 15px; margin: 15px 0; }}
                .metadata {{ background-color: #e9ecef; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .actions {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d; }}
                .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold; }}
                .level-{alert.level.value} {{ background-color: {color}; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} CryptoBot Alert</h1>
                    <span class="badge level-{alert.level.value}">{alert.level.value.upper()}</span>
                </div>

                <div class="content">
                    <div class="alert-info">
                        <h2 style="margin-top: 0; color: {color};">{alert.title}</h2>
                        <p><strong>Message:</strong> {alert.message}</p>
                        <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    </div>

                    <table>
                        <tr><th>Property</th><th>Value</th></tr>
                        <tr><td>Category</td><td>{alert.category.value}</td></tr>
                        <tr><td>Alert Type</td><td>{alert.alert_type.value}</td></tr>
                        <tr><td>Alert ID</td><td><code>{alert.id}</code></td></tr>
        """

        # メタデータを追加
        if alert.metadata:
            if alert.metadata.symbol:
                html += f"<tr><td>Symbol</td><td><strong>{alert.metadata.symbol}</strong></td></tr>"

            if alert.metadata.strategy_name:
                html += f"<tr><td>Strategy</td><td><strong>{alert.metadata.strategy_name}</strong></td></tr>"

            if alert.metadata.current_value is not None:
                html += f"<tr><td>Current Value</td><td>{alert.metadata.current_value}</td></tr>"

            if alert.metadata.threshold_value is not None:
                html += f"<tr><td>Threshold</td><td>{alert.metadata.threshold_value}</td></tr>"

        html += "</table>"

        # 推奨アクションを追加
        if alert.recommended_actions:
            html += '<div class="actions"><h3>Recommended Actions:</h3><ul>'
            for action in alert.recommended_actions:
                html += f"<li><strong>{action.action_type}:</strong> {action.description} <em>(Urgency: {action.urgency})</em></li>"
            html += "</ul></div>"

        # メタデータの詳細
        if alert.metadata and alert.metadata.additional_data:
            html += '<div class="metadata"><h3>Additional Details:</h3><table>'
            for key, value in alert.metadata.additional_data.items():
                html += f"<tr><td>{key.title()}</td><td>{value}</td></tr>"
            html += "</table></div>"

        html += """
                </div>

                <div class="footer">
                    <p>This is an automated message from CryptoBot Alert System.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _get_subject(self, alert: UnifiedAlert) -> str:
        """メール件名を生成"""
        prefix = self.email_config.subject_prefix
        level = alert.level.value.upper()
        symbol_str = f" [{alert.metadata.symbol}]" if alert.metadata and alert.metadata.symbol else ""

        return f"{prefix} {level}{symbol_str}: {alert.title}"

    def _get_recipients(self, alert: UnifiedAlert) -> List[str]:
        """受信者リストを決定"""
        config = self.email_config

        # 基本受信者
        recipients = list(config.to_emails)

        # レベル別の追加受信者
        if alert.level == AlertLevel.CRITICAL and config.critical_recipients:
            recipients.extend(config.critical_recipients)
        elif alert.level in [AlertLevel.ERROR, AlertLevel.WARNING] and config.high_priority_recipients:
            recipients.extend(config.high_priority_recipients)

        # 重複除去
        return list(set(recipients))

    def _create_email_message(self, alert: UnifiedAlert, formatted_message: str) -> MIMEMultipart:
        """メールメッセージを作成"""
        config = self.email_config

        msg = MIMEMultipart("alternative")
        msg["From"] = config.from_email
        msg["Subject"] = self._get_subject(alert)

        if config.html_format:
            # HTMLメッセージ
            html_part = MIMEText(formatted_message, "html", "utf-8")
            msg.attach(html_part)

            # プレーンテキスト版も追加
            plain_text = self._get_plain_standard_template(alert)
            text_part = MIMEText(plain_text, "plain", "utf-8")
            msg.attach(text_part)
        else:
            # プレーンテキストのみ
            text_part = MIMEText(formatted_message, "plain", "utf-8")
            msg.attach(text_part)

        return msg

    def _send_email_sync(
        self, alert: UnifiedAlert, formatted_message: str, recipients: List[str]
    ) -> NotificationResult:
        """同期的にメールを送信（スレッドプールで実行）"""
        config = self.email_config

        try:
            # メールメッセージを作成
            msg = self._create_email_message(alert, formatted_message)

            # SMTP接続
            if config.use_ssl:
                server = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port)
            else:
                server = smtplib.SMTP(config.smtp_server, config.smtp_port)
                if config.use_tls:
                    server.starttls()

            # 認証
            if config.username and config.password:
                server.login(config.username, config.password)

            # バッチ送信
            sent_count = 0
            failed_recipients = []

            for i in range(0, len(recipients), config.batch_size):
                batch = recipients[i : i + config.batch_size]

                try:
                    msg["To"] = ", ".join(batch)
                    server.send_message(msg, to_addrs=batch)
                    sent_count += len(batch)

                    # バッチ間の遅延
                    if i + config.batch_size < len(recipients):
                        import time

                        time.sleep(config.batch_delay_seconds)

                except Exception as e:
                    logger.error(f"Failed to send to batch {batch}: {e}")
                    failed_recipients.extend(batch)
                finally:
                    # To フィールドをクリア
                    del msg["To"]

            server.quit()

            if sent_count > 0:
                message = f"Email sent to {sent_count}/{len(recipients)} recipients"
                if failed_recipients:
                    message += f" (failed: {len(failed_recipients)})"

                return NotificationResult(
                    status=NotificationStatus.SUCCESS,
                    message=message,
                    channel_name=self.name,
                    alert_id=alert.id,
                    response_data={
                        "sent_count": sent_count,
                        "total_recipients": len(recipients),
                        "failed_recipients": failed_recipients,
                    },
                )
            else:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    message="Failed to send to any recipients",
                    channel_name=self.name,
                    alert_id=alert.id,
                    error_details=f"All recipients failed: {failed_recipients}",
                )

        except smtplib.SMTPAuthenticationError as e:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                message=f"SMTP authentication failed: {str(e)}",
                channel_name=self.name,
                alert_id=alert.id,
                error_details=str(e),
            )

        except smtplib.SMTPConnectError as e:
            return NotificationResult(
                status=NotificationStatus.RETRY,
                message=f"SMTP connection failed: {str(e)}",
                channel_name=self.name,
                alert_id=alert.id,
                error_details=str(e),
            )

        except smtplib.SMTPException as e:
            return NotificationResult(
                status=NotificationStatus.RETRY,
                message=f"SMTP error: {str(e)}",
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

    async def _send_notification(self, alert: UnifiedAlert, formatted_message: str) -> NotificationResult:
        """メール通知を送信"""
        recipients = self._get_recipients(alert)

        if len(recipients) > self.email_config.max_recipients:
            return NotificationResult(
                status=NotificationStatus.FAILED,
                message=f"Too many recipients: {len(recipients)} > {self.email_config.max_recipients}",
                channel_name=self.name,
                alert_id=alert.id,
            )

        # スレッドプールで同期的な送信処理を実行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.thread_pool,
            self._send_email_sync,
            alert,
            formatted_message,
            recipients,
        )

        return result

    async def _perform_health_check(self) -> Dict[str, Any]:
        """メールヘルスチェック"""
        try:
            config = self.email_config

            # SMTP接続テスト
            loop = asyncio.get_event_loop()

            def test_smtp_connection():
                try:
                    if config.use_ssl:
                        server = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port)
                    else:
                        server = smtplib.SMTP(config.smtp_server, config.smtp_port)
                        if config.use_tls:
                            server.starttls()

                    if config.username and config.password:
                        server.login(config.username, config.password)

                    server.quit()
                    return True, "Connection successful"

                except smtplib.SMTPAuthenticationError:
                    return False, "Authentication failed"
                except smtplib.SMTPConnectError as e:
                    return False, f"Connection failed: {str(e)}"
                except Exception as e:
                    return False, f"Error: {str(e)}"

            success, message = await loop.run_in_executor(self.thread_pool, test_smtp_connection)

            return {
                "healthy": success,
                "message": message,
                "details": {
                    "smtp_server": config.smtp_server,
                    "smtp_port": config.smtp_port,
                    "use_tls": config.use_tls,
                    "use_ssl": config.use_ssl,
                    "recipients_count": len(config.to_emails),
                },
            }

        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "details": {"error": str(e)},
            }

    def get_config_info(self) -> Dict[str, Any]:
        """設定情報を取得（機密情報を除く）"""
        config = self.email_config

        return {
            "smtp_server": config.smtp_server,
            "smtp_port": config.smtp_port,
            "from_email": config.from_email,
            "recipients_count": len(config.to_emails),
            "use_tls": config.use_tls,
            "use_ssl": config.use_ssl,
            "html_format": config.html_format,
            "subject_prefix": config.subject_prefix,
            "max_recipients": config.max_recipients,
            "batch_size": config.batch_size,
            "enabled": config.enabled,
            "timeout_seconds": config.timeout_seconds,
            "retry_attempts": config.retry_attempts,
            "username_configured": bool(config.username),
            "password_configured": bool(config.password),
        }

    def __del__(self):
        """デストラクタでスレッドプールを閉じる"""
        if hasattr(self, "thread_pool"):
            self.thread_pool.shutdown(wait=False)
