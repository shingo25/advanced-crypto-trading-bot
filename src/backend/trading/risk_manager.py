"""
リスク管理クラス
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from .engine import Order, Position

logger = logging.getLogger(__name__)


class RiskManager:
    """リスク管理クラス"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.is_enabled = self.config.get("enable_risk_management", True)

        # リスク制限の設定
        self.risk_limits = self.config.get(
            "risk_limits",
            {
                "max_position_size": 10000.0,
                "max_daily_loss": 1000.0,
                "max_drawdown": 0.1,
                "max_leverage": 1.0,
                "max_correlation": 0.7,
                "max_portfolio_heat": 0.02,
                "position_size_limit_pct": 0.1,
            },
        )

        # イベントハンドラー
        self.on_risk_violation: Optional[Callable] = None
        self.on_emergency_stop: Optional[Callable] = None

        # 統計
        self.stats = {
            "risk_violations": 0,
            "emergency_stops": 0,
            "position_size_violations": 0,
            "drawdown_violations": 0,
            "correlation_violations": 0,
            "last_risk_check": datetime.now(timezone.utc),
        }

        logger.info("RiskManager initialized")

    def check_order_risk(self, order: Order, current_positions: Dict[str, Position], current_pnl: float) -> bool:
        """注文リスクをチェック"""
        if not self.is_enabled:
            return True

        # ポジションサイズ制限
        if not self._check_position_size_limit(order, current_positions):
            return False

        # 日次損失制限
        if not self._check_daily_loss_limit(current_pnl):
            return False

        # レバレッジ制限
        if not self._check_leverage_limit(order, current_positions):
            return False

        # 相関制限
        if not self._check_correlation_limit(order, current_positions):
            return False

        # ポートフォリオヒート
        if not self._check_portfolio_heat(order, current_positions):
            return False

        return True

    def check_position_risk(self, positions: Dict[str, Position], current_pnl: float) -> List[str]:
        """ポジションリスクをチェック"""
        if not self.is_enabled:
            return []

        violations = []

        # 個別ポジションサイズ
        for symbol, position in positions.items():
            position_value = float(position.get_market_value())
            if position_value > self.risk_limits["max_position_size"]:
                violations.append(f"Position size limit exceeded: {symbol}")
                self.stats["position_size_violations"] += 1

        # 日次損失制限
        if current_pnl < -self.risk_limits["max_daily_loss"]:
            violations.append(f"Daily loss limit exceeded: {current_pnl}")

        # 最大ドローダウン
        if self._calculate_current_drawdown(current_pnl) > self.risk_limits["max_drawdown"]:
            violations.append(f"Max drawdown exceeded: {self._calculate_current_drawdown(current_pnl)}")
            self.stats["drawdown_violations"] += 1

        # ポートフォリオ集中度
        concentration_risk = self._check_portfolio_concentration(positions)
        if concentration_risk:
            violations.append(concentration_risk)

        self.stats["last_risk_check"] = datetime.now(timezone.utc)

        if violations:
            self.stats["risk_violations"] += len(violations)
            if self.on_risk_violation:
                self.on_risk_violation(violations)

        return violations

    def should_emergency_stop(self, positions: Dict[str, Position], current_pnl: float) -> bool:
        """緊急停止が必要かチェック"""
        if not self.is_enabled:
            return False

        # 極度の損失
        extreme_loss_threshold = self.risk_limits["max_daily_loss"] * 2
        if current_pnl < -extreme_loss_threshold:
            logger.critical(f"Emergency stop triggered: extreme loss {current_pnl}")
            self.stats["emergency_stops"] += 1
            if self.on_emergency_stop:
                self.on_emergency_stop("extreme_loss", current_pnl)
            return True

        # 極度のドローダウン
        extreme_drawdown_threshold = self.risk_limits["max_drawdown"] * 2
        if self._calculate_current_drawdown(current_pnl) > extreme_drawdown_threshold:
            logger.critical("Emergency stop triggered: extreme drawdown")
            self.stats["emergency_stops"] += 1
            if self.on_emergency_stop:
                self.on_emergency_stop("extreme_drawdown", self._calculate_current_drawdown(current_pnl))
            return True

        return False

    def calculate_position_size(
        self,
        symbol: str,
        risk_amount: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        """ポジションサイズを計算"""
        if stop_loss_price == 0 or entry_price == 0:
            return 0.0

        # リスク1単位あたりの損失
        risk_per_unit = abs(entry_price - stop_loss_price)

        # 最大ポジションサイズ
        max_position_size = risk_amount / risk_per_unit

        # 制限内に収める
        max_allowed = self.risk_limits["max_position_size"]
        return min(max_position_size, max_allowed)

    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """ケリー基準を計算"""
        if avg_loss == 0:
            return 0.0

        win_loss_ratio = avg_win / abs(avg_loss)
        kelly_fraction = win_rate - ((1 - win_rate) / win_loss_ratio)

        # 保守的に制限
        kelly_cap = self.config.get("kelly_fraction_cap", 0.25)
        return max(0, min(kelly_fraction, kelly_cap))

    def _check_position_size_limit(self, order: Order, current_positions: Dict[str, Position]) -> bool:
        """ポジションサイズ制限をチェック"""
        # 新しいポジションサイズを計算
        # Decimal型で統一
        order_amount = Decimal(str(order.amount))
        order_price = Decimal(str(order.price)) if order.price else Decimal("50000.0")
        estimated_value_decimal = order_amount * order_price

        # 既存ポジションがある場合は統合
        if order.symbol in current_positions:
            current_position = current_positions[order.symbol]
            if current_position.side == order.side:
                estimated_value_decimal += current_position.get_market_value()

        estimated_value_float = float(estimated_value_decimal)
        if estimated_value_float > self.risk_limits["max_position_size"]:
            logger.warning(f"Position size limit exceeded: {estimated_value_float}")
            return False

        return True

    def _check_daily_loss_limit(self, current_pnl: float) -> bool:
        """日次損失制限をチェック"""
        if current_pnl < -self.risk_limits["max_daily_loss"]:
            logger.warning(f"Daily loss limit exceeded: {current_pnl}")
            return False
        return True

    def _check_leverage_limit(self, order: Order, current_positions: Dict[str, Position]) -> bool:
        """レバレッジ制限をチェック"""
        # 簡単な実装（実際のレバレッジ計算は複雑）
        total_exposure = float(sum(pos.get_market_value() for pos in current_positions.values()))
        order_value = order.amount * (order.price or 50000.0)

        # 仮の資本金（実際の実装では動的に計算）
        capital = 100000.0

        leverage = (total_exposure + order_value) / capital
        if leverage > self.risk_limits["max_leverage"]:
            logger.warning(f"Leverage limit exceeded: {leverage}")
            return False

        return True

    def _check_correlation_limit(self, order: Order, current_positions: Dict[str, Position]) -> bool:
        """相関制限をチェック"""
        # 簡単な実装（実際の相関計算は複雑）
        # 同じ市場での過度の集中を防ぐ

        if order.symbol.endswith("USDT") or order.symbol.endswith("BTC"):
            similar_positions = [
                pos for pos in current_positions.values() if pos.symbol.endswith("USDT") or pos.symbol.endswith("BTC")
            ]

            if len(similar_positions) > 3:  # 3つ以上の類似ポジション
                logger.warning("Correlation limit exceeded: too many similar positions")
                self.stats["correlation_violations"] += 1
                return False

        return True

    def _check_portfolio_heat(self, order: Order, current_positions: Dict[str, Position]) -> bool:
        """ポートフォリオヒートをチェック"""
        # 各ポジションのリスクを合計
        total_risk = 0.0

        for position in current_positions.values():
            # 未実現損失の割合
            pnl = float(position.unrealized_pnl)
            market_value = float(position.get_market_value())
            if pnl < 0 and market_value > 0:
                total_risk += abs(pnl) / market_value

        # 新規注文のリスク
        order_risk = self.risk_limits["position_size_limit_pct"]

        if total_risk + order_risk > self.risk_limits["max_portfolio_heat"]:
            logger.warning(f"Portfolio heat limit exceeded: {total_risk + order_risk}")
            return False

        return True

    def _check_portfolio_concentration(self, positions: Dict[str, Position]) -> Optional[str]:
        """ポートフォリオ集中度をチェック"""
        if not positions:
            return None

        total_value = float(sum(pos.get_market_value() for pos in positions.values()))

        for symbol, position in positions.items():
            position_value = float(position.get_market_value())
            concentration = position_value / total_value if total_value > 0 else 0
            if concentration > self.risk_limits["position_size_limit_pct"]:
                return f"Portfolio concentration risk: {symbol} ({concentration:.2%})"

        return None

    def _calculate_current_drawdown(self, current_pnl: float) -> float:
        """現在のドローダウンを計算"""
        # 簡単な実装（実際は履歴データが必要）
        if current_pnl < 0:
            return abs(current_pnl) / 100000.0  # 仮の初期資本
        return 0.0

    def update_config(self, new_config: Dict[str, Any]):
        """設定を更新"""
        self.config.update(new_config)
        self.risk_limits.update(new_config.get("risk_limits", {}))
        self.is_enabled = self.config.get("enable_risk_management", True)
        logger.info("RiskManager configuration updated")

    def get_risk_metrics(self, positions: Dict[str, Position], current_pnl: float) -> Dict[str, Any]:
        """リスクメトリクスを取得"""
        total_exposure = float(sum(pos.get_market_value() for pos in positions.values()))

        return {
            "total_exposure": total_exposure,
            "position_count": len(positions),
            "current_pnl": current_pnl,
            "current_drawdown": self._calculate_current_drawdown(current_pnl),
            "risk_limit_usage": {
                "max_position_size": max(
                    float(pos.get_market_value()) / self.risk_limits["max_position_size"] for pos in positions.values()
                )
                if positions
                else 0.0,
                "daily_loss": abs(current_pnl) / self.risk_limits["max_daily_loss"],
                "drawdown": self._calculate_current_drawdown(current_pnl) / self.risk_limits["max_drawdown"],
            },
            "risk_violations": self.stats["risk_violations"],
            "emergency_stops": self.stats["emergency_stops"],
            "last_risk_check": self.stats["last_risk_check"].isoformat(),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "risk_violations": self.stats["risk_violations"],
            "emergency_stops": self.stats["emergency_stops"],
            "position_size_violations": self.stats["position_size_violations"],
            "drawdown_violations": self.stats["drawdown_violations"],
            "correlation_violations": self.stats["correlation_violations"],
            "last_risk_check": self.stats["last_risk_check"].isoformat(),
            "is_enabled": self.is_enabled,
        }
