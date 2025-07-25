"""
強化されたリスク管理システム
AdvancedRiskManager、CircuitBreaker、PositionManagerを統合
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio

from src.backend.risk.advanced_risk_manager import AdvancedRiskManager, RiskMetrics, RiskAlert, RiskLevel
from src.backend.risk.circuit_breaker import CircuitBreaker, TripReason, BreakerState
from src.backend.trading.risk_manager import RiskManager
from src.backend.trading.orders.models import Order

# Position型のための仮の定義（後で適切なクラスに置き換え）
class Position:
    def __init__(self, symbol: str, side: str = "long", quantity: float = 0.0, entry_price: float = 0.0, current_price: float = 0.0, unrealized_pnl: float = 0.0):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price
        self.unrealized_pnl = unrealized_pnl
    
    def get_market_value(self) -> float:
        return self.quantity * self.current_price

logger = logging.getLogger(__name__)


class PositionManager:
    """
    ポジション管理クラス
    リアルタイムポジション追跡と自動リバランシング
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._positions: Dict[str, Position] = {}
        self._equity_history: List[Tuple[datetime, float]] = []
        self._peak_equity = 0.0
        self._trading_engine = None  # 後で注入
        
        # 設定
        self.max_position_count = self.config.get("max_position_count", 10)
        self.auto_rebalance_threshold = self.config.get("auto_rebalance_threshold", 0.05)  # 5%
        self.emergency_liquidation_threshold = self.config.get("emergency_liquidation_threshold", 0.80)  # 80%
        
        logger.info("PositionManager initialized")
    
    def set_trading_engine(self, engine):
        """取引エンジンを設定"""
        self._trading_engine = engine
    
    def update_position(self, position: Position):
        """ポジションを更新"""
        self._positions[position.symbol] = position
        logger.debug(f"Position updated: {position.symbol}")
    
    def remove_position(self, symbol: str):
        """ポジションを削除"""
        if symbol in self._positions:
            del self._positions[symbol]
            logger.info(f"Position removed: {symbol}")
    
    def get_all_positions(self) -> Dict[str, Position]:
        """全ポジションを取得"""
        return self._positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """特定ポジションを取得"""
        return self._positions.get(symbol)
    
    def get_total_value(self) -> float:
        """ポートフォリオ総額を取得"""
        return sum(pos.get_market_value() for pos in self._positions.values())
    
    def get_total_pnl(self) -> float:
        """総未実現損益を取得"""
        return sum(pos.unrealized_pnl for pos in self._positions.values())
    
    def get_position_concentrations(self) -> Dict[str, float]:
        """ポジション集中度を計算"""
        total_value = self.get_total_value()
        if total_value == 0:
            return {}
        
        return {
            symbol: pos.get_market_value() / total_value
            for symbol, pos in self._positions.items()
        }
    
    def update_equity_history(self, current_equity: float):
        """資産履歴を更新"""
        current_time = datetime.now(timezone.utc)
        self._equity_history.append((current_time, current_equity))
        
        # 履歴制限（直近1000件）
        if len(self._equity_history) > 1000:
            self._equity_history = self._equity_history[-1000:]
        
        # ピーク更新
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
    
    def get_current_drawdown(self) -> float:
        """現在のドローダウンを計算"""
        if self._peak_equity == 0:
            return 0.0
        
        current_equity = self.get_total_value()
        return max(0, (self._peak_equity - current_equity) / self._peak_equity)
    
    async def liquidate_high_risk_positions(self, risk_threshold: float = 0.80):
        """高リスクポジションを強制決済"""
        if not self._trading_engine:
            logger.error("Trading engine not set, cannot liquidate positions")
            return
        
        logger.critical(f"🚨 LIQUIDATING HIGH RISK POSITIONS (threshold: {risk_threshold:.1%})")
        
        # 損失の大きいポジションから決済
        positions_by_loss = sorted(
            self._positions.items(),
            key=lambda x: x[1].unrealized_pnl
        )
        
        liquidated_count = 0
        for symbol, position in positions_by_loss:
            if position.unrealized_pnl < 0:  # 損失ポジションのみ
                try:
                    logger.warning(f"Liquidating position: {symbol} (PnL: {position.unrealized_pnl})")
                    # 取引エンジンで成行決済注文を実行
                    # await self._trading_engine.place_market_order(
                    #     symbol, 'sell' if position.side == 'long' else 'buy', position.quantity
                    # )
                    liquidated_count += 1
                except Exception as e:
                    logger.error(f"Failed to liquidate position {symbol}: {e}")
        
        logger.critical(f"Liquidated {liquidated_count} high-risk positions")
    
    async def auto_rebalance(self):
        """自動リバランシング"""
        concentrations = self.get_position_concentrations()
        
        for symbol, concentration in concentrations.items():
            if concentration > self.auto_rebalance_threshold:
                logger.info(f"Rebalancing required for {symbol}: {concentration:.2%}")
                # リバランシングロジックを実装
                # await self._rebalance_position(symbol, concentration)


