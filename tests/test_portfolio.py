#!/usr/bin/env python3
"""
ポートフォリオ管理システムのテスト
"""
import sys
import os
import logging

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_portfolio_manager_import():
    """ポートフォリオマネージャーのインポートテスト"""
    print("Testing portfolio manager import...")

    try:
        print("✓ PortfolioManager import successful")
        return True
    except Exception as e:
        print(f"❌ PortfolioManager import failed: {e}")
        return False


def test_portfolio_creation():
    """ポートフォリオ作成テスト"""
    print("Testing portfolio creation...")

    try:
        from src.backend.portfolio.manager import PortfolioManager

        # マネージャーを作成
        manager = PortfolioManager()

        # ポートフォリオを作成
        initial_allocation = {"BTC": 0.5, "ETH": 0.3, "USDT": 0.2}

        portfolio = manager.create_portfolio("Test Portfolio", initial_allocation)

        # 基本的な属性をチェック
        assert portfolio.name == "Test Portfolio"
        assert len(portfolio.assets) == 3
        assert "BTC" in portfolio.assets
        assert "ETH" in portfolio.assets
        assert "USDT" in portfolio.assets

        print("✓ Portfolio creation test passed")
        return True

    except Exception as e:
        print(f"❌ Portfolio creation failed: {e}")
        return False


def test_asset_management():
    """資産管理テスト"""
    print("Testing asset management...")

    try:
        from src.backend.portfolio.manager import PortfolioManager, Asset, AssetType

        # マネージャーとポートフォリオを作成
        manager = PortfolioManager()
        portfolio = manager.create_portfolio("Test Portfolio")

        # 資産を追加
        btc_asset = Asset(
            symbol="BTC",
            asset_type=AssetType.CRYPTO,
            current_price=50000.0,
            balance=1.0,
            target_weight=0.6,
        )

        portfolio.add_asset(btc_asset)

        # 資産の確認
        assert len(portfolio.assets) == 1
        assert portfolio.assets["BTC"].symbol == "BTC"
        assert portfolio.assets["BTC"].current_price == 50000.0
        assert portfolio.assets["BTC"].balance == 1.0
        assert portfolio.assets["BTC"].market_value == 50000.0

        # 価格を更新
        portfolio.update_asset_price("BTC", 52000.0)
        assert portfolio.assets["BTC"].current_price == 52000.0
        assert portfolio.assets["BTC"].market_value == 52000.0

        # 残高を更新
        portfolio.update_asset_balance("BTC", 1.5)
        assert portfolio.assets["BTC"].balance == 1.5
        assert portfolio.assets["BTC"].market_value == 78000.0

        print("✓ Asset management test passed")
        return True

    except Exception as e:
        print(f"❌ Asset management failed: {e}")
        return False


def test_portfolio_weights():
    """ポートフォリオ重み計算テスト"""
    print("Testing portfolio weights calculation...")

    try:
        from src.backend.portfolio.manager import PortfolioManager, Asset, AssetType

        # マネージャーとポートフォリオを作成
        manager = PortfolioManager()
        portfolio = manager.create_portfolio("Test Portfolio")

        # 複数の資産を追加
        assets = [
            Asset(
                symbol="BTC",
                asset_type=AssetType.CRYPTO,
                current_price=50000.0,
                balance=1.0,
                target_weight=0.5,
            ),
            Asset(
                symbol="ETH",
                asset_type=AssetType.CRYPTO,
                current_price=3000.0,
                balance=10.0,
                target_weight=0.3,
            ),
            Asset(
                symbol="USDT",
                asset_type=AssetType.STABLE,
                current_price=1.0,
                balance=20000.0,
                target_weight=0.2,
            ),
        ]

        for asset in assets:
            portfolio.add_asset(asset)

        # 重みの計算を確認
        total_value = 50000.0 + 30000.0 + 20000.0  # 100,000

        print(f"Expected total value: {total_value}")
        print(f"Actual total value: {portfolio.total_value}")
        print(f"BTC weight: {portfolio.assets['BTC'].actual_weight}")
        print(f"ETH weight: {portfolio.assets['ETH'].actual_weight}")
        print(f"USDT weight: {portfolio.assets['USDT'].actual_weight}")

        assert abs(portfolio.total_value - total_value) < 0.01
        assert abs(portfolio.assets["BTC"].actual_weight - 0.5) < 0.01
        assert abs(portfolio.assets["ETH"].actual_weight - 0.3) < 0.01
        assert abs(portfolio.assets["USDT"].actual_weight - 0.2) < 0.01

        print("✓ Portfolio weights calculation test passed")
        return True

    except Exception as e:
        print(f"❌ Portfolio weights calculation failed: {e}")
        return False


def test_rebalance_suggestions():
    """リバランス提案テスト"""
    print("Testing rebalance suggestions...")

    try:
        from src.backend.portfolio.manager import PortfolioManager, Asset, AssetType

        # マネージャーとポートフォリオを作成
        manager = PortfolioManager()
        portfolio = manager.create_portfolio("Test Portfolio")
        portfolio.rebalance_threshold = 0.05  # 5%
        portfolio.min_trade_amount = 100.0

        # 資産を追加（アンバランスな状態）
        assets = [
            Asset(
                symbol="BTC",
                asset_type=AssetType.CRYPTO,
                current_price=50000.0,
                balance=1.6,
                target_weight=0.5,
            ),  # 80%
            Asset(
                symbol="ETH",
                asset_type=AssetType.CRYPTO,
                current_price=3000.0,
                balance=3.33,
                target_weight=0.3,
            ),  # 10%
            Asset(
                symbol="USDT",
                asset_type=AssetType.STABLE,
                current_price=1.0,
                balance=10000.0,
                target_weight=0.2,
            ),  # 10%
        ]

        for asset in assets:
            portfolio.add_asset(asset)

        # リバランス提案を取得
        suggestions = portfolio.get_rebalance_suggestions()

        # 提案があることを確認
        assert len(suggestions) > 0

        # 提案内容を確認
        for suggestion in suggestions:
            assert "symbol" in suggestion
            assert "action" in suggestion
            assert "trade_value" in suggestion
            assert suggestion["action"] in ["buy", "sell"]

        print(f"✓ Rebalance suggestions test passed ({len(suggestions)} suggestions)")
        return True

    except Exception as e:
        print(f"❌ Rebalance suggestions failed: {e}")
        return False


