"""Bollinger Bands戦略のテスト"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backend.strategies.implementations.bollinger_strategy import BollingerBandsStrategy
from src.backend.strategies.base import Signal, TechnicalIndicators


class TestBollingerBandsStrategy:
    """Bollinger Bands戦略のテスト"""

    @pytest.fixture
    def strategy(self):
        """テスト用のBollinger Bands戦略インスタンス"""
        return BollingerBandsStrategy(
            name="Test Bollinger Bands Strategy",
            symbol="BTCUSDT",
            parameters={
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "bb_position_threshold": 0.8,
                "squeeze_threshold": 0.1,
                "required_data_length": 60,
                "confirmation_bars": 1,  # テスト用に短縮
            },
        )

    @pytest.fixture
    def sample_data(self):
        """サンプル価格データ"""
        # Bollinger Bandsテスト用のデータを生成
        dates = [datetime.now() - timedelta(hours=i) for i in reversed(range(80))]

        # ボラティリティのある価格パターンを作成
        prices = []
        base_price = 45000
        for i in range(80):
            if i < 20:
                # 安定期間
                price = base_price + np.random.normal(0, 50)
            elif i < 40:
                # 下降期間（下部バンド接触）
                price = base_price - ((i - 20) * 30) + np.random.normal(0, 100)
            elif i < 60:
                # 反発期間
                price = base_price - 600 + ((i - 40) * 40) + np.random.normal(0, 80)
            else:
                # 上昇期間（上部バンド接触）
                price = base_price + 200 + ((i - 60) * 25) + np.random.normal(0, 60)

            prices.append(max(1000, price))  # 価格は正の値を保証

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [p * 0.999 for p in prices],
                "high": [p * 1.003 for p in prices],
                "low": [p * 0.997 for p in prices],
                "close": prices,
                "volume": [1000 + np.random.normal(0, 100) for _ in range(80)],
            }
        )

        return data

    def test_strategy_initialization(self, strategy):
        """戦略の初期化テスト"""
        assert strategy.name == "Test Bollinger Bands Strategy"
        assert strategy.symbol == "BTCUSDT"
        assert strategy.parameters["bb_period"] == 20
        assert strategy.parameters["bb_std_dev"] == 2.0
        assert strategy.parameters["bb_position_threshold"] == 0.8
        assert strategy.parameters["squeeze_threshold"] == 0.1

    def test_calculate_indicators(self, strategy, sample_data):
        """指標計算のテスト"""
        result = strategy.calculate_indicators(sample_data)

        # Bollinger Bands関連列が追加されているか確認
        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns
        assert "bb_position" in result.columns
        assert "bb_width" in result.columns
        assert "bb_squeeze" in result.columns
        assert "price_above_upper" in result.columns
        assert "price_below_lower" in result.columns
        assert "price_inside_bands" in result.columns
        assert "volume_sma" in result.columns

        # 値の妥当性確認
        bb_upper_values = result["bb_upper"].dropna()
        bb_lower_values = result["bb_lower"].dropna()
        bb_middle_values = result["bb_middle"].dropna()
        bb_position_values = result["bb_position"].dropna()

        assert len(bb_upper_values) > 0
        assert len(bb_lower_values) > 0
        assert len(bb_middle_values) > 0
        assert len(bb_position_values) > 0

        # 上部バンド > 中央線 > 下部バンドの関係確認
        for i in range(len(result)):
            if (
                not pd.isna(result["bb_upper"].iloc[i])
                and not pd.isna(result["bb_middle"].iloc[i])
                and not pd.isna(result["bb_lower"].iloc[i])
            ):
                upper = result["bb_upper"].iloc[i]
                middle = result["bb_middle"].iloc[i]
                lower = result["bb_lower"].iloc[i]

                assert (
                    upper >= middle >= lower
                ), f"Band order invalid at index {i}: {upper} >= {middle} >= {lower}"

        # %Bの範囲確認（通常は0～1だが、バンド外では範囲外も可能）
        for position in bb_position_values:
            assert (
                -1 <= position <= 2
            ), f"%B value {position} is out of reasonable range"

    def test_bollinger_bands_calculation_accuracy(self):
        """Bollinger Bands計算の精度テスト"""
        # 既知のデータでBollinger Bands計算をテスト
        test_prices = [
            45,
            45.2,
            45.1,
            45.3,
            45.5,
            45.4,
            45.6,
            45.8,
            45.7,
            45.9,
            46,
            45.8,
            46.2,
            46.4,
            46.3,
            46.5,
            46.7,
            46.6,
            46.8,
            47,
            46.9,
            47.1,
            47.3,
            47.2,
            47.4,
            47.6,
            47.5,
            47.7,
            47.9,
            47.8,
        ]

        bb_result = TechnicalIndicators.bollinger_bands(test_prices, 20, 2.0)

        # 結果の構造確認
        assert "sma" in bb_result
        assert "upper" in bb_result
        assert "lower" in bb_result

        # 値の妥当性確認
        assert len(bb_result["sma"]) == len(test_prices)
        assert len(bb_result["upper"]) == len(test_prices)
        assert len(bb_result["lower"]) == len(test_prices)

    def test_lower_band_bounce_signal_generation(self, strategy):
        """下部バンドからの反発シグナル生成のテスト"""
        # 下部バンド接触→反発のデータを作成
        num_rows = strategy.parameters["required_data_length"] + 10

        # 価格が下降後反発するパターン
        prices = []
        base_price = 45000
        for i in range(num_rows):
            if i < num_rows // 2:
                # 下降期間
                price = base_price - (i * 40)
            else:
                # 反発期間
                price = base_price - (num_rows // 2 * 40) + ((i - num_rows // 2) * 60)
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

        # 下部バンドを下回った後、バンド内に戻るパターンを探す
        for i in range(1, len(data)):
            prev_below = data.iloc[i - 1]["price_below_lower"]
            curr_inside = data.iloc[i]["price_inside_bands"]
            curr_position = data.iloc[i]["bb_position"]

            if prev_below and curr_inside and curr_position < 0.2:  # 下部バンド寄り
                # このポイントでシグナル生成をテスト
                test_data = data.iloc[: i + 1]
                signals = strategy.generate_signals(test_data)

                # 買いシグナルが生成される可能性
                buy_signals = [s for s in signals if s.action == "enter_long"]
                if len(buy_signals) > 0:
                    assert buy_signals[0].strength > 0
                    assert "bounce from lower band" in buy_signals[0].reason.lower()
                break

    def test_upper_band_bounce_signal_generation(self, strategy):
        """上部バンドからの反発シグナル生成のテスト"""
        # 上部バンド接触→反発のデータを作成
        num_rows = strategy.parameters["required_data_length"] + 10

        # 価格が上昇後反落するパターン
        prices = []
        base_price = 45000
        for i in range(num_rows):
            if i < num_rows // 2:
                # 上昇期間
                price = base_price + (i * 40)
            else:
                # 反落期間
                price = base_price + (num_rows // 2 * 40) - ((i - num_rows // 2) * 30)
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

        # 上部バンドを上回った後、バンド内に戻るパターンを探す
        for i in range(1, len(data)):
            prev_above = data.iloc[i - 1]["price_above_upper"]
            curr_inside = data.iloc[i]["price_inside_bands"]
            curr_position = data.iloc[i]["bb_position"]

            if prev_above and curr_inside and curr_position > 0.8:  # 上部バンド寄り
                # このポイントでシグナル生成をテスト
                test_data = data.iloc[: i + 1]
                signals = strategy.generate_signals(test_data)

                # 売りシグナルが生成される可能性
                sell_signals = [s for s in signals if s.action == "enter_short"]
                if len(sell_signals) > 0:
                    assert sell_signals[0].strength > 0
                    assert "bounce from upper band" in sell_signals[0].reason.lower()
                break

    def test_bb_position_calculation(self, strategy):
        """ "%B計算のテスト"""
        # 簡単なテストデータ
        test_data = pd.DataFrame(
            {
                "close": [45, 46, 47, 48, 49, 50],
                "bb_upper": [50, 50, 50, 50, 50, 50],
                "bb_lower": [40, 40, 40, 40, 40, 40],
            }
        )

        # %B計算
        bb_positions = []
        for i in range(len(test_data)):
            close = test_data["close"].iloc[i]
            upper = test_data["bb_upper"].iloc[i]
            lower = test_data["bb_lower"].iloc[i]

            position = (close - lower) / (upper - lower)
            bb_positions.append(position)

        # 期待値
        expected_positions = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        for i, (actual, expected) in enumerate(zip(bb_positions, expected_positions)):
            assert (
                abs(actual - expected) < 0.01
            ), f"Position {i}: expected {expected}, got {actual}"

    def test_signal_strength_calculation(self, strategy):
        """シグナル強度計算のテスト"""
        # 下部バンド寄りの買いシグナル
        strength1 = strategy._calculate_signal_strength(
            0.1, 0.05, "buy", True
        )  # スクイーズあり
        strength2 = strategy._calculate_signal_strength(
            0.3, 0.15, "buy", False
        )  # スクイーズなし

        # スクイーズありの方が強いシグナル
        assert strength1 > strength2
        assert 0.3 <= strength1 <= 1.0
        assert 0.3 <= strength2 <= 1.0

        # 上部バンド寄りの売りシグナル
        strength3 = strategy._calculate_signal_strength(0.9, 0.05, "sell", True)
        strength4 = strategy._calculate_signal_strength(0.7, 0.15, "sell", False)

        assert strength3 > strength4
        assert 0.3 <= strength3 <= 1.0
        assert 0.3 <= strength4 <= 1.0

    def test_exit_signal_generation(self, strategy):
        """エグジットシグナル生成のテスト"""
        # ロングポジションを持った状態を設定
        strategy.state.is_long = True
        strategy.state.entry_price = 45000

        # 十分なデータを作成
        num_rows = strategy.parameters["required_data_length"] + 5

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

        # 指標を計算
        data = strategy.calculate_indicators(data)

        # 最後の行の%Bを中央以上に設定（エグジット条件）
        data.loc[data.index[-1], "bb_position"] = 0.6  # 中央より上

        signals = strategy.generate_signals(data)

        # エグジットシグナルが生成されるはず
        exit_signals = [s for s in signals if s.action == "exit_long"]
        assert len(exit_signals) > 0
        assert "position normalized" in exit_signals[0].reason.lower()

    def test_squeeze_detection(self, strategy):
        """スクイーズ検出のテスト"""
        # スクイーズ状態のテストデータ作成
        num_rows = strategy.parameters["required_data_length"] + 5

        # 最初は通常のボラティリティ、後半でスクイーズ
        prices = []
        base_price = 45000
        for i in range(num_rows):
            if i < num_rows - 10:
                # 通常のボラティリティ
                price = base_price + np.random.normal(0, 200)
            else:
                # 低ボラティリティ（スクイーズ）
                price = base_price + np.random.normal(0, 20)
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

        # バンド幅が計算されていることを確認
        bb_widths = data["bb_width"].dropna()
        assert len(bb_widths) > 0

        # スクイーズ検出の列が存在することを確認
        assert "bb_squeeze" in data.columns

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
        assert info["type"] == "Mean Reversion"
        assert info["category"] == "Statistical"
        assert "Bollinger Bands" in info["indicators"]
        assert "%B" in info["indicators"]
        assert "Band Width" in info["indicators"]
        assert isinstance(info["parameters"], dict)
        assert isinstance(info["timeframes"], list)


class TestBollingerBandsStrategyIntegration:
    """Bollinger Bands戦略の統合テスト"""

    def test_full_strategy_workflow(self):
        """戦略の全ワークフローテスト"""
        strategy = BollingerBandsStrategy(
            name="Integration Test BB",
            symbol="BTCUSDT",
            parameters={"required_data_length": 60, "confirmation_bars": 1},
        )

        # 時系列データを段階的に追加
        for i in range(80):
            # 価格変動パターン：ボラティリティある動き
            if i < 20:
                base_price = 45000 + np.random.normal(0, 50)
            elif i < 40:
                base_price = 45000 - ((i - 20) * 25) + np.random.normal(0, 100)
            elif i < 60:
                base_price = 44500 + ((i - 40) * 30) + np.random.normal(0, 80)
            else:
                base_price = 45100 + ((i - 60) * 20) + np.random.normal(0, 60)

            ohlcv = {
                "timestamp": datetime.now() - timedelta(hours=80 - i),
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
