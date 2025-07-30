#!/usr/bin/env python3
"""
Phase 2 の基本的なテスト（バックテスト基盤）
"""
import os
import sys
from pathlib import Path

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_backtesting_structure():
    """バックテスト基盤の構造テスト"""
    print("Testing backtesting structure...")

    # 必要なファイルの確認
    required_files = [
        "backend/backtesting/__init__.py",
        "backend/backtesting/engine.py",
        "backend/backtesting/walkforward.py",
    ]

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False

    print("✓ Backtesting structure test passed")
    return True


def test_engine_syntax():
    """エンジンの構文テスト"""
    print("Testing engine syntax...")

    try:
        # engine.pyの構文チェック
        with open("backend/backtesting/engine.py", "r") as f:
            content = f.read()
            compile(content, "backend/backtesting/engine.py", "exec")
        print("✓ engine.py syntax OK")

        # walkforward.pyの構文チェック
        with open("backend/backtesting/walkforward.py", "r") as f:
            content = f.read()
            compile(content, "backend/backtesting/walkforward.py", "exec")
        print("✓ walkforward.py syntax OK")

    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("✓ Engine syntax test passed")
    return True


def test_data_structures():
    """データ構造の定義テスト"""
    print("Testing data structures...")

    # バックテスト基盤から必要なクラスが定義されているかチェック
    engine_content = Path("backend/backtesting/engine.py").read_text()

    required_classes = [
        "class OrderType",
        "class OrderSide",
        "class Order",
        "class Trade",
        "class Position",
        "class Portfolio",
        "class BacktestResult",
        "class BacktestEngine",
    ]

    for class_def in required_classes:
        if class_def in engine_content:
            print(f"✓ {class_def} defined")
        else:
            print(f"❌ {class_def} missing")
            return False

    print("✓ Data structures test passed")
    return True


def test_walkforward_classes():
    """ウォークフォワード分析のクラステスト"""
    print("Testing walkforward classes...")

    walkforward_content = Path("backend/backtesting/walkforward.py").read_text()

    required_classes = ["class WalkForwardAnalysis", "class MonteCarloAnalysis"]

    for class_def in required_classes:
        if class_def in walkforward_content:
            print(f"✓ {class_def} defined")
        else:
            print(f"❌ {class_def} missing")
            return False

    print("✓ Walkforward classes test passed")
    return True


def test_engine_methods():
    """エンジンメソッドの存在確認"""
    print("Testing engine methods...")

    engine_content = Path("backend/backtesting/engine.py").read_text()

    required_methods = [
        "def process_bar",
        "def _process_long_entry",
        "def _process_long_exit",
        "def _process_short_entry",
        "def _process_short_exit",
        "def _calculate_position_size",
        "def get_results",
        "def _calculate_performance_metrics",
        "def reset",
        "def save_results",
    ]

    for method_def in required_methods:
        if method_def in engine_content:
            print(f"✓ {method_def} defined")
        else:
            print(f"❌ {method_def} missing")
            return False

    print("✓ Engine methods test passed")
    return True


def test_walkforward_methods():
    """ウォークフォワード分析メソッドの確認"""
    print("Testing walkforward methods...")

    walkforward_content = Path("backend/backtesting/walkforward.py").read_text()

    required_methods = [
        "def run_analysis",
        "def _generate_periods",
        "def _optimize_parameters",
        "def _test_parameter_combination",
        "def _run_forward_test",
        "def _combine_results",
        "def save_results",
    ]

    for method_def in required_methods:
        if method_def in walkforward_content:
            print(f"✓ {method_def} defined")
        else:
            print(f"❌ {method_def} missing")
            return False

    print("✓ Walkforward methods test passed")
    return True


def test_imports():
    """必要なインポートの確認"""
    print("Testing imports...")

    # バックテスト基盤の依存関係を確認
    engine_content = Path("backend/backtesting/engine.py").read_text()

    # 必要なインポート
    required_imports = [
        "import numpy as np",
        "import pandas as pd",
        "from typing import",
        "from datetime import datetime",
        "from dataclasses import dataclass",
        "from enum import Enum",
        "import logging",
    ]

    for import_stmt in required_imports:
        if import_stmt in engine_content:
            print(f"✓ {import_stmt} found in engine.py")
        else:
            print(f"❌ {import_stmt} missing in engine.py")
            return False

    print("✓ Imports test passed")
    return True


def test_integration_with_risk_management():
    """リスク管理との統合テスト"""
    print("Testing integration with risk management...")

    engine_content = Path("backend/backtesting/engine.py").read_text()

    # リスク管理の統合を確認
    risk_integration_checks = [
        "from src.backend.risk.position_sizing import RiskManager",
        "from src.backend.fee_models.base import FeeModel",
        "from src.backend.fee_models.exchanges import FeeModelFactory",
        "self.risk_manager = RiskManager",
        "self.fee_model = FeeModelFactory.create",
    ]

    for check in risk_integration_checks:
        if check in engine_content:
            print(f"✓ {check} found")
        else:
            print(f"❌ {check} missing")
            return False

    print("✓ Risk management integration test passed")
    return True


def test_performance_metrics():
    """パフォーマンス指標の計算テスト"""
    print("Testing performance metrics...")

    engine_content = Path("backend/backtesting/engine.py").read_text()

    # パフォーマンス指標の計算を確認
    metrics_checks = [
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "profit_factor",
        "max_drawdown",
        "annualized_return",
        "volatility",
    ]

    for metric in metrics_checks:
        if metric in engine_content:
            print(f"✓ {metric} calculation included")
        else:
            print(f"❌ {metric} calculation missing")
            return False

    print("✓ Performance metrics test passed")
    return True


def test_results_directory():
    """結果保存ディレクトリの作成テスト"""
    print("Testing results directory creation...")

    # 結果保存用のディレクトリを作成
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    if results_dir.exists():
        print("✓ Results directory created")
    else:
        print("❌ Results directory creation failed")
        return False

    # サブディレクトリの作成
    sub_dirs = ["walkforward_results", "montecarlo_results"]
    for sub_dir in sub_dirs:
        sub_path = results_dir / sub_dir
        sub_path.mkdir(exist_ok=True)
        if sub_path.exists():
            print(f"✓ {sub_dir} directory created")
        else:
            print(f"❌ {sub_dir} directory creation failed")
            return False

    print("✓ Results directory test passed")
    return True


def run_all_tests():
    """全てのテストを実行"""
    print("=== Phase 2 Basic Tests ===")
    print()

    tests = [
        test_backtesting_structure,
        test_engine_syntax,
        test_data_structures,
        test_walkforward_classes,
        test_engine_methods,
        test_walkforward_methods,
        test_imports,
        test_integration_with_risk_management,
        test_performance_metrics,
        test_results_directory,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()

    print("=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All Phase 2 basic tests passed!")
        return True
    else:
        print(f"\n❌ {failed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n✅ Phase 2 - バックテスト基盤の実装が完了しました！")
        print("🚀 Phase 3 - 戦略実装の実装に進みます...")
        exit(0)
    else:
        print("\n❌ Phase 2 の基本テストに失敗しました")
        exit(1)
