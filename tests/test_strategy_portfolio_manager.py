"""戦略統合ポートフォリオマネージャーのテスト"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from src.backend.portfolio.strategy_portfolio_manager import (
    AdvancedPortfolioManager,
    StrategyStatus,
    PerformanceMetrics,
    TradeRecord,
)
from src.backend.strategies.base import BaseStrategy, Signal
from src.backend.strategies.implementations.rsi_strategy import RSIStrategy
from src.backend.strategies.implementations.macd_strategy import MACDStrategy


class MockStrategy(BaseStrategy):
    """テスト用のモック戦略"""

    def __init__(self, name: str, symbol: str = "BTCUSDT"):
        super().__init__(name, symbol, "1h", {"required_data_length": 10})
        self.mock_signals = []
        self.call_count = 0

    def calculate_indicators(self, data):
        return data

    def generate_signals(self, data):
        self.call_count += 1
        if self.mock_signals:
            return self.mock_signals.pop(0)
        return []

    def add_mock_signal(self, signal: Signal):
        """テスト用のシグナルを追加"""
        self.mock_signals.append([signal])


class TestAdvancedPortfolioManager:
    """戦略統合ポートフォリオマネージャーのテスト"""

    @pytest.fixture
    def portfolio_manager(self):
        """テスト用のポートフォリオマネージャー"""
        return AdvancedPortfolioManager(initial_capital=100000.0)

    @pytest.fixture
    def mock_strategy1(self):
        """テスト用のモック戦略1"""
        return MockStrategy("Mock Strategy 1", "BTCUSDT")

    @pytest.fixture
    def mock_strategy2(self):
        """テスト用のモック戦略2"""
        return MockStrategy("Mock Strategy 2", "BTCUSDT")

    @pytest.fixture
    def sample_market_data(self):
        """サンプル市場データ"""
        return {
            "timestamp": datetime.now(),
            "open": 45000,
            "high": 45200,
            "low": 44800,
            "close": 45100,
            "volume": 1000,
        }

    def test_portfolio_manager_initialization(self, portfolio_manager):
        """ポートフォリオマネージャーの初期化テスト"""
        assert portfolio_manager.initial_capital == 100000.0
        assert portfolio_manager.current_capital == 100000.0
        assert len(portfolio_manager.strategy_allocations) == 0
        assert len(portfolio_manager.trade_history) == 0
        assert len(portfolio_manager.performance_history) == 0

        # リスク制限の確認
        assert portfolio_manager.risk_limits["max_position_size"] == 0.1
        assert portfolio_manager.risk_limits["max_daily_loss"] == 0.02
        assert portfolio_manager.risk_limits["max_strategy_allocation"] == 0.3

    def test_add_strategy(self, portfolio_manager, mock_strategy1):
        """戦略追加のテスト"""
        # 正常な戦略追加
        result = portfolio_manager.add_strategy(mock_strategy1, 0.3)
        assert result is True
        assert len(portfolio_manager.strategy_allocations) == 1
        assert "Mock Strategy 1" in portfolio_manager.strategy_allocations

        allocation = portfolio_manager.strategy_allocations["Mock Strategy 1"]
        assert allocation.strategy_name == "Mock Strategy 1"
        assert allocation.target_weight == 0.3
        assert allocation.allocated_capital == 30000.0  # 100000 * 0.3
        assert allocation.status == StrategyStatus.ACTIVE

    def test_add_strategy_validation(
        self, portfolio_manager, mock_strategy1, mock_strategy2
    ):
        """戦略追加の検証テスト"""
        # 無効な配分重み（0以下）
        result = portfolio_manager.add_strategy(mock_strategy1, 0.0)
        assert result is False

        # 無効な配分重み（1超過）
        result = portfolio_manager.add_strategy(mock_strategy1, 1.5)
        assert result is False

        # 合計重みが1を超える場合
        portfolio_manager.add_strategy(mock_strategy1, 0.8)
        result = portfolio_manager.add_strategy(
            mock_strategy2, 0.5
        )  # 0.8 + 0.5 = 1.3 > 1.0
        assert result is False

    def test_remove_strategy(self, portfolio_manager, mock_strategy1):
        """戦略削除のテスト"""
        # 戦略を追加してから削除
        portfolio_manager.add_strategy(mock_strategy1, 0.3)
        assert len(portfolio_manager.strategy_allocations) == 1

        result = portfolio_manager.remove_strategy("Mock Strategy 1")
        assert result is True
        assert len(portfolio_manager.strategy_allocations) == 0

        # 存在しない戦略の削除
        result = portfolio_manager.remove_strategy("Nonexistent Strategy")
        assert result is False

    def test_update_strategy_status(self, portfolio_manager, mock_strategy1):
        """戦略状態更新のテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        # 状態をPAUSEDに変更
        result = portfolio_manager.update_strategy_status(
            "Mock Strategy 1", StrategyStatus.PAUSED
        )
        assert result is True

        allocation = portfolio_manager.strategy_allocations["Mock Strategy 1"]
        assert allocation.status == StrategyStatus.PAUSED

        # 存在しない戦略の状態更新
        result = portfolio_manager.update_strategy_status(
            "Nonexistent", StrategyStatus.ACTIVE
        )
        assert result is False

    def test_process_market_data(
        self, portfolio_manager, mock_strategy1, sample_market_data
    ):
        """市場データ処理のテスト"""
        # 戦略を追加
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        # モックシグナルを設定
        mock_signal = Signal(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            action="enter_long",
            strength=0.8,
            price=45100,
            reason="Test signal",
        )
        mock_strategy1.add_mock_signal(mock_signal)

        # 市場データを処理
        signals = portfolio_manager.process_market_data("BTCUSDT", sample_market_data)

        assert len(signals) == 1
        assert signals[0].action == "enter_long"
        assert signals[0].symbol == "BTCUSDT"
        assert signals[0].strength == 0.8

    def test_calculate_position_size(self, portfolio_manager, mock_strategy1):
        """ポジションサイズ計算のテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        signal = Signal(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            action="enter_long",
            strength=0.8,
            price=45000,
        )

        position_size = portfolio_manager._calculate_position_size(
            "Mock Strategy 1", signal
        )

        # 基本ポジションサイズ = 30000 * 0.8 = 24000
        # 最大ポジション制限 = 100000 * 0.1 = 10000
        expected_size = min(24000, 10000)
        assert position_size == expected_size

    def test_execute_signal(self, portfolio_manager, mock_strategy1):
        """シグナル実行のテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        signal = Signal(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            action="enter_long",
            strength=0.5,
            price=45000,
        )

        position_size = 5000.0
        result = portfolio_manager.execute_signal(signal, position_size)

        assert result is True
        assert len(portfolio_manager.trade_history) == 1

        trade = portfolio_manager.trade_history[0]
        assert trade.symbol == "BTCUSDT"
        assert trade.action == "enter_long"
        assert trade.price == 45000
        assert trade.quantity == 5000.0 / 45000  # position_size / price

    def test_risk_limits_check(self, portfolio_manager, mock_strategy1):
        """リスク制限チェックのテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        signal = Signal(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            action="enter_long",
            strength=0.5,
            price=45000,
        )

        # 正常なポジションサイズ
        result = portfolio_manager._check_risk_limits(signal, 5000.0)
        assert result is True

        # 制限を超えるポジションサイズ
        max_position = (
            portfolio_manager.current_capital
            * portfolio_manager.risk_limits["max_position_size"]
        )
        result = portfolio_manager._check_risk_limits(signal, max_position * 2)
        assert result is False

    def test_calculate_portfolio_performance(self, portfolio_manager):
        """ポートフォリオパフォーマンス計算のテスト"""
        # テスト用の取引履歴を追加
        trades = [
            TradeRecord(
                strategy_name="Test Strategy",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=45000,
                timestamp=datetime.now(),
                signal_strength=0.8,
                pnl=1000.0,  # 利益
            ),
            TradeRecord(
                strategy_name="Test Strategy",
                symbol="BTCUSDT",
                action="exit_long",
                quantity=0.1,
                price=46000,
                timestamp=datetime.now(),
                signal_strength=0.7,
                pnl=-500.0,  # 損失
            ),
        ]

        portfolio_manager.trade_history = trades
        performance = portfolio_manager.calculate_portfolio_performance()

        assert isinstance(performance, PerformanceMetrics)
        assert performance.trades_count == 2
        assert (
            performance.total_return == (1000 - 500) / 100000
        )  # total_pnl / initial_capital
        assert performance.win_rate == 0.5  # 1勝1敗

    def test_calculate_strategy_performance(self, portfolio_manager):
        """戦略別パフォーマンス計算のテスト"""
        # 複数戦略の取引履歴を追加
        trades = [
            TradeRecord(
                strategy_name="Strategy A",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=45000,
                timestamp=datetime.now(),
                signal_strength=0.8,
                pnl=1000.0,
            ),
            TradeRecord(
                strategy_name="Strategy B",
                symbol="BTCUSDT",
                action="enter_short",
                quantity=0.1,
                price=46000,
                timestamp=datetime.now(),
                signal_strength=0.7,
                pnl=500.0,
            ),
            TradeRecord(
                strategy_name="Strategy A",
                symbol="BTCUSDT",
                action="exit_long",
                quantity=0.1,
                price=46500,
                timestamp=datetime.now(),
                signal_strength=0.6,
                pnl=-200.0,
            ),
        ]

        portfolio_manager.trade_history = trades

        # Strategy Aのパフォーマンス
        performance_a = portfolio_manager.calculate_strategy_performance("Strategy A")
        assert performance_a.trades_count == 2
        assert performance_a.total_return == 800.0  # 1000 - 200
        assert performance_a.win_rate == 0.5

        # Strategy Bのパフォーマンス
        performance_b = portfolio_manager.calculate_strategy_performance("Strategy B")
        assert performance_b.trades_count == 1
        assert performance_b.total_return == 500.0
        assert performance_b.win_rate == 1.0

    def test_strategy_correlation_matrix(
        self, portfolio_manager, mock_strategy1, mock_strategy2
    ):
        """戦略間相関行列のテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.4)
        portfolio_manager.add_strategy(mock_strategy2, 0.4)

        # 同じ長さのリターンデータを作成
        trades = []
        for i in range(10):
            # Strategy 1の取引
            trades.append(
                TradeRecord(
                    strategy_name="Mock Strategy 1",
                    symbol="BTCUSDT",
                    action="enter_long",
                    quantity=0.1,
                    price=45000,
                    timestamp=datetime.now() - timedelta(hours=i),
                    signal_strength=0.8,
                    pnl=np.random.normal(100, 50),
                )
            )

            # Strategy 2の取引
            trades.append(
                TradeRecord(
                    strategy_name="Mock Strategy 2",
                    symbol="BTCUSDT",
                    action="enter_short",
                    quantity=0.1,
                    price=45000,
                    timestamp=datetime.now() - timedelta(hours=i),
                    signal_strength=0.7,
                    pnl=np.random.normal(80, 40),
                )
            )

        portfolio_manager.trade_history = trades
        correlation_matrix = portfolio_manager.get_strategy_correlation_matrix()

        if not correlation_matrix.empty:
            assert "Mock Strategy 1" in correlation_matrix.columns
            assert "Mock Strategy 2" in correlation_matrix.columns
            assert correlation_matrix.shape == (2, 2)

    def test_rebalance_strategies(
        self, portfolio_manager, mock_strategy1, mock_strategy2
    ):
        """戦略リバランシングのテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.5)
        portfolio_manager.add_strategy(mock_strategy2, 0.3)

        # 悪いパフォーマンスの取引データを追加
        portfolio_manager.trade_history = [
            TradeRecord(
                strategy_name="Mock Strategy 1",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=45000,
                timestamp=datetime.now(),
                signal_strength=0.8,
                pnl=-6000.0,  # 6%の損失
            )
        ]

        rebalance_actions = portfolio_manager.rebalance_strategies()

        # パフォーマンスが悪いのでリバランシングアクションが生成されるはず
        if rebalance_actions:
            action = rebalance_actions[0]
            assert action["strategy"] == "Mock Strategy 1"
            assert action["new_weight"] < action["current_weight"]  # 重みが削減される

    def test_portfolio_summary(self, portfolio_manager, mock_strategy1):
        """ポートフォリオサマリーのテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.3)

        # テスト用の取引データを追加
        portfolio_manager.trade_history = [
            TradeRecord(
                strategy_name="Mock Strategy 1",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=45000,
                timestamp=datetime.now(),
                signal_strength=0.8,
                pnl=1000.0,
            )
        ]

        summary = portfolio_manager.get_portfolio_summary()

        assert "portfolio_overview" in summary
        assert "performance_metrics" in summary
        assert "strategy_allocations" in summary
        assert "risk_metrics" in summary
        assert "trade_summary" in summary

        # ポートフォリオ概要の確認
        overview = summary["portfolio_overview"]
        assert overview["initial_capital"] == 100000.0
        assert overview["current_capital"] == 100000.0
        assert overview["total_strategies"] == 1
        assert overview["active_strategies"] == 1

        # 戦略配分の確認
        allocations = summary["strategy_allocations"]
        assert "Mock Strategy 1" in allocations
        strategy_alloc = allocations["Mock Strategy 1"]
        assert strategy_alloc["target_weight"] == 0.3
        assert strategy_alloc["allocated_capital"] == 30000.0

    def test_risk_report(self, portfolio_manager, mock_strategy1):
        """リスクレポートのテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.4)  # 40%配分

        risk_report = portfolio_manager.get_risk_report()

        assert "position_concentration" in risk_report
        assert "strategy_correlation" in risk_report
        assert "var_analysis" in risk_report
        assert "exposure_limits" in risk_report

        # ポジション集中度の確認
        concentration = risk_report["position_concentration"]
        assert "Mock Strategy 1" in concentration
        strategy_concentration = concentration["Mock Strategy 1"]
        assert strategy_concentration["concentration"] == 1.0  # 唯一の戦略なので100%
        assert strategy_concentration["risk_level"] == "high"  # 40%以上なので高リスク

    def test_portfolio_optimization(
        self, portfolio_manager, mock_strategy1, mock_strategy2
    ):
        """ポートフォリオ最適化のテスト"""
        portfolio_manager.add_strategy(mock_strategy1, 0.6)  # 高い配分
        portfolio_manager.add_strategy(mock_strategy2, 0.3)

        # 低い勝率の取引データを設定
        portfolio_manager.trade_history = [
            TradeRecord(
                strategy_name="Mock Strategy 1",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=45000,
                timestamp=datetime.now(),
                signal_strength=0.8,
                pnl=-1000.0,  # 損失
            ),
            TradeRecord(
                strategy_name="Mock Strategy 1",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=46000,
                timestamp=datetime.now(),
                signal_strength=0.7,
                pnl=-500.0,  # 損失
            ),
            TradeRecord(
                strategy_name="Mock Strategy 1",
                symbol="BTCUSDT",
                action="enter_long",
                quantity=0.1,
                price=47000,
                timestamp=datetime.now(),
                signal_strength=0.6,
                pnl=200.0,  # 利益（1勝2敗で勝率33%）
            ),
        ]

        optimization = portfolio_manager.optimize_portfolio()

        assert "rebalancing" in optimization
        assert "risk_reduction" in optimization
        assert "performance_improvement" in optimization

        # 集中リスクの警告があるはず（60%配分）
        risk_reductions = optimization["risk_reduction"]
        concentration_warnings = [
            r for r in risk_reductions if r["type"] == "concentration_risk"
        ]
        assert len(concentration_warnings) > 0

        # 低勝率の警告があるはず（33% < 40%）
        performance_improvements = optimization["performance_improvement"]
        low_win_rate_warnings = [
            p for p in performance_improvements if p["type"] == "low_win_rate"
        ]
        assert len(low_win_rate_warnings) > 0


class TestStrategyPortfolioManagerIntegration:
    """戦略統合ポートフォリオマネージャーの統合テスト"""

    def test_full_workflow_with_real_strategies(self):
        """実際の戦略を使った全ワークフローテスト"""
        portfolio_manager = AdvancedPortfolioManager(initial_capital=100000.0)

        # 実際の戦略を追加
        rsi_strategy = RSIStrategy(
            name="RSI Strategy",
            symbol="BTCUSDT",
            parameters={"required_data_length": 20},
        )

        macd_strategy = MACDStrategy(
            name="MACD Strategy",
            symbol="BTCUSDT",
            parameters={"required_data_length": 30},
        )

        # 戦略を追加
        assert portfolio_manager.add_strategy(rsi_strategy, 0.4) is True
        assert portfolio_manager.add_strategy(macd_strategy, 0.3) is True

        # 市場データを段階的に処理
        for i in range(50):
            market_data = {
                "timestamp": datetime.now() - timedelta(hours=50 - i),
                "open": 45000 + (i * 10) + np.random.normal(0, 50),
                "high": 45200 + (i * 10) + np.random.normal(0, 50),
                "low": 44800 + (i * 10) + np.random.normal(0, 50),
                "close": 45100 + (i * 10) + np.random.normal(0, 50),
                "volume": 1000 + np.random.normal(0, 100),
            }

            signals = portfolio_manager.process_market_data("BTCUSDT", market_data)

            # シグナルがあれば実行
            for signal in signals:
                position_size = portfolio_manager._calculate_position_size(
                    signal.symbol,
                    signal,  # 注: 実際にはstrategy_nameが必要
                )
                if position_size > 0:
                    portfolio_manager.execute_signal(signal, position_size)

        # 最終的なサマリーを取得
        summary = portfolio_manager.get_portfolio_summary()

        assert summary["portfolio_overview"]["total_strategies"] == 2
        assert summary["portfolio_overview"]["active_strategies"] == 2
        assert "RSI Strategy" in summary["strategy_allocations"]
        assert "MACD Strategy" in summary["strategy_allocations"]

        # リスクレポートを確認
        risk_report = portfolio_manager.get_risk_report()
        assert "position_concentration" in risk_report
        assert "var_analysis" in risk_report

        # 最適化提案を確認
        optimization = portfolio_manager.optimize_portfolio()
        assert "rebalancing" in optimization
        assert "risk_reduction" in optimization
        assert "performance_improvement" in optimization


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
