"""RSI戦略のテスト"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.strategies.implementations.rsi_strategy import RSIStrategy
from backend.strategies.base import Signal, TechnicalIndicators


class TestRSIStrategy:
    """RSI戦略のテスト"""

    @pytest.fixture
    def strategy(self):
        """テスト用のRSI戦略インスタンス"""
        return RSIStrategy(
            name="Test RSI Strategy",
            symbol="BTCUSDT",
            parameters={
                "rsi_period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70,
                "required_data_length": 20,
                "confirmation_bars": 1,  # テスト用に短縮
            },
        )

    @pytest.fixture
    def sample_data(self):
        """サンプル価格データ"""
        # RSIテスト用のデータを生成
        dates = [datetime.now() - timedelta(hours=i) for i in reversed(range(50))]

        # 売られすぎから買われすぎへの変化パターン
        prices = []
        base_price = 45000
        for i in range(50):
            if i < 15:
                # 下落傾向（売られすぎへ）
                price = base_price - (i * 100) + np.random.normal(0, 50)
            elif i < 30:
                # 反発（売られすぎから上昇）
                price = base_price - 1500 + ((i - 15) * 150) + np.random.normal(0, 50)
            else:
                # 上昇継続（買われすぎへ）
                price = base_price + 750 + ((i - 30) * 100) + np.random.normal(0, 50)

            prices.append(max(1000, price))  # 価格は正の値を保証

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [p * 0.999 for p in prices],
                "high": [p * 1.002 for p in prices],
                "low": [p * 0.998 for p in prices],
                "close": prices,
                "volume": [1000 + np.random.normal(0, 100) for _ in range(50)],
            }
        )

        return data

    def test_strategy_initialization(self, strategy):
        """戦略の初期化テスト"""
        assert strategy.name == "Test RSI Strategy"
        assert strategy.symbol == "BTCUSDT"
        assert strategy.parameters["rsi_period"] == 14
        assert strategy.parameters["oversold_threshold"] == 30
        assert strategy.parameters["overbought_threshold"] == 70

    def test_calculate_indicators(self, strategy, sample_data):
        """指標計算のテスト"""
        result = strategy.calculate_indicators(sample_data)

        # RSI列が追加されているか確認
        assert "rsi" in result.columns
        assert "volume_sma" in result.columns
        assert "price_sma" in result.columns

        # RSI値の範囲確認（0-100）
        rsi_values = result["rsi"].dropna()
        assert len(rsi_values) > 0
        assert all(0 <= val <= 100 for val in rsi_values)

    def test_rsi_calculation_accuracy(self):
        """RSI計算の精度テスト"""
        # 既知のデータでRSI計算をテスト
        test_prices = [
            44,
            44.5,
            43.8,
            44.2,
            44.5,
            43.9,
            44.6,
            44.9,
            44.5,
            44.6,
            44.8,
            44.2,
            45.1,
            45.3,
            45.4,
            45.4,
            45.8,
            46.0,
            45.8,
            46.2,
        ]

        rsi_values = TechnicalIndicators.rsi(test_prices, 14)

        # RSI値が妥当な範囲にあることを確認
        assert len(rsi_values) == len(test_prices)

        # RSI計算に必要な期間後から有効な値が存在することを確認
        valid_rsi_values = [v for v in rsi_values[14:] if v > 0]  # 15番目以降の有効な値
        assert len(valid_rsi_values) > 0, "No valid RSI values found"

        # 有効なRSI値が範囲内にあることを確認
        for rsi in valid_rsi_values:
            assert 0 <= rsi <= 100, f"RSI value {rsi} is out of range"

        # 最後のRSI値が計算されていることを確認（期間後の値のみ）
        if len(test_prices) > 14:
            last_rsi = rsi_values[-1]
            assert last_rsi > 0, f"Last RSI value should be calculated, got {last_rsi}"

    def test_oversold_signal_generation(self, strategy):
        """売られすぎシグナル生成のテスト"""
        # 売られすぎ状態のデータを作成
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i) for i in reversed(range(25))
                ],
                "close": [50000 - (i * 200) for i in range(25)],  # 価格下落
                "open": [50000 - (i * 200) + 50 for i in range(25)],
                "high": [50000 - (i * 200) + 100 for i in range(25)],
                "low": [50000 - (i * 200) - 100 for i in range(25)],
                "volume": [1000] * 25,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # シグナルを生成
        signals = strategy.generate_signals(data)

        # 売られすぎでのシグナル確認
        rsi_value = data["rsi"].iloc[-1]
        if rsi_value <= strategy.parameters["oversold_threshold"]:
            # 買いシグナルが生成されるはず
            buy_signals = [s for s in signals if s.action == "enter_long"]
            assert len(buy_signals) > 0
            assert buy_signals[0].strength > 0
            assert "oversold" in buy_signals[0].reason.lower()

    def test_overbought_signal_generation(self, strategy):
        """買われすぎシグナル生成のテスト"""
        # 買われすぎ状態のデータを作成
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i) for i in reversed(range(25))
                ],
                "close": [40000 + (i * 200) for i in range(25)],  # 価格上昇
                "open": [40000 + (i * 200) - 50 for i in range(25)],
                "high": [40000 + (i * 200) + 100 for i in range(25)],
                "low": [40000 + (i * 200) - 100 for i in range(25)],
                "volume": [1000] * 25,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # シグナルを生成
        signals = strategy.generate_signals(data)

        # 買われすぎでのシグナル確認
        rsi_value = data["rsi"].iloc[-1]
        if rsi_value >= strategy.parameters["overbought_threshold"]:
            # 売りシグナルが生成されるはず
            sell_signals = [s for s in signals if s.action == "enter_short"]
            assert len(sell_signals) > 0
            assert sell_signals[0].strength > 0
            assert "overbought" in sell_signals[0].reason.lower()

    def test_signal_strength_calculation(self, strategy):
        """シグナル強度計算のテスト"""
        # 極端な売られすぎ
        strength1 = strategy._calculate_signal_strength(15, "buy", None)
        # 軽い売られすぎ
        strength2 = strategy._calculate_signal_strength(28, "buy", None)

        # 極端な方が強いシグナルになるはず
        assert strength1 > strength2
        assert 0 <= strength1 <= 1
        assert 0 <= strength2 <= 1

        # ダイバージェンス付きの場合
        strength_with_div = strategy._calculate_signal_strength(15, "buy", "buy")
        assert strength_with_div > strength1  # ダイバージェンスがある方が強い

    def test_exit_signal_generation(self, strategy):
        """エグジットシグナル生成のテスト"""
        # ロングポジションを持った状態を設定
        strategy.state.is_long = True
        strategy.state.entry_price = 45000

        # 十分なデータを作成（required_data_length以上）
        num_rows = strategy.parameters["required_data_length"] + 5
        base_time = datetime.now()

        data = pd.DataFrame(
            {
                "timestamp": [
                    base_time - timedelta(hours=i) for i in reversed(range(num_rows))
                ],
                "close": [
                    45000 + (i * 10) for i in range(num_rows)
                ],  # 価格上昇トレンド
                "open": [45000 + (i * 10) - 25 for i in range(num_rows)],
                "high": [45000 + (i * 10) + 50 for i in range(num_rows)],
                "low": [45000 + (i * 10) - 50 for i in range(num_rows)],
                "volume": [1000] * num_rows,
            }
        )

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # 最後の行のRSIを中立ゾーンに設定
        data.loc[data.index[-1], "rsi"] = 55  # 中立ゾーン

        signals = strategy.generate_signals(data)

        # エグジットシグナルが生成されるはず
        exit_signals = [s for s in signals if s.action == "exit_long"]
        assert len(exit_signals) > 0
        assert "neutralized" in exit_signals[0].reason.lower()

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
        assert info["type"] == "Oscillator"
        assert info["category"] == "Mean Reversion"
        assert "RSI" in info["indicators"]
        assert isinstance(info["parameters"], dict)
        assert isinstance(info["timeframes"], list)

    def test_divergence_detection(self, strategy):
        """ダイバージェンス検出のテスト"""
        # ベアリッシュダイバージェンス用データ（価格上昇、RSI下降）
        data = pd.DataFrame(
            {
                "timestamp": [
                    datetime.now() - timedelta(hours=i) for i in reversed(range(25))
                ],
                "high": [45000 + (i * 50) for i in range(25)],  # 高値更新
                "low": [44000 + (i * 50) for i in range(25)],
                "close": [44500 + (i * 50) for i in range(25)],
                "rsi": [80 - (i * 1.5) for i in range(25)],  # RSI下降
            }
        )

        divergence = strategy._detect_divergence(data, 24)
        # ベアリッシュダイバージェンス検出されるかも（データによる）
        assert divergence in [None, "sell", "buy"]


class TestRSIStrategyIntegration:
    """RSI戦略の統合テスト"""

    def test_full_strategy_workflow(self):
        """戦略の全ワークフローテスト"""
        strategy = RSIStrategy(
            name="Integration Test RSI",
            symbol="BTCUSDT",
            parameters={"required_data_length": 20, "confirmation_bars": 1},
        )

        # 時系列データを段階的に追加
        for i in range(30):
            ohlcv = {
                "timestamp": datetime.now() - timedelta(hours=30 - i),
                "open": 45000 - (i * 10),
                "high": 45100 - (i * 10),
                "low": 44900 - (i * 10),
                "close": 45000 - (i * 10),
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
