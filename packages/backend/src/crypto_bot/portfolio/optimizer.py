"""
ポートフォリオ最適化システム
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """最適化目的"""

    SHARPE_RATIO = "sharpe_ratio"
    MIN_VOLATILITY = "min_volatility"
    MAX_RETURN = "max_return"
    RISK_PARITY = "risk_parity"


@dataclass
class OptimizationConstraint:
    """最適化制約"""

    asset: str
    constraint_type: str  # 'min_weight', 'max_weight', 'exact_weight'
    value: float

    def is_satisfied(self, weight: float) -> bool:
        """制約が満たされているかチェック"""
        if self.constraint_type == "min_weight":
            return weight >= self.value
        elif self.constraint_type == "max_weight":
            return weight <= self.value
        elif self.constraint_type == "exact_weight":
            return abs(weight - self.value) < 0.001
        return True


@dataclass
class OptimizationResult:
    """最適化結果"""

    objective: OptimizationObjective
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_time: float
    constraints_satisfied: bool
    convergence_status: str

    def get_allocation_summary(self) -> Dict[str, Any]:
        """配分概要を取得"""
        return {
            "objective": self.objective.value,
            "total_weight": sum(self.weights.values()),
            "asset_count": len(self.weights),
            "expected_return": self.expected_return,
            "expected_volatility": self.expected_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "weights": self.weights,
            "constraints_satisfied": self.constraints_satisfied,
            "convergence_status": self.convergence_status,
        }


class PortfolioOptimizer:
    """ポートフォリオ最適化エンジン"""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.optimization_history: List[OptimizationResult] = []
        logger.info("PortfolioOptimizer initialized")

    def optimize(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        objective: OptimizationObjective = OptimizationObjective.SHARPE_RATIO,
        constraints: List[OptimizationConstraint] = None,
    ) -> OptimizationResult:
        """ポートフォリオを最適化"""

        start_time = datetime.now()

        # 制約を初期化
        if constraints is None:
            constraints = []

        # 基本制約（重みの合計が1）
        constraints.append(OptimizationConstraint("_sum", "exact_weight", 1.0))

        # 負の重みを禁止
        for asset in assets:
            constraints.append(OptimizationConstraint(asset, "min_weight", 0.0))

        # 最適化を実行
        if objective == OptimizationObjective.SHARPE_RATIO:
            result = self._optimize_sharpe_ratio(assets, expected_returns, covariance_matrix, constraints)
        elif objective == OptimizationObjective.MIN_VOLATILITY:
            result = self._optimize_min_volatility(assets, expected_returns, covariance_matrix, constraints)
        elif objective == OptimizationObjective.MAX_RETURN:
            result = self._optimize_max_return(assets, expected_returns, covariance_matrix, constraints)
        elif objective == OptimizationObjective.RISK_PARITY:
            result = self._optimize_risk_parity(assets, expected_returns, covariance_matrix, constraints)
        else:
            raise ValueError(f"Unknown optimization objective: {objective}")

        # 実行時間を記録
        optimization_time = (datetime.now() - start_time).total_seconds()
        result.optimization_time = optimization_time

        # 履歴に追加
        self.optimization_history.append(result)

        logger.info(f"Optimization completed in {optimization_time:.2f}s")
        return result

    def _optimize_sharpe_ratio(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: List[OptimizationConstraint],
    ) -> OptimizationResult:
        """シャープレシオを最大化"""

        # 簡易最適化（実際の実装では scipy.optimize を使用）
        best_weights = self._equal_weight_portfolio(assets)
        best_sharpe = self._calculate_sharpe_ratio(best_weights, expected_returns, covariance_matrix)

        # グリッドサーチによる近似最適化
        for iteration in range(100):
            # ランダムな重みを生成
            weights = self._generate_random_weights(assets, constraints)

            if weights is None:
                continue

            sharpe = self._calculate_sharpe_ratio(weights, expected_returns, covariance_matrix)

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = weights

        # 結果を作成
        portfolio_return = self._calculate_portfolio_return(best_weights, expected_returns)
        portfolio_volatility = self._calculate_portfolio_volatility(best_weights, covariance_matrix)

        return OptimizationResult(
            objective=OptimizationObjective.SHARPE_RATIO,
            weights=best_weights,
            expected_return=portfolio_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=best_sharpe,
            optimization_time=0.0,
            constraints_satisfied=self._check_constraints(best_weights, constraints),
            convergence_status="completed",
        )

    def _optimize_min_volatility(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: List[OptimizationConstraint],
    ) -> OptimizationResult:
        """ボラティリティを最小化"""

        best_weights = self._equal_weight_portfolio(assets)
        best_volatility = self._calculate_portfolio_volatility(best_weights, covariance_matrix)

        # グリッドサーチによる近似最適化
        for iteration in range(100):
            weights = self._generate_random_weights(assets, constraints)

            if weights is None:
                continue

            volatility = self._calculate_portfolio_volatility(weights, covariance_matrix)

            if volatility < best_volatility:
                best_volatility = volatility
                best_weights = weights

        # 結果を作成
        portfolio_return = self._calculate_portfolio_return(best_weights, expected_returns)
        sharpe_ratio = self._calculate_sharpe_ratio(best_weights, expected_returns, covariance_matrix)

        return OptimizationResult(
            objective=OptimizationObjective.MIN_VOLATILITY,
            weights=best_weights,
            expected_return=portfolio_return,
            expected_volatility=best_volatility,
            sharpe_ratio=sharpe_ratio,
            optimization_time=0.0,
            constraints_satisfied=self._check_constraints(best_weights, constraints),
            convergence_status="completed",
        )

    def _optimize_max_return(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: List[OptimizationConstraint],
    ) -> OptimizationResult:
        """リターンを最大化"""

        best_weights = self._equal_weight_portfolio(assets)
        best_return = self._calculate_portfolio_return(best_weights, expected_returns)

        # グリッドサーチによる近似最適化
        for iteration in range(100):
            weights = self._generate_random_weights(assets, constraints)

            if weights is None:
                continue

            portfolio_return = self._calculate_portfolio_return(weights, expected_returns)

            if portfolio_return > best_return:
                best_return = portfolio_return
                best_weights = weights

        # 結果を作成
        portfolio_volatility = self._calculate_portfolio_volatility(best_weights, covariance_matrix)
        sharpe_ratio = self._calculate_sharpe_ratio(best_weights, expected_returns, covariance_matrix)

        return OptimizationResult(
            objective=OptimizationObjective.MAX_RETURN,
            weights=best_weights,
            expected_return=best_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            optimization_time=0.0,
            constraints_satisfied=self._check_constraints(best_weights, constraints),
            convergence_status="completed",
        )

    def _optimize_risk_parity(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        constraints: List[OptimizationConstraint],
    ) -> OptimizationResult:
        """リスクパリティ最適化"""

        # 簡易リスクパリティ（逆ボラティリティ重み）
        asset_volatilities = {}
        for asset in assets:
            asset_volatilities[asset] = math.sqrt(covariance_matrix[asset][asset])

        # 逆ボラティリティの重みを計算
        inverse_volatilities = {asset: 1.0 / vol for asset, vol in asset_volatilities.items()}
        total_inverse_vol = sum(inverse_volatilities.values())

        weights = {asset: inv_vol / total_inverse_vol for asset, inv_vol in inverse_volatilities.items()}

        # 結果を作成
        portfolio_return = self._calculate_portfolio_return(weights, expected_returns)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, covariance_matrix)
        sharpe_ratio = self._calculate_sharpe_ratio(weights, expected_returns, covariance_matrix)

        return OptimizationResult(
            objective=OptimizationObjective.RISK_PARITY,
            weights=weights,
            expected_return=portfolio_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            optimization_time=0.0,
            constraints_satisfied=self._check_constraints(weights, constraints),
            convergence_status="completed",
        )

    def _equal_weight_portfolio(self, assets: List[str]) -> Dict[str, float]:
        """等重みポートフォリオを作成"""
        weight = 1.0 / len(assets)
        return {asset: weight for asset in assets}

    def _generate_random_weights(
        self, assets: List[str], constraints: List[OptimizationConstraint]
    ) -> Optional[Dict[str, float]]:
        """制約を満たすランダムな重みを生成"""
        import random

        # ランダムな重みを生成
        raw_weights = [random.random() for _ in assets]  # nosec B311
        total_weight = sum(raw_weights)

        # 正規化
        weights = {asset: weight / total_weight for asset, weight in zip(assets, raw_weights)}

        # 制約をチェック
        if self._check_constraints(weights, constraints):
            return weights

        return None

    def _check_constraints(self, weights: Dict[str, float], constraints: List[OptimizationConstraint]) -> bool:
        """制約が満たされているかチェック"""
        for constraint in constraints:
            if constraint.asset == "_sum":
                if not constraint.is_satisfied(sum(weights.values())):
                    return False
            elif constraint.asset in weights:
                if not constraint.is_satisfied(weights[constraint.asset]):
                    return False
        return True

    def _calculate_portfolio_return(self, weights: Dict[str, float], expected_returns: Dict[str, float]) -> float:
        """ポートフォリオの期待リターンを計算"""
        return sum(weights[asset] * expected_returns[asset] for asset in weights)

    def _calculate_portfolio_volatility(
        self, weights: Dict[str, float], covariance_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """ポートフォリオのボラティリティを計算"""
        variance = 0.0

        for asset1 in weights:
            for asset2 in weights:
                variance += weights[asset1] * weights[asset2] * covariance_matrix[asset1][asset2]

        return math.sqrt(variance)

    def _calculate_sharpe_ratio(
        self,
        weights: Dict[str, float],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
    ) -> float:
        """シャープレシオを計算"""
        portfolio_return = self._calculate_portfolio_return(weights, expected_returns)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, covariance_matrix)

        if portfolio_volatility == 0:
            return 0.0

        return (portfolio_return - self.risk_free_rate) / portfolio_volatility

    def generate_efficient_frontier(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        num_portfolios: int = 50,
    ) -> List[Dict[str, Any]]:
        """効率的フロンティアを生成"""

        frontier_portfolios = []

        # リターンの範囲を設定
        min_return = min(expected_returns.values())
        max_return = max(expected_returns.values())

        return_range = [
            min_return + (max_return - min_return) * i / (num_portfolios - 1) for i in range(num_portfolios)
        ]

        for target_return in return_range:
            # 目標リターンを制約として追加
            constraints = [OptimizationConstraint("_return", "exact_weight", target_return)]

            # 最小ボラティリティで最適化
            try:
                result = self._optimize_min_volatility_with_return_constraint(
                    assets,
                    expected_returns,
                    covariance_matrix,
                    target_return,
                    constraints,
                )

                frontier_portfolios.append(
                    {
                        "expected_return": result.expected_return,
                        "volatility": result.expected_volatility,
                        "sharpe_ratio": result.sharpe_ratio,
                        "weights": result.weights,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to optimize for return {target_return}: {e}")
                continue

        return frontier_portfolios

    def _optimize_min_volatility_with_return_constraint(
        self,
        assets: List[str],
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        target_return: float,
        constraints: List[OptimizationConstraint],
    ) -> OptimizationResult:
        """目標リターン制約付きの最小ボラティリティ最適化"""

        best_weights = self._equal_weight_portfolio(assets)
        best_volatility = float("inf")

        # グリッドサーチによる近似最適化
        for iteration in range(200):
            weights = self._generate_random_weights(assets, constraints)

            if weights is None:
                continue

            # リターン制約をチェック
            portfolio_return = self._calculate_portfolio_return(weights, expected_returns)
            if abs(portfolio_return - target_return) > 0.005:  # 0.5%の許容範囲
                continue

            volatility = self._calculate_portfolio_volatility(weights, covariance_matrix)

            if volatility < best_volatility:
                best_volatility = volatility
                best_weights = weights

        # 結果を作成
        portfolio_return = self._calculate_portfolio_return(best_weights, expected_returns)
        sharpe_ratio = self._calculate_sharpe_ratio(best_weights, expected_returns, covariance_matrix)

        return OptimizationResult(
            objective=OptimizationObjective.MIN_VOLATILITY,
            weights=best_weights,
            expected_return=portfolio_return,
            expected_volatility=best_volatility,
            sharpe_ratio=sharpe_ratio,
            optimization_time=0.0,
            constraints_satisfied=True,
            convergence_status="completed",
        )

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """最適化履歴を取得"""
        return [result.get_allocation_summary() for result in self.optimization_history]

    def clear_optimization_history(self):
        """最適化履歴をクリア"""
        self.optimization_history.clear()
        logger.info("Optimization history cleared")

    def compare_portfolios(self, results: List[OptimizationResult]) -> Dict[str, Any]:
        """複数のポートフォリオを比較"""

        comparison = {
            "portfolio_count": len(results),
            "best_sharpe": None,
            "best_return": None,
            "best_volatility": None,
            "portfolios": [],
        }

        best_sharpe_value = float("-inf")
        best_return_value = float("-inf")
        best_volatility_value = float("inf")

        for i, result in enumerate(results):
            portfolio_info = {
                "index": i,
                "objective": result.objective.value,
                "expected_return": result.expected_return,
                "volatility": result.expected_volatility,
                "sharpe_ratio": result.sharpe_ratio,
                "weights": result.weights,
            }

            comparison["portfolios"].append(portfolio_info)

            # 最適ポートフォリオを特定
            if result.sharpe_ratio > best_sharpe_value:
                best_sharpe_value = result.sharpe_ratio
                comparison["best_sharpe"] = portfolio_info

            if result.expected_return > best_return_value:
                best_return_value = result.expected_return
                comparison["best_return"] = portfolio_info

            if result.expected_volatility < best_volatility_value:
                best_volatility_value = result.expected_volatility
                comparison["best_volatility"] = portfolio_info

        return comparison
