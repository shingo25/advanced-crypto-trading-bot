"""
サーキットブレーカー実装
取引システムの自動停止・復旧機能を提供
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class BreakerState(Enum):
    """サーキットブレーカーの状態"""

    CLOSED = "CLOSED"  # 通常状態（取引許可）
    OPEN = "OPEN"  # 取引停止状態
    HALF_OPEN = "HALF_OPEN"  # 部分再開状態（限定的取引許可）


class TripReason(Enum):
    """サーキットブレーカー作動理由"""

    CONSECUTIVE_LOSSES = "consecutive_losses"
    VOLATILITY_SPIKE = "volatility_spike"
    DRAWDOWN_LIMIT = "drawdown_limit"
    VAR_BREACH = "var_breach"
    SYSTEM_ERROR = "system_error"
    MANUAL_OVERRIDE = "manual_override"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CORRELATION_SPIKE = "correlation_spike"


@dataclass
class BreakerEvent:
    """サーキットブレーカーイベント"""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""  # "trip", "reset", "attempt_reset"
    reason: Optional[TripReason] = None
    old_state: Optional[BreakerState] = None
    new_state: Optional[BreakerState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """
    取引システム用サーキットブレーカー
    異常状況での自動取引停止・復旧機能
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: サーキットブレーカー設定
        """
        self.config = config
        self.state = BreakerState.CLOSED

        # 設定パラメータ
        self.failure_threshold = config.get("failure_threshold", 5)
        self.recovery_timeout_seconds = config.get("recovery_timeout_seconds", 300)  # 5分
        self.volatility_threshold = config.get("volatility_threshold", 0.10)  # 10%
        self.drawdown_threshold = config.get("drawdown_threshold", 0.20)  # 20%
        self.var_threshold = config.get("var_threshold", 0.08)  # 8%
        self.half_open_test_trades = config.get("half_open_test_trades", 3)  # テスト取引数

        # 状態管理
        self.consecutive_losses = 0
        self.consecutive_gains = 0
        self.last_failure_time: Optional[datetime] = None
        self.trip_time: Optional[datetime] = None
        self.manual_override = False
        self.test_trades_executed = 0

        # イベント履歴
        self.event_history: list[BreakerEvent] = []
        self.max_history_size = config.get("max_history_size", 1000)

        # コールバック関数
        self.on_trip_callback: Optional[Callable] = None
        self.on_reset_callback: Optional[Callable] = None
        self.notification_callback: Optional[Callable] = None

        logger.info(f"CircuitBreaker initialized with config: {config}")

    def set_callbacks(
        self,
        on_trip: Optional[Callable] = None,
        on_reset: Optional[Callable] = None,
        notification: Optional[Callable] = None,
    ):
        """コールバック関数を設定"""
        self.on_trip_callback = on_trip
        self.on_reset_callback = on_reset
        self.notification_callback = notification

    def trip(self, reason: TripReason, metadata: Dict[str, Any] = None):
        """
        サーキットブレーカーを作動させる

        Args:
            reason: 作動理由
            metadata: 追加情報
        """
        if self.state == BreakerState.OPEN:
            logger.debug(f"Circuit breaker already OPEN, ignoring trip request: {reason}")
            return

        old_state = self.state
        self.state = BreakerState.OPEN
        self.trip_time = datetime.now(timezone.utc)
        self.last_failure_time = self.trip_time
        self.test_trades_executed = 0

        # イベント記録
        event = BreakerEvent(
            event_type="trip", reason=reason, old_state=old_state, new_state=self.state, metadata=metadata or {}
        )
        self._add_event(event)

        # ログとアラート
        logger.critical(
            f"🚨 CIRCUIT BREAKER TRIPPED 🚨\n"
            f"State: {old_state.value} → {self.state.value}\n"
            f"Reason: {reason.value}\n"
            f"Metadata: {metadata}\n"
            f"Time: {self.trip_time.isoformat()}"
        )

        # コールバック実行
        if self.on_trip_callback:
            try:
                self.on_trip_callback(reason, metadata)
            except Exception as e:
                logger.error(f"Error in trip callback: {e}")

        # 通知
        if self.notification_callback:
            try:
                self.notification_callback(
                    level="critical",
                    title="Circuit Breaker Tripped",
                    message=f"Trading stopped due to: {reason.value}",
                    metadata=metadata,
                )
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

    def attempt_reset(self) -> bool:
        """
        ハーフオープン状態への移行を試行

        Returns:
            bool: 移行成功かどうか
        """
        if self.state != BreakerState.OPEN:
            return False

        if not self.trip_time:
            return False

        # タイムアウトチェック
        elapsed = (datetime.now(timezone.utc) - self.trip_time).total_seconds()
        if elapsed < self.recovery_timeout_seconds:
            logger.debug(f"Circuit breaker timeout not reached: {elapsed}/{self.recovery_timeout_seconds}s")
            return False

        # 手動オーバーライドチェック
        if self.manual_override:
            logger.debug("Manual override active, cannot auto-reset")
            return False

        old_state = self.state
        self.state = BreakerState.HALF_OPEN
        self.test_trades_executed = 0

        # イベント記録
        event = BreakerEvent(
            event_type="attempt_reset", old_state=old_state, new_state=self.state, metadata={"elapsed_seconds": elapsed}
        )
        self._add_event(event)

        logger.warning(
            f"🔄 Circuit Breaker state changed to HALF_OPEN\n"
            f"Time elapsed: {elapsed:.1f}s\n"
            f"Test trades allowed: {self.half_open_test_trades}"
        )

        return True

    def reset(self, force: bool = False):
        """
        サーキットブレーカーを完全リセット

        Args:
            force: 強制リセット（手動オーバーライド無視）
        """
        if not force and self.manual_override:
            logger.warning("Cannot reset: manual override active")
            return

        old_state = self.state
        self.state = BreakerState.CLOSED
        self.consecutive_losses = 0
        self.consecutive_gains = 0
        self.last_failure_time = None
        self.trip_time = None
        self.test_trades_executed = 0

        if force:
            self.manual_override = False

        # イベント記録
        event = BreakerEvent(event_type="reset", old_state=old_state, new_state=self.state, metadata={"forced": force})
        self._add_event(event)

        logger.info(f"✅ Circuit Breaker RESET to CLOSED state\nPrevious state: {old_state.value}\nForced: {force}")

        # コールバック実行
        if self.on_reset_callback:
            try:
                self.on_reset_callback()
            except Exception as e:
                logger.error(f"Error in reset callback: {e}")

        # 通知
        if self.notification_callback:
            try:
                self.notification_callback(
                    level="info",
                    title="Circuit Breaker Reset",
                    message="Trading has been restored to normal operation",
                    metadata={"forced": force},
                )
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

    def on_trade_result(self, success: bool, metadata: Dict[str, Any] = None):
        """
        取引結果を受信してカウンターを更新

        Args:
            success: 取引成功フラグ
            metadata: 取引詳細情報
        """
        try:
            if success:
                self.consecutive_gains += 1
                self.consecutive_losses = 0

                # HALF_OPEN状態での成功
                if self.state == BreakerState.HALF_OPEN:
                    self.test_trades_executed += 1
                    logger.info(
                        f"HALF_OPEN test trade {self.test_trades_executed}/{self.half_open_test_trades} succeeded"
                    )

                    if self.test_trades_executed >= self.half_open_test_trades:
                        self.reset()
            else:
                self.consecutive_losses += 1
                self.consecutive_gains = 0

                # HALF_OPEN状態での失敗
                if self.state == BreakerState.HALF_OPEN:
                    logger.warning("HALF_OPEN test trade failed, returning to OPEN state")
                    self.trip(TripReason.CONSECUTIVE_LOSSES, metadata)

                # 連続損失チェック
                elif self.consecutive_losses >= self.failure_threshold:
                    trip_metadata = {
                        "consecutive_losses": self.consecutive_losses,
                        "threshold": self.failure_threshold,
                    }
                    if metadata:
                        trip_metadata.update(metadata)
                    self.trip(TripReason.CONSECUTIVE_LOSSES, trip_metadata)

        except Exception as e:
            logger.error(f"Error processing trade result: {e}")

    def check_volatility(self, current_volatility: float, metadata: Dict[str, Any] = None):
        """
        ボラティリティ異常をチェック

        Args:
            current_volatility: 現在のボラティリティ
            metadata: 追加情報
        """
        try:
            if current_volatility > self.volatility_threshold:
                trip_metadata = {
                    "current_volatility": current_volatility,
                    "threshold": self.volatility_threshold,
                }
                if metadata:
                    trip_metadata.update(metadata)
                self.trip(TripReason.VOLATILITY_SPIKE, trip_metadata)
        except Exception as e:
            logger.error(f"Error checking volatility: {e}")

    def check_drawdown(self, current_drawdown: float, metadata: Dict[str, Any] = None):
        """
        ドローダウン制限をチェック

        Args:
            current_drawdown: 現在のドローダウン
            metadata: 追加情報
        """
        try:
            if current_drawdown > self.drawdown_threshold:
                trip_metadata = {
                    "current_drawdown": current_drawdown,
                    "threshold": self.drawdown_threshold,
                }
                if metadata:
                    trip_metadata.update(metadata)
                self.trip(TripReason.DRAWDOWN_LIMIT, trip_metadata)
        except Exception as e:
            logger.error(f"Error checking drawdown: {e}")

    def check_var_breach(self, current_var: float, metadata: Dict[str, Any] = None):
        """
        VaR制限違反をチェック

        Args:
            current_var: 現在のVaR
            metadata: 追加情報
        """
        try:
            if current_var > self.var_threshold:
                trip_metadata = {
                    "current_var": current_var,
                    "threshold": self.var_threshold,
                }
                if metadata:
                    trip_metadata.update(metadata)
                self.trip(TripReason.VAR_BREACH, trip_metadata)
        except Exception as e:
            logger.error(f"Error checking VaR: {e}")

    def manual_trip(self, reason: str = "Manual emergency stop"):
        """
        手動でサーキットブレーカーを作動

        Args:
            reason: 手動停止理由
        """
        self.manual_override = True
        self.trip(TripReason.MANUAL_OVERRIDE, {"reason": reason})

    def manual_release(self):
        """手動停止を解除"""
        if self.manual_override:
            self.manual_override = False
            self.reset(force=True)
            logger.info("Manual override released and circuit breaker reset")

    @property
    def is_trading_allowed(self) -> bool:
        """
        取引が許可されているかチェック

        Returns:
            bool: 取引許可フラグ
        """
        if self.state == BreakerState.CLOSED:
            return True
        elif self.state == BreakerState.HALF_OPEN:
            return self.test_trades_executed < self.half_open_test_trades
        else:  # OPEN
            # 自動復旧を試行
            self.attempt_reset()
            return False

    @property
    def is_open(self) -> bool:
        """サーキットブレーカーが開いているか"""
        return self.state == BreakerState.OPEN

    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            "state": self.state.value,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_gains": self.consecutive_gains,
            "manual_override": self.manual_override,
            "trip_time": self.trip_time.isoformat() if self.trip_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "test_trades_executed": self.test_trades_executed,
            "thresholds": {
                "failure_threshold": self.failure_threshold,
                "volatility_threshold": self.volatility_threshold,
                "drawdown_threshold": self.drawdown_threshold,
                "var_threshold": self.var_threshold,
            },
            "config": self.config,
        }

    def get_recent_events(self, limit: int = 10) -> list[Dict[str, Any]]:
        """最近のイベント履歴を取得"""
        recent_events = self.event_history[-limit:] if self.event_history else []
        return [
            {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "reason": event.reason.value if event.reason else None,
                "old_state": event.old_state.value if event.old_state else None,
                "new_state": event.new_state.value if event.new_state else None,
                "metadata": event.metadata,
            }
            for event in recent_events
        ]

    def _add_event(self, event: BreakerEvent):
        """イベントを履歴に追加"""
        self.event_history.append(event)

        # 履歴サイズ制限
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size :]

    def update_config(self, new_config: Dict[str, Any]):
        """設定を動的更新"""
        old_config = self.config.copy()
        self.config.update(new_config)

        # パラメータを更新
        self.failure_threshold = self.config.get("failure_threshold", self.failure_threshold)
        self.recovery_timeout_seconds = self.config.get("recovery_timeout_seconds", self.recovery_timeout_seconds)
        self.volatility_threshold = self.config.get("volatility_threshold", self.volatility_threshold)
        self.drawdown_threshold = self.config.get("drawdown_threshold", self.drawdown_threshold)
        self.var_threshold = self.config.get("var_threshold", self.var_threshold)
        self.half_open_test_trades = self.config.get("half_open_test_trades", self.half_open_test_trades)

        logger.info(f"Circuit breaker config updated: {old_config} → {self.config}")

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self.state.value}, "
            f"consecutive_losses={self.consecutive_losses}, "
            f"manual_override={self.manual_override})"
        )
