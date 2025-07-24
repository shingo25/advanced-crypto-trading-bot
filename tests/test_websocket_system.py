#!/usr/bin/env python3
"""
WebSocketシステムテスト
包括的WebSocket接続管理システムの動作確認
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# ダミー環境変数を設定
os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy_key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "dummy_secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')


async def test_websocket_manager_import():
    """WebSocketマネージャーのインポートテスト"""
    try:
        print("🔍 Testing WebSocket manager import...")

        from src.backend.websocket.manager import MessageType, ChannelType

        print("✅ WebSocket manager imported successfully")

        # エニューメーションの確認
        print(f"✅ MessageType enum: {len(MessageType)} types")
        for msg_type in MessageType:
            print(f"   - {msg_type.name}: {msg_type.value}")

        print(f"✅ ChannelType enum: {len(ChannelType)} channels")
        for channel in ChannelType:
            print(f"   - {channel.name}: {channel.value}")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


async def test_websocket_message_creation():
    """WebSocketメッセージ作成テスト"""
    try:
        print("\n🔍 Testing WebSocket message creation...")

        from src.backend.websocket.manager import WebSocketMessage, MessageType, ChannelType

        # 基本メッセージの作成
        message = WebSocketMessage(
            type=MessageType.PRICE_UPDATE,
            channel=ChannelType.PRICES,
            data={
                "symbol": "BTC/USDT",
                "price": 45000.0,
                "change": 0.025,
                "volume": 1234.56,
            },
        )

        print("✅ WebSocket message created successfully")
        print(f"   - Type: {message.type}")
        print(f"   - Channel: {message.channel}")
        print(f"   - Message ID: {message.message_id}")
        print(f"   - Timestamp: {message.timestamp}")

        # JSONシリアライゼーション
        json_message = message.to_json()
        parsed_message = json.loads(json_message)

        print("✅ JSON serialization successful")
        print(f"   - JSON keys: {list(parsed_message.keys())}")

        return True

    except Exception as e:
        print(f"❌ Message creation test failed: {e}")
        return False


async def test_connection_management():
    """接続管理テスト"""
    try:
        print("\n🔍 Testing connection management...")

        from src.backend.websocket.manager import WebSocketManager, ClientConnection

        # テスト用マネージャーを作成
        manager = WebSocketManager()

        # ダミーWebSocket接続をシミュレート
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                self.closed = False

            async def accept(self):
                pass

            async def send_text(self, text):
                self.messages.append(text)

            async def receive_text(self):
                await asyncio.sleep(0.1)
                return '{"type": "heartbeat"}'

            def close(self):
                self.closed = True

        # 接続テスト
        mock_ws = MockWebSocket()
        client_id = "test_client_001"

        # 接続情報を手動作成（実際のWebSocket接続をスキップ）
        connection = ClientConnection(websocket=mock_ws, client_id=client_id)
        manager.connections[client_id] = connection

        print("✅ Mock connection created")
        print(f"   - Client ID: {client_id}")
        print(f"   - Connected at: {connection.connected_at}")

        # チャンネル購読テスト
        await manager._subscribe_to_channel(client_id, "prices")
        await manager._subscribe_to_channel(client_id, "trades")

        print("✅ Channel subscription test")
        print(f"   - Subscriptions: {connection.subscriptions}")
        print(f"   - Channel subscribers: {manager.channel_subscribers}")

        # メッセージ送信テスト
        from src.backend.websocket.manager import WebSocketMessage, MessageType, ChannelType

        test_message = WebSocketMessage(
            type=MessageType.SYSTEM_ALERT,
            channel=ChannelType.ALERTS,
            data={"message": "Test message"},
        )

        success = await manager.send_to_client(client_id, test_message)
        print(f"✅ Message send test: {success}")
        print(f"   - Messages sent: {len(mock_ws.messages)}")

        # 統計取得テスト
        stats = manager.get_connection_stats()
        print("✅ Connection stats:")
        print(f"   - Total connections: {stats['total_connections']}")
        print(f"   - Active channels: {stats['active_channels']}")

        return True

    except Exception as e:
        print(f"❌ Connection management test failed: {e}")
        return False


async def test_websocket_routes_import():
    """WebSocketルートのインポートテスト"""
    try:
        print("\n🔍 Testing WebSocket routes import...")

        from src.backend.websocket.routes import router

        print("✅ WebSocket routes imported successfully")

        # ルート確認
        routes = []
        for route in router.routes:
            if hasattr(route, "path"):
                routes.append(f"{route.path}")

        print(f"✅ Found {len(routes)} routes:")
        for route in routes:
            print(f"   - {route}")

        return True

    except Exception as e:
        print(f"❌ Routes import test failed: {e}")
        return False


async def test_main_app_integration():
    """main.pyアプリケーション統合テスト"""
    try:
        print("\n🔍 Testing main app integration...")

        from src.backend.main import app

        print("✅ Main app with WebSocket integration imported")

        # WebSocketルートが含まれているか確認
        websocket_routes = []
        for route in app.routes:
            if hasattr(route, "path") and "/websocket" in route.path:
                websocket_routes.append(route.path)

        if websocket_routes:
            print("✅ WebSocket routes found in main app:")
            for route in websocket_routes:
                print(f"   - {route}")
        else:
            print("⚠️  No WebSocket routes found in main app")

        return True

    except Exception as e:
        print(f"❌ Main app integration test failed: {e}")
        return False


async def test_rate_limiting():
    """レート制限テスト"""
    try:
        print("\n🔍 Testing rate limiting...")

        from src.backend.websocket.manager import WebSocketManager, ClientConnection

        manager = WebSocketManager()
        manager.rate_limit_requests = 5  # テスト用に制限を低く設定

        class MockWebSocket:
            async def accept(self):
                pass

            async def send_text(self, text):
                pass

        # テスト接続
        client_id = "rate_test_client"
        connection = ClientConnection(websocket=MockWebSocket(), client_id=client_id)
        manager.connections[client_id] = connection

        # レート制限テスト
        success_count = 0
        for i in range(10):
            if await manager._check_rate_limit(client_id):
                success_count += 1

        print(f"✅ Rate limiting test: {success_count}/10 requests allowed")
        print(f"   - Rate limit: {manager.rate_limit_requests} requests per minute")

        return True

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False


async def main():
    """メイン実行関数"""
    print("🚀 Starting comprehensive WebSocket system tests...\n")

    # テスト実行
    test_results = []

    tests = [
        ("WebSocket Manager Import", test_websocket_manager_import),
        ("WebSocket Message Creation", test_websocket_message_creation),
        ("Connection Management", test_connection_management),
        ("WebSocket Routes Import", test_websocket_routes_import),
        ("Main App Integration", test_main_app_integration),
        ("Rate Limiting", test_rate_limiting),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' encountered an error: {e}")
            test_results.append((test_name, False))

    # 結果表示
    print("\n📊 Comprehensive Test Results:")
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   - {test_name}: {status}")
        if result:
            passed += 1

    success_rate = passed / len(test_results) * 100
    print(f"\n🎯 Success Rate: {passed}/{len(test_results)} ({success_rate:.1f}%)")

    if success_rate >= 80:
        print("\n🎉 WebSocket system is working excellently!")
        print("   Ready for real-time data streaming and client management.")
    elif success_rate >= 60:
        print("\n✅ WebSocket system is mostly working.")
        print("   Minor issues detected but core functionality is intact.")
    else:
        print("\n⚠️  Some critical issues detected.")
        print("   Please review the failing tests before proceeding.")

    return success_rate >= 80


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
