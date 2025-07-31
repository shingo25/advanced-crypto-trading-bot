#!/usr/bin/env python3
"""
EMA戦略のE2Eテスト（End-to-End Test）
データ収集からバックテストまでの全体フローをテスト
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_data() -> pd.DataFrame:
    """サンプルデータを作成"""
    print("Creating sample OHLCV data...")

    # 100日分の1時間足データを作成
    start_date = datetime.now(timezone.utc) - timedelta(days=100)
    dates = pd.date_range(start=start_date, periods=100 * 24, freq="H")

    # 価格データを生成（ランダムウォーク + トレンド）
    np.random.seed(42)

    # 基準価格
    base_price = 50000

    # 価格変動を生成
    returns = np.random.normal(0, 0.001, len(dates))  # 0.1%の標準偏差

    # トレンドを追加
    trend = np.sin(np.arange(len(dates)) * 0.01) * 0.0005
    returns += trend

    # 価格を計算
    prices = base_price * np.exp(np.cumsum(returns))

    # OHLCV データを作成
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 各時間のOHLCを生成
        volatility = np.random.uniform(0.995, 1.005)

        open_price = price
        high_price = price * np.random.uniform(1.0, 1.01)
        low_price = price * np.random.uniform(0.99, 1.0)
        close_price = price * volatility
        volume = np.random.uniform(100, 1000)

        data.append(
            {
                "timestamp": date,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)
    print(f"✓ Created {len(df)} sample data points")
    return df


def test_ema_strategy_creation():
    """EMA戦略の作成テスト"""
    print("Testing EMA strategy creation...")

    try:
        from backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy(
            name="Test EMA Strategy",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={
                "ema_fast": 12,
                "ema_slow": 26,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.06,
            },
        )

        # 基本的な属性をチェック
        assert strategy.name == "Test EMA Strategy"
        assert strategy.symbol == "BTCUSDT"
        assert strategy.timeframe == "1h"
        assert strategy.parameters["ema_fast"] == 12
        assert strategy.parameters["ema_slow"] == 26

        print("✓ EMA strategy creation test passed")
        return strategy

    except Exception as e:
        print(f"❌ EMA strategy creation failed: {e}")
        raise


def test_indicator_calculation(strategy, data):
    """指標計算のテスト"""
    print("Testing indicator calculation...")

    try:
        # 指標を計算
        data_with_indicators = strategy.calculate_indicators(data.copy())

        # 必要な指標が存在するかチェック
        required_indicators = ["ema_fast", "ema_slow", "volume_sma", "trend_strength"]

        for indicator in required_indicators:
            assert indicator in data_with_indicators.columns, f"Missing indicator: {indicator}"

        # 指標の値が計算されているかチェック（NaN以外）
        assert not data_with_indicators["ema_fast"].iloc[-1] != data_with_indicators["ema_fast"].iloc[-1]  # NaNチェック
        assert not data_with_indicators["ema_slow"].iloc[-1] != data_with_indicators["ema_slow"].iloc[-1]  # NaNチェック

        print("✓ Indicator calculation test passed")
        return data_with_indicators

    except Exception as e:
        print(f"❌ Indicator calculation failed: {e}")
        raise


def test_signal_generation(strategy, data):
    """シグナル生成のテスト"""
    print("Testing signal generation...")

    try:
        signals = []

        # データを順次処理してシグナルを生成
        for i in range(len(data)):
            if i < strategy.get_required_data_length():
                continue

            # 現在の行までのデータを使用
            current_data = data.iloc[: i + 1]

            # 指標を計算
            data_with_indicators = strategy.calculate_indicators(current_data)

            # シグナルを生成
            new_signals = strategy.generate_signals(data_with_indicators)

            for signal in new_signals:
                signals.append(signal)

                # ポジションを更新
                strategy.update_position(signal.action, signal.price, signal.timestamp)

        print(f"✓ Generated {len(signals)} signals")

        # シグナルの妥当性をチェック
        if signals:
            # 最初のシグナルが enter_long または enter_short であることを確認
            valid_first_actions = ["enter_long", "enter_short"]
            assert signals[0].action in valid_first_actions, f"First signal should be entry, got {signals[0].action}"

            # シグナルのタイムスタンプが昇順であることを確認
            for i in range(1, len(signals)):
                assert signals[i].timestamp >= signals[i - 1].timestamp, "Signals should be in chronological order"

        print("✓ Signal generation test passed")
        return signals

    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        raise


def test_backtest_integration(strategy, data):
    """バックテストエンジンとの統合テスト"""
    print("Testing backtest integration...")

    try:
        from backend.backtesting.engine import BacktestEngine

        # バックテストエンジンを初期化
        engine = BacktestEngine(initial_capital=10000.0, commission=0.001, slippage=0.0005)

        # データを順次処理
        for i, row in data.iterrows():
            if i < strategy.get_required_data_length():
                continue

            # OHLCV データを準備
            ohlcv = {
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }

            # 戦略を更新
            signal = strategy.update(ohlcv)

            # シグナルを変換
            signals = {}
            if signal:
                if signal.action == "enter_long":
                    signals["enter_long"] = 1
                elif signal.action == "exit_long":
                    signals["exit_long"] = 1
                elif signal.action == "enter_short":
                    signals["enter_short"] = 1
                elif signal.action == "exit_short":
                    signals["exit_short"] = 1

                signals["symbol"] = signal.symbol

            # バックテストエンジンでバーを処理
            engine.process_bar(
                timestamp=row["timestamp"],
                ohlcv=ohlcv,
                signals=signals,
                strategy_name=strategy.name,
            )

        # 結果を取得
        result = engine.get_results(strategy.name)

        # 基本的な結果をチェック
        assert result.initial_capital == 10000.0
        assert result.final_capital >= 0  # 負の資産にはならない
        assert result.total_trades >= 0
        assert result.win_rate >= 0 and result.win_rate <= 1

        print("✓ Backtest completed:")
        print(f"  Initial Capital: ${result.initial_capital:,.2f}")
        print(f"  Final Capital: ${result.final_capital:,.2f}")
        print(f"  Total Return: {result.total_return:.2%}")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Win Rate: {result.win_rate:.2%}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.3f}")
        print(f"  Max Drawdown: {result.max_drawdown:.2%}")

        print("✓ Backtest integration test passed")
        return result

    except Exception as e:
        print(f"❌ Backtest integration failed: {e}")
        raise


def test_strategy_performance(result):
    """戦略パフォーマンスのテスト"""
    print("Testing strategy performance...")

    try:
        # 基本的なパフォーマンス指標をチェック
        assert hasattr(result, "total_return")
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "profit_factor")

        # 合理的な範囲内の値であることを確認
        assert -1.0 <= result.total_return <= 10.0, f"Total return seems unrealistic: {result.total_return}"
        assert -10.0 <= result.sharpe_ratio <= 10.0, f"Sharpe ratio seems unrealistic: {result.sharpe_ratio}"
        assert 0.0 <= result.max_drawdown <= 1.0, f"Max drawdown should be between 0 and 1: {result.max_drawdown}"

        # 最低限の取引があることを確認
        assert result.total_trades >= 0, "Total trades should be non-negative"

        print("✓ Strategy performance test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy performance test failed: {e}")
        raise


def test_strategy_state_management(strategy):
    """戦略状態管理のテスト"""
    print("Testing strategy state management...")

    try:
        # 初期状態をチェック
        position = strategy.get_current_position()
        assert not position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] is None

        # ロングポジションに入る
        strategy.update_position("enter_long", 50000.0, datetime.now(timezone.utc))

        position = strategy.get_current_position()
        assert position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] == 50000.0

        # ロングポジションを終了
        strategy.update_position("exit_long", 51000.0, datetime.now(timezone.utc))

        position = strategy.get_current_position()
        assert not position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] is None

        print("✓ Strategy state management test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy state management test failed: {e}")
        raise


def test_strategy_validation():
    """戦略バリデーションのテスト"""
    print("Testing strategy validation...")

    try:
        from backend.strategies.base import StrategyValidator
        from backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

        # 基本的な検証
        assert strategy.validate_parameters()

        # サンプルデータでデータ要件を検証
        sample_data = create_sample_data()
        assert StrategyValidator.validate_data_requirements(strategy, sample_data)

        print("✓ Strategy validation test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy validation test failed: {e}")
        raise


def run_e2e_test():
    """E2Eテストを実行"""
    print("=== EMA Strategy E2E Test ===")
    print()

    try:
        # 1. サンプルデータを作成
        sample_data = create_sample_data()
        print()

        # 2. 戦略を作成
        strategy = test_ema_strategy_creation()
        print()

        # 3. 指標計算をテスト
        test_indicator_calculation(strategy, sample_data)
        print()

        # 4. シグナル生成をテスト
        signals = test_signal_generation(strategy, sample_data)
        print()

        # 5. 戦略状態管理をテスト
        test_strategy_state_management(strategy)
        print()

        # 6. バックテスト統合をテスト
        result = test_backtest_integration(strategy, sample_data)
        print()

        # 7. パフォーマンスをテスト
        test_strategy_performance(result)
        print()

        # 8. バリデーションをテスト
        test_strategy_validation()
        print()

        print("🎉 All E2E tests passed!")
        print()
        print("=== Test Summary ===")
        print(f"✓ Data points processed: {len(sample_data)}")
        print(f"✓ Signals generated: {len(signals)}")
        print(f"✓ Trades executed: {result.total_trades}")
        print(f"✓ Final return: {result.total_return:.2%}")
        print(f"✓ Sharpe ratio: {result.sharpe_ratio:.3f}")

        return True

    except Exception as e:
        print(f"❌ E2E test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_e2e_test()
    if success:
        print("\n✅ EMA戦略のE2Eテストが完了しました！")
        print("🚀 戦略基盤が正常に動作しています")
        exit(0)
    else:
        print("\n❌ EMA戦略のE2Eテストに失敗しました")
        exit(1)
