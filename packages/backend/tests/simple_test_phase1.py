#!/usr/bin/env python3
"""
Phase 1 の基本的なテスト（pytest不要）
"""
import sys
import os
from datetime import datetime, timezone

# テスト用のパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.exchanges.base import TimeFrame, OHLCV
from backend.exchanges.factory import ExchangeFactory
from backend.data_pipeline.collector import DataCollector
from backend.data_pipeline.onchain import OnChainDataCollector


def test_timeframe_enum():
    """TimeFrameの値テスト"""
    print("Testing TimeFrame enum...")
    assert TimeFrame.MINUTE_1.value == "1m"
    assert TimeFrame.HOUR_1.value == "1h"
    assert TimeFrame.DAY_1.value == "1d"
    print("✓ TimeFrame enum test passed")


def test_ohlcv_dataclass():
    """OHLCV データクラスのテスト"""
    print("Testing OHLCV dataclass...")
    now = datetime.now(timezone.utc)
    ohlcv = OHLCV(
        timestamp=now, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0
    )

    assert ohlcv.timestamp == now
    assert ohlcv.open == 100.0
    assert ohlcv.high == 110.0
    assert ohlcv.low == 90.0
    assert ohlcv.close == 105.0
    assert ohlcv.volume == 1000.0
    print("✓ OHLCV dataclass test passed")


def test_exchange_factory():
    """ExchangeFactoryのテスト"""
    print("Testing ExchangeFactory...")
    supported = ExchangeFactory.get_supported_exchanges()
    assert "binance" in supported
    assert "bybit" in supported
    print("✓ ExchangeFactory test passed")


def test_data_collector_initialization():
    """DataCollectorの初期化テスト"""
    print("Testing DataCollector initialization...")
    collector = DataCollector()
    assert collector.exchange_name == "binance"
    assert collector.adapter is None
    assert len(collector.symbols) == 8
    assert "BTC/USDT" in collector.symbols
    print("✓ DataCollector initialization test passed")


def test_onchain_collector_initialization():
    """OnChainDataCollectorの初期化テスト"""
    print("Testing OnChainDataCollector initialization...")
    collector = OnChainDataCollector()
    assert collector.glassnode_client is None
    assert collector.cryptoquant_client is None
    assert collector.symbols == ["BTC", "ETH"]
    print("✓ OnChainDataCollector initialization test passed")


def test_directory_structure():
    """ディレクトリ構造のテスト"""
    print("Testing directory structure...")
    from pathlib import Path

    # 基本的なディレクトリ構造の確認
    backend_dir = Path("backend")
    assert backend_dir.exists(), "backend directory should exist"

    exchanges_dir = backend_dir / "exchanges"
    assert exchanges_dir.exists(), "exchanges directory should exist"

    data_pipeline_dir = backend_dir / "data_pipeline"
    assert data_pipeline_dir.exists(), "data_pipeline directory should exist"

    print("✓ Directory structure test passed")


def test_imports():
    """必要なモジュールのインポートテスト"""
    print("Testing imports...")

    try:
        from backend.exchanges.base import AbstractExchangeAdapter
        from backend.exchanges.binance import BinanceAdapter
        from backend.exchanges.bybit import BybitAdapter
        from backend.exchanges.factory import ExchangeFactory
        from backend.data_pipeline.collector import DataCollector
        from backend.data_pipeline.onchain import OnChainDataCollector

        print("✓ All required imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        raise


def test_basic_functionality():
    """基本機能のテスト"""
    print("Testing basic functionality...")

    # Exchange Factory
    try:
        supported_exchanges = ExchangeFactory.get_supported_exchanges()
        assert len(supported_exchanges) >= 2
        print(f"✓ Supported exchanges: {supported_exchanges}")
    except Exception as e:
        print(f"❌ Exchange factory error: {e}")
        raise

    # Data Collector
    try:
        collector = DataCollector("binance")
        assert collector.exchange_name == "binance"
        print("✓ Data collector creation successful")
    except Exception as e:
        print(f"❌ Data collector error: {e}")
        raise

    # OnChain Collector
    try:
        onchain_collector = OnChainDataCollector()
        assert onchain_collector.symbols == ["BTC", "ETH"]
        print("✓ OnChain collector creation successful")
    except Exception as e:
        print(f"❌ OnChain collector error: {e}")
        raise


def run_all_tests():
    """全てのテストを実行"""
    print("=== Phase 1 Tests ===")
    print()

    tests = [
        test_timeframe_enum,
        test_ohlcv_dataclass,
        test_exchange_factory,
        test_data_collector_initialization,
        test_onchain_collector_initialization,
        test_directory_structure,
        test_imports,
        test_basic_functionality,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()

    print("=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All Phase 1 tests passed!")
        return True
    else:
        print(f"\n❌ {failed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n✅ Phase 1 の実装とテストが完了しました！")
        print("🚀 Phase 2 - バックテスト基盤の実装に進みます...")
        exit(0)
    else:
        print("\n❌ Phase 1 のテストに失敗しました")
        exit(1)
