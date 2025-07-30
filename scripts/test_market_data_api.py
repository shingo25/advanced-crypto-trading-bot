#!/usr/bin/env python3
"""
Market Data API テストスクリプト

APIエンドポイントの実データ対応機能をテストします。
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# API Base URL
API_BASE_URL = "http://localhost:8000"


async def test_api_endpoint(session: aiohttp.ClientSession, endpoint: str, params: dict = None):
    """APIエンドポイントをテスト"""
    url = f"{API_BASE_URL}{endpoint}"

    print(f"\n🔍 Testing: {endpoint}")
    print(f"📍 URL: {url}")
    if params:
        print(f"📊 Params: {params}")

    try:
        async with session.get(url, params=params) as response:
            print(f"📡 Status: {response.status}")

            if response.status == 200:
                data = await response.json()
                print(f"✅ Success: {len(data) if isinstance(data, list) else 'OK'}")

                # データの詳細を少し表示
                if isinstance(data, list) and data:
                    print(f"📄 Sample data: {json.dumps(data[0], indent=2, default=str)[:200]}...")
                elif isinstance(data, dict):
                    print(f"📄 Response: {json.dumps(data, indent=2, default=str)[:300]}...")

                return True
            else:
                error_text = await response.text()
                print(f"❌ Error: {response.status} - {error_text}")
                return False

    except Exception as e:
        print(f"🚨 Exception: {e}")
        return False


async def test_market_data_endpoints():
    """Market Data APIエンドポイントのテスト"""
    print("🧪 Market Data API エンドポイントテスト開始")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        test_results = []

        # 1. ヘルスチェック
        result = await test_api_endpoint(session, "/api/market-data/health")
        test_results.append(("Health Check", result))

        # 2. シンボル一覧
        result = await test_api_endpoint(session, "/api/market-data/symbols")
        test_results.append(("Symbols", result))

        # 3. 時間足一覧
        result = await test_api_endpoint(session, "/api/market-data/timeframes")
        test_results.append(("Timeframes", result))

        # 4. 最新価格
        result = await test_api_endpoint(session, "/api/market-data/latest", {"symbols": "BTCUSDT,ETHUSDT"})
        test_results.append(("Latest Prices", result))

        # 5. OHLCVデータ
        result = await test_api_endpoint(
            session,
            "/api/market-data/ohlcv",
            {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 10},
        )
        test_results.append(("OHLCV Data", result))

        # 6. OHLCVデータ（時間範囲指定）
        end_time = datetime.now(timezone.utc)
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await test_api_endpoint(
            session,
            "/api/market-data/ohlcv",
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )
        test_results.append(("OHLCV with Time Range", result))

        return test_results


async def test_performance_endpoints():
    """Performance APIエンドポイントのテスト"""
    print("\n🧪 Performance API エンドポイントテスト開始")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        test_results = []

        # 1. ヘルスチェック
        result = await test_api_endpoint(session, "/api/performance/health")
        test_results.append(("Performance Health", result))

        # 2. パフォーマンス履歴
        result = await test_api_endpoint(session, "/api/performance/history", {"period": "7d"})
        test_results.append(("Performance History", result))

        # 3. パフォーマンスサマリー
        result = await test_api_endpoint(session, "/api/performance/summary")
        test_results.append(("Performance Summary", result))

        return test_results


async def test_error_handling():
    """エラーハンドリングのテスト"""
    print("\n🧪 エラーハンドリングテスト開始")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        test_results = []

        # 1. 無効なシンボル
        result = await test_api_endpoint(session, "/api/market-data/ohlcv", {"symbol": "INVALID", "timeframe": "1h"})
        test_results.append(("Invalid Symbol", not result))  # エラーが期待される

        # 2. 無効な時間足
        result = await test_api_endpoint(
            session,
            "/api/market-data/ohlcv",
            {"symbol": "BTCUSDT", "timeframe": "invalid"},
        )
        test_results.append(("Invalid Timeframe", not result))  # エラーが期待される

        # 3. 無効な期間
        result = await test_api_endpoint(session, "/api/performance/history", {"period": "invalid"})
        test_results.append(("Invalid Period", not result))  # エラーが期待される

        return test_results


async def main():
    """メイン実行関数"""
    print("🚀 API エンドポイント総合テスト")
    print("=" * 60)
    print(f"📍 API Base URL: {API_BASE_URL}")
    print(f"🕒 Test Time: {datetime.now(timezone.utc)}")

    # サーバーが起動しているかチェック
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/") as response:
                if response.status != 200:
                    print("❌ サーバーが起動していません")
                    return
                print("✅ サーバー接続確認OK")
    except Exception as e:
        print(f"❌ サーバー接続エラー: {e}")
        print("💡 サーバーを起動してからテストを実行してください:")
        print("   uvicorn backend.main:app --reload")
        return

    # テスト実行
    all_results = []

    # Market Data API テスト
    market_results = await test_market_data_endpoints()
    all_results.extend(market_results)

    # Performance API テスト
    performance_results = await test_performance_endpoints()
    all_results.extend(performance_results)

    # エラーハンドリングテスト
    error_results = await test_error_handling()
    all_results.extend(error_results)

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー")
    print("-" * 60)

    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)

    for test_name, result in all_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    print("-" * 60)
    print(f"📊 合計: {passed}/{total} テスト通過")

    if passed == total:
        print("🎉 全てのテストが成功しました！")
        print("Phase2のAPIエンドポイント実装は正常に動作しています。")
    else:
        print(f"⚠️ {total - passed}個のテストが失敗しました。")
        print("ログを確認して問題を解決してください。")

    print("\n💡 次のステップ:")
    print("1. バックテスト機能の実データ対応")
    print("2. WebSocketリアルタイム通信実装")
    print("3. フロントエンド統合テスト")


if __name__ == "__main__":
    asyncio.run(main())
