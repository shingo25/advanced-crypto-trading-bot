"""
高度なリスク管理システム

VaR計算、ストレステスト、動的リスク調整などの
高度なリスク管理機能を提供するAdvancedRiskManager
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .position_sizing import RiskManager

logger = logging.getLogger(__name__)


def norm_ppf(p: float) -> float:
    """標準正規分布のパーセンタイル点関数（scipy.stats.norm.ppfの代替）"""
    # Beasley-Springer-Moro algorithm の簡易版
    if p <= 0 or p >= 1:
        raise ValueError("p must be between 0 and 1")

    if p == 0.5:
        return 0.0

    # より正確な近似を使用
    if p < 0.5:
        # 下側
        q = np.sqrt(-2 * np.log(p))
        result = -(((2.30753 + q * 0.27061) / (1 + q * (0.99229 + q * 0.04481))) - q)
    else:
        # 上側
        q = np.sqrt(-2 * np.log(1 - p))
        result = ((2.30753 + q * 0.27061) / (1 + q * (0.99229 + q * 0.04481))) - q

    return result


def norm_pdf(x: float) -> float:
    """標準正規分布の確率密度関数（scipy.stats.norm.pdfの代替）"""
    return (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x**2)


class RiskLevel(Enum):
    """リスクレベル"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """アラートタイプ"""

    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    CONCENTRATION = "concentration"
    VAR_BREACH = "var_breach"
    CORRELATION = "correlation"
    DAILY_LOSS = "daily_loss"


@dataclass
class RiskAlert:
    """リスクアラート"""

    alert_type: AlertType
    risk_level: RiskLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    recommended_action: Optional[str] = None


@dataclass
class VaRResult:
    """VaR計算結果"""

    var_95: float  # 95% VaR
    var_99: float  # 99% VaR
    expected_shortfall_95: float  # 95% Expected Shortfall
    expected_shortfall_99: float  # 99% Expected Shortfall
    confidence_interval: Tuple[float, float]
    methodology: str
    observation_period: int


@dataclass
class StressTestResult:
    """ストレステスト結果"""

    scenario_name: str
    portfolio_impact: float  # ポートフォリオへの影響（%）
    strategy_impacts: Dict[str, float]  # 戦略別影響
    max_loss: float
    probability: float
    recovery_time_estimate: int  # 回復予想時間（日数）


@dataclass
class RiskMetrics:
    """リスクメトリクス"""

    total_var_95: float
    total_var_99: float
    max_drawdown: float
    current_drawdown: float
    volatility: float
    sharpe_ratio: float
    calmar_ratio: float
    concentration_risk: float
    correlation_risk: float
    leverage_ratio: float
    daily_var: float
    weekly_var: float
    monthly_var: float


class AdvancedRiskManager(RiskManager):
    """高度なリスク管理システム"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.risk_limits = {
            "max_portfolio_var_95": config.get("max_portfolio_var_95", 0.05),  # 5%
            "max_portfolio_var_99": config.get("max_portfolio_var_99", 0.08),  # 8%
            "max_daily_loss": config.get("max_daily_loss", 0.02),  # 2%
            "max_weekly_loss": config.get("max_weekly_loss", 0.05),  # 5%
            "max_monthly_loss": config.get("max_monthly_loss", 0.10),  # 10%
            "max_concentration": config.get("max_concentration", 0.30),  # 30%
            "max_correlation": config.get("max_correlation", 0.70),  # 70%
            "max_leverage": config.get("max_leverage", 2.0),  # 2x
            "min_liquidity_ratio": config.get("min_liquidity_ratio", 0.05),  # 5%
        }

        self.returns_history: List[float] = []
        self.price_history: Dict[str, List[float]] = {}
        self.risk_alerts: List[RiskAlert] = []
        self.stress_test_scenarios = self._initialize_stress_scenarios()

        # リスク計算パラメータ
        self.var_window = config.get("var_window", 252)  # 1年間
        self.correlation_window = config.get("correlation_window", 126)  # 6ヶ月

        logger.info("AdvancedRiskManager initialized")

    def _initialize_stress_scenarios(self) -> Dict[str, Dict[str, float]]:
        """ストレステストシナリオを初期化"""
        return {
            "market_crash": {
                "btc_drop": -0.30,  # 30%下落
                "eth_drop": -0.35,  # 35%下落
                "alt_drop": -0.50,  # 50%下落
                "volume_spike": 3.0,  # 3倍の出来高
                "volatility_spike": 2.5,  # 2.5倍のボラティリティ
            },
            "flash_crash": {
                "btc_drop": -0.20,  # 20%下落
                "eth_drop": -0.25,  # 25%下落
                "recovery_factor": 0.5,  # 50%回復
                "duration_hours": 2,  # 2時間で発生
            },
            "liquidity_crisis": {
                "spread_widening": 5.0,  # 5倍のスプレッド
                "volume_reduction": 0.3,  # 70%の出来高減少
                "slippage_factor": 2.0,  # 2倍のスリッページ
            },
            "regulatory_shock": {
                "general_drop": -0.15,  # 15%下落
                "volatility_increase": 1.8,  # 1.8倍のボラティリティ
                "correlation_increase": 0.2,  # 相関の増加
            },
        }

    def update_price_history(self, symbol: str, price: float, timestamp: datetime):
        """価格履歴を更新"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append(price)

        # 履歴長制限
        max_history = self.var_window * 2
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]

    def update_portfolio_returns(self, portfolio_return: float):
        """ポートフォリオリターンを更新"""
        self.returns_history.append(portfolio_return)

        # 履歴長制限
        max_history = self.var_window * 2
        if len(self.returns_history) > max_history:
            self.returns_history = self.returns_history[-max_history:]

    def calculate_var(
        self,
        returns: List[float],
        confidence_levels: List[float] = [0.95, 0.99],
        method: str = "historical",
    ) -> VaRResult:
        """VaR（Value at Risk）を計算"""
        try:
            if len(returns) < 30:
                return VaRResult(0, 0, 0, 0, (0, 0), method, len(returns))

            returns_array = np.array(returns)

            if method == "historical":
                # 履歴シミュレーション法
                var_95 = -np.percentile(returns_array, 5)
                var_99 = -np.percentile(returns_array, 1)

                # Expected Shortfall (Conditional VaR)
                es_95 = -np.mean(returns_array[returns_array <= -var_95])
                es_99 = -np.mean(returns_array[returns_array <= -var_99])

            elif method == "parametric":
                # パラメトリック法（正規分布仮定）
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)

                var_95 = -(mean_return + norm_ppf(0.05) * std_return)
                var_99 = -(mean_return + norm_ppf(0.01) * std_return)

                # Expected Shortfall
                es_95 = -(mean_return + std_return * norm_pdf(norm_ppf(0.05)) / 0.05)
                es_99 = -(mean_return + std_return * norm_pdf(norm_ppf(0.01)) / 0.01)

            elif method == "monte_carlo":
                # モンテカルロシミュレーション
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)

                # 10,000回のシミュレーション
                simulated_returns = np.random.normal(mean_return, std_return, 10000)

                var_95 = -np.percentile(simulated_returns, 5)
                var_99 = -np.percentile(simulated_returns, 1)

                es_95 = -np.mean(simulated_returns[simulated_returns <= -var_95])
                es_99 = -np.mean(simulated_returns[simulated_returns <= -var_99])

            else:
                raise ValueError(f"Unknown VaR method: {method}")

            # 信頼区間計算（ブートストラップ）
            bootstrap_vars = []
            for _ in range(1000):
                bootstrap_sample = np.random.choice(
                    returns_array, size=len(returns_array), replace=True
                )
                bootstrap_var = -np.percentile(bootstrap_sample, 5)
                bootstrap_vars.append(bootstrap_var)

            confidence_interval = (
                np.percentile(bootstrap_vars, 2.5),
                np.percentile(bootstrap_vars, 97.5),
            )

            return VaRResult(
                var_95=var_95,
                var_99=var_99,
                expected_shortfall_95=es_95,
                expected_shortfall_99=es_99,
                confidence_interval=confidence_interval,
                methodology=method,
                observation_period=len(returns),
            )

        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return VaRResult(0, 0, 0, 0, (0, 0), method, len(returns))

    def perform_stress_test(
        self, portfolio_positions: Dict[str, float], scenario_name: str = "market_crash"
    ) -> StressTestResult:
        """ストレステストを実行"""
        try:
            if scenario_name not in self.stress_test_scenarios:
                raise ValueError(f"Unknown stress test scenario: {scenario_name}")

            scenario = self.stress_test_scenarios[scenario_name]
            strategy_impacts = {}
            total_impact = 0.0

            for strategy, position_size in portfolio_positions.items():
                # 戦略別の影響を計算（簡略化）
                if "btc" in strategy.lower():
                    impact = scenario.get("btc_drop", -0.20) * position_size
                elif "eth" in strategy.lower():
                    impact = scenario.get("eth_drop", -0.25) * position_size
                else:
                    impact = scenario.get("general_drop", -0.15) * position_size

                strategy_impacts[strategy] = impact
                total_impact += impact

            # 最大損失計算
            max_loss = abs(min(strategy_impacts.values())) if strategy_impacts else 0

            # 回復時間推定（シナリオによる）
            if scenario_name == "flash_crash":
                recovery_time = 1  # 1日
            elif scenario_name == "market_crash":
                recovery_time = 30  # 30日
            elif scenario_name == "liquidity_crisis":
                recovery_time = 7  # 7日
            else:
                recovery_time = 14  # 2週間

            # 発生確率（簡略化）
            probability_map = {
                "market_crash": 0.05,  # 5%
                "flash_crash": 0.10,  # 10%
                "liquidity_crisis": 0.08,  # 8%
                "regulatory_shock": 0.15,  # 15%
            }

            return StressTestResult(
                scenario_name=scenario_name,
                portfolio_impact=total_impact,
                strategy_impacts=strategy_impacts,
                max_loss=max_loss,
                probability=probability_map.get(scenario_name, 0.10),
                recovery_time_estimate=recovery_time,
            )

        except Exception as e:
            logger.error(f"Error performing stress test: {e}")
            return StressTestResult(scenario_name, 0, {}, 0, 0, 0)

    def calculate_correlation_matrix(
        self, strategy_returns: Dict[str, List[float]]
    ) -> pd.DataFrame:
        """戦略間相関行列を計算"""
        try:
            if len(strategy_returns) < 2:
                return pd.DataFrame()

            # データ長を揃える
            min_length = min(len(returns) for returns in strategy_returns.values())
            if min_length < 30:  # 最低30観測
                return pd.DataFrame()

            aligned_returns = {
                strategy: returns[-min_length:]
                for strategy, returns in strategy_returns.items()
            }

            df = pd.DataFrame(aligned_returns)
            correlation_matrix = df.corr()

            return correlation_matrix

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()

    def calculate_portfolio_risk_metrics(
        self,
        portfolio_returns: List[float],
        strategy_returns: Dict[str, List[float]],
        portfolio_positions: Dict[str, float],
    ) -> RiskMetrics:
        """包括的なリスクメトリクスを計算"""
        try:
            # VaR計算
            var_result = self.calculate_var(portfolio_returns)

            # 基本統計
            returns_array = (
                np.array(portfolio_returns) if portfolio_returns else np.array([0])
            )

            volatility = (
                np.std(returns_array) * np.sqrt(252) if len(returns_array) > 1 else 0
            )
            mean_return = np.mean(returns_array) * 252 if len(returns_array) > 0 else 0

            # シャープレシオ（リスクフリーレート0と仮定）
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0

            # ドローダウン計算
            cumulative_returns = np.cumsum(returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
            current_drawdown = drawdowns[-1] if len(drawdowns) > 0 else 0

            # カルマー・レシオ
            calmar_ratio = mean_return / abs(max_drawdown) if max_drawdown != 0 else 0

            # 集中度リスク
            if portfolio_positions:
                position_values = list(portfolio_positions.values())
                total_position = sum(position_values)
                if total_position > 0:
                    weights = [pos / total_position for pos in position_values]
                    concentration_risk = max(weights)  # 最大ウェイト
                else:
                    concentration_risk = 0
            else:
                concentration_risk = 0

            # 相関リスク
            correlation_matrix = self.calculate_correlation_matrix(strategy_returns)
            if not correlation_matrix.empty:
                correlations = correlation_matrix.values
                # 対角成分を除外して最大相関を取得
                mask = ~np.eye(correlations.shape[0], dtype=bool)
                correlation_risk = (
                    np.max(np.abs(correlations[mask])) if mask.any() else 0
                )
            else:
                correlation_risk = 0

            # レバレッジ比率（簡略化）
            leverage_ratio = (
                sum(abs(pos) for pos in portfolio_positions.values())
                if portfolio_positions
                else 0
            )

            # 時間別VaR
            daily_var = var_result.var_95
            weekly_var = daily_var * np.sqrt(5)  # 週次
            monthly_var = daily_var * np.sqrt(21)  # 月次

            return RiskMetrics(
                total_var_95=var_result.var_95,
                total_var_99=var_result.var_99,
                max_drawdown=abs(max_drawdown),
                current_drawdown=abs(current_drawdown),
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                concentration_risk=concentration_risk,
                correlation_risk=correlation_risk,
                leverage_ratio=leverage_ratio,
                daily_var=daily_var,
                weekly_var=weekly_var,
                monthly_var=monthly_var,
            )

        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def check_risk_limits(
        self, risk_metrics: RiskMetrics, portfolio_positions: Dict[str, float]
    ) -> List[RiskAlert]:
        """リスク制限をチェックしてアラートを生成"""
        alerts = []

        try:
            # VaR制限チェック
            if risk_metrics.total_var_95 > self.risk_limits["max_portfolio_var_95"]:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.VAR_BREACH,
                        risk_level=RiskLevel.HIGH,
                        message="Portfolio VaR 95% exceeds limit",
                        current_value=risk_metrics.total_var_95,
                        threshold_value=self.risk_limits["max_portfolio_var_95"],
                        recommended_action="Reduce position sizes or hedge",
                    )
                )

            if risk_metrics.total_var_99 > self.risk_limits["max_portfolio_var_99"]:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.VAR_BREACH,
                        risk_level=RiskLevel.CRITICAL,
                        message="Portfolio VaR 99% exceeds limit",
                        current_value=risk_metrics.total_var_99,
                        threshold_value=self.risk_limits["max_portfolio_var_99"],
                        recommended_action="Immediately reduce exposure",
                    )
                )

            # ドローダウン制限チェック
            max_dd_limit = 0.15  # 15%
            if risk_metrics.current_drawdown > max_dd_limit:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.DRAWDOWN,
                        risk_level=RiskLevel.HIGH
                        if risk_metrics.current_drawdown < 0.20
                        else RiskLevel.CRITICAL,
                        message="Current drawdown exceeds limit",
                        current_value=risk_metrics.current_drawdown,
                        threshold_value=max_dd_limit,
                        recommended_action="Review and adjust strategy allocations",
                    )
                )

            # 集中度リスク
            if risk_metrics.concentration_risk > self.risk_limits["max_concentration"]:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.CONCENTRATION,
                        risk_level=RiskLevel.MEDIUM,
                        message="Portfolio concentration exceeds limit",
                        current_value=risk_metrics.concentration_risk,
                        threshold_value=self.risk_limits["max_concentration"],
                        recommended_action="Diversify positions across more strategies",
                    )
                )

            # 相関リスク
            if risk_metrics.correlation_risk > self.risk_limits["max_correlation"]:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.CORRELATION,
                        risk_level=RiskLevel.MEDIUM,
                        message="Strategy correlation exceeds limit",
                        current_value=risk_metrics.correlation_risk,
                        threshold_value=self.risk_limits["max_correlation"],
                        recommended_action="Reduce allocation to highly correlated strategies",
                    )
                )

            # ボラティリティ制限
            volatility_limit = 0.30  # 30%
            if risk_metrics.volatility > volatility_limit:
                alerts.append(
                    RiskAlert(
                        alert_type=AlertType.VOLATILITY,
                        risk_level=RiskLevel.HIGH,
                        message="Portfolio volatility exceeds limit",
                        current_value=risk_metrics.volatility,
                        threshold_value=volatility_limit,
                        recommended_action="Reduce position sizes or add stabilizing assets",
                    )
                )

            return alerts

        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return []

    def generate_risk_report(
        self,
        portfolio_returns: List[float],
        strategy_returns: Dict[str, List[float]],
        portfolio_positions: Dict[str, float],
    ) -> Dict[str, Any]:
        """包括的なリスクレポートを生成"""
        try:
            # リスクメトリクス計算
            risk_metrics = self.calculate_portfolio_risk_metrics(
                portfolio_returns, strategy_returns, portfolio_positions
            )

            # リスクアラート確認
            current_alerts = self.check_risk_limits(risk_metrics, portfolio_positions)

            # ストレステスト実行
            stress_tests = {}
            for scenario in self.stress_test_scenarios.keys():
                stress_tests[scenario] = self.perform_stress_test(
                    portfolio_positions, scenario
                )

            # VaR詳細計算
            var_results = {}
            for method in ["historical", "parametric", "monte_carlo"]:
                var_results[method] = self.calculate_var(
                    portfolio_returns, method=method
                )

            # 相関分析
            correlation_matrix = self.calculate_correlation_matrix(strategy_returns)

            return {
                "timestamp": datetime.now().isoformat(),
                "risk_metrics": {
                    "var_95": risk_metrics.total_var_95,
                    "var_99": risk_metrics.total_var_99,
                    "max_drawdown": risk_metrics.max_drawdown,
                    "current_drawdown": risk_metrics.current_drawdown,
                    "volatility": risk_metrics.volatility,
                    "sharpe_ratio": risk_metrics.sharpe_ratio,
                    "calmar_ratio": risk_metrics.calmar_ratio,
                    "concentration_risk": risk_metrics.concentration_risk,
                    "correlation_risk": risk_metrics.correlation_risk,
                    "leverage_ratio": risk_metrics.leverage_ratio,
                    "daily_var": risk_metrics.daily_var,
                    "weekly_var": risk_metrics.weekly_var,
                    "monthly_var": risk_metrics.monthly_var,
                },
                "risk_alerts": [
                    {
                        "type": alert.alert_type.value,
                        "level": alert.risk_level.value,
                        "message": alert.message,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold_value,
                        "action": alert.recommended_action,
                        "timestamp": alert.timestamp.isoformat(),
                    }
                    for alert in current_alerts
                ],
                "var_analysis": {
                    method: {
                        "var_95": result.var_95,
                        "var_99": result.var_99,
                        "expected_shortfall_95": result.expected_shortfall_95,
                        "expected_shortfall_99": result.expected_shortfall_99,
                        "confidence_interval": result.confidence_interval,
                        "observations": result.observation_period,
                    }
                    for method, result in var_results.items()
                },
                "stress_tests": {
                    scenario: {
                        "portfolio_impact": result.portfolio_impact,
                        "strategy_impacts": result.strategy_impacts,
                        "max_loss": result.max_loss,
                        "probability": result.probability,
                        "recovery_time": result.recovery_time_estimate,
                    }
                    for scenario, result in stress_tests.items()
                },
                "correlation_analysis": {
                    "matrix": correlation_matrix.to_dict()
                    if not correlation_matrix.empty
                    else {},
                    "max_correlation": float(correlation_matrix.abs().max().max())
                    if not correlation_matrix.empty
                    else 0,
                    "avg_correlation": float(correlation_matrix.abs().mean().mean())
                    if not correlation_matrix.empty
                    else 0,
                },
                "risk_limits": self.risk_limits,
                "recommendations": self._generate_risk_recommendations(
                    risk_metrics, current_alerts
                ),
            }

        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return {"error": str(e)}

    def _generate_risk_recommendations(
        self, risk_metrics: RiskMetrics, alerts: List[RiskAlert]
    ) -> List[str]:
        """リスク推奨事項を生成"""
        recommendations = []

        try:
            # 高リスクアラートベースの推奨
            high_risk_alerts = [
                a
                for a in alerts
                if a.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            ]

            if high_risk_alerts:
                recommendations.append(
                    "Immediate attention required: High/Critical risk alerts present"
                )

            # 具体的な推奨事項
            if risk_metrics.concentration_risk > 0.4:
                recommendations.append(
                    "Diversify portfolio: Reduce concentration in single strategies"
                )

            if risk_metrics.correlation_risk > 0.7:
                recommendations.append(
                    "Reduce correlation risk: Add uncorrelated strategies"
                )

            if risk_metrics.volatility > 0.25:
                recommendations.append(
                    "Reduce volatility: Consider position sizing adjustments"
                )

            if risk_metrics.sharpe_ratio < 0.5:
                recommendations.append(
                    "Improve risk-adjusted returns: Review strategy performance"
                )

            if risk_metrics.current_drawdown > 0.10:
                recommendations.append(
                    "Address drawdown: Consider defensive positioning"
                )

            if not recommendations:
                recommendations.append(
                    "Portfolio risk profile appears healthy - maintain current approach"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Unable to generate recommendations due to calculation error"]

    def get_dynamic_position_sizing(
        self,
        strategy_name: str,
        base_position_size: float,
        current_volatility: float,
        recent_performance: float,
    ) -> float:
        """動的ポジションサイジング"""
        try:
            adjusted_size = base_position_size

            # ボラティリティ調整
            if current_volatility > 0.20:  # 20%以上のボラティリティ
                volatility_factor = 0.20 / current_volatility
                adjusted_size *= volatility_factor

            # パフォーマンス調整
            if recent_performance < -0.05:  # 5%以上の損失
                performance_factor = max(0.5, 1 + recent_performance)  # 最大50%削減
                adjusted_size *= performance_factor
            elif recent_performance > 0.10:  # 10%以上の利益
                performance_factor = min(
                    1.2, 1 + recent_performance * 0.5
                )  # 最大20%増加
                adjusted_size *= performance_factor

            # 最小・最大制限
            min_size = base_position_size * 0.25  # 最低25%
            max_size = base_position_size * 2.0  # 最大200%

            adjusted_size = max(min_size, min(adjusted_size, max_size))

            logger.info(
                f"Dynamic position sizing for {strategy_name}: {base_position_size:.4f} -> {adjusted_size:.4f}"
            )
            return adjusted_size

        except Exception as e:
            logger.error(f"Error in dynamic position sizing: {e}")
            return base_position_size
