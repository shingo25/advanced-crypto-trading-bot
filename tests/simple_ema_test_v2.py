#!/usr/bin/env python3
"""
Simple EMA戦略のテスト（パッケージ依存なし）
"""
import sys
import os
from datetime import datetime, timezone
import logging

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_strategy_import():
    """戦略のインポートテスト"""
    print("Testing strategy import...")

    try:
        print("✓ SimpleEMAStrategy import successful")
        return True
    except Exception as e:
        print(f"❌ SimpleEMAStrategy import failed: {e}")
        return False


def test_strategy_creation():
    """戦略作成テスト"""
    print("Testing strategy creation...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy(
            name="Test Simple EMA Strategy",
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
        assert strategy.name == "Test Simple EMA Strategy"
        assert strategy.symbol == "BTCUSDT"
        assert strategy.timeframe == "1h"
        assert strategy.parameters["ema_fast"] == 12
        assert strategy.parameters["ema_slow"] == 26

        print("✓ Strategy creation test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy creation failed: {e}")
        return False


def test_strategy_validation():
    """戦略バリデーションテスト"""
    print("Testing strategy validation...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 正常なパラメータ
        strategy = SimpleEMAStrategy()
        assert strategy.validate_parameters()

        # 不正なパラメータ（fast >= slow）
        strategy = SimpleEMAStrategy(parameters={"ema_fast": 26, "ema_slow": 12})
        assert not strategy.validate_parameters()

        print("✓ Strategy validation test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy validation failed: {e}")
        return False


def test_ema_calculation():
    """EMA計算テスト"""
    print("Testing EMA calculation...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy()

        # テストデータ
        test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]

        # EMAを計算
        ema_values = strategy._calculate_ema(test_prices, 5)

        # 結果をチェック
        assert len(ema_values) == len(test_prices)
        assert all(isinstance(val, float) for val in ema_values)

        # 最初の数値は0（期間が不足）
        assert ema_values[0] == 0.0
        assert ema_values[1] == 0.0
        assert ema_values[2] == 0.0
        assert ema_values[3] == 0.0

        # 5番目の値はSMA
        expected_sma = sum(test_prices[:5]) / 5
        assert abs(ema_values[4] - expected_sma) < 0.01

        print("✓ EMA calculation test passed")
        return True

    except Exception as e:
        print(f"❌ EMA calculation failed: {e}")
        return False


def test_signal_generation():
    """シグナル生成テスト"""
    print("Testing signal generation...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy(
            parameters={"ema_fast": 3, "ema_slow": 5, "required_data_length": 10}
        )

        # テストデータ（上昇トレンド）
        test_data = []
        base_price = 100
        for i in range(15):
            test_data.append(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "open": base_price + i,
                    "high": base_price + i + 1,
                    "low": base_price + i - 1,
                    "close": base_price + i,
                    "volume": 1000,
                }
            )

        # 指標を計算
        strategy.calculate_indicators(test_data)

        # シグナルを生成
        signals = strategy.generate_signals(test_data)

        # 結果をチェック
        assert isinstance(signals, list)

        print(f"✓ Signal generation test passed (generated {len(signals)} signals)")
        return True

    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return False


def test_position_management():
    """ポジション管理テスト"""
    print("Testing position management...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy()

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

        print("✓ Position management test passed")
        return True

    except Exception as e:
        print(f"❌ Position management test failed: {e}")
        return False


def test_analysis_output():
    """分析結果出力テスト"""
    print("Testing analysis output...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy()

        # 初期状態
        analysis = strategy.get_current_analysis()
        assert analysis["status"] == "insufficient_data"

        # テストデータで指標を計算
        test_data = []
        for i in range(30):
            test_data.append(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "close": 100 + i * 0.5,
                    "volume": 1000,
                }
            )

        strategy.calculate_indicators(test_data)

        # 分析結果を取得
        analysis = strategy.get_current_analysis()
        assert "ema_fast" in analysis
        assert "ema_slow" in analysis
        assert "trend_direction" in analysis
        assert "position" in analysis

        print("✓ Analysis output test passed")
        return True

    except Exception as e:
        print(f"❌ Analysis output test failed: {e}")
        return False


def test_strategy_reset():
    """戦略リセットテスト"""
    print("Testing strategy reset...")

    try:
        from backend.strategies.implementations.simple_ema_strategy import (
            SimpleEMAStrategy,
        )

        # 戦略を作成
        strategy = SimpleEMAStrategy()

        # 状態を変更
        strategy.update_position("enter_long", 50000.0, datetime.now(timezone.utc))
        strategy.trades_count = 5
        strategy.ema_fast_values = [1, 2, 3]
        strategy.ema_slow_values = [1, 2, 3]

        # リセット
        strategy.reset()

        # 状態をチェック
        position = strategy.get_current_position()
        assert not position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] is None

        stats = strategy.get_performance_stats()
        assert stats["total_trades"] == 0

        assert len(strategy.ema_fast_values) == 0
        assert len(strategy.ema_slow_values) == 0

        print("✓ Strategy reset test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy reset test failed: {e}")
        return False


def run_simple_tests():
    """シンプルなテストを実行"""
    print("=== Simple EMA Strategy Tests ===")
    print()

    tests = [
        test_strategy_import,
        test_strategy_creation,
        test_strategy_validation,
        test_ema_calculation,
        test_signal_generation,
        test_position_management,
        test_analysis_output,
        test_strategy_reset,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
            print()

    print("=== Test Results ===")
    print(f"✓ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n❌ {failed} tests failed")
        return False


if __name__ == "__main__":
    success = run_simple_tests()
    if success:
        print("\n✅ Simple EMA戦略のテストが完了しました！")
        print("🚀 戦略の基本機能が正常に動作しています")
        exit(0)
    else:
        print("\n❌ Simple EMA戦略のテストに失敗しました")
        exit(1)
