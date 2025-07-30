#!/usr/bin/env python3
"""
戦略APIのSupabase SDK対応をテストするスクリプト
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import uuid

from dotenv import load_dotenv

from src.backend.core.config import settings
from src.backend.core.security import authenticate_user
from src.backend.models.trading import get_strategies_model


async def setup_test_user():
    """テスト用ユーザーの認証情報を取得"""
    print("🔑 テスト用ユーザーの認証...")

    try:
        user = await authenticate_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
        if user:
            print(f"   ✅ 認証成功: {user['username']} (ID: {user['id']})")
            return user
        else:
            print("   ❌ 認証失敗")
            return None
    except Exception as e:
        print(f"   ❌ 認証エラー: {e}")
        return None


async def test_strategies_model():
    """StrategiesModelの直接テスト"""
    print("\n🎯 StrategiesModelの直接テスト...")

    try:
        user = await setup_test_user()
        if not user:
            return False

        strategies_model = get_strategies_model()
        user_id = user["id"]

        # 1. 既存戦略の取得
        print("   📊 既存戦略の取得...")
        existing_strategies = strategies_model.get_user_strategies(user_id)
        print(f"   📊 既存戦略数: {len(existing_strategies)}")

        # 2. 新しい戦略の作成
        print("   🆕 新しい戦略の作成...")
        test_strategy_name = f"テスト戦略 {uuid.uuid4().hex[:8]}"

        new_strategy = strategies_model.create_strategy(
            user_id=user_id,
            name=test_strategy_name,
            description="APIテスト用の戦略",
            parameters={
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "ema_fast": 12,
                "ema_slow": 26,
            },
            is_active=False,
        )

        if new_strategy:
            strategy_id = new_strategy["id"]
            print(f"   ✅ 戦略作成成功: {new_strategy['name']}")
            print(f"   📊 戦略ID: {strategy_id}")

            # 3. 戦略の取得
            print("   🔍 作成した戦略の取得...")
            retrieved_strategy = strategies_model.get_strategy_by_id(strategy_id)
            if retrieved_strategy:
                print(f"   ✅ 戦略取得成功: {retrieved_strategy['name']}")
            else:
                print("   ❌ 戦略取得失敗")

            # 4. 戦略の更新
            print("   📝 戦略の更新...")
            updated_strategy = strategies_model.update_strategy(
                strategy_id, description="更新されたテスト戦略", is_active=True
            )
            if updated_strategy and updated_strategy["is_active"]:
                print("   ✅ 戦略更新成功")
            else:
                print("   ❌ 戦略更新失敗")

            # 5. アクティブ戦略の取得
            print("   🎯 アクティブ戦略の取得...")
            active_strategies = strategies_model.get_active_strategies(user_id)
            print(f"   📊 アクティブ戦略数: {len(active_strategies)}")

            return True
        else:
            print("   ❌ 戦略作成失敗")
            return False

    except Exception as e:
        print(f"   ❌ StrategiesModelテストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_api_simulation():
    """戦略API エンドポイントのシミュレーション"""
    print("\n🌐 戦略API エンドポイントのシミュレーション...")

    try:
        user = await setup_test_user()
        if not user:
            return False

        # FastAPI Dependenciesをシミュレート
        current_user = user

        # strategies.pyの関数を直接呼び出してテスト
        from src.backend.api.strategies import (
            StrategyCreate,
            StrategyUpdate,
            create_strategy,
            get_strategies,
            get_strategy,
            update_strategy,
        )

        # 1. 戦略一覧取得のシミュレーション
        print("   📋 GET /strategies/ のシミュレーション...")
        strategies_list = await get_strategies(current_user)
        print(f"   ✅ 戦略一覧取得成功: {len(strategies_list)}件")

        # 2. 戦略作成のシミュレーション
        print("   🆕 POST /strategies/ のシミュレーション...")
        new_strategy_data = StrategyCreate(
            name=f"API Test Strategy {uuid.uuid4().hex[:8]}",
            description="API経由で作成されたテスト戦略",
            parameters={
                "symbol": "ETHUSDT",
                "strategy_type": "momentum",
                "risk_level": "medium",
            },
            is_active=False,
        )

        created_strategy = await create_strategy(new_strategy_data, current_user)
        if created_strategy:
            strategy_id = created_strategy.id
            print(f"   ✅ 戦略作成成功: {created_strategy.name}")
            print(f"   📊 戦略ID: {strategy_id}")

            # 3. 個別戦略取得のシミュレーション
            print("   🔍 GET /strategies/{strategy_id} のシミュレーション...")
            retrieved_strategy = await get_strategy(strategy_id, current_user)
            if retrieved_strategy:
                print(f"   ✅ 戦略取得成功: {retrieved_strategy.name}")
            else:
                print("   ❌ 戦略取得失敗")

            # 4. 戦略更新のシミュレーション
            print("   📝 PATCH /strategies/{strategy_id} のシミュレーション...")
            update_data = StrategyUpdate(description="APIで更新されたテスト戦略", is_active=True)

            updated_strategy = await update_strategy(strategy_id, update_data, current_user)
            if updated_strategy and updated_strategy.is_active:
                print("   ✅ 戦略更新成功")
            else:
                print("   ❌ 戦略更新失敗")

            return True
        else:
            print("   ❌ 戦略作成失敗")
            return False

    except Exception as e:
        print(f"   ❌ APIシミュレーションエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """メインテスト関数"""
    print("🧪 戦略API Supabase SDK対応の包括テスト")
    print("=" * 60)

    # 環境変数を読み込み
    load_dotenv()

    # テスト結果を追跡
    test_results = []

    # 1. StrategiesModelの直接テスト
    test_results.append(await test_strategies_model())

    # 2. API エンドポイントのシミュレーション
    test_results.append(await test_api_simulation())

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"   成功: {passed}/{total}")
    print(f"   成功率: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 Phase1-1.5 戦略API更新が完了しました！")
        print("🔄 次のステップ: trades.py と backtest.py の更新、またはAPIサーバーデプロイ")
        return True
    else:
        print("⚠️ 一部のテストで問題が発生しました")
        print("   修正が必要な可能性があります")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ 戦略API テスト完了")
    else:
        print("\n❌ 戦略APIに重大な問題があります")