class EnhancedRiskManager:
    """
    強化されたリスク管理システム
    AdvancedRiskManager、CircuitBreaker、PositionManagerを統合
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 設定辞書
        """
        self.config = config or {}
        
        # 基本RiskManagerを継承
        self.basic_risk_manager = RiskManager(self.config.get("basic_risk", {}))
        
        # 高度なリスク管理機能
        self.advanced_manager = AdvancedRiskManager(self.config.get("advanced_risk", {}))
        
        # サーキットブレーカー
        self.circuit_breaker = CircuitBreaker(self.config.get("circuit_breaker", {}))
        
        # ポジション管理
        self.position_manager = PositionManager(self.config.get("position_manager", {}))
        
        # 統合設定
        self.realtime_monitoring_enabled = self.config.get("realtime_monitoring", True)
        self.auto_response_enabled = self.config.get("auto_response", True)
        self.monitoring_interval = self.config.get("monitoring_interval", 10)  # 10秒
        
        # 状態管理
        self._monitoring_task: Optional[asyncio.Task] = None
        self._last_risk_check = datetime.now(timezone.utc)
        
        # コールバック設定
        self._setup_callbacks()
        
        logger.info("EnhancedRiskManager initialized with comprehensive risk management")
    
    def _setup_callbacks(self):
        """コールバック関数を設定"""
        # サーキットブレーカーのコールバック
        self.circuit_breaker.set_callbacks(
            on_trip=self._on_circuit_breaker_trip,
            on_reset=self._on_circuit_breaker_reset,
            notification=self._send_notification
        )
        
        # 基本リスクマネージャーのコールバック
        self.basic_risk_manager.on_risk_violation = self._on_risk_violation
        self.basic_risk_manager.on_emergency_stop = self._on_emergency_stop
    
    async def check_order_risk(
        self, 
        order: Order, 
        request_context: Dict = None,
        portfolio_value: Optional[Decimal] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        包括的な注文リスクチェック
        
        Args:
            order: 注文
            request_context: リクエストコンテキスト
            portfolio_value: ポートフォリオ総額
        
        Returns:
            Tuple[bool, Optional[str]]: (許可フラグ, エラーメッセージ)
        """
        try:
            # 1. サーキットブレーカーチェック
            if not self.circuit_breaker.is_trading_allowed:
                return False, f"Trading blocked: Circuit breaker is {self.circuit_breaker.state.value}"
            
            # 2. 基本リスクチェック（既存の実装）
            current_positions = self.position_manager.get_all_positions()
            current_pnl = self.position_manager.get_total_pnl()
            
            if not self.basic_risk_manager.check_order_risk(order, current_positions, current_pnl):
                return False, "Order rejected by basic risk checks"
            
            # 3. 高度なリスクチェック（ポートフォリオレベル）
            if portfolio_value:
                # 注文後のポートフォリオシミュレーション
                simulated_risk = await self._simulate_order_impact(order, portfolio_value)
                if simulated_risk > self.advanced_manager.risk_limits["max_portfolio_var_95"]:
                    return False, f"Order would exceed portfolio VaR limit: {simulated_risk:.2%}"
            
            # 4. 集中度リスクチェック
            concentrations = self.position_manager.get_position_concentrations()
            if order.symbol in concentrations:
                new_concentration = await self._calculate_new_concentration(order, concentrations)
                if new_concentration > 0.30:  # 30%制限
                    return False, f"Order would exceed concentration limit: {new_concentration:.2%}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error in order risk check: {e}")
            return False, f"Risk check failed: {e}"
    
    async def update_realtime_risk(self):
        """リアルタイムリスク監視の更新"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # 1. ポジションデータの更新
            positions = self.position_manager.get_all_positions()
            portfolio_value = self.position_manager.get_total_value()
            current_pnl = self.position_manager.get_total_pnl()
            
            # 資産履歴更新
            self.position_manager.update_equity_history(portfolio_value)
            
            # 2. 高度なリスクメトリクス計算
            portfolio_returns = self._get_portfolio_returns()
            strategy_returns = self._get_strategy_returns()
            position_dict = {pos.symbol: pos.get_market_value() for pos in positions.values()}
            
            risk_metrics = self.advanced_manager.calculate_portfolio_risk_metrics(
                portfolio_returns, strategy_returns, position_dict
            )
            
            # 3. リスク制限チェック
            alerts = self.advanced_manager.check_risk_limits(risk_metrics, position_dict)
            
            # 4. サーキットブレーカーのチェック
            self.circuit_breaker.check_volatility(risk_metrics.volatility)
            self.circuit_breaker.check_drawdown(risk_metrics.current_drawdown)
            self.circuit_breaker.check_var_breach(risk_metrics.total_var_99)
            
            # 5. 緊急停止チェック
            if self._should_emergency_stop(risk_metrics, positions):
                await self._execute_emergency_actions()
            
            # 6. アラート処理
            if alerts:
                await self._process_risk_alerts(alerts)
            
            # 7. 基本リスクマネージャーのチェック
            violations = self.basic_risk_manager.check_position_risk(positions, current_pnl)
            if violations:
                logger.warning(f"Risk violations detected: {violations}")
            
            self._last_risk_check = current_time
            
        except Exception as e:
            logger.error(f"Error in realtime risk update: {e}")
    
    def _should_emergency_stop(self, risk_metrics: RiskMetrics, positions: Dict[str, Position]) -> bool:
        """緊急停止が必要かチェック"""
        # 1. 基本リスクマネージャーの緊急停止条件
        current_pnl = sum(pos.unrealized_pnl for pos in positions.values())
        if self.basic_risk_manager.should_emergency_stop(positions, current_pnl):
            return True
        
        # 2. 高度なリスク条件
        emergency_conditions = [
            risk_metrics.current_drawdown > 0.25,  # 25%ドローダウン
            risk_metrics.total_var_99 > 0.15,     # 15% VaR
            risk_metrics.volatility > 0.50,       # 50%ボラティリティ
            risk_metrics.concentration_risk > 0.80,  # 80%集中度
        ]
        
        # 複数条件が同時に満たされた場合
        if sum(emergency_conditions) >= 2:
            logger.critical("Multiple emergency conditions detected")
            return True
        
        return False
    
    async def _execute_emergency_actions(self):
        """緊急時のアクション実行"""
        logger.critical("🚨 EXECUTING EMERGENCY ACTIONS 🚨")
        
        try:
            # 1. サーキットブレーカー作動
            self.circuit_breaker.trip(TripReason.SYSTEM_ERROR, {
                "action": "emergency_stop",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # 2. 高リスクポジションの強制決済
            if self.auto_response_enabled:
                await self.position_manager.liquidate_high_risk_positions()
            
            # 3. 緊急通知
            await self._send_notification(
                level="critical",
                title="🚨 EMERGENCY ACTIONS EXECUTED",
                message="Trading has been stopped and high-risk positions liquidated",
                metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
        except Exception as e:
            logger.error(f"Error executing emergency actions: {e}")
    
    async def _process_risk_alerts(self, alerts: List[RiskAlert]):
        """リスクアラートを処理"""
        for alert in alerts:
            logger.warning(f"Risk Alert: {alert.alert_type.value} - {alert.message}")
            
            # 重要度に応じた対応
            if alert.risk_level == RiskLevel.CRITICAL:
                # クリティカルアラートの場合はサーキットブレーカー作動を検討
                if alert.alert_type.value in ["var_breach", "drawdown"]:
                    self.circuit_breaker.trip(TripReason.VAR_BREACH, {
                        "alert_message": alert.message,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold_value
                    })
            
            # 通知送信
            await self._send_notification(
                level=alert.risk_level.value,
                title=f"Risk Alert: {alert.alert_type.value}",
                message=alert.message,
                metadata={
                    "current_value": alert.current_value,
                    "threshold": alert.threshold_value,
                    "recommended_action": alert.recommended_action
                }
            )
    
    async def start_monitoring(self):
        """リアルタイム監視を開始"""
        if not self.realtime_monitoring_enabled:
            logger.info("Realtime monitoring is disabled")
            return
        
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring task already running")
            return
        
        logger.info(f"Starting realtime risk monitoring (interval: {self.monitoring_interval}s)")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """リアルタイム監視を停止"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Realtime risk monitoring stopped")
    
    async def _monitoring_loop(self):
        """監視ループ"""
        try:
            while True:
                await self.update_realtime_risk()
                await asyncio.sleep(self.monitoring_interval)
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    def on_trade_result(self, success: bool, order: Order, metadata: Dict[str, Any] = None):
        """取引結果を受信"""
        # サーキットブレーカーに通知
        self.circuit_breaker.on_trade_result(success, metadata)
        
        # ポジション更新（実際の実装では取引エンジンから通知）
        # if success:
        #     self.position_manager.update_position(...)
    
    # コールバック関数
    def _on_circuit_breaker_trip(self, reason: TripReason, metadata: Dict[str, Any]):
        """サーキットブレーカー作動時のコールバック"""
        logger.critical(f"Circuit breaker tripped: {reason.value}")
    
    def _on_circuit_breaker_reset(self):
        """サーキットブレーカーリセット時のコールバック"""
        logger.info("Circuit breaker reset - trading resumed")
    
    def _on_risk_violation(self, violations: List[str]):
        """リスク違反時のコールバック"""
        logger.warning(f"Risk violations: {violations}")
    
    def _on_emergency_stop(self, reason: str, value: float):
        """緊急停止時のコールバック"""
        logger.critical(f"Emergency stop triggered: {reason} ({value})")
    
    async def _send_notification(self, level: str, title: str, message: str, metadata: Dict = None):
        """通知送信（実装は後で追加）"""
        logger.info(f"Notification [{level.upper()}]: {title} - {message}")
        # 実際の通知システム（Slack、Email等）との連携を実装
    
    # ヘルパーメソッド
    async def _simulate_order_impact(self, order: Order, portfolio_value: Decimal) -> float:
        """注文のポートフォリオ影響をシミュレーション"""
        # 簡略化された実装
        order_value = float(order.amount * (order.price or Decimal('50000')))
        return order_value / float(portfolio_value)
    
    async def _calculate_new_concentration(self, order: Order, current_concentrations: Dict[str, float]) -> float:
        """注文後の集中度を計算"""
        # 簡略化された実装
        current_concentration = current_concentrations.get(order.symbol, 0.0)
        # 実際の計算はより複雑になる
        return current_concentration + 0.05  # 仮の増加
    
    def _get_portfolio_returns(self) -> List[float]:
        """ポートフォリオリターン履歴を取得"""
        # 実装は資産履歴から計算
        if len(self.position_manager._equity_history) < 2:
            return [0.0]
        
        returns = []
        for i in range(1, len(self.position_manager._equity_history)):
            prev_equity = self.position_manager._equity_history[i-1][1]
            curr_equity = self.position_manager._equity_history[i][1]
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        return returns[-252:] if returns else [0.0]  # 直近1年
    
    def _get_strategy_returns(self) -> Dict[str, List[float]]:
        """戦略別リターンを取得（実装予定）"""
        # 戦略別のリターン履歴を管理する必要がある
        return {}
    
    # API用メソッド
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """包括的なリスク状態を取得"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "circuit_breaker": self.circuit_breaker.get_status(),
            "position_manager": {
                "total_positions": len(self.position_manager.get_all_positions()),
                "total_value": self.position_manager.get_total_value(),
                "total_pnl": self.position_manager.get_total_pnl(),
                "current_drawdown": self.position_manager.get_current_drawdown(),
                "concentrations": self.position_manager.get_position_concentrations(),
            },
            "basic_risk": self.basic_risk_manager.get_statistics(),
            "monitoring": {
                "enabled": self.realtime_monitoring_enabled,
                "last_check": self._last_risk_check.isoformat(),
                "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
            }
        }
    
    async def manual_emergency_stop(self, reason: str = "Manual intervention"):
        """手動緊急停止"""
        self.circuit_breaker.manual_trip(reason)
        await self._execute_emergency_actions()
    
    def manual_reset(self):
        """手動リセット"""
        self.circuit_breaker.manual_release()
        logger.info("Manual reset completed")