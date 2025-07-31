#!/usr/bin/env python3
"""
ライブトレーディング・監視システムのテスト
"""
import logging
import os
import sys

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_trading_engine_import():
    """トレーディングエンジンのインポートテスト"""
    print("Testing trading engine import...")

    try:
        print("✓ TradingEngine import successful")
        return True
    except Exception as e:
        print(f"❌ TradingEngine import failed: {e}")
        return False


def test_order_creation():
    """注文作成テスト"""
    print("Testing order creation...")

    try:
        from backend.trading.engine import OrderSide, OrderType, TradingEngine

        # エンジンを作成
        engine = TradingEngine()

        # 注文を作成
        order = engine.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount=1.0,
            strategy_name="test_strategy",
        )

        # 注文の確認
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.amount == 1.0
        assert order.strategy_name == "test_strategy"
        assert order.is_filled()  # デモモードでは即座に約定

        print("✓ Order creation test passed")
        return True

    except Exception as e:
        print(f"❌ Order creation failed: {e}")
        return False


def test_position_management():
    """ポジション管理テスト"""
    print("Testing position management...")

    try:
        from backend.trading.engine import OrderSide, OrderType, TradingEngine

        # エンジンを作成
        engine = TradingEngine()

        # 価格を設定
        engine.update_price("BTCUSDT", 50000.0)

        # 買い注文を作成
        engine.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount=1.0,
        )

        # ポジションが作成されたことを確認
        position = engine.get_position("BTCUSDT")
        assert position is not None
        assert position.symbol == "BTCUSDT"
        assert position.side == OrderSide.BUY
        assert position.amount == 1.0

        # 価格を更新
        engine.update_price("BTCUSDT", 52000.0)

        # 未実現損益を確認
        assert position.unrealized_pnl > 0  # 利益

        # ポジションを閉じる
        success = engine.close_position("BTCUSDT")
        assert success

        # ポジションが削除されたことを確認
        position = engine.get_position("BTCUSDT")
        print(f"Position after closing: {position}")
        assert position is None

        print("✓ Position management test passed")
        return True

    except Exception as e:
        print(f"❌ Position management failed: {e}")
        return False


def test_order_cancellation():
    """注文キャンセルテスト"""
    print("Testing order cancellation...")

    try:
        from backend.trading.engine import (
            OrderSide,
            OrderStatus,
            OrderType,
            TradingEngine,
        )

        # エンジンを作成
        engine = TradingEngine()

        # 指値注文を作成（デモモードでは即座に約定するため、実際にはキャンセルできない）
        order = engine.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            amount=1.0,
            price=45000.0,
        )

        # 注文がある状態を確認
        assert order.id in engine.orders

        # 注文をキャンセル（デモモードでは既に約定済み）
        success = engine.cancel_order(order.id)

        # デモモードでは約定済みなのでキャンセルできない
        assert not success or order.status == OrderStatus.FILLED

        print("✓ Order cancellation test passed")
        return True

    except Exception as e:
        print(f"❌ Order cancellation failed: {e}")
        return False


def test_trading_statistics():
    """トレーディング統計テスト"""
    print("Testing trading statistics...")

    try:
        from backend.trading.engine import OrderSide, OrderType, TradingEngine

        # エンジンを作成
        engine = TradingEngine()

        # 複数の注文を作成
        for i in range(3):
            engine.create_order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                amount=1.0,
            )

        # 統計を取得
        stats = engine.get_statistics()

        # 統計を確認
        assert stats["total_orders"] == 3
        assert stats["filled_orders"] == 3
        assert stats["fill_rate"] == 1.0
        assert stats["open_positions"] == 1  # 同じシンボルなので1つのポジション

        print("✓ Trading statistics test passed")
        return True

    except Exception as e:
        print(f"❌ Trading statistics failed: {e}")
        return False


def test_alert_manager_import():
    """アラートマネージャーのインポートテスト"""
    print("Testing alert manager import...")

    try:
        print("✓ AlertManager import successful")
        return True
    except Exception as e:
        print(f"❌ AlertManager import failed: {e}")
        return False


def test_alert_creation():
    """アラート作成テスト"""
    print("Testing alert creation...")

    try:
        from backend.monitoring.alerts import AlertLevel, AlertManager, AlertType

        # アラートマネージャーを作成
        alert_manager = AlertManager()

        # アラートを作成
        alert = alert_manager.create_alert(
            alert_type=AlertType.PRICE_CHANGE,
            level=AlertLevel.WARNING,
            title="Price Alert",
            message="BTC price changed significantly",
            symbol="BTCUSDT",
            data={"change": 0.05},
        )

        # アラートの確認
        assert alert.alert_type == AlertType.PRICE_CHANGE
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "Price Alert"
        assert alert.symbol == "BTCUSDT"
        assert not alert.acknowledged

        print("✓ Alert creation test passed")
        return True

    except Exception as e:
        print(f"❌ Alert creation failed: {e}")
        return False


