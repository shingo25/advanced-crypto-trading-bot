"""
統一アラートモデル

既存のRiskAlertとAlertシステムを統合した
包括的なアラートシステムのデータモデル
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertLevel(Enum):
    """アラートレベル - 重要度順"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """アラートカテゴリ - 機能別分類"""

    RISK = "risk"  # リスク管理関連
    PERFORMANCE = "performance"  # パフォーマンス監視
    EXECUTION = "execution"  # 注文・実行関連
    SYSTEM = "system"  # システム・インフラ関連
    MARKET = "market"  # 市場状況・価格関連


class AlertType(Enum):
    """詳細なアラートタイプ"""

    # Risk Management (RISK)
    VAR_BREACH = "var_breach"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    CONCENTRATION = "concentration"
    CORRELATION = "correlation"
    DAILY_LOSS = "daily_loss"
    LEVERAGE_EXCESS = "leverage_excess"

    # Performance (PERFORMANCE)
    STRATEGY_PERFORMANCE = "strategy_performance"
    LOW_SHARPE_RATIO = "low_sharpe_ratio"
    HIGH_DRAWDOWN = "high_drawdown"
    LOW_WIN_RATE = "low_win_rate"

    # Execution (EXECUTION)
    ORDER_EXECUTION = "order_execution"
    ORDER_FAILED = "order_failed"
    SLIPPAGE_HIGH = "slippage_high"
    POSITION_SIZE_ERROR = "position_size_error"

    # System (SYSTEM)
    SYSTEM_ERROR = "system_error"
    NETWORK_ISSUE = "network_issue"
    DATABASE_ERROR = "database_error"
    API_RATE_LIMIT = "api_rate_limit"
    BALANCE_LOW = "balance_low"

    # Market (MARKET)
    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"
    MARKET_ANOMALY = "market_anomaly"
    LIQUIDITY_SHORTAGE = "liquidity_shortage"


@dataclass
class AlertMetadata:
    """アラートのメタデータ"""

    source_component: str  # e.g., "advanced_risk_manager"
    source_file: str  # e.g., "advanced_risk_manager.py"
    symbol: Optional[str] = None  # 関連するシンボル
    strategy_name: Optional[str] = None  # 関連する戦略名
    position_id: Optional[str] = None  # 関連するポジションID
    order_id: Optional[str] = None  # 関連する注文ID

    # 数値データ
    current_value: Optional[float] = None  # 現在値
    threshold_value: Optional[float] = None  # 閾値
    change_percent: Optional[float] = None  # 変化率

    # 追加のコンテキストデータ
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertAction:
    """推奨アクション"""

    action_type: str  # e.g., "reduce_position", "review_strategy"
    description: str  # アクション詳細
    urgency: str  # "immediate", "high", "medium", "low"
    automated: bool = False  # 自動実行可能か
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedAlert:
    """統一アラートメッセージ"""

    # 必須フィールド
    id: str
    category: AlertCategory
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # メタデータ
    metadata: Optional[AlertMetadata] = None

    # 推奨アクション
    recommended_actions: List[AlertAction] = field(default_factory=list)

    # 処理状況
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    # 通知状況
    notification_sent: bool = False
    notification_channels: List[str] = field(default_factory=list)
    notification_attempts: int = 0
    last_notification_attempt: Optional[datetime] = None

    # 関連アラート
    parent_alert_id: Optional[str] = None
    child_alert_ids: List[str] = field(default_factory=list)

    # ハッシュ値（重複検知用）
    content_hash: Optional[str] = None

    def __post_init__(self):
        """初期化後の処理"""
        if not self.id:
            self.id = str(uuid.uuid4())

        if not self.content_hash:
            self.content_hash = self._generate_content_hash()

    def _generate_content_hash(self) -> str:
        """コンテンツハッシュを生成（重複検知用）"""
        content = {
            "category": self.category.value,
            "alert_type": self.alert_type.value,
            "title": self.title,
            "symbol": self.metadata.symbol if self.metadata else None,
            "strategy": self.metadata.strategy_name if self.metadata else None,
        }

        content_str = json.dumps(content, sort_keys=True)
        # 簡易ハッシュ（実際の実装では hashlib.sha256 を使用）
        return str(hash(content_str))

    def acknowledge(self, acknowledged_by: str = "system"):
        """アラートを確認済みにする"""
        self.acknowledged = True
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by = acknowledged_by

    def resolve(self):
        """アラートを解決済みにする"""
        self.resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        if not self.acknowledged:
            self.acknowledge("auto_resolved")

    def add_child_alert(self, child_alert_id: str):
        """子アラートを追加"""
        if child_alert_id not in self.child_alert_ids:
            self.child_alert_ids.append(child_alert_id)

    def record_notification_attempt(self, channel: str, success: bool = True):
        """通知試行を記録"""
        self.notification_attempts += 1
        self.last_notification_attempt = datetime.now(timezone.utc)

        if success:
            self.notification_sent = True
            if channel not in self.notification_channels:
                self.notification_channels.append(channel)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "category": self.category.value,
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": {
                "source_component": self.metadata.source_component if self.metadata else None,
                "source_file": self.metadata.source_file if self.metadata else None,
                "symbol": self.metadata.symbol if self.metadata else None,
                "strategy_name": self.metadata.strategy_name if self.metadata else None,
                "current_value": self.metadata.current_value if self.metadata else None,
                "threshold_value": self.metadata.threshold_value if self.metadata else None,
                "additional_data": self.metadata.additional_data if self.metadata else {},
            },
            "recommended_actions": [
                {
                    "action_type": action.action_type,
                    "description": action.description,
                    "urgency": action.urgency,
                    "automated": action.automated,
                    "parameters": action.parameters,
                }
                for action in self.recommended_actions
            ],
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notification_sent": self.notification_sent,
            "notification_channels": self.notification_channels,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedAlert":
        """辞書から復元"""
        metadata_dict = data.get("metadata", {})
        metadata = (
            AlertMetadata(
                source_component=metadata_dict.get("source_component", "unknown"),
                source_file=metadata_dict.get("source_file", "unknown"),
                symbol=metadata_dict.get("symbol"),
                strategy_name=metadata_dict.get("strategy_name"),
                current_value=metadata_dict.get("current_value"),
                threshold_value=metadata_dict.get("threshold_value"),
                additional_data=metadata_dict.get("additional_data", {}),
            )
            if metadata_dict.get("source_component")
            else None
        )

        actions = [
            AlertAction(
                action_type=action_data["action_type"],
                description=action_data["description"],
                urgency=action_data["urgency"],
                automated=action_data.get("automated", False),
                parameters=action_data.get("parameters", {}),
            )
            for action_data in data.get("recommended_actions", [])
        ]

        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            category=AlertCategory(data["category"]),
            alert_type=AlertType(data["alert_type"]),
            level=AlertLevel(data["level"]),
            title=data["title"],
            message=data["message"],
            timestamp=timestamp,
            metadata=metadata,
            recommended_actions=actions,
            acknowledged=data.get("acknowledged", False),
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"].replace("Z", "+00:00"))
            if data.get("acknowledged_at")
            else None,
            acknowledged_by=data.get("acknowledged_by"),
            resolved=data.get("resolved", False),
            resolved_at=datetime.fromisoformat(data["resolved_at"].replace("Z", "+00:00"))
            if data.get("resolved_at")
            else None,
            notification_sent=data.get("notification_sent", False),
            notification_channels=data.get("notification_channels", []),
            content_hash=data.get("content_hash"),
        )


# ヘルパー関数
def create_risk_alert(
    alert_type: AlertType,
    level: AlertLevel,
    title: str,
    message: str,
    source_component: str,
    symbol: Optional[str] = None,
    strategy_name: Optional[str] = None,
    current_value: Optional[float] = None,
    threshold_value: Optional[float] = None,
    recommended_action: Optional[str] = None,
) -> UnifiedAlert:
    """リスクアラートを作成するヘルパー関数"""

    metadata = AlertMetadata(
        source_component=source_component,
        source_file=f"{source_component}.py",
        symbol=symbol,
        strategy_name=strategy_name,
        current_value=current_value,
        threshold_value=threshold_value,
    )

    actions = []
    if recommended_action:
        actions.append(
            AlertAction(
                action_type="manual_review",
                description=recommended_action,
                urgency="high" if level in [AlertLevel.ERROR, AlertLevel.CRITICAL] else "medium",
            )
        )

    return UnifiedAlert(
        id=str(uuid.uuid4()),
        category=AlertCategory.RISK,
        alert_type=alert_type,
        level=level,
        title=title,
        message=message,
        metadata=metadata,
        recommended_actions=actions,
    )


def create_system_alert(
    alert_type: AlertType,
    level: AlertLevel,
    title: str,
    message: str,
    source_component: str,
    error_details: Optional[Dict[str, Any]] = None,
) -> UnifiedAlert:
    """システムアラートを作成するヘルパー関数"""

    metadata = AlertMetadata(
        source_component=source_component,
        source_file=f"{source_component}.py",
        additional_data=error_details or {},
    )

    actions = []
    if level == AlertLevel.CRITICAL:
        actions.append(
            AlertAction(
                action_type="immediate_investigation",
                description="Critical system error requires immediate attention",
                urgency="immediate",
            )
        )

    return UnifiedAlert(
        id=str(uuid.uuid4()),
        category=AlertCategory.SYSTEM,
        alert_type=alert_type,
        level=level,
        title=title,
        message=message,
        metadata=metadata,
        recommended_actions=actions,
    )


def create_performance_alert(
    alert_type: AlertType,
    level: AlertLevel,
    title: str,
    message: str,
    strategy_name: str,
    metrics: Dict[str, Any],
    recommended_action: Optional[str] = None,
) -> UnifiedAlert:
    """パフォーマンスアラートを作成するヘルパー関数"""

    metadata = AlertMetadata(
        source_component="performance_monitor",
        source_file="performance_monitor.py",
        strategy_name=strategy_name,
        additional_data=metrics,
    )

    actions = []
    if recommended_action:
        actions.append(
            AlertAction(
                action_type="strategy_review",
                description=recommended_action,
                urgency="medium",
            )
        )

    return UnifiedAlert(
        id=str(uuid.uuid4()),
        category=AlertCategory.PERFORMANCE,
        alert_type=alert_type,
        level=level,
        title=title,
        message=message,
        metadata=metadata,
        recommended_actions=actions,
    )
