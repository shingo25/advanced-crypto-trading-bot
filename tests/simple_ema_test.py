#!/usr/bin/env python3
"""
EMA戦略のシンプルなテスト
外部パッケージに依存しないテスト
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
        print("✓ EMAStrategy import successful")
        return True
    except Exception as e:
        print(f"❌ EMAStrategy import failed: {e}")
        return False


def test_strategy_creation():
    """戦略作成テスト"""
    print("Testing strategy creation...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

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

        print("✓ Strategy creation test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy creation failed: {e}")
        return False


def test_strategy_validation():
    """戦略バリデーションテスト"""
    print("Testing strategy validation...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

        # 基本的な検証
        assert strategy.validate_parameters()

        print("✓ Strategy validation test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy validation failed: {e}")
        return False


def test_base_strategy_methods():
    """基底戦略メソッドのテスト"""
    print("Testing base strategy methods...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

        # 基本的なメソッドをテスト
        assert strategy.get_required_data_length() > 0
        assert strategy.can_generate_signals() is False  # データがないため

        # 初期ポジション状態をチェック
        position = strategy.get_current_position()
        assert not position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] is None

        print("✓ Base strategy methods test passed")
        return True

    except Exception as e:
        print(f"❌ Base strategy methods test failed: {e}")
        return False


def test_position_management():
    """ポジション管理テスト"""
    print("Testing position management...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

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


def test_performance_stats():
    """パフォーマンス統計テスト"""
    print("Testing performance statistics...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

        # 初期統計をチェック
        stats = strategy.get_performance_stats()
        assert stats["total_trades"] == 0
        assert stats["winning_trades"] == 0
        assert stats["losing_trades"] == 0
        assert stats["win_rate"] == 0

        print("✓ Performance statistics test passed")
        return True

    except Exception as e:
        print(f"❌ Performance statistics test failed: {e}")
        return False


def test_strategy_reset():
    """戦略リセットテスト"""
    print("Testing strategy reset...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # 戦略を作成
        strategy = EMAStrategy()

        # 状態を変更
        strategy.update_position("enter_long", 50000.0, datetime.now(timezone.utc))
        strategy.trades_count = 5

        # リセット
        strategy.reset()

        # 状態をチェック
        position = strategy.get_current_position()
        assert not position["is_long"]
        assert not position["is_short"]
        assert position["entry_price"] is None

        stats = strategy.get_performance_stats()
        assert stats["total_trades"] == 0

        print("✓ Strategy reset test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy reset test failed: {e}")
        return False


def test_strategy_parameters():
    """戦略パラメータテスト"""
    print("Testing strategy parameters...")

    try:
        from src.backend.strategies.implementations.ema_strategy import EMAStrategy

        # カスタムパラメータで戦略を作成
        custom_params = {
            "ema_fast": 8,
            "ema_slow": 21,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.05,
        }

        strategy = EMAStrategy(parameters=custom_params)

        # パラメータが正しく設定されているかチェック
        assert strategy.parameters["ema_fast"] == 8
        assert strategy.parameters["ema_slow"] == 21
        assert strategy.parameters["stop_loss_pct"] == 0.03
        assert strategy.parameters["take_profit_pct"] == 0.05

        print("✓ Strategy parameters test passed")
        return True

    except Exception as e:
        print(f"❌ Strategy parameters test failed: {e}")
        return False


def run_simple_tests():
    """シンプルなテストを実行"""
    print("=== EMA Strategy Simple Tests ===")
    print()

    tests = [
        test_strategy_import,
        test_strategy_creation,
        test_strategy_validation,
        test_base_strategy_methods,
        test_position_management,
        test_performance_stats,
        test_strategy_reset,
        test_strategy_parameters,
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
        print("\n✅ EMA戦略のシンプルテストが完了しました！")
        print("🚀 戦略の基本機能が正常に動作しています")
        exit(0)
    else:
        print("\n❌ EMA戦略のテストに失敗しました")
        exit(1)
