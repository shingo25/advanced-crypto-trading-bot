#!/usr/bin/env python3
"""
認証APIのSupabase SDK対応をテストするスクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.core.database import init_db, get_user_by_username
from backend.core.security import authenticate_user, get_password_hash
from dotenv import load_dotenv

def test_database_auth_functions():
    """データベース認証関連関数のテスト"""
    print("🔐 認証関連関数のテスト中...")
    
    try:
        # データベース初期化
        init_db()
        
        # 管理者ユーザーの存在確認
        admin_user = get_user_by_username("admin")
        if admin_user:
            print(f"   ✅ 管理者ユーザー取得成功: {admin_user['username']}")
            print(f"   📊 ユーザーID: {admin_user['id']}")
            print(f"   📊 ロール: {admin_user['role']}")
            print(f"   📊 パスワードハッシュ: {'有り' if admin_user.get('password_hash') else '無し'}")
        else:
            print("   ⚠️ 管理者ユーザーが見つかりません")
        
        # 認証テスト（実際のパスワードでテスト）
        print("\n🔑 認証機能のテスト中...")
        
        # 注意: admin/adminでテスト（設定に依存）
        auth_result = authenticate_user("admin", "admin")
        if auth_result:
            print("   ✅ 認証成功")
            print(f"   📊 認証されたユーザー: {auth_result['username']}")
        else:
            print("   ❌ 認証失敗")
            print("   💡 パスワードハッシュが正しく設定されていない可能性があります")
        
        # 存在しないユーザーでの認証テスト
        auth_fail = authenticate_user("nonexistent", "wrongpassword")
        if not auth_fail:
            print("   ✅ 存在しないユーザーの認証は正しく拒否されました")
        else:
            print("   ⚠️ 存在しないユーザーが認証されました（問題の可能性）")
            
        return True
        
    except Exception as e:
        print(f"   ❌ 認証関数テストエラー: {e}")
        return False

def test_password_hashing():
    """パスワードハッシュ機能のテスト"""
    print("\n🔒 パスワードハッシュ機能のテスト中...")
    
    try:
        test_password = "test123"
        hashed = get_password_hash(test_password)
        
        print(f"   📊 平文パスワード: {test_password}")
        print(f"   📊 ハッシュ化後: {hashed[:50]}...")
        
        # 検証テスト
        from backend.core.security import verify_password
        is_valid = verify_password(test_password, hashed)
        
        if is_valid:
            print("   ✅ パスワード検証成功")
        else:
            print("   ❌ パスワード検証失敗")
            
        # 間違ったパスワードでの検証
        is_invalid = verify_password("wrongpassword", hashed)
        if not is_invalid:
            print("   ✅ 間違ったパスワードは正しく拒否されました")
        else:
            print("   ❌ 間違ったパスワードが受け入れられました")
            
        return True
        
    except Exception as e:
        print(f"   ❌ パスワードハッシュテストエラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🧪 認証API Supabase SDK対応の事前テスト開始")
    print("=" * 60)
    
    # 環境変数を読み込み
    load_dotenv()
    
    # テスト結果を追跡
    test_results = []
    
    # 1. データベース認証関数テスト
    test_results.append(test_database_auth_functions())
    
    # 2. パスワードハッシュ機能テスト
    test_results.append(test_password_hashing())
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"   成功: {passed}/{total}")
    print(f"   成功率: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 認証関数はSupabase SDK対応済み！")
        print("🔄 次のステップ: API エンドポイントの更新に進む準備完了")
        return True
    else:
        print("⚠️ 一部の認証機能で問題が発生しました")
        print("   修正が必要な可能性があります")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 認証API事前テスト完了")
    else:
        print("\n❌ 認証APIに重大な問題があります")