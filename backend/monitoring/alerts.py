"""
監視・アラートシステム
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """アラートレベル"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """アラートタイプ"""

    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"
    POSITION_LOSS = "position_loss"
    SYSTEM_ERROR = "system_error"
    STRATEGY_PERFORMANCE = "strategy_performance"
    ORDER_EXECUTION = "order_execution"
    BALANCE_LOW = "balance_low"
    NETWORK_ISSUE = "network_issue"


@dataclass
class Alert:
    """アラート"""

    id: str
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    symbol: Optional[str] = None
    strategy_name: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    def acknowledge(self):
        """アラートを確認済みにする"""
        self.acknowledged = True
        self.acknowledged_at = datetime.now(timezone.utc)


@dataclass
class AlertRule:
    """アラートルール"""

    id: str
    alert_type: AlertType
    level: AlertLevel
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown_seconds: int = 300  # 5分間のクールダウン
    last_triggered: Optional[datetime] = None

    def can_trigger(self) -> bool:
        """トリガー可能かチェック"""
        if not self.enabled:
            return False

        if self.last_triggered is None:
            return True

        time_since_last = (
            datetime.now(timezone.utc) - self.last_triggered
        ).total_seconds()
        return time_since_last >= self.cooldown_seconds

    def trigger(self):
        """ルールをトリガー"""
        self.last_triggered = datetime.now(timezone.utc)


class AlertManager:
    """アラートマネージャー"""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_counter = 0
        self.notification_channels = {}

        # 設定
        self.config = {
            "max_alerts": 1000,
            "alert_retention_days": 30,
            "enable_email": False,
            "enable_slack": False,
            "enable_telegram": False,
            "email_config": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": [],
            },
        }

        # デフォルトルールを設定
        self._setup_default_rules()

        logger.info("AlertManager initialized")

    def _setup_default_rules(self):
        """デフォルトのアラートルールを設定"""

        # 価格変動アラート
        self.add_alert_rule(
            AlertRule(
                id="price_change_5pct",
                alert_type=AlertType.PRICE_CHANGE,
                level=AlertLevel.WARNING,
                conditions={"threshold": 0.05, "timeframe": 300},  # 5分間で5%変動
                cooldown_seconds=600,
            )
        )

        # ポジション損失アラート
        self.add_alert_rule(
            AlertRule(
                id="position_loss_10pct",
                alert_type=AlertType.POSITION_LOSS,
                level=AlertLevel.ERROR,
                conditions={"threshold": -0.1},  # 10%の損失
                cooldown_seconds=300,
            )
        )

        # システムエラーアラート
        self.add_alert_rule(
            AlertRule(
                id="system_error",
                alert_type=AlertType.SYSTEM_ERROR,
                level=AlertLevel.CRITICAL,
                conditions={},
                cooldown_seconds=60,
            )
        )

        # 残高不足アラート
        self.add_alert_rule(
            AlertRule(
                id="balance_low",
                alert_type=AlertType.BALANCE_LOW,
                level=AlertLevel.WARNING,
                conditions={"threshold": 100.0},  # 100 USDT以下
                cooldown_seconds=1800,
            )
        )

    def add_alert_rule(self, rule: AlertRule):
        """アラートルールを追加"""
        self.alert_rules[rule.id] = rule
        logger.info(f"Alert rule added: {rule.id}")

    def remove_alert_rule(self, rule_id: str):
        """アラートルールを削除"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Alert rule removed: {rule_id}")

    def create_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        title: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        data: Dict[str, Any] = None,
    ) -> Alert:
        """アラートを作成"""

        # アラートIDを生成
        alert_id = f"alert_{self.alert_counter:06d}"
        self.alert_counter += 1

        # アラートを作成
        alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            symbol=symbol,
            strategy_name=strategy_name,
            data=data or {},
        )

        # アラートを保存
        self.alerts.append(alert)

        # 古いアラートを削除
        self._cleanup_old_alerts()

        # 通知を送信
        self._send_notifications(alert)

        logger.info(f"Alert created: {alert_id} - {title}")
        return alert

    def check_price_change(self, symbol: str, old_price: float, new_price: float):
        """価格変動をチェック"""
        rule = self.alert_rules.get("price_change_5pct")
        if not rule or not rule.can_trigger():
            return

        change_pct = abs(new_price - old_price) / old_price
        threshold = rule.conditions["threshold"]

        if change_pct >= threshold:
            self.create_alert(
                alert_type=AlertType.PRICE_CHANGE,
                level=AlertLevel.WARNING,
                title=f"Price Change Alert: {symbol}",
                message=f"{symbol} price changed by {change_pct:.2%} from {old_price:.2f} to {new_price:.2f}",
                symbol=symbol,
                data={
                    "old_price": old_price,
                    "new_price": new_price,
                    "change_pct": change_pct,
                },
            )
            rule.trigger()

    def check_position_loss(self, symbol: str, pnl: float, strategy_name: str = None):
        """ポジション損失をチェック"""
        rule = self.alert_rules.get("position_loss_10pct")
        if not rule or not rule.can_trigger():
            return

        threshold = rule.conditions["threshold"]

        if pnl <= threshold:
            self.create_alert(
                alert_type=AlertType.POSITION_LOSS,
                level=AlertLevel.ERROR,
                title=f"Position Loss Alert: {symbol}",
                message=f"{symbol} position showing {pnl:.2%} loss",
                symbol=symbol,
                strategy_name=strategy_name,
                data={"pnl": pnl, "threshold": threshold},
            )
            rule.trigger()

    def check_balance_low(self, balance: float, currency: str = "USDT"):
        """残高不足をチェック"""
        rule = self.alert_rules.get("balance_low")
        if not rule or not rule.can_trigger():
            return

        threshold = rule.conditions["threshold"]

        if balance <= threshold:
            self.create_alert(
                alert_type=AlertType.BALANCE_LOW,
                level=AlertLevel.WARNING,
                title=f"Low Balance Alert: {currency}",
                message=f"{currency} balance is low: {balance:.2f} (threshold: {threshold:.2f})",
                data={"balance": balance, "currency": currency, "threshold": threshold},
            )
            rule.trigger()

    def report_system_error(self, error_message: str, component: str = None):
        """システムエラーを報告"""
        rule = self.alert_rules.get("system_error")
        if not rule or not rule.can_trigger():
            return

        self.create_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            level=AlertLevel.CRITICAL,
            title="System Error",
            message=f"System error occurred: {error_message}",
            data={"error_message": error_message, "component": component},
        )
        rule.trigger()

    def report_order_execution_issue(
        self, order_id: str, symbol: str, error_message: str
    ):
        """注文実行の問題を報告"""
        self.create_alert(
            alert_type=AlertType.ORDER_EXECUTION,
            level=AlertLevel.ERROR,
            title=f"Order Execution Issue: {order_id}",
            message=f"Order {order_id} for {symbol} failed: {error_message}",
            symbol=symbol,
            data={"order_id": order_id, "error_message": error_message},
        )

    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[AlertType] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """アラートを取得"""

        filtered_alerts = self.alerts

        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]

        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]

        if acknowledged is not None:
            filtered_alerts = [
                a for a in filtered_alerts if a.acknowledged == acknowledged
            ]

        # 最新のアラートを返す
        return sorted(filtered_alerts, key=lambda x: x.created_at, reverse=True)[:limit]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """アラートを確認済みにする"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledge()
                logger.info(f"Alert acknowledged: {alert_id}")
                return True

        logger.warning(f"Alert not found: {alert_id}")
        return False

    def acknowledge_all_alerts(self):
        """すべてのアラートを確認済みにする"""
        count = 0
        for alert in self.alerts:
            if not alert.acknowledged:
                alert.acknowledge()
                count += 1

        logger.info(f"Acknowledged {count} alerts")

    def _cleanup_old_alerts(self):
        """古いアラートを削除"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=self.config["alert_retention_days"]
        )

        old_count = len(self.alerts)
        self.alerts = [alert for alert in self.alerts if alert.created_at > cutoff_date]

        # 最大数を超えた場合は古いものから削除
        if len(self.alerts) > self.config["max_alerts"]:
            self.alerts = sorted(self.alerts, key=lambda x: x.created_at, reverse=True)[
                : self.config["max_alerts"]
            ]

        removed_count = old_count - len(self.alerts)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old alerts")

    def _send_notifications(self, alert: Alert):
        """通知を送信"""
        try:
            # メール通知
            if self.config["enable_email"]:
                self._send_email_notification(alert)

            # Slack通知
            if self.config["enable_slack"]:
                self._send_slack_notification(alert)

            # Telegram通知
            if self.config["enable_telegram"]:
                self._send_telegram_notification(alert)

        except Exception as e:
            logger.error(f"Notification sending failed: {e}")

    def _send_email_notification(self, alert: Alert):
        """メール通知を送信"""
        try:
            email_config = self.config["email_config"]

            if not email_config["username"] or not email_config["to_emails"]:
                return

            # メッセージを作成
            msg = MIMEMultipart()
            msg["From"] = email_config["from_email"]
            msg["To"] = ", ".join(email_config["to_emails"])
            msg["Subject"] = f"[{alert.level.value.upper()}] {alert.title}"

            body = f"""
Alert Details:
- Type: {alert.alert_type.value}
- Level: {alert.level.value}
- Time: {alert.created_at}
- Symbol: {alert.symbol or "N/A"}
- Strategy: {alert.strategy_name or "N/A"}

Message:
{alert.message}

Data:
{json.dumps(alert.data, indent=2)}
            """

            msg.attach(MIMEText(body, "plain"))

            # SMTPサーバーに接続して送信
            server = smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            )
            server.starttls()
            server.login(email_config["username"], email_config["password"])
            server.send_message(msg)
            server.quit()

            logger.info(f"Email notification sent for alert: {alert.id}")

        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    def _send_slack_notification(self, alert: Alert):
        """Slack通知を送信"""
        # Slack webhook実装
        # 実際の実装では requests ライブラリを使用
        logger.info(f"Slack notification would be sent for alert: {alert.id}")

    def _send_telegram_notification(self, alert: Alert):
        """Telegram通知を送信"""
        # Telegram Bot API実装
        # 実際の実装では requests ライブラリを使用
        logger.info(f"Telegram notification would be sent for alert: {alert.id}")

    def get_alert_statistics(self) -> Dict[str, Any]:
        """アラート統計を取得"""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(days=1)
        last_7d = now - timedelta(days=7)

        recent_alerts = [a for a in self.alerts if a.created_at >= last_24h]
        weekly_alerts = [a for a in self.alerts if a.created_at >= last_7d]

        return {
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": len(
                [a for a in self.alerts if not a.acknowledged]
            ),
            "alerts_last_24h": len(recent_alerts),
            "alerts_last_7d": len(weekly_alerts),
            "alerts_by_level": {
                level.value: len([a for a in self.alerts if a.level == level])
                for level in AlertLevel
            },
            "alerts_by_type": {
                alert_type.value: len(
                    [a for a in self.alerts if a.alert_type == alert_type]
                )
                for alert_type in AlertType
            },
            "active_rules": len([r for r in self.alert_rules.values() if r.enabled]),
        }

    def export_alerts(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """アラートをエクスポート"""
        filtered_alerts = self.alerts

        if start_date:
            filtered_alerts = [a for a in filtered_alerts if a.created_at >= start_date]

        if end_date:
            filtered_alerts = [a for a in filtered_alerts if a.created_at <= end_date]

        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type.value,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "symbol": alert.symbol,
                "strategy_name": alert.strategy_name,
                "data": alert.data,
                "created_at": alert.created_at.isoformat(),
                "acknowledged": alert.acknowledged,
                "acknowledged_at": alert.acknowledged_at.isoformat()
                if alert.acknowledged_at
                else None,
            }
            for alert in sorted(
                filtered_alerts, key=lambda x: x.created_at, reverse=True
            )
        ]


