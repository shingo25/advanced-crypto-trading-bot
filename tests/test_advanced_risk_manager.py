"""高度なリスク管理システムのテスト"""

import pytest
import numpy as np
from datetime import datetime

from src.backend.risk.advanced_risk_manager import (
    AdvancedRiskManager,
    RiskLevel,
    AlertType,
    RiskAlert,
    VaRResult,
    StressTestResult,
    RiskMetrics,
)


class TestAdvancedRiskManager:
    """高度なリスク管理システムのテスト"""

    @pytest.fixture
    def risk_config(self):
        """テスト用のリスク設定"""
        return {
            "max_portfolio_var_95": 0.05,
            "max_portfolio_var_99": 0.08,
            "max_daily_loss": 0.02,
            "max_weekly_loss": 0.05,
            "max_monthly_loss": 0.10,
            "max_concentration": 0.30,
            "max_correlation": 0.70,
            "max_leverage": 2.0,
            "var_window": 252,
            "correlation_window": 126,
            # 基本的なリスク管理設定
            "fixed_risk_per_trade": 0.02,
            "kelly_fraction_cap": 0.5,
            "target_volatility": 0.15,
            "max_position_size_pct": 0.1,
            "max_drawdown_per_strategy": 0.15,
        }

    @pytest.fixture
    def risk_manager(self, risk_config):
        """テスト用のリスク管理システム"""
        return AdvancedRiskManager(risk_config)

    @pytest.fixture
    def sample_returns(self):
        """サンプルリターンデータ"""
        np.random.seed(42)  # 再現性のため
        # 正規分布ベースのリターンデータ生成
        returns = np.random.normal(0.001, 0.02, 100)  # 平均0.1%、標準偏差2%
        return returns.tolist()

    @pytest.fixture
    def sample_strategy_returns(self):
        """サンプル戦略別リターンデータ"""
        np.random.seed(42)
        return {
            "RSI_Strategy": np.random.normal(0.0008, 0.018, 100).tolist(),
            "MACD_Strategy": np.random.normal(0.0012, 0.022, 100).tolist(),
            "BB_Strategy": np.random.normal(0.0005, 0.015, 100).tolist(),
        }

    @pytest.fixture
    def sample_portfolio_positions(self):
        """サンプルポートフォリオポジション"""
        return {"RSI_Strategy": 0.4, "MACD_Strategy": 0.35, "BB_Strategy": 0.25}

    def test_risk_manager_initialization(self, risk_manager):
        """リスク管理システムの初期化テスト"""
        assert risk_manager.risk_limits["max_portfolio_var_95"] == 0.05
        assert risk_manager.risk_limits["max_portfolio_var_99"] == 0.08
        assert risk_manager.risk_limits["max_daily_loss"] == 0.02
        assert risk_manager.risk_limits["max_concentration"] == 0.30

        assert len(risk_manager.returns_history) == 0
        assert len(risk_manager.price_history) == 0
        assert len(risk_manager.risk_alerts) == 0

        # ストレステストシナリオの確認
        assert "market_crash" in risk_manager.stress_test_scenarios
        assert "flash_crash" in risk_manager.stress_test_scenarios
        assert "liquidity_crisis" in risk_manager.stress_test_scenarios
        assert "regulatory_shock" in risk_manager.stress_test_scenarios

    def test_update_price_history(self, risk_manager):
        """価格履歴更新のテスト"""
        symbol = "BTCUSDT"
        price = 45000.0
        timestamp = datetime.now()

        risk_manager.update_price_history(symbol, price, timestamp)

        assert symbol in risk_manager.price_history
        assert len(risk_manager.price_history[symbol]) == 1
        assert risk_manager.price_history[symbol][0] == price

        # 複数回更新
        for i in range(10):
            risk_manager.update_price_history(symbol, price + i * 100, timestamp)

        assert len(risk_manager.price_history[symbol]) == 11  # 1 + 10

    def test_update_portfolio_returns(self, risk_manager):
        """ポートフォリオリターン更新のテスト"""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015]

        for ret in returns:
            risk_manager.update_portfolio_returns(ret)

        assert len(risk_manager.returns_history) == 5
        assert risk_manager.returns_history == returns

    def test_calculate_var_historical(self, risk_manager, sample_returns):
        """VaR計算（履歴シミュレーション法）のテスト"""
        var_result = risk_manager.calculate_var(sample_returns, method="historical")

        assert isinstance(var_result, VaRResult)
        assert var_result.methodology == "historical"
        assert var_result.observation_period == len(sample_returns)

        # VaR値の妥当性チェック
        assert 0 <= var_result.var_95 <= 0.2  # 0-20%の範囲
        assert 0 <= var_result.var_99 <= 0.2
        assert var_result.var_99 >= var_result.var_95  # 99% VaR >= 95% VaR

        # Expected Shortfallの妥当性チェック
        assert var_result.expected_shortfall_95 >= var_result.var_95
        assert var_result.expected_shortfall_99 >= var_result.var_99

        # 信頼区間の確認
        assert len(var_result.confidence_interval) == 2
        assert var_result.confidence_interval[0] <= var_result.confidence_interval[1]

    def test_calculate_var_parametric(self, risk_manager, sample_returns):
        """VaR計算（パラメトリック法）のテスト"""
        var_result = risk_manager.calculate_var(sample_returns, method="parametric")

        assert var_result.methodology == "parametric"
        # VaRは損失を表すため、通常は正の値ですが、
        # 平均リターンが高い場合、負の値（利益の可能性）になることもある
        assert isinstance(var_result.var_95, (int, float))
        assert isinstance(var_result.var_99, (float, int))
        # 99% VaRは95% VaRよりリスクが高い（絶対値が大きい）
        assert abs(var_result.var_99) >= abs(var_result.var_95)

    def test_calculate_var_monte_carlo(self, risk_manager, sample_returns):
        """VaR計算（モンテカルロ法）のテスト"""
        var_result = risk_manager.calculate_var(sample_returns, method="monte_carlo")

        assert var_result.methodology == "monte_carlo"
        assert var_result.var_95 > 0
        assert var_result.var_99 > 0
        assert var_result.var_99 >= var_result.var_95

    def test_calculate_var_insufficient_data(self, risk_manager):
        """データ不足時のVaR計算テスト"""
        insufficient_returns = [0.01, -0.005]  # 2つだけのデータ

        var_result = risk_manager.calculate_var(insufficient_returns)

        # データ不足の場合は0を返す
        assert var_result.var_95 == 0
        assert var_result.var_99 == 0
        assert var_result.expected_shortfall_95 == 0
        assert var_result.expected_shortfall_99 == 0

    def test_perform_stress_test_market_crash(
        self, risk_manager, sample_portfolio_positions
    ):
        """ストレステスト（市場クラッシュ）のテスト"""
        stress_result = risk_manager.perform_stress_test(
            sample_portfolio_positions, "market_crash"
        )

        assert isinstance(stress_result, StressTestResult)
        assert stress_result.scenario_name == "market_crash"
        assert stress_result.portfolio_impact < 0  # 負の影響
        assert len(stress_result.strategy_impacts) == len(sample_portfolio_positions)
        assert stress_result.probability > 0
        assert stress_result.recovery_time_estimate > 0

        # 各戦略への影響確認
        for strategy in sample_portfolio_positions.keys():
            assert strategy in stress_result.strategy_impacts
            assert stress_result.strategy_impacts[strategy] < 0  # 負の影響

    def test_perform_stress_test_flash_crash(
        self, risk_manager, sample_portfolio_positions
    ):
        """ストレステスト（フラッシュクラッシュ）のテスト"""
        stress_result = risk_manager.perform_stress_test(
            sample_portfolio_positions, "flash_crash"
        )

        assert stress_result.scenario_name == "flash_crash"
        assert stress_result.recovery_time_estimate < 10  # 短期回復

    def test_calculate_correlation_matrix(self, risk_manager, sample_strategy_returns):
        """相関行列計算のテスト"""
        correlation_matrix = risk_manager.calculate_correlation_matrix(
            sample_strategy_returns
        )

        assert not correlation_matrix.empty
        assert correlation_matrix.shape == (3, 3)  # 3戦略なので3x3

        # 対角成分は1（自己相関）
        for strategy in sample_strategy_returns.keys():
            assert abs(correlation_matrix.loc[strategy, strategy] - 1.0) < 0.001

        # 相関値は-1から1の範囲
        for col in correlation_matrix.columns:
            for idx in correlation_matrix.index:
                corr_value = correlation_matrix.loc[idx, col]
                assert -1 <= corr_value <= 1

    def test_calculate_correlation_matrix_insufficient_data(self, risk_manager):
        """データ不足時の相関行列計算テスト"""
        insufficient_data = {
            "Strategy_A": [0.01, -0.005],  # 2つだけのデータ
            "Strategy_B": [0.02, 0.001],
        }

        correlation_matrix = risk_manager.calculate_correlation_matrix(
            insufficient_data
        )
        assert correlation_matrix.empty  # データ不足時は空のDataFrame

    def test_calculate_portfolio_risk_metrics(
        self,
        risk_manager,
        sample_returns,
        sample_strategy_returns,
        sample_portfolio_positions,
    ):
        """ポートフォリオリスクメトリクス計算のテスト"""
        risk_metrics = risk_manager.calculate_portfolio_risk_metrics(
            sample_returns, sample_strategy_returns, sample_portfolio_positions
        )

        assert isinstance(risk_metrics, RiskMetrics)

        # 基本メトリクスの妥当性チェック
        assert risk_metrics.total_var_95 >= 0
        assert risk_metrics.total_var_99 >= risk_metrics.total_var_95
        assert 0 <= risk_metrics.max_drawdown <= 1
        assert 0 <= risk_metrics.current_drawdown <= 1
        assert risk_metrics.volatility >= 0

        # 集中度リスク（最大ウェイト）
        assert 0 <= risk_metrics.concentration_risk <= 1
        expected_max_weight = max(sample_portfolio_positions.values())
        assert abs(risk_metrics.concentration_risk - expected_max_weight) < 0.01

        # 相関リスク
        assert 0 <= risk_metrics.correlation_risk <= 1

        # レバレッジ比率
        expected_leverage = sum(abs(pos) for pos in sample_portfolio_positions.values())
        assert abs(risk_metrics.leverage_ratio - expected_leverage) < 0.01

        # 時間別VaR
        assert risk_metrics.weekly_var >= risk_metrics.daily_var
        assert risk_metrics.monthly_var >= risk_metrics.weekly_var

    def test_check_risk_limits_normal(self, risk_manager):
        """正常範囲内でのリスク制限チェックテスト"""
        # 正常範囲内のリスクメトリクス
        normal_metrics = RiskMetrics(
            total_var_95=0.03,  # 制限内（5%以下）
            total_var_99=0.06,  # 制限内（8%以下）
            max_drawdown=0.08,
            current_drawdown=0.05,
            volatility=0.20,
            sharpe_ratio=1.2,
            calmar_ratio=2.0,
            concentration_risk=0.25,  # 制限内（30%以下）
            correlation_risk=0.60,  # 制限内（70%以下）
            leverage_ratio=1.5,
            daily_var=0.03,
            weekly_var=0.07,
            monthly_var=0.15,
        )

        positions = {"Strategy_A": 0.6, "Strategy_B": 0.4}
        alerts = risk_manager.check_risk_limits(normal_metrics, positions)

        # 正常範囲内なのでアラートは少ないはず
        assert len(alerts) <= 2  # ボラティリティのみ警告の可能性

    def test_check_risk_limits_violations(self, risk_manager):
        """リスク制限違反時のアラートテスト"""
        # 制限違反のリスクメトリクス
        violation_metrics = RiskMetrics(
            total_var_95=0.08,  # 制限超過（5%超）
            total_var_99=0.12,  # 制限超過（8%超）
            max_drawdown=0.25,
            current_drawdown=0.20,  # 制限超過（15%超）
            volatility=0.35,  # 制限超過（30%超）
            sharpe_ratio=0.3,
            calmar_ratio=1.0,
            concentration_risk=0.45,  # 制限超過（30%超）
            correlation_risk=0.80,  # 制限超過（70%超）
            leverage_ratio=2.5,
            daily_var=0.08,
            weekly_var=0.18,
            monthly_var=0.35,
        )

        positions = {"Strategy_A": 0.8, "Strategy_B": 0.2}
        alerts = risk_manager.check_risk_limits(violation_metrics, positions)

        # 複数の制限違反があるはず
        assert len(alerts) >= 5

        # 特定のアラートタイプの確認
        alert_types = [alert.alert_type for alert in alerts]
        assert AlertType.VAR_BREACH in alert_types
        assert AlertType.DRAWDOWN in alert_types
        assert AlertType.CONCENTRATION in alert_types
        assert AlertType.CORRELATION in alert_types
        assert AlertType.VOLATILITY in alert_types

        # クリティカルレベルのアラート確認
        critical_alerts = [
            alert for alert in alerts if alert.risk_level == RiskLevel.CRITICAL
        ]
        assert len(critical_alerts) >= 1  # VaR 99%違反はクリティカル

    def test_generate_risk_report(
        self,
        risk_manager,
        sample_returns,
        sample_strategy_returns,
        sample_portfolio_positions,
    ):
        """リスクレポート生成のテスト"""
        # 履歴データを設定
        risk_manager.returns_history = sample_returns

        report = risk_manager.generate_risk_report(
            sample_returns, sample_strategy_returns, sample_portfolio_positions
        )

        # レポート構造の確認
        assert "timestamp" in report
        assert "risk_metrics" in report
        assert "risk_alerts" in report
        assert "var_analysis" in report
        assert "stress_tests" in report
        assert "correlation_analysis" in report
        assert "risk_limits" in report
        assert "recommendations" in report

        # リスクメトリクスの確認
        metrics = report["risk_metrics"]
        assert "var_95" in metrics
        assert "var_99" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics

        # VaR分析の確認
        var_analysis = report["var_analysis"]
        assert "historical" in var_analysis
        assert "parametric" in var_analysis
        assert "monte_carlo" in var_analysis

        # ストレステストの確認
        stress_tests = report["stress_tests"]
        assert "market_crash" in stress_tests
        assert "flash_crash" in stress_tests
        assert "liquidity_crisis" in stress_tests
        assert "regulatory_shock" in stress_tests

        # 相関分析の確認
        correlation_analysis = report["correlation_analysis"]
        assert "matrix" in correlation_analysis
        assert "max_correlation" in correlation_analysis
        assert "avg_correlation" in correlation_analysis

        # 推奨事項の確認
        recommendations = report["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_dynamic_position_sizing_normal(self, risk_manager):
        """通常時の動的ポジションサイジングテスト"""
        strategy_name = "Test_Strategy"
        base_size = 0.10
        normal_volatility = 0.15
        normal_performance = 0.02  # 2%の利益

        adjusted_size = risk_manager.get_dynamic_position_sizing(
            strategy_name, base_size, normal_volatility, normal_performance
        )

        # 通常時は大きな調整は行われない
        assert 0.05 <= adjusted_size <= 0.20  # 基本サイズの50%-200%の範囲
        assert adjusted_size >= base_size * 1.0  # 少し増加する可能性

    def test_dynamic_position_sizing_high_volatility(self, risk_manager):
        """高ボラティリティ時の動的ポジションサイジングテスト"""
        strategy_name = "Test_Strategy"
        base_size = 0.10
        high_volatility = 0.30  # 30%の高ボラティリティ
        normal_performance = 0.01

        adjusted_size = risk_manager.get_dynamic_position_sizing(
            strategy_name, base_size, high_volatility, normal_performance
        )

        # 高ボラティリティ時はサイズが削減される
        assert adjusted_size < base_size
        expected_reduction = 0.20 / high_volatility
        expected_size = base_size * expected_reduction
        assert abs(adjusted_size - expected_size) < 0.01

    def test_dynamic_position_sizing_poor_performance(self, risk_manager):
        """悪いパフォーマンス時の動的ポジションサイジングテスト"""
        strategy_name = "Test_Strategy"
        base_size = 0.10
        normal_volatility = 0.15
        poor_performance = -0.08  # 8%の損失

        adjusted_size = risk_manager.get_dynamic_position_sizing(
            strategy_name, base_size, normal_volatility, poor_performance
        )

        # 悪いパフォーマンス時はサイズが削減される
        assert adjusted_size < base_size
        assert adjusted_size >= base_size * 0.25  # 最低25%は保持

    def test_dynamic_position_sizing_good_performance(self, risk_manager):
        """良いパフォーマンス時の動的ポジションサイジングテスト"""
        strategy_name = "Test_Strategy"
        base_size = 0.10
        normal_volatility = 0.15
        good_performance = 0.15  # 15%の利益

        adjusted_size = risk_manager.get_dynamic_position_sizing(
            strategy_name, base_size, normal_volatility, good_performance
        )

        # 良いパフォーマンス時はサイズが増加される
        assert adjusted_size > base_size
        assert adjusted_size <= base_size * 2.0  # 最大200%まで

    def test_risk_recommendations_generation(self, risk_manager):
        """リスク推奨事項生成のテスト"""
        # 問題のあるリスクメトリクス
        problematic_metrics = RiskMetrics(
            total_var_95=0.07,  # 高い
            total_var_99=0.10,  # 高い
            max_drawdown=0.20,  # 高い
            current_drawdown=0.15,  # 高い
            volatility=0.30,  # 高い
            sharpe_ratio=0.3,  # 低い
            calmar_ratio=1.0,
            concentration_risk=0.45,  # 高い
            correlation_risk=0.80,  # 高い
            leverage_ratio=2.5,
            daily_var=0.07,
            weekly_var=0.16,
            monthly_var=0.35,
        )

        # 高リスクアラート
        alerts = [
            RiskAlert(AlertType.VAR_BREACH, RiskLevel.HIGH, "High VaR"),
            RiskAlert(
                AlertType.CONCENTRATION, RiskLevel.CRITICAL, "High concentration"
            ),
        ]

        recommendations = risk_manager._generate_risk_recommendations(
            problematic_metrics, alerts
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # 具体的な推奨事項の確認
        recommendation_text = " ".join(recommendations).lower()
        assert (
            "diversify" in recommendation_text or "concentration" in recommendation_text
        )
        assert (
            "correlation" in recommendation_text or "volatility" in recommendation_text
        )


class TestAdvancedRiskManagerIntegration:
    """高度なリスク管理システムの統合テスト"""

    def test_full_risk_management_workflow(self):
        """リスク管理の全ワークフローテスト"""
        # 設定
        config = {
            "max_portfolio_var_95": 0.05,
            "max_portfolio_var_99": 0.08,
            "max_daily_loss": 0.02,
            "max_concentration": 0.30,
            "max_correlation": 0.70,
            "fixed_risk_per_trade": 0.02,
            "max_position_size_pct": 0.1,
        }

        risk_manager = AdvancedRiskManager(config)

        # 段階的にデータを追加
        portfolio_returns = []
        strategy_returns = {"RSI": [], "MACD": [], "BB": []}

        np.random.seed(42)
        for i in range(100):
            # ポートフォリオリターン
            portfolio_ret = np.random.normal(0.001, 0.02)
            portfolio_returns.append(portfolio_ret)
            risk_manager.update_portfolio_returns(portfolio_ret)

            # 戦略別リターン
            for strategy in strategy_returns.keys():
                strategy_ret = np.random.normal(0.0008, 0.018)
                strategy_returns[strategy].append(strategy_ret)

            # 価格履歴の更新
            price = 45000 + i * 100 + np.random.normal(0, 200)
            risk_manager.update_price_history("BTCUSDT", price, datetime.now())

        # ポートフォリオポジション
        positions = {"RSI": 0.4, "MACD": 0.35, "BB": 0.25}

        # リスクメトリクス計算
        risk_metrics = risk_manager.calculate_portfolio_risk_metrics(
            portfolio_returns, strategy_returns, positions
        )

        # リスク制限チェック
        alerts = risk_manager.check_risk_limits(risk_metrics, positions)

        # VaR計算
        var_result = risk_manager.calculate_var(portfolio_returns)

        # ストレステスト
        stress_result = risk_manager.perform_stress_test(positions, "market_crash")

        # 相関分析
        correlation_matrix = risk_manager.calculate_correlation_matrix(strategy_returns)

        # 動的ポジションサイジング
        adjusted_size = risk_manager.get_dynamic_position_sizing(
            "RSI", 0.10, 0.18, 0.02
        )

        # 包括的レポート生成
        report = risk_manager.generate_risk_report(
            portfolio_returns, strategy_returns, positions
        )

        # 結果の妥当性確認
        assert isinstance(risk_metrics, RiskMetrics)
        assert isinstance(alerts, list)
        assert isinstance(var_result, VaRResult)
        assert isinstance(stress_result, StressTestResult)
        assert not correlation_matrix.empty
        assert 0.02 <= adjusted_size <= 0.20
        assert "risk_metrics" in report
        assert "recommendations" in report

        # データが蓄積されていることを確認
        assert len(risk_manager.returns_history) == 100
        assert "BTCUSDT" in risk_manager.price_history
        assert len(risk_manager.price_history["BTCUSDT"]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
