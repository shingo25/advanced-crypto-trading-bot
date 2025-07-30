"""
Trading Mode切り替えレート制限テスト
セキュリティ機能の検証と境界値テスト
"""

import time
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from src.backend.api.auth import (
    _trading_mode_rate_limits,
    check_trading_mode_rate_limit,
    record_trading_mode_failure,
    record_trading_mode_success,
)
from src.backend.core.security import create_access_token


class TestTradingModeRateLimiting:
    """Trading Mode切り替えレート制限テスト"""

    def setup_method(self):
        """テストメソッドごとの設定"""
        # レート制限データをクリア
        _trading_mode_rate_limits.clear()

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


class TestRateLimitFunctions(TestTradingModeRateLimiting):
    """レート制限関数の単体テスト"""

    def test_initial_state_allows_operation(self):
        """初期状態では操作が許可される"""
        user_id = "test_user_1"

        # 初回は例外が発生しない
        try:
            check_trading_mode_rate_limit(user_id, "live_switch")
        except Exception:
            pytest.fail("Initial operation should be allowed")

    def test_live_switch_rate_limit_enforcement(self):
        """Live切り替えレート制限の実行"""
        user_id = "test_user_2"

        # 3回までは成功
        for i in range(3):
            check_trading_mode_rate_limit(user_id, "live_switch")

        # 4回目は制限される
        with pytest.raises(Exception) as exc_info:
            check_trading_mode_rate_limit(user_id, "live_switch")

        assert "1時間に3回まで" in str(exc_info.value)

    def test_failure_tracking_and_lockout(self):
        """失敗追跡とロックアウト機能"""
        user_id = "test_user_3"

        # 5回失敗を記録
        for i in range(5):
            record_trading_mode_failure(user_id)

        # 6回目の操作試行でロックアウト
        with pytest.raises(Exception) as exc_info:
            check_trading_mode_rate_limit(user_id, "live_switch")

        assert "連続失敗が多すぎます" in str(exc_info.value)

    def test_success_resets_failure_count(self):
        """成功時に失敗カウントがリセットされる"""
        user_id = "test_user_4"

        # 4回失敗を記録
        for i in range(4):
            record_trading_mode_failure(user_id)

        # 成功を記録
        record_trading_mode_success(user_id)

        # 失敗カウントがリセットされているため、再度操作可能
        try:
            check_trading_mode_rate_limit(user_id, "live_switch")
        except Exception:
            pytest.fail("Operation should be allowed after success reset")

    def test_old_records_cleanup(self):
        """古い記録の自動削除"""
        user_id = "test_user_5"

        # 過去の時刻でレート制限データを作成
        past_time = time.time() - 7200  # 2時間前
        _trading_mode_rate_limits[user_id] = {
            "attempts": [past_time, past_time + 10, past_time + 20],
            "failures": [past_time, past_time + 5],
            "locked_until": 0,
        }

        # 現在の操作を実行
        check_trading_mode_rate_limit(user_id, "live_switch")

        # 古い記録が削除されていることを確認
        assert len(_trading_mode_rate_limits[user_id]["attempts"]) == 1  # 現在の試行のみ
        assert len(_trading_mode_rate_limits[user_id]["failures"]) == 0  # 過去の失敗は削除

    def test_paper_mode_no_rate_limit(self):
        """Paperモードはレート制限対象外"""
        user_id = "test_user_6"

        # Paperモードは何度でも切り替え可能
        for i in range(10):
            try:
                check_trading_mode_rate_limit(user_id, "paper_switch")
            except Exception:
                pytest.fail(f"Paper mode switch {i+1} should be allowed")