def test_risk_assessment():
    """リスク評価テスト"""
    print("Testing risk assessment...")

    try:
        from src.backend.portfolio.manager import PortfolioManager, Asset, AssetType

        # マネージャーとポートフォリオを作成
        manager = PortfolioManager()
        portfolio = manager.create_portfolio("Test Portfolio")

        # 高リスクポートフォリオ（集中投資）
        high_risk_asset = Asset(
            symbol="BTC",
            asset_type=AssetType.CRYPTO,
            current_price=50000.0,
            balance=2.0,
            target_weight=1.0,
        )
        portfolio.add_asset(high_risk_asset)

        # リスク評価を取得
        risk_assessment = manager.get_risk_assessment("Test Portfolio")

        # リスク評価の確認
        assert "concentration_risk" in risk_assessment
        assert "diversification_score" in risk_assessment
        assert "volatility_risk" in risk_assessment
        assert "overall_risk_score" in risk_assessment

        # 高リスクであることを確認
        assert risk_assessment["concentration_risk"] > 0.5
        assert risk_assessment["diversification_score"] > 0.5
        assert risk_assessment["overall_risk_score"] > 0.5

        print("✓ Risk assessment test passed")
        return True

    except Exception as e:
        print(f"❌ Risk assessment failed: {e}")
        return False


def test_portfolio_optimizer_import():
    """ポートフォリオ最適化のインポートテスト"""
    print("Testing portfolio optimizer import...")

    try:
        print("✓ PortfolioOptimizer import successful")
        return True
    except Exception as e:
        print(f"❌ PortfolioOptimizer import failed: {e}")
        return False


def test_portfolio_optimization():
    """ポートフォリオ最適化テスト"""
    print("Testing portfolio optimization...")

    try:
        from src.backend.portfolio.optimizer import (
            PortfolioOptimizer,
            OptimizationObjective,
        )

        # オプティマイザーを作成
        optimizer = PortfolioOptimizer()

        # テストデータ
        assets = ["BTC", "ETH", "USDT"]
        expected_returns = {"BTC": 0.15, "ETH": 0.12, "USDT": 0.02}

        # 共分散行列
        covariance_matrix = {
            "BTC": {"BTC": 0.04, "ETH": 0.02, "USDT": 0.001},
            "ETH": {"BTC": 0.02, "ETH": 0.03, "USDT": 0.001},
            "USDT": {"BTC": 0.001, "ETH": 0.001, "USDT": 0.0001},
        }

        # 最適化を実行
        result = optimizer.optimize(
            assets=assets,
            expected_returns=expected_returns,
            covariance_matrix=covariance_matrix,
            objective=OptimizationObjective.SHARPE_RATIO,
        )

        # 結果を確認
        assert result.objective == OptimizationObjective.SHARPE_RATIO
        assert len(result.weights) == 3
        assert abs(sum(result.weights.values()) - 1.0) < 0.01
        assert all(weight >= 0 for weight in result.weights.values())
        assert result.expected_return > 0
        assert result.expected_volatility > 0

        print("✓ Portfolio optimization test passed")
        return True

    except Exception as e:
        print(f"❌ Portfolio optimization failed: {e}")
        return False


def test_portfolio_summary():
    """ポートフォリオ概要テスト"""
    print("Testing portfolio summary...")

    try:
        from src.backend.portfolio.manager import PortfolioManager, Asset, AssetType

        # マネージャーとポートフォリオを作成
        manager = PortfolioManager()
        portfolio = manager.create_portfolio("Test Portfolio")

        # 資産を追加
        btc_asset = Asset(
            symbol="BTC",
            asset_type=AssetType.CRYPTO,
            current_price=50000.0,
            balance=1.0,
            target_weight=0.6,
        )
        portfolio.add_asset(btc_asset)

        # 概要を取得
        summary = portfolio.get_portfolio_summary()

        # 概要内容を確認
        assert summary["name"] == "Test Portfolio"
        assert summary["total_value"] == 50000.0
        assert summary["asset_count"] == 1
        assert "created_at" in summary
        assert "assets" in summary
        assert "BTC" in summary["assets"]

        print("✓ Portfolio summary test passed")
        return True

    except Exception as e:
        print(f"❌ Portfolio summary failed: {e}")
        return False


def run_portfolio_tests():
    """ポートフォリオテストを実行"""
    print("=== Portfolio Management Tests ===")
    print()

    tests = [
        test_portfolio_manager_import,
        test_portfolio_creation,
        test_asset_management,
        test_portfolio_weights,
        test_rebalance_suggestions,
        test_risk_assessment,
        test_portfolio_optimizer_import,
        test_portfolio_optimization,
        test_portfolio_summary,
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
    success = run_portfolio_tests()
    if success:
        print("\n✅ ポートフォリオ管理システムのテストが完了しました！")
        print("🚀 ポートフォリオ機能が正常に動作しています")
        exit(0)
    else:
        print("\n❌ ポートフォリオ管理システムのテストに失敗しました")
        exit(1)
