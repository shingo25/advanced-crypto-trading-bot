#!/usr/bin/env python3
"""
Market Data API テストスクリプト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx

API_BASE_URL = "http://localhost:8000"


async def test_market_data_endpoints():
    """Market Data APIエンドポイントをテスト"""
    async with httpx.AsyncClient() as client:
        print("🧪 Market Data API エンドポイントテスト開始")
        print(f"📡 API Base URL: {API_BASE_URL}")
        print("-" * 50)

        # 1. ヘルスチェック
        print("1️⃣ ヘルスチェック")
        try:
            response = await client.get(f"{API_BASE_URL}/api/market-data/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ ヘルスチェック成功: {health_data}")
            else:
                print(f"❌ ヘルスチェック失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ ヘルスチェックエラー: {e}")

        print()

        # 2. 利用可能なシンボル取得
        print("2️⃣ 利用可能なシンボル取得")
        try:
            response = await client.get(f"{API_BASE_URL}/api/market-data/symbols")
            if response.status_code == 200:
                symbols_data = response.json()
                symbols = symbols_data.get("symbols", [])
                print(f"✅ シンボル取得成功: {len(symbols)}個のシンボル")
                print(f"   📋 シンボル例: {symbols[:5]}")
            else:
                print(f"❌ シンボル取得失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ シンボル取得エラー: {e}")

        print()

        # 3. 利用可能な時間足取得
        print("3️⃣ 利用可能な時間足取得")
        try:
            response = await client.get(f"{API_BASE_URL}/api/market-data/timeframes")
            if response.status_code == 200:
                timeframes_data = response.json()
                timeframes = timeframes_data.get("timeframes", [])
                print(f"✅ 時間足取得成功: {timeframes}")
            else:
                print(f"❌ 時間足取得失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 時間足取得エラー: {e}")

        print()

        # 4. OHLCVデータ取得（BTCUSDT）
        print("4️⃣ OHLCVデータ取得（BTCUSDT, 1h, 10件）")
        try:
            params = {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 10}
            response = await client.get(
                f"{API_BASE_URL}/api/market-data/ohlcv", params=params
            )
            if response.status_code == 200:
                ohlcv_data = response.json()
                print(f"✅ OHLCVデータ取得成功: {len(ohlcv_data)}件")
                if ohlcv_data:
                    latest = ohlcv_data[-1]
                    print(
                        f"   📊 最新データ: {latest['timestamp']} - Close: ${latest['close']:,.2f}"
                    )
            else:
                print(f"❌ OHLCVデータ取得失敗: {response.status_code}")
                print(f"   レスポンス: {response.text}")
        except Exception as e:
            print(f"❌ OHLCVデータ取得エラー: {e}")

        print()

        # 5. 最新価格取得
        print("5️⃣ 最新価格取得")
        try:
            params = {"symbols": "BTCUSDT,ETHUSDT", "timeframe": "1h"}
            response = await client.get(
                f"{API_BASE_URL}/api/market-data/latest", params=params
            )
            if response.status_code == 200:
                latest_data = response.json()
                latest_prices = latest_data.get("latest_prices", [])
                print(f"✅ 最新価格取得成功: {len(latest_prices)}件")
                for price in latest_prices:
                    print(f"   💰 {price['symbol']}: ${price['close']:,.2f}")
            else:
                print(f"❌ 最新価格取得失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 最新価格取得エラー: {e}")

        print()


async def test_performance_endpoints():
    """Performance APIエンドポイントをテスト"""
    async with httpx.AsyncClient() as client:
        print("🧪 Performance API エンドポイントテスト開始")
        print("-" * 50)

        # 1. ヘルスチェック
        print("1️⃣ Performance ヘルスチェック")
        try:
            response = await client.get(f"{API_BASE_URL}/api/performance/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ ヘルスチェック成功: {health_data}")
            else:
                print(f"❌ ヘルスチェック失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ ヘルスチェックエラー: {e}")

        print()

        # 2. パフォーマンス履歴取得
        print("2️⃣ パフォーマンス履歴取得（7日間）")
        try:
            params = {"period": "7d"}
            response = await client.get(
                f"{API_BASE_URL}/api/performance/history", params=params
            )
            if response.status_code == 200:
                performance_data = response.json()
                print(f"✅ パフォーマンス履歴取得成功: {len(performance_data)}件")
                if performance_data:
                    latest = performance_data[-1]
                    print(
                        f"   📈 最新: ${latest['total_value']:,.2f} (累積リターン: {latest['cumulative_return']:.2%})"
                    )
            else:
                print(f"❌ パフォーマンス履歴取得失敗: {response.status_code}")
                print(f"   レスポンス: {response.text}")
        except Exception as e:
            print(f"❌ パフォーマンス履歴取得エラー: {e}")

        print()

        # 3. パフォーマンスサマリー取得
        print("3️⃣ パフォーマンスサマリー取得")
        try:
            response = await client.get(f"{API_BASE_URL}/api/performance/summary")
            if response.status_code == 200:
                summary_data = response.json()
                print("✅ パフォーマンスサマリー取得成功")
                print(f"   💼 総資産: ${summary_data['total_value']:,.2f}")
                print(f"   📊 累積リターン: {summary_data['cumulative_return']:.2%}")
                print(f"   📉 最大ドローダウン: {summary_data['max_drawdown']:.2%}")
                print(f"   📐 シャープレシオ: {summary_data['sharpe_ratio']:.3f}")
            else:
                print(f"❌ パフォーマンスサマリー取得失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ パフォーマンスサマリー取得エラー: {e}")

        print()


async def main():
    """メイン関数"""
    print("🚀 Crypto Bot API テスト開始")
    print("=" * 60)

    try:
        await test_market_data_endpoints()
        print()
        await test_performance_endpoints()

        print("=" * 60)
        print("✅ APIテスト完了")

    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