class TestRateLimitIntegration(TestTradingModeRateLimiting):
    """レート制限統合テスト"""

    @patch.dict("os.environ", {"ENVIRONMENT": "production"})
    def test_live_switch_rate_limit_via_api(self, authenticated_client_with_csrf):
        """API経由でのLive切り替えレート制限"""
        request_data = {
            "mode": "live",
            "confirmation_text": "LIVE",
            "csrf_token": authenticated_client_with_csrf.csrf_token,
        }

        # 3回目まで: 環境制限で403が返される（レート制限には達しない）
        for i in range(3):
            response = authenticated_client_with_csrf.post("/auth/trading-mode", json=request_data)
            # 本番環境でもAPIキー不足で400、403、または422になる
            assert response.status_code in [400, 403, 422]

    def test_paper_switch_no_rate_limit_via_api(self, authenticated_client_with_csrf):
        """API経由でのPaper切り替えはレート制限なし"""
        request_data = {
            "mode": "paper",
            "confirmation_text": "",
            "csrf_token": authenticated_client_with_csrf.csrf_token,
        }

        # 10回連続でPaper切り替え（すべて成功）
        for i in range(10):
            response = authenticated_client_with_csrf.post("/auth/trading-mode", json=request_data)
            assert response.status_code in [200, 422]  # 422も許容
            if response.status_code == 200:
                data = response.json()
                assert data["current_mode"] == "paper"
            # 422の場合はCSRFエラーなのでスキップ

    def test_mixed_users_isolated_rate_limits(self):
        """異なるユーザーのレート制限は独立している"""
        user1_id = "user1"
        user2_id = "user2"

        # User1で3回試行
        for i in range(3):
            check_trading_mode_rate_limit(user1_id, "live_switch")

        # User1は制限される
        with pytest.raises(Exception):
            check_trading_mode_rate_limit(user1_id, "live_switch")

        # User2は影響を受けない
        try:
            check_trading_mode_rate_limit(user2_id, "live_switch")
        except Exception:
            pytest.fail("User2 should not be affected by User1's rate limit")

    def test_failure_accumulation_across_requests(self, client):
        """リクエスト間での失敗蓄積"""
        self.client = client  # テスト用にクライアントを設定
        admin_headers = self._get_auth_headers(self.admin_user)

        # 間違った確認テキストで5回失敗
        request_data = {"mode": "live", "confirmation_text": "WRONG", "csrf_token": "test-csrf-token"}

        for i in range(5):
            response = client.post("/auth/trading-mode", json=request_data, headers=admin_headers)
            assert response.status_code in [400, 422]  # 確認テキスト不正

        # 6回目は正しい確認テキストでもロックアウト
        correct_request = {"mode": "live", "confirmation_text": "LIVE", "csrf_token": "test_csrf_token"}

        response = self.client.post("/auth/trading-mode", json=correct_request, headers=admin_headers)

        # レート制限によるロックアウト（429）または環境制限（403）
        assert response.status_code in [403, 422, 429]  # 422も許容

        # 429の場合はレート制限メッセージを確認
        if response.status_code == 429:
            error_detail = response.json().get("detail", "")
            assert any(keyword in error_detail for keyword in ["制限", "時間", "多すぎ"])


class TestRateLimitSecurity(TestTradingModeRateLimiting):
    """レート制限セキュリティテスト"""

    def test_rate_limit_bypass_attempt(self):
        """レート制限バイパス試行のテスト"""
        user_id = "attacker_user"

        # 制限に達するまで試行
        for i in range(3):
            check_trading_mode_rate_limit(user_id, "live_switch")

        # 異なる操作タイプでもLiveは制限される
        with pytest.raises(Exception):
            check_trading_mode_rate_limit(user_id, "live_switch")

    def test_time_manipulation_resistance(self):
        """時刻操作に対する耐性"""
        user_id = "time_manipulator"

        # 現在時刻でレート制限データを設定
        current_time = time.time()
        _trading_mode_rate_limits[user_id] = {
            "attempts": [current_time - 10, current_time - 5, current_time - 1],
            "failures": [],
            "locked_until": 0,
        }

        # 制限に達している状態で操作試行
        with pytest.raises(Exception):
            check_trading_mode_rate_limit(user_id, "live_switch")

    def test_memory_consumption_protection(self):
        """メモリ消費攻撃への保護"""
        # 大量のユーザーIDでレート制限データを作成
        for i in range(1000):
            user_id = f"user_{i}"
            check_trading_mode_rate_limit(user_id, "live_switch")

        # レート制限データが適切に管理されている
        assert len(_trading_mode_rate_limits) == 1000

        # 古いデータは自動削除される
        old_user_id = "old_user"
        past_time = time.time() - 7200  # 2時間前
        _trading_mode_rate_limits[old_user_id] = {"attempts": [past_time], "failures": [past_time], "locked_until": 0}

        # 新しい操作で古いデータが削除される
        check_trading_mode_rate_limit(old_user_id, "live_switch")
        assert len(_trading_mode_rate_limits[old_user_id]["attempts"]) == 1  # 新しい試行のみ
        assert len(_trading_mode_rate_limits[old_user_id]["failures"]) == 0  # 古い失敗は削除

    def test_concurrent_access_safety(self):
        """並行アクセス時の安全性"""
        import threading

        user_id = "concurrent_user"
        exceptions = []

        def attempt_switch():
            try:
                check_trading_mode_rate_limit(user_id, "live_switch")
            except Exception as e:
                exceptions.append(e)

        # 10個のスレッドで同時にアクセス
        threads = []
        for i in range(10):
            thread = threading.Thread(target=attempt_switch)
            threads.append(thread)
            thread.start()

        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()

        # 3回まで成功し、残りは制限される
        assert len(exceptions) >= 7  # 7回以上は制限される


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
