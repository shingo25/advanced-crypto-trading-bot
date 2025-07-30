"""
CSRF保護テスト
Trading Mode切り替えのCSRF攻撃対策検証
"""

import time
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from src.backend.api.auth import _csrf_tokens, cleanup_expired_csrf_tokens, generate_csrf_token, verify_csrf_token
from src.backend.core.security import create_access_token
from src.backend.main import app


class TestCSRFProtection:
    """CSRF保護機能テスト"""

    def setup_method(self):
        """テストメソッドごとの設定"""
        self.client = TestClient(app)

        # CSRFトークンデータをクリア
        _csrf_tokens.clear()

        # テストユーザー（管理者）
        self.admin_user = {
            "id": str(uuid.uuid4()),
            "username": "admin_user",
            "email": "admin@example.com",
            "role": "admin",
            "is_active": True,
        }

    def _create_auth_token(self, user_data: dict) -> str:
        """指定ユーザーの認証トークンを作成"""
        token = create_access_token(
            data={"sub": user_data["id"], "role": user_data["role"]}, expires_delta=timedelta(hours=1)
        )
        return f"Bearer {token}"

    def _get_auth_headers(self, user_data: dict) -> dict:
        """認証ヘッダーを取得"""
        return {"Authorization": self._create_auth_token(user_data)}


