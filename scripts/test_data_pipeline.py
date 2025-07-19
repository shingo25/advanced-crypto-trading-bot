#!/usr/bin/env python3
"""
データパイプライン機能の実動作テスト

このスクリプトは実際にBinance APIからデータを取得し、
Supabaseに保存する動作をテストします。

使用方法:
python scripts/test_data_pipeline.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.logging import setup_logging  # noqa: E402
from backend.data_pipeline.collector import DataCollector  # noqa: E402
from backend.exchanges.base import TimeFrame  # noqa: E402


async def test_basic_data_collection():
    """基本的なデータ収集テスト"""
    print("🚀 Phase2データパイプライン機能テスト開始")
    print("-" * 50)

    # ロガー設定
    setup_logging()

    # DataCollectorを初期化
    collector = DataCollector("binance")

    try:
        print("📡 BinanceAdapterを初期化中...")
        await collector.initialize()
        print("✅ BinanceAdapter初期化完了")

        # テスト用シンボルとタイムフレーム
        test_symbol = "BTC/USDT"
        test_timeframe = TimeFrame.HOUR_1

        print(f"📊 {test_symbol} {test_timeframe.value} データを取得中...")

        # 過去24時間のデータを取得
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        ohlcv_data = await collector.collect_ohlcv(
            symbol=test_symbol,
            timeframe=test_timeframe,
            since=since,
            limit=24,  # 24時間分
        )

        print(f"✅ {len(ohlcv_data)}件のOHLCVデータを取得")

        if ohlcv_data:
            # 最新データの詳細を表示
            latest = ohlcv_data[-1]
            print("📈 最新データ:")
            print(f"   時刻: {latest.timestamp}")
            print(f"   開始価格: ${latest.open:,.2f}")
            print(f"   終了価格: ${latest.close:,.2f}")
            print(f"   出来高: {latest.volume:,.2f}")

            # Supabaseへの保存テスト
            print("💾 Supabaseへの保存をテスト中...")
            await collector._save_ohlcv_to_supabase(
                symbol=test_symbol, timeframe=test_timeframe, ohlcv_data=ohlcv_data
            )
            print("✅ Supabaseへの保存完了")

        print("\n🎉 基本的なデータ収集テスト完了")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False

    finally:
        await collector.close()

    return True


async def test_batch_collection():
    """バッチ収集機能のテスト"""
    print("\n📦 バッチ収集機能テスト開始")
    print("-" * 50)

    collector = DataCollector("binance")

    try:
        await collector.initialize()

        # 複数シンボル・タイムフレームでテスト
        test_symbols = ["BTC/USDT", "ETH/USDT"]
        test_timeframes = [TimeFrame.HOUR_1, TimeFrame.HOUR_4]

        print(
            f"📊 {len(test_symbols)}シンボル × {len(test_timeframes)}タイムフレームでバッチ収集"
        )

        since = datetime.now(timezone.utc) - timedelta(hours=12)

        results = await collector.collect_batch_ohlcv(
            symbols=test_symbols, timeframes=test_timeframes, since=since
        )

        print("✅ バッチ収集完了")

        # 結果詳細
        for symbol, timeframe_data in results.items():
            print(f"  {symbol}:")
            for timeframe, ohlcv_list in timeframe_data.items():
                print(f"    {timeframe}: {len(ohlcv_list)}件")

        print("🎉 バッチ収集テスト完了")

    except Exception as e:
        print(f"❌ バッチ収集エラー: {e}")
        return False

    finally:
        await collector.close()

    return True


async def test_error_handling():
    """エラーハンドリングのテスト"""
    print("\n🛡️ エラーハンドリングテスト開始")
    print("-" * 50)

    collector = DataCollector("binance")

    try:
        await collector.initialize()

        # 存在しないシンボルでテスト
        print("📊 存在しないシンボルでエラーハンドリングをテスト")

        try:
            await collector.collect_ohlcv(
                symbol="INVALID/PAIR", timeframe=TimeFrame.HOUR_1, limit=1
            )
            print("❌ エラーが発生しなかった（想定外）")
            return False

        except Exception as e:
            print(f"✅ 期待通りエラーをキャッチ: {type(e).__name__}")

        print("🎉 エラーハンドリングテスト完了")

    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

    finally:
        await collector.close()

    return True


async def main():
    """メイン実行関数"""
    print("🧪 Phase2データパイプライン機能テスト")
    print("=" * 60)

    # 環境変数チェック
    required_env = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]

    if missing_env:
        print(f"❌ 必要な環境変数が不足しています: {missing_env}")
        print("💡 .envファイルを設定してください")
        return

    # テスト実行
    tests = [
        ("基本データ収集", test_basic_data_collection),
        ("バッチ収集", test_batch_collection),
        ("エラーハンドリング", test_error_handling),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}テスト実行中...")
        success = await test_func()
        results.append((test_name, success))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー")
    print("-" * 60)

    all_passed = True
    for test_name, success in results:
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False

    print("-" * 60)
    if all_passed:
        print("🎉 全てのテストが成功しました！")
        print("Phase2データパイプライン機能は正常に動作しています。")
    else:
        print("❌ いくつかのテストが失敗しました。")
        print("ログを確認して問題を解決してください。")

    print("\n💡 次のステップ:")
    print("1. GitHub Actionsでスケジューラーを設定")
    print("2. API エンドポイントの実データ対応")
    print("3. バックテスト機能の改善")


if __name__ == "__main__":
    asyncio.run(main())
