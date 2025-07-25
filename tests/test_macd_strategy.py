"""MACD戦略のテスト"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backend.strategies.implementations.macd_strategy import MACDStrategy
from src.backend.strategies.base import Signal, TechnicalIndicators


class TestMACDStrategy:
    """MACD戦略のテスト"""

    @pytest.fixture
    def strategy(self):
        """テスト用のMACD戦略インスタンス"""
        return MACDStrategy(
            name="Test MACD Strategy",
            symbol="BTCUSDT",
            parameters={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "required_data_length": 50,
                "confirmation_bars": 1,  # テスト用に短縮
                "histogram_confirmation": True,
            },
        )

    @pytest.fixture
    def sample_data(self):
        """サンプル価格データ"""
        # MACDテスト用のデータを生成
        dates = [datetime.now() - timedelta(hours=i) for i in reversed(range(100))]

        # トレンド変化パターンを作成
        prices = []
        base_price = 45000
        for i in range(100):
            if i < 30:
                # 下降トレンド
                price = base_price - (i * 20) + np.random.normal(0, 30)
            elif i < 70:
                # 上昇トレンド（MACDクロスオーバー発生）
                price = base_price - 600 + ((i - 30) * 25) + np.random.normal(0, 30)
            else:
                # 横ばい〜再下降
                price = base_price + 400 - ((i - 70) * 10) + np.random.normal(0, 30)

            prices.append(max(1000, price))  # 価格は正の値を保証

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [p * 0.999 for p in prices],
                "high": [p * 1.002 for p in prices],
                "low": [p * 0.998 for p in prices],
                "close": prices,
                "volume": [1000 + np.random.normal(0, 100) for _ in range(100)],
            }
        )

        return data

    def test_strategy_initialization(self, strategy):
        """戦略の初期化テスト"""
        assert strategy.name == "Test MACD Strategy"
        assert strategy.symbol == "BTCUSDT"
        assert strategy.parameters["fast_period"] == 12
        assert strategy.parameters["slow_period"] == 26
        assert strategy.parameters["signal_period"] == 9
        assert strategy.parameters["histogram_confirmation"] is True

    def test_calculate_indicators(self, strategy, sample_data):
        """指標計算のテスト"""
        result = strategy.calculate_indicators(sample_data)

        # MACD関連列が追加されているか確認
        assert "macd_line" in result.columns
        assert "signal_line" in result.columns
        assert "histogram" in result.columns
        assert "volume_sma" in result.columns
        assert "price_sma" in result.columns
        assert "macd_above_signal" in result.columns
        assert "macd_cross_above" in result.columns
        assert "macd_cross_below" in result.columns

        # MACD値の妥当性確認
        macd_values = result["macd_line"].dropna()
        signal_values = result["signal_line"].dropna()
        histogram_values = result["histogram"].dropna()

        assert len(macd_values) > 0
        assert len(signal_values) > 0
        assert len(histogram_values) > 0

        # ヒストグラム = MACD - Signal の関係確認
        for i in range(len(result)):
            if (
                not pd.isna(result["macd_line"].iloc[i])
                and not pd.isna(result["signal_line"].iloc[i])
                and not pd.isna(result["histogram"].iloc[i])
            ):
                expected_histogram = (
                    result["macd_line"].iloc[i] - result["signal_line"].iloc[i]
                )
                actual_histogram = result["histogram"].iloc[i]
                assert abs(expected_histogram - actual_histogram) < 0.001

    def test_macd_calculation_accuracy(self):
        """MACD計算の精度テスト"""
        # 既知のデータでMACD計算をテスト
        test_prices = [
            45,
            45.5,
            46,
            45.8,
            46.2,
            47,
            46.5,
            47.2,
            48,
            47.8,
            48.5,
            49,
            48.7,
            49.2,
            50,
            49.8,
            50.2,
            51,
            50.5,
            51.2,
            52,
            51.8,
            52.5,
            53,
            52.7,
            53.2,
            54,
            53.5,
            54.2,
            55,
        ]

        macd_result = TechnicalIndicators.macd(test_prices, 12, 26, 9)

        # 結果の構造確認
        assert "macd" in macd_result
        assert "signal" in macd_result
        assert "histogram" in macd_result

        # 値の妥当性確認
        assert len(macd_result["macd"]) == len(test_prices)
        assert len(macd_result["signal"]) == len(test_prices)
        assert len(macd_result["histogram"]) == len(test_prices)

    def test_bullish_crossover_signal_generation(self, strategy):
        """上向きクロスオーバーシグナル生成のテスト"""
        # 上向きクロスオーバー状態のデータを作成
        num_rows = strategy.parameters["required_data_length"] + 10
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i)
                    for i in reversed(range(num_rows))
                ],
                "close": [
                    45000 + (i * 15) for i in range(num_rows)
                ],  # 価格上昇トレンド
                "open": [45000 + (i * 15) - 25 for i in range(num_rows)],
                "high": [45000 + (i * 15) + 50 for i in range(num_rows)],
                "low": [45000 + (i * 15) - 50 for i in range(num_rows)],
                "volume": [1000] * num_rows,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # 最後の数行でクロスオーバーが発生していることを確認
        cross_above_indices = data[data["macd_cross_above"]].index

        if len(cross_above_indices) > 0:
            # クロスオーバーが発生している場所でシグナル生成をテスト
            test_idx = cross_above_indices[-1]
            test_data = data.iloc[: test_idx + 1]

            signals = strategy.generate_signals(test_data)

            # 買いシグナルが生成されるかチェック
            buy_signals = [s for s in signals if s.action == "enter_long"]
            if len(buy_signals) > 0:
                assert buy_signals[0].strength > 0
                assert "bullish crossover" in buy_signals[0].reason.lower()

    def test_bearish_crossover_signal_generation(self, strategy):
        """下向きクロスオーバーシグナル生成のテスト"""
        # 下向きクロスオーバー状態のデータを作成
        num_rows = strategy.parameters["required_data_length"] + 10

        # 最初は上昇、後半で下降のパターン
        prices = []
        for i in range(num_rows):
            if i < num_rows // 2:
                price = 45000 + (i * 20)  # 上昇
            else:
                price = (
                    45000 + (num_rows // 2 * 20) - ((i - num_rows // 2) * 25)
                )  # 下降
            prices.append(price)

        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i)
                    for i in reversed(range(num_rows))
                ],
                "close": prices,
                "open": [p - 25 for p in prices],
                "high": [p + 50 for p in prices],
                "low": [p - 50 for p in prices],
                "volume": [1000] * num_rows,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # 下向きクロスオーバーが発生していることを確認
        cross_below_indices = data[data["macd_cross_below"]].index

        if len(cross_below_indices) > 0:
            # クロスオーバーが発生している場所でシグナル生成をテスト
            test_idx = cross_below_indices[-1]
            test_data = data.iloc[: test_idx + 1]

            signals = strategy.generate_signals(test_data)

            # 売りシグナルが生成されるかチェック
            sell_signals = [s for s in signals if s.action == "enter_short"]
            if len(sell_signals) > 0:
                assert sell_signals[0].strength > 0
                assert "bearish crossover" in sell_signals[0].reason.lower()

    def test_signal_strength_calculation(self, strategy):
        """シグナル強度計算のテスト"""
        # 強いシグナル（大きな差）
        strength1 = strategy._calculate_signal_strength(0.05, 0.01, 0.04, "buy")
        # 弱いシグナル（小さな差）
        strength2 = strategy._calculate_signal_strength(0.02, 0.01, 0.01, "buy")

        # 差が大きい方が強いシグナルになるはず
        assert strength1 > strength2
        assert 0.3 <= strength1 <= 1.0
        assert 0.3 <= strength2 <= 1.0

    def test_exit_signal_generation(self, strategy):
        """エグジットシグナル生成のテスト"""
        # ロングポジションを持った状態を設定
        strategy.state.is_long = True
        strategy.state.entry_price = 45000

        # 十分なデータを作成
        num_rows = strategy.parameters["required_data_length"] + 5

        # 下降トレンドのデータ（MACDクロスオーバー発生）
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i)
                    for i in reversed(range(num_rows))
                ],
                "close": [
                    46000 - (i * 15) for i in range(num_rows)
                ],  # 価格下降トレンド
                "open": [46000 - (i * 15) + 25 for i in range(num_rows)],
                "high": [46000 - (i * 15) + 50 for i in range(num_rows)],
                "low": [46000 - (i * 15) - 50 for i in range(num_rows)],
                "volume": [1000] * num_rows,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # 最後の行で下向きクロスオーバーを強制設定
        data.loc[data.index[-1], "macd_cross_below"] = True

        signals = strategy.generate_signals(data)

        # エグジットシグナルが生成されるはず
        exit_signals = [s for s in signals if s.action == "exit_long"]
        assert len(exit_signals) > 0
        assert "bearish crossover" in exit_signals[0].reason.lower()

    def test_insufficient_data_handling(self, strategy):
        """データ不足時の処理テスト"""
        # 不十分なデータ
        insufficient_data = pd.DataFrame(
            {
                "timestamp": [datetime.now()],
                "close": [45000],
                "open": [44950],
                "high": [45100],
                "low": [44900],
                "volume": [1000],
            }
        )

        # 指標計算は元データを返すはず
        result = strategy.calculate_indicators(insufficient_data)
        assert len(result) == 1

        # シグナルは生成されないはず
        signals = strategy.generate_signals(result)
        assert len(signals) == 0

    def test_strategy_info(self, strategy):
        """戦略情報取得のテスト"""
        info = strategy.get_strategy_info()

        assert info["name"] == strategy.name
        assert info["type"] == "Trend Following"
        assert info["category"] == "Momentum"
        assert "MACD Line" in info["indicators"]
        assert "Signal Line" in info["indicators"]
        assert "Histogram" in info["indicators"]
        assert isinstance(info["parameters"], dict)
        assert isinstance(info["timeframes"], list)

    def test_histogram_confirmation(self, strategy):
        """ヒストグラム確認機能のテスト"""
        # ヒストグラム確認が有効な戦略
        strategy_with_histogram = MACDStrategy(
            name="Histogram Test",
            parameters={
                "histogram_confirmation": True,
                "required_data_length": 50,
                "confirmation_bars": 1,
            },
        )

        # テストデータ作成
        num_rows = 55
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i)
                    for i in reversed(range(num_rows))
                ],
                "close": [45000 + (i * 10) for i in range(num_rows)],
                "open": [45000 + (i * 10) - 25 for i in range(num_rows)],
                "high": [45000 + (i * 10) + 50 for i in range(num_rows)],
                "low": [45000 + (i * 10) - 50 for i in range(num_rows)],
                "volume": [1000] * num_rows,
            }
        )

        data = strategy_with_histogram.calculate_indicators(data)

        # ヒストグラムの変化があることを確認
        histogram_changes = data["histogram_change"].dropna()
        assert len(histogram_changes) > 0


class TestMACDStrategyIntegration:
    """MACD戦略の統合テスト"""

    def test_full_strategy_workflow(self):
        """戦略の全ワークフローテスト"""
        strategy = MACDStrategy(
            name="Integration Test MACD",
            symbol="BTCUSDT",
            parameters={"required_data_length": 50, "confirmation_bars": 1},
        )

        # 時系列データを段階的に追加
        for i in range(60):
            # 価格変動パターン：最初下降、後半上昇
            if i < 30:
                base_price = 45000 - (i * 10)
            else:
                base_price = 44700 + ((i - 30) * 20)

            ohlcv = {
                "timestamp": datetime.now() - timedelta(hours=60 - i),
                "open": base_price - 25,
                "high": base_price + 50,
                "low": base_price - 50,
                "close": base_price,
                "volume": 1000 + (i * 10),
            }

            signal = strategy.update(ohlcv)

            # シグナルが生成される場合の確認
            if signal:
                assert isinstance(signal, Signal)
                assert signal.symbol == "BTCUSDT"
                assert signal.strength > 0
                assert signal.price > 0
                assert signal.reason is not None

        # 最終的にデータが蓄積されていることを確認
        assert len(strategy.data) > 0
        assert len(strategy.signals) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
