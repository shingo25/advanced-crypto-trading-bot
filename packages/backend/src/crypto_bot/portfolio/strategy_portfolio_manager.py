"""
戦略統合ポートフォリオマネージャー

複数の取引戦略を統合し、パフォーマンス追跡と
リスク管理を行うAdvancedPortfolioManager
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..strategies.base import BaseStrategy, Signal
from .manager import PortfolioManager

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """戦略の状態"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class StrategyAllocation:
    """戦略別資金配分"""

    strategy_name: str
    strategy_instance: BaseStrategy
    allocated_capital: float
    target_weight: float
    current_weight: float = 0.0
    status: StrategyStatus = StrategyStatus.ACTIVE
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_signal: Optional[Signal] = None
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""

    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    trades_count: int = 0
    avg_trade_return: float = 0.0
    volatility: float = 0.0
    var_95: float = 0.0  # 95% VaR
    calmar_ratio: float = 0.0


@dataclass
class TradeRecord:
    """取引記録"""

    strategy_name: str
    symbol: str
    action: str  # 'enter_long', 'exit_long', etc.
    quantity: float
    price: float
    timestamp: datetime
    signal_strength: float
    pnl: Optional[float] = None
    commission: float = 0.0
    trade_id: str = ""


class AdvancedPortfolioManager(PortfolioManager):
    """戦略統合ポートフォリオマネージャー"""

    def __init__(self, initial_capital: float = 100000.0):
        super().__init__()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        self.trade_history: List[TradeRecord] = []
        self.performance_history: List[Dict[str, Any]] = []
        self.risk_limits = {
            "max_position_size": 0.1,  # 単一ポジションの最大サイズ（10%）
            "max_daily_loss": 0.02,  # 日次最大損失（2%）
            "max_strategy_allocation": 0.3,  # 単一戦略の最大配分（30%）
            "correlation_threshold": 0.7,  # 戦略間相関制限
        }
        self.daily_pnl: Dict[str, float] = {}  # 日次損益
        self.position_sizes: Dict[str, float] = {}  # ポジションサイズ

        logger.info(f"AdvancedPortfolioManager initialized with capital: {initial_capital}")

    def add_strategy(
        self,
        strategy: BaseStrategy,
        allocation_weight: float,
        status: StrategyStatus = StrategyStatus.ACTIVE,
    ) -> bool:
        """戦略を追加"""
        try:
            if allocation_weight <= 0 or allocation_weight > 1:
                raise ValueError("Allocation weight must be between 0 and 1")

            # 既存の配分重みとの合計をチェック
            total_weight = sum(alloc.target_weight for alloc in self.strategy_allocations.values())
            if total_weight + allocation_weight > 1.0:
                raise ValueError("Total allocation weight exceeds 100%")

            # 単一戦略の最大配分をチェック
            if allocation_weight > self.risk_limits["max_strategy_allocation"]:
                logger.warning(
                    f"Strategy allocation {allocation_weight} exceeds limit {self.risk_limits['max_strategy_allocation']}"
                )

            allocated_capital = self.current_capital * allocation_weight

            allocation = StrategyAllocation(
                strategy_name=strategy.name,
                strategy_instance=strategy,
                allocated_capital=allocated_capital,
                target_weight=allocation_weight,
                status=status,
            )

            self.strategy_allocations[strategy.name] = allocation
            logger.info(f"Added strategy {strategy.name} with {allocation_weight*100:.1f}% allocation")
            return True

        except Exception as e:
            logger.error(f"Error adding strategy {strategy.name}: {e}")
            return False

    def remove_strategy(self, strategy_name: str) -> bool:
        """戦略を削除"""
        try:
            if strategy_name not in self.strategy_allocations:
                logger.warning(f"Strategy {strategy_name} not found")
                return False

            # ポジションがある場合は警告
            allocation = self.strategy_allocations[strategy_name]
            if allocation.strategy_instance.state.is_long or allocation.strategy_instance.state.is_short:
                logger.warning(f"Strategy {strategy_name} has open positions")

            del self.strategy_allocations[strategy_name]
            logger.info(f"Removed strategy {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Error removing strategy {strategy_name}: {e}")
            return False

    def update_strategy_status(self, strategy_name: str, status: StrategyStatus) -> bool:
        """戦略の状態を更新"""
        try:
            if strategy_name not in self.strategy_allocations:
                return False

            self.strategy_allocations[strategy_name].status = status
            logger.info(f"Updated strategy {strategy_name} status to {status.value}")
            return True

        except Exception as e:
            logger.error(f"Error updating strategy status: {e}")
            return False

    def process_market_data(self, symbol: str, ohlcv_data: Dict[str, Any]) -> List[Signal]:
        """市場データを処理して全戦略のシグナルを生成"""
        all_signals = []

        try:
            for strategy_name, allocation in self.strategy_allocations.items():
                if allocation.status != StrategyStatus.ACTIVE:
                    continue

                strategy = allocation.strategy_instance

                # 戦略が対象シンボルをサポートしているかチェック
                if strategy.symbol != symbol:
                    continue

                # 戦略を更新してシグナルを取得
                signal = strategy.update(ohlcv_data)

                if signal:
                    # ポジションサイズを計算
                    position_size = self._calculate_position_size(strategy_name, signal)
                    if position_size > 0:
                        # シグナルにポジションサイズ情報を追加
                        signal.price = ohlcv_data.get("close", signal.price)
                        allocation.last_signal = signal
                        allocation.last_updated = datetime.now()
                        all_signals.append(signal)

                        logger.info(f"Signal from {strategy_name}: {signal.action} {signal.symbol} @ {signal.price}")

            return all_signals

        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            return []

    def _calculate_position_size(self, strategy_name: str, signal: Signal) -> float:
        """ポジションサイズを計算"""
        try:
            allocation = self.strategy_allocations[strategy_name]

            # 基本ポジションサイズ（戦略の配分資本から）
            base_size = allocation.allocated_capital * signal.strength

            # リスク制限を適用
            max_position = self.current_capital * self.risk_limits["max_position_size"]
            position_size = min(base_size, max_position)

            # 既存ポジションを考慮
            strategy = allocation.strategy_instance
            if strategy.state.is_long or strategy.state.is_short:
                # 既にポジションがある場合は調整
                position_size *= 0.5

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def execute_signal(self, signal: Signal, position_size: float) -> bool:
        """シグナルを実行"""
        try:
            # リスク制限チェック
            if not self._check_risk_limits(signal, position_size):
                logger.warning(f"Risk limits prevent execution of {signal.action} {signal.symbol}")
                return False

            # 取引記録を作成
            trade_record = TradeRecord(
                strategy_name=signal.symbol,  # TODO: 戦略名を適切に設定
                symbol=signal.symbol,
                action=signal.action,
                quantity=position_size / signal.price if signal.price > 0 else 0,
                price=signal.price,
                timestamp=signal.timestamp,
                signal_strength=signal.strength,
                trade_id=f"{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}",
            )

            self.trade_history.append(trade_record)

            # ポジションサイズを更新
            position_key = f"{signal.symbol}_{signal.action}"
            self.position_sizes[position_key] = position_size

            logger.info(
                f"Executed signal: {signal.action} {trade_record.quantity:.4f} {signal.symbol} @ {signal.price}"
            )
            return True

        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False

    def _check_risk_limits(self, signal: Signal, position_size: float) -> bool:
        """リスク制限をチェック"""
        try:
            # 日次損失制限
            today = datetime.now().date()
            daily_loss = self.daily_pnl.get(str(today), 0.0)
            max_daily_loss = self.current_capital * self.risk_limits["max_daily_loss"]

            if abs(daily_loss) > max_daily_loss:
                return False

            # ポジションサイズ制限
            max_position = self.current_capital * self.risk_limits["max_position_size"]
            if position_size > max_position:
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return False

    def calculate_portfolio_performance(self) -> PerformanceMetrics:
        """ポートフォリオパフォーマンスを計算"""
        try:
            if not self.trade_history:
                return PerformanceMetrics()

            # 取引から収益を計算
            returns = []
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0.0

            for trade in self.trade_history:
                if trade.pnl is not None:
                    returns.append(trade.pnl / self.initial_capital)
                    total_pnl += trade.pnl

                    if trade.pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1

            if not returns:
                return PerformanceMetrics()

            returns_array = np.array(returns)

            # 基本メトリクス
            total_return = total_pnl / self.initial_capital
            win_rate = winning_trades / len(returns) if returns else 0
            avg_return = np.mean(returns_array)
            volatility = np.std(returns_array) * np.sqrt(252)  # 年率化

            # シャープレシオ（リスクフリーレート0と仮定）
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0

            # 最大ドローダウン
            cumulative_returns = np.cumsum(returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0

            # カルマー・レシオ
            calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

            # 95% VaR
            var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0

            # プロフィット・ファクター
            gross_profit = sum(r for r in returns_array if r > 0)
            gross_loss = abs(sum(r for r in returns_array if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            return PerformanceMetrics(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                trades_count=len(returns),
                avg_trade_return=avg_return,
                volatility=volatility,
                var_95=var_95,
                calmar_ratio=calmar_ratio,
            )

        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            return PerformanceMetrics()

    def calculate_strategy_performance(self, strategy_name: str) -> PerformanceMetrics:
        """戦略別パフォーマンスを計算"""
        try:
            strategy_trades = [t for t in self.trade_history if t.strategy_name == strategy_name]

            if not strategy_trades:
                return PerformanceMetrics()

            # 戦略固有の取引データから計算
            # (ポートフォリオパフォーマンス計算と同様のロジック)
            returns = []
            for trade in strategy_trades:
                if trade.pnl is not None:
                    returns.append(trade.pnl)

            if not returns:
                return PerformanceMetrics()

            # 基本統計
            total_return = sum(returns)
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            avg_return = np.mean(returns)

            return PerformanceMetrics(
                total_return=total_return,
                win_rate=win_rate,
                trades_count=len(returns),
                avg_trade_return=avg_return,
            )

        except Exception as e:
            logger.error(f"Error calculating strategy performance: {e}")
            return PerformanceMetrics()

    def get_strategy_correlation_matrix(self) -> pd.DataFrame:
        """戦略間の相関行列を取得"""
        try:
            strategy_names = list(self.strategy_allocations.keys())
            if len(strategy_names) < 2:
                return pd.DataFrame()

            # 各戦略のリターン系列を取得
            strategy_returns = {}
            for strategy_name in strategy_names:
                strategy_trades = [t for t in self.trade_history if t.strategy_name == strategy_name]
                returns = [t.pnl for t in strategy_trades if t.pnl is not None]
                if returns:
                    strategy_returns[strategy_name] = returns

            if len(strategy_returns) < 2:
                return pd.DataFrame()

            # データ長を揃える
            min_length = min(len(returns) for returns in strategy_returns.values())
            aligned_returns = {name: returns[-min_length:] for name, returns in strategy_returns.items()}

            # 相関行列を計算
            df = pd.DataFrame(aligned_returns)
            return df.corr()

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()

    def rebalance_strategies(self) -> List[Dict[str, Any]]:
        """戦略の配分を再調整"""
        try:
            rebalance_actions = []

            # 現在の戦略パフォーマンスを基に重みを調整
            total_performance = 0.0
            strategy_performances = {}

            for strategy_name, allocation in self.strategy_allocations.items():
                performance = self.calculate_strategy_performance(strategy_name)
                strategy_performances[strategy_name] = performance.total_return
                total_performance += performance.total_return

            # パフォーマンスベースの重み調整
            for strategy_name, allocation in self.strategy_allocations.items():
                current_performance = strategy_performances[strategy_name]

                # パフォーマンスが悪い戦略の配分を削減
                if current_performance < 0 and abs(current_performance) > 0.05:  # 5%以上の損失
                    new_weight = allocation.target_weight * 0.8  # 20%削減
                    rebalance_actions.append(
                        {
                            "strategy": strategy_name,
                            "current_weight": allocation.target_weight,
                            "new_weight": new_weight,
                            "reason": f"Poor performance: {current_performance:.2%}",
                        }
                    )
                    allocation.target_weight = new_weight

            # 配分の正規化
            total_weight = sum(alloc.target_weight for alloc in self.strategy_allocations.values())
            if total_weight > 0:
                for allocation in self.strategy_allocations.values():
                    allocation.target_weight /= total_weight

            return rebalance_actions

        except Exception as e:
            logger.error(f"Error rebalancing strategies: {e}")
            return []

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """詳細なポートフォリオサマリーを取得"""
        try:
            performance = self.calculate_portfolio_performance()
            correlation_matrix = self.get_strategy_correlation_matrix()

            strategy_summaries = {}
            for strategy_name, allocation in self.strategy_allocations.items():
                strategy_perf = self.calculate_strategy_performance(strategy_name)
                strategy_summaries[strategy_name] = {
                    "target_weight": allocation.target_weight,
                    "allocated_capital": allocation.allocated_capital,
                    "status": allocation.status.value,
                    "performance": {
                        "total_return": strategy_perf.total_return,
                        "win_rate": strategy_perf.win_rate,
                        "trades_count": strategy_perf.trades_count,
                    },
                    "last_signal": {
                        "action": allocation.last_signal.action if allocation.last_signal else None,
                        "timestamp": allocation.last_signal.timestamp.isoformat() if allocation.last_signal else None,
                    },
                }

            return {
                "portfolio_overview": {
                    "initial_capital": self.initial_capital,
                    "current_capital": self.current_capital,
                    "total_strategies": len(self.strategy_allocations),
                    "active_strategies": len(
                        [a for a in self.strategy_allocations.values() if a.status == StrategyStatus.ACTIVE]
                    ),
                },
                "performance_metrics": {
                    "total_return": performance.total_return,
                    "sharpe_ratio": performance.sharpe_ratio,
                    "max_drawdown": performance.max_drawdown,
                    "win_rate": performance.win_rate,
                    "profit_factor": performance.profit_factor,
                    "volatility": performance.volatility,
                    "var_95": performance.var_95,
                    "calmar_ratio": performance.calmar_ratio,
                },
                "strategy_allocations": strategy_summaries,
                "correlation_matrix": correlation_matrix.to_dict() if not correlation_matrix.empty else {},
                "risk_metrics": {
                    "current_exposure": sum(
                        allocation.allocated_capital for allocation in self.strategy_allocations.values()
                    ),
                    "max_position_size": self.risk_limits["max_position_size"],
                    "max_daily_loss": self.risk_limits["max_daily_loss"],
                },
                "trade_summary": {
                    "total_trades": len(self.trade_history),
                    "recent_trades": [
                        {
                            "strategy": trade.strategy_name,
                            "symbol": trade.symbol,
                            "action": trade.action,
                            "price": trade.price,
                            "timestamp": trade.timestamp.isoformat(),
                        }
                        for trade in self.trade_history[-10:]  # 最新10取引
                    ],
                },
            }

        except Exception as e:
            logger.error(f"Error generating portfolio summary: {e}")
            return {"error": str(e)}

    def get_risk_report(self) -> Dict[str, Any]:
        """リスクレポートを生成"""
        try:
            correlation_matrix = self.get_strategy_correlation_matrix()

            risk_report = {
                "position_concentration": {},
                "strategy_correlation": {},
                "var_analysis": {},
                "exposure_limits": {},
            }

            # ポジション集中度分析
            total_exposure = sum(allocation.allocated_capital for allocation in self.strategy_allocations.values())
            for strategy_name, allocation in self.strategy_allocations.items():
                concentration = allocation.allocated_capital / total_exposure if total_exposure > 0 else 0
                risk_report["position_concentration"][strategy_name] = {
                    "concentration": concentration,
                    "risk_level": "high" if concentration > 0.4 else "medium" if concentration > 0.2 else "low",
                }

            # 戦略間相関分析
            if not correlation_matrix.empty:
                high_correlations = []
                for i in range(len(correlation_matrix.columns)):
                    for j in range(i + 1, len(correlation_matrix.columns)):
                        corr = correlation_matrix.iloc[i, j]
                        if abs(corr) > self.risk_limits["correlation_threshold"]:
                            high_correlations.append(
                                {
                                    "strategy1": correlation_matrix.columns[i],
                                    "strategy2": correlation_matrix.columns[j],
                                    "correlation": corr,
                                }
                            )

                risk_report["strategy_correlation"] = {
                    "high_correlations": high_correlations,
                    "max_correlation": float(correlation_matrix.abs().max().max())
                    if not correlation_matrix.empty
                    else 0,
                }

            # VaR分析
            performance = self.calculate_portfolio_performance()
            risk_report["var_analysis"] = {
                "var_95": performance.var_95,
                "expected_shortfall": performance.var_95 * 1.3,  # 簡易的なExpected Shortfall
                "volatility": performance.volatility,
            }

            # 露出制限チェック
            risk_report["exposure_limits"] = {
                "current_exposure": total_exposure,
                "exposure_ratio": total_exposure / self.current_capital,
                "within_limits": total_exposure <= self.current_capital,
            }

            return risk_report

        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {"error": str(e)}

    def optimize_portfolio(self) -> Dict[str, Any]:
        """ポートフォリオ最適化の提案"""
        try:
            optimization_suggestions = {
                "rebalancing": [],
                "risk_reduction": [],
                "performance_improvement": [],
            }

            # リバランシング提案
            rebalance_actions = self.rebalance_strategies()
            optimization_suggestions["rebalancing"] = rebalance_actions

            # リスク削減提案
            risk_report = self.get_risk_report()

            # 高相関戦略の警告
            if "high_correlations" in risk_report.get("strategy_correlation", {}):
                for corr_pair in risk_report["strategy_correlation"]["high_correlations"]:
                    optimization_suggestions["risk_reduction"].append(
                        {
                            "type": "correlation_risk",
                            "description": f"High correlation between {corr_pair['strategy1']} and {corr_pair['strategy2']}: {corr_pair['correlation']:.2f}",
                            "suggestion": "Consider reducing allocation to one of these strategies",
                        }
                    )

            # 集中リスクの警告
            for strategy_name, concentration_data in risk_report.get("position_concentration", {}).items():
                if concentration_data["risk_level"] == "high":
                    optimization_suggestions["risk_reduction"].append(
                        {
                            "type": "concentration_risk",
                            "description": f"High concentration in {strategy_name}: {concentration_data['concentration']:.1%}",
                            "suggestion": "Consider diversifying into additional strategies",
                        }
                    )

            # パフォーマンス改善提案
            for strategy_name, allocation in self.strategy_allocations.items():
                strategy_perf = self.calculate_strategy_performance(strategy_name)
                if strategy_perf.win_rate < 0.4:  # 勝率40%未満
                    optimization_suggestions["performance_improvement"].append(
                        {
                            "type": "low_win_rate",
                            "strategy": strategy_name,
                            "current_win_rate": strategy_perf.win_rate,
                            "suggestion": "Review strategy parameters or consider pausing",
                        }
                    )

            return optimization_suggestions

        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return {"error": str(e)}
