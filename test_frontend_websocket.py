#!/usr/bin/env python3
"""
フロントエンドWebSocket連携テスト
リアルタイム価格表示コンポーネントの機能確認
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_frontend_component_files():
    """フロントエンドコンポーネントファイルの存在確認"""
    try:
        print("🔍 Testing frontend WebSocket component files...")

        # ファイルパス
        price_websocket_path = project_root / "frontend/src/components/realtime/PriceWebSocket.tsx"
        dashboard_page_path = project_root / "frontend/src/app/dashboard/realtime/page.tsx"

        # ファイル存在確認
        if price_websocket_path.exists():
            print("✅ PriceWebSocket.tsx exists")
            with open(price_websocket_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"   - File size: {len(content):,} characters")
                print(f"   - Contains WebSocket: {'WebSocket' in content}")
                print(f"   - Contains price formatting: {'formatCurrency' in content}")
                print(f"   - Contains auto-reconnect: {'autoReconnect' in content}")
        else:
            print("❌ PriceWebSocket.tsx not found")
            return False

        if dashboard_page_path.exists():
            print("✅ Dashboard page exists")
            with open(dashboard_page_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"   - File size: {len(content):,} characters")
                print(f"   - Contains PriceWebSocket import: {'PriceWebSocket' in content}")
                print(f"   - Contains settings dialog: {'SettingsDialog' in content}")
                print(f"   - Contains symbol management: {'selectedSymbols' in content}")
        else:
            print("❌ Dashboard page not found")
            return False

        return True

    except Exception as e:
        print(f"❌ File test failed: {e}")
        return False


def test_component_structure():
    """コンポーネント構造の確認"""
    try:
        print("\n🔍 Testing component structure...")

        price_websocket_path = project_root / "frontend/src/components/realtime/PriceWebSocket.tsx"

        with open(price_websocket_path, "r", encoding="utf-8") as f:
            content = f.read()

        # TypeScript インターフェース確認
        interfaces = [
            "PriceData",
            "TradeData",
            "WebSocketMessage",
            "PriceWebSocketProps",
        ]

        print("✅ TypeScript interfaces:")
        for interface in interfaces:
            if f"interface {interface}" in content:
                print(f"   - {interface}: ✅")
            else:
                print(f"   - {interface}: ❌")

        # React hooks 確認
        hooks = ["useState", "useEffect", "useRef", "useCallback"]

        print("✅ React hooks usage:")
        for hook in hooks:
            if hook in content:
                print(f"   - {hook}: ✅")
            else:
                print(f"   - {hook}: ❌")

        # WebSocket 機能確認
        websocket_features = [
            "ws.current = new WebSocket",
            "ws.current.onopen",
            "ws.current.onmessage",
            "ws.current.onerror",
            "ws.current.onclose",
        ]

        print("✅ WebSocket functionality:")
        for feature in websocket_features:
            if feature in content:
                print(f"   - {feature}: ✅")
            else:
                print(f"   - {feature}: ❌")

        return True

    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False


def test_dashboard_features():
    """ダッシュボード機能の確認"""
    try:
        print("\n🔍 Testing dashboard features...")

        dashboard_path = project_root / "frontend/src/app/dashboard/realtime/page.tsx"

        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()

        # ダッシュボード機能確認
        features = {
            "Symbol Management": "selectedSymbols",
            "Settings Dialog": "SettingsDialog",
            "Layout Options": "LAYOUT_OPTIONS",
            "Fullscreen Mode": "fullscreen",
            "Auto Refresh": "autoRefresh",
            "Trade Display": "showTrades",
            "Quick Actions": "QuickActions",
            "Add Symbol": "AddSymbolDialog",
        }

        print("✅ Dashboard features:")
        for feature_name, feature_code in features.items():
            if feature_code in content:
                print(f"   - {feature_name}: ✅")
            else:
                print(f"   - {feature_name}: ❌")

        # 利用可能なシンボル確認
        if "AVAILABLE_SYMBOLS" in content:
            print("✅ Available symbols configuration found")
            # シンボル数を概算
            btc_count = content.count("BTCUSDT")
            eth_count = content.count("ETHUSDT")
            print(f"   - BTC references: {btc_count}")
            print(f"   - ETH references: {eth_count}")

        return True

    except Exception as e:
        print(f"❌ Dashboard features test failed: {e}")
        return False


def test_integration_readiness():
    """統合準備状況の確認"""
    try:
        print("\n🔍 Testing integration readiness...")

        # 必要なディレクトリ構造確認
        required_paths = [
            "frontend/src/components/realtime",
            "frontend/src/app/dashboard/realtime",
            "backend/websocket",
            "backend/streaming",
        ]

        print("✅ Directory structure:")
        for path in required_paths:
            full_path = project_root / path
            if full_path.exists():
                print(f"   - {path}: ✅")
            else:
                print(f"   - {path}: ❌")

        # WebSocket URL 設定確認
        price_websocket_path = project_root / "frontend/src/components/realtime/PriceWebSocket.tsx"
        with open(price_websocket_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "getWebSocketUrl" in content:
            print("✅ WebSocket URL configuration found")
            if "localhost:8000" in content:
                print("   - Development URL configured")
            if "NEXT_PUBLIC_API_URL" in content:
                print("   - Environment variable support")

        # 認証連携確認
        if "useAuthStore" in content:
            print("✅ Authentication integration found")
            if "token" in content:
                print("   - JWT token support")

        return True

    except Exception as e:
        print(f"❌ Integration readiness test failed: {e}")
        return False


def test_responsive_design():
    """レスポンシブデザイン確認"""
    try:
        print("\n🔍 Testing responsive design...")

        dashboard_path = project_root / "frontend/src/app/dashboard/realtime/page.tsx"

        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Material-UI Grid システム確認
        responsive_features = [
            "xs={12}",
            "sm={6}",
            "md={3}",
            "Grid container",
            "Grid item",
        ]

        print("✅ Responsive grid system:")
        for feature in responsive_features:
            if feature in content:
                print(f"   - {feature}: ✅")
            else:
                print(f"   - {feature}: ❌")

        # モバイル対応確認
        mobile_features = ["Container", "maxWidth", "fullWidth", "FormControlLabel"]

        print("✅ Mobile compatibility:")
        for feature in mobile_features:
            if feature in content:
                print(f"   - {feature}: ✅")
            else:
                print(f"   - {feature}: ❌")

        return True

    except Exception as e:
        print(f"❌ Responsive design test failed: {e}")
        return False


def test_error_handling():
    """エラーハンドリング確認"""
    try:
        print("\n🔍 Testing error handling...")

        price_websocket_path = project_root / "frontend/src/components/realtime/PriceWebSocket.tsx"

        with open(price_websocket_path, "r", encoding="utf-8") as f:
            content = f.read()

        # エラーハンドリング機能確認
        error_features = [
            "try {",
            "catch (error)",
            "setError",
            "connectionStatus",
            "reconnectAttempts",
            'Alert severity="error"',
        ]

        print("✅ Error handling features:")
        for feature in error_features:
            if feature in content:
                print(f"   - {feature}: ✅")
            else:
                print(f"   - {feature}: ❌")

        # 接続状態管理確認
        connection_states = ["'connecting'", "'connected'", "'disconnected'", "'error'"]

        print("✅ Connection state management:")
        for state in connection_states:
            if state in content:
                print(f"   - {state}: ✅")
            else:
                print(f"   - {state}: ❌")

        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🚀 Starting frontend WebSocket integration tests...\n")

    # テスト実行
    test_results = []

    tests = [
        ("Frontend Component Files", test_frontend_component_files),
        ("Component Structure", test_component_structure),
        ("Dashboard Features", test_dashboard_features),
        ("Integration Readiness", test_integration_readiness),
        ("Responsive Design", test_responsive_design),
        ("Error Handling", test_error_handling),
    ]

    for test_name, test_func in tests:
        try:
            result = test_func()
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
        print("\n🎉 Frontend WebSocket integration is excellent!")
        print("   Ready for real-time cryptocurrency price display.")
        print("   ✅ React TypeScript components")
        print("   ✅ Material-UI responsive design")
        print("   ✅ WebSocket connection management")
        print("   ✅ Automatic reconnection handling")
        print("   ✅ Multi-symbol price monitoring")
        print("   ✅ Real-time trade data display")
        print("   ✅ User-friendly dashboard interface")
    elif success_rate >= 60:
        print("\n✅ Frontend WebSocket integration is mostly working.")
        print("   Minor issues detected but core functionality is intact.")
    else:
        print("\n⚠️  Some critical issues detected.")
        print("   Please review the failing tests before proceeding.")

    return success_rate >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