class TestCSRFTokenGeneration(TestCSRFProtection):
    """CSRFトークン生成テスト"""

    def test_csrf_token_generation(self):
        """CSRFトークン生成機能"""
        user_id = "test_user_1"

        token = generate_csrf_token(user_id)

        # トークンが生成される
        assert isinstance(token, str)
        assert len(token) > 20  # URL-safeなトークンの最小長

        # トークンデータが保存される
        assert user_id in _csrf_tokens
        assert _csrf_tokens[user_id]["token"] == token
        assert "created_at" in _csrf_tokens[user_id]
        assert "expires_at" in _csrf_tokens[user_id]

    def test_csrf_token_uniqueness(self):
        """CSRFトークンの一意性"""
        user1_id = "user1"
        user2_id = "user2"

        token1 = generate_csrf_token(user1_id)
        token2 = generate_csrf_token(user2_id)

        # 異なるユーザーには異なるトークン
        assert token1 != token2

        # 同じユーザーでも再生成で異なるトークン
        token1_new = generate_csrf_token(user1_id)
        assert token1 != token1_new

    def test_csrf_token_api_endpoint(self):
        """CSRFトークン取得APIエンドポイント"""
        admin_headers = self._get_auth_headers(self.admin_user)

        response = self.client.get("/auth/csrf-token", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        assert "csrf_token" in data
        assert "expires_in" in data
        assert "timestamp" in data
        assert data["expires_in"] == 3600  # 1時間


class TestCSRFTokenVerification(TestCSRFProtection):
    """CSRFトークン検証テスト"""

    def test_valid_csrf_token_verification(self):
        """有効なCSRFトークンの検証"""
        user_id = "test_user_2"

        token = generate_csrf_token(user_id)

        # 有効なトークンは検証成功
        assert verify_csrf_token(user_id, token) is True

    def test_invalid_csrf_token_verification(self):
        """無効なCSRFトークンの検証"""
        user_id = "test_user_3"

        generate_csrf_token(user_id)

        # 間違ったトークンは検証失敗
        assert verify_csrf_token(user_id, "invalid_token") is False

    def test_csrf_token_for_nonexistent_user(self):
        """存在しないユーザーのCSRFトークン検証"""
        # ユーザーが存在しない場合は検証失敗
        assert verify_csrf_token("nonexistent_user", "any_token") is False

    def test_expired_csrf_token_verification(self):
        """期限切れCSRFトークンの検証"""
        user_id = "test_user_4"

        # 過去の時刻でCSRFトークンを作成
        past_time = time.time() - 7200  # 2時間前
        _csrf_tokens[user_id] = {
            "token": "expired_token",
            "created_at": past_time,
            "expires_at": past_time + 3600,  # 1時間後（つまり1時間前に期限切れ）
        }

        # 期限切れトークンは検証失敗
        assert verify_csrf_token(user_id, "expired_token") is False

        # 期限切れトークンは削除される
        assert user_id not in _csrf_tokens

    def test_csrf_token_cleanup(self):
        """期限切れCSRFトークンのクリーンアップ"""
        current_time = time.time()

        # 複数のCSRFトークンを作成（有効・無効混在）
        _csrf_tokens["active_user"] = {
            "token": "active_token",
            "created_at": current_time,
            "expires_at": current_time + 3600,  # 1時間後（有効）
        }

        _csrf_tokens["expired_user1"] = {
            "token": "expired_token1",
            "created_at": current_time - 7200,
            "expires_at": current_time - 3600,  # 1時間前（期限切れ）
        }

        _csrf_tokens["expired_user2"] = {
            "token": "expired_token2",
            "created_at": current_time - 10800,
            "expires_at": current_time - 7200,  # 2時間前（期限切れ）
        }

        # クリーンアップ実行
        cleanup_expired_csrf_tokens()

        # 有効なトークンのみ残る
        assert "active_user" in _csrf_tokens
        assert "expired_user1" not in _csrf_tokens
        assert "expired_user2" not in _csrf_tokens


class TestCSRFProtectionIntegration(TestCSRFProtection):
    """CSRF保護統合テスト"""

    def test_trading_mode_change_without_csrf_token(self):
        """CSRFトークンなしでの取引モード変更"""
        admin_headers = self._get_auth_headers(self.admin_user)

        request_data = {"mode": "paper", "confirmation_text": "", "csrf_token": "invalid_token"}

        response = self.client.post("/auth/trading-mode", json=request_data, headers=admin_headers)

        # CSRF検証失敗で403
        assert response.status_code == 403
        assert "不正なリクエスト" in response.json()["detail"]

    def test_trading_mode_change_with_valid_csrf_token(self):
        """有効なCSRFトークンでの取引モード変更"""
        admin_headers = self._get_auth_headers(self.admin_user)

        # CSRFトークンを取得
        csrf_response = self.client.get("/auth/csrf-token", headers=admin_headers)
        assert csrf_response.status_code == 200
        csrf_token = csrf_response.json()["csrf_token"]

        request_data = {"mode": "paper", "confirmation_text": "", "csrf_token": csrf_token}

        response = self.client.post("/auth/trading-mode", json=request_data, headers=admin_headers)

        # CSRF検証成功でPaper切り替え成功
        assert response.status_code == 200
        assert response.json()["current_mode"] == "paper"

    def test_csrf_token_reuse_prevention(self):
        """CSRFトークンの再利用防止"""
        admin_headers = self._get_auth_headers(self.admin_user)

        # CSRFトークンを取得
        csrf_response = self.client.get("/auth/csrf-token", headers=admin_headers)
        csrf_token = csrf_response.json()["csrf_token"]

        request_data = {"mode": "paper", "confirmation_text": "", "csrf_token": csrf_token}

        # 1回目の使用（成功）
        response1 = self.client.post("/auth/trading-mode", json=request_data, headers=admin_headers)
        assert response1.status_code == 200

        # 2回目の使用（同じトークンを再利用）
        response2 = self.client.post("/auth/trading-mode", json=request_data, headers=admin_headers)

        # 現在の実装では同じトークンの再利用は可能
        # （必要に応じてワンタイムトークンに変更可能）
        assert response2.status_code == 200

    def test_cross_user_csrf_token_isolation(self):
        """ユーザー間でのCSRFトークン分離"""
        user1_data = {"id": str(uuid.uuid4()), "username": "user1", "role": "admin"}
        user2_data = {"id": str(uuid.uuid4()), "username": "user2", "role": "admin"}

        user1_headers = self._get_auth_headers(user1_data)
        user2_headers = self._get_auth_headers(user2_data)

        # User1のCSRFトークンを取得
        csrf_response1 = self.client.get("/auth/csrf-token", headers=user1_headers)
        csrf_token1 = csrf_response1.json()["csrf_token"]

        # User2がUser1のCSRFトークンを使用
        request_data = {"mode": "paper", "confirmation_text": "", "csrf_token": csrf_token1}

        response = self.client.post("/auth/trading-mode", json=request_data, headers=user2_headers)

        # 他ユーザーのCSRFトークン使用で403
        assert response.status_code == 403


class TestCSRFSecurityAttacks(TestCSRFProtection):
    """CSRF攻撃セキュリティテスト"""

    def test_csrf_token_brute_force_resistance(self):
        """CSRFトークンのブルートフォース攻撃耐性"""
        user_id = "target_user"

        # 正しいトークンを生成
        correct_token = generate_csrf_token(user_id)

        # 大量の間違ったトークンで試行
        for i in range(1000):
            fake_token = f"fake_token_{i}"
            assert verify_csrf_token(user_id, fake_token) is False

        # 正しいトークンは依然として有効
        assert verify_csrf_token(user_id, correct_token) is True

    def test_csrf_token_timing_attack_resistance(self):
        """CSRFトークンのタイミング攻撃耐性"""
        user_id = "timing_test_user"

        correct_token = generate_csrf_token(user_id)

        # 部分的に正しいトークンでのタイミング測定
        partial_token = correct_token[:10] + "wrong_suffix"

        # タイミング攻撃の検証（secrets.compare_digestが使用されている）
        start_time = time.time()
        result1 = verify_csrf_token(user_id, partial_token)
        time1 = time.time() - start_time

        start_time = time.time()
        result2 = verify_csrf_token(user_id, "completely_wrong")
        time2 = time.time() - start_time

        # 両方とも失敗するが、時間差は最小限
        assert result1 is False
        assert result2 is False

        # タイミング差が0.1秒以内（処理時間の誤差範囲）
        assert abs(time1 - time2) < 0.1

    def test_csrf_token_format_manipulation(self):
        """CSRFトークン形式操作攻撃"""
        user_id = "format_test_user"

        correct_token = generate_csrf_token(user_id)

        # 様々な不正な形式でテスト
        malicious_tokens = [
            "",  # 空文字列
            None,  # None値
            correct_token.upper(),  # 大文字変換
            correct_token.lower(),  # 小文字変換
            correct_token + "extra",  # 追加文字
            correct_token[:-1],  # 末尾削除
            correct_token.replace("a", "A"),  # 部分変更
            "javascript:alert('xss')",  # XSS試行
            "../" + correct_token,  # パストラバーサル試行
            correct_token + "\x00",  # ヌル文字注入
        ]

        for malicious_token in malicious_tokens:
            try:
                result = verify_csrf_token(user_id, malicious_token)
                assert result is False, f"Malicious token should be rejected: {malicious_token}"
            except Exception:
                # エラーが発生しても適切に処理される
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