class PerformanceMonitor:
    """パフォーマンス監視"""

    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.metrics = {
            "strategy_performance": {},
            "system_health": {},
            "trading_metrics": {},
        }
        self.thresholds = {
            "min_sharpe_ratio": 0.5,
            "max_drawdown": 0.15,
            "min_win_rate": 0.4,
            "max_cpu_usage": 80.0,
            "max_memory_usage": 80.0,
        }

        logger.info("PerformanceMonitor initialized")

    def update_strategy_performance(self, strategy_name: str, metrics: Dict[str, Any]):
        """戦略パフォーマンスを更新"""
        self.metrics["strategy_performance"][strategy_name] = {
            **metrics,
            "last_updated": datetime.now(timezone.utc),
        }

        # パフォーマンスアラートをチェック
        self._check_strategy_performance_alerts(strategy_name, metrics)

    def _check_strategy_performance_alerts(
        self, strategy_name: str, metrics: Dict[str, Any]
    ):
        """戦略パフォーマンスアラートをチェック"""

        # シャープレシオが低い
        if metrics.get("sharpe_ratio", 0) < self.thresholds["min_sharpe_ratio"]:
            self.alert_manager.create_alert(
                alert_type=AlertType.STRATEGY_PERFORMANCE,
                level=AlertLevel.WARNING,
                title=f"Low Sharpe Ratio: {strategy_name}",
                message=f"Strategy {strategy_name} has low Sharpe ratio: {metrics.get('sharpe_ratio', 0):.3f}",
                strategy_name=strategy_name,
                data=metrics,
            )

        # ドローダウンが大きい
        if metrics.get("max_drawdown", 0) > self.thresholds["max_drawdown"]:
            self.alert_manager.create_alert(
                alert_type=AlertType.STRATEGY_PERFORMANCE,
                level=AlertLevel.ERROR,
                title=f"High Drawdown: {strategy_name}",
                message=f"Strategy {strategy_name} has high drawdown: {metrics.get('max_drawdown', 0):.2%}",
                strategy_name=strategy_name,
                data=metrics,
            )

        # 勝率が低い
        if metrics.get("win_rate", 0) < self.thresholds["min_win_rate"]:
            self.alert_manager.create_alert(
                alert_type=AlertType.STRATEGY_PERFORMANCE,
                level=AlertLevel.WARNING,
                title=f"Low Win Rate: {strategy_name}",
                message=f"Strategy {strategy_name} has low win rate: {metrics.get('win_rate', 0):.2%}",
                strategy_name=strategy_name,
                data=metrics,
            )

    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス概要を取得"""
        return {
            "strategy_count": len(self.metrics["strategy_performance"]),
            "strategies": self.metrics["strategy_performance"],
            "system_health": self.metrics["system_health"],
            "trading_metrics": self.metrics["trading_metrics"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