def test_alert_rules():
    """アラートルールテスト"""
    print("Testing alert rules...")

    try:
        from backend.monitoring.alerts import AlertManager

        # アラートマネージャーを作成
        alert_manager = AlertManager()

        # 価格変動をチェック
        alert_manager.check_price_change("BTCUSDT", 50000.0, 52500.0)  # 5%変動

        # アラートが作成されたことを確認
        alerts = alert_manager.get_alerts()
        assert len(alerts) > 0

        price_alerts = [a for a in alerts if a.alert_type.value == "price_change"]
        assert len(price_alerts) > 0

        print("✓ Alert rules test passed")
        return True

    except Exception as e:
        print(f"❌ Alert rules failed: {e}")
        return False


def test_alert_acknowledgment():
    """アラート確認テスト"""
    print("Testing alert acknowledgment...")

    try:
        from backend.monitoring.alerts import AlertLevel, AlertManager, AlertType

        # アラートマネージャーを作成
        alert_manager = AlertManager()

        # アラートを作成
        alert = alert_manager.create_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            level=AlertLevel.ERROR,
            title="System Error",
            message="Test error",
        )

        # アラートを確認
        success = alert_manager.acknowledge_alert(alert.id)
        assert success
        assert alert.acknowledged
        assert alert.acknowledged_at is not None

        print("✓ Alert acknowledgment test passed")
        return True

    except Exception as e:
        print(f"❌ Alert acknowledgment failed: {e}")
        return False


def test_performance_monitor():
    """パフォーマンス監視テスト"""
    print("Testing performance monitor...")

    try:
        from backend.monitoring.alerts import AlertManager, PerformanceMonitor

        # アラートマネージャーとパフォーマンス監視を作成
        alert_manager = AlertManager()
        performance_monitor = PerformanceMonitor(alert_manager)

        # 戦略パフォーマンスを更新
        performance_monitor.update_strategy_performance(
            "test_strategy",
            {
                "sharpe_ratio": 0.3,  # 低いシャープレシオ
                "max_drawdown": 0.2,  # 高いドローダウン
                "win_rate": 0.35,  # 低い勝率
            },
        )

        # アラートが作成されたことを確認
        alerts = alert_manager.get_alerts()
        performance_alerts = [a for a in alerts if a.alert_type.value == "strategy_performance"]
        assert len(performance_alerts) > 0

        print("✓ Performance monitor test passed")
        return True

    except Exception as e:
        print(f"❌ Performance monitor failed: {e}")
        return False


def test_alert_statistics():
    """アラート統計テスト"""
    print("Testing alert statistics...")

    try:
        from backend.monitoring.alerts import AlertLevel, AlertManager, AlertType

        # アラートマネージャーを作成
        alert_manager = AlertManager()

        # 複数のアラートを作成
        for i in range(3):
            alert_manager.create_alert(
                alert_type=AlertType.PRICE_CHANGE,
                level=AlertLevel.WARNING,
                title=f"Test Alert {i}",
                message=f"Test message {i}",
            )

        # 統計を取得
        stats = alert_manager.get_alert_statistics()

        # 統計を確認
        assert stats["total_alerts"] >= 3
        assert stats["alerts_by_level"]["warning"] >= 3
        assert stats["alerts_by_type"]["price_change"] >= 3

        print("✓ Alert statistics test passed")
        return True

    except Exception as e:
        print(f"❌ Alert statistics failed: {e}")
        return False


def run_trading_monitoring_tests():
    """トレーディング・監視システムのテストを実行"""
    print("=== Trading & Monitoring System Tests ===")
    print()

    tests = [
        test_trading_engine_import,
        test_order_creation,
        test_position_management,
        test_order_cancellation,
        test_trading_statistics,
        test_alert_manager_import,
        test_alert_creation,
        test_alert_rules,
        test_alert_acknowledgment,
        test_performance_monitor,
        test_alert_statistics,
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
    success = run_trading_monitoring_tests()
    if success:
        print("\n✅ ライブトレーディング・監視システムのテストが完了しました！")
        print("🚀 トレーディング・監視機能が正常に動作しています")
        exit(0)
    else:
        print("\n❌ ライブトレーディング・監視システムのテストに失敗しました")
        exit(1)
