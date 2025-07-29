"""
セキュリティ機能のテスト
環境変数管理、レート制限、APIキー管理のテスト
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi import Request, HTTPException

from src.backend.core.config import Settings
from src.backend.core.rate_limiter import (
    EnhancedRateLimiter, 
    get_client_ip, 
    get_user_id_or_ip,
    get_rate_limit_status
)
from src.backend.core.api_key_manager import (
    APIKeyManager, 
    validate_exchange_credentials,
    get_secure_api_credentials
)


class TestConfigSecurity:
    """設定とセキュリティポリシーのテスト"""
    
    def test_jwt_secret_length_validation(self):
        """JWT_SECRETの長さ検証テスト"""
        # 短すぎるJWT_SECRETでエラーが発生することを確認
        with patch.dict(os.environ, {"JWT_SECRET": "short"}):
            with pytest.raises(ValueError, match="JWT_SECRET must be at least 32 characters long"):
                Settings()
    
    def test_production_password_validation(self):
        """本番環境でのデフォルトパスワード検証テスト"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "ADMIN_PASSWORD": "change_this_password"
        }):
            with pytest.raises(ValueError, match="Default admin password must be changed in production"):
                Settings()
    
    def test_development_environment_properties(self):
        """開発環境プロパティテスト"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            assert settings.is_development is True
            assert settings.is_production is False
    
    def test_production_environment_properties(self):
        """本番環境プロパティテスト"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "ADMIN_PASSWORD": "secure_production_password_123!",
            "JWT_SECRET": "very_secure_jwt_secret_key_for_production_environment_32chars"
        }):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is True


class TestRateLimiter:
    """レート制限機能のテスト"""
    
    def test_enhanced_rate_limiter_failed_attempts(self):
        """失敗試行の記録とロックアウトテスト"""
        limiter = EnhancedRateLimiter()
        client_id = "test_client"
        
        # 最初はロックアウトされていない
        assert limiter.is_locked_out(client_id) is False
        
        # 失敗試行を記録
        for i in range(4):
            limiter.record_failed_attempt(client_id)
            assert limiter.is_locked_out(client_id) is False
        
        # 5回目でロックアウト
        limiter.record_failed_attempt(client_id)
        assert limiter.is_locked_out(client_id) is True
    
    def test_enhanced_rate_limiter_successful_reset(self):
        """成功時の失敗カウンターリセットテスト"""
        limiter = EnhancedRateLimiter()
        client_id = "test_client"
        
        # いくつか失敗を記録
        limiter.record_failed_attempt(client_id)
        limiter.record_failed_attempt(client_id)
        assert limiter.failed_attempts[client_id] == 2
        
        # 成功でリセット
        limiter.record_successful_attempt(client_id)
        assert client_id not in limiter.failed_attempts
    
    def test_get_client_ip_forwarded_for(self):
        """X-Forwarded-ForヘッダーからのIP取得テスト"""
        request = MagicMock()
        request.headers.get.side_effect = lambda header: {
            "X-Forwarded-For": "192.168.1.100, 10.0.0.1",
            "X-Real-IP": None
        }.get(header)
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_real_ip(self):
        """X-Real-IPヘッダーからのIP取得テスト"""
        request = MagicMock()
        request.headers.get.side_effect = lambda header: {
            "X-Forwarded-For": None,
            "X-Real-IP": "203.0.113.195"
        }.get(header)
        
        with patch('src.backend.core.rate_limiter.get_remote_address') as mock_get_remote:
            mock_get_remote.return_value = "127.0.0.1"
            ip = get_client_ip(request)
            assert ip == "203.0.113.195"
    
    def test_get_user_id_or_ip_authenticated(self):
        """認証済みユーザーの識別テスト"""
        request = MagicMock()
        user = MagicMock()
        user.id = "user123"
        request.state.user = user
        
        identifier = get_user_id_or_ip(request)
        assert identifier == "user:user123"
    
    def test_get_user_id_or_ip_unauthenticated(self):
        """未認証ユーザーのIP識別テスト"""
        request = MagicMock()
        request.state = MagicMock()
        request.state.user = None
        request.headers.get.return_value = None
        
        with patch('src.backend.core.rate_limiter.get_remote_address') as mock_get_remote:
            mock_get_remote.return_value = "192.168.1.1"
            identifier = get_user_id_or_ip(request)
            assert identifier == "ip:192.168.1.1"
    
    def test_rate_limit_status(self):
        """レート制限状況取得テスト"""
        # グローバルインスタンスを使用
        from src.backend.core.rate_limiter import enhanced_limiter
        client_id = "test_status_client"
        
        # 初期状態
        status = get_rate_limit_status(client_id)
        assert status["failed_attempts"] == 0
        assert status["is_locked_out"] is False
        
        # 失敗試行後
        enhanced_limiter.record_failed_attempt(client_id)
        status = get_rate_limit_status(client_id)
        assert status["failed_attempts"] == 1


class TestAPIKeyManager:
    """APIキー管理のテスト"""
    
    def setup_method(self):
        """テスト用のAPIキーマネージャーを設定"""
        self.manager = APIKeyManager("test_master_key_for_encryption_32ch")
    
    def test_api_key_encryption_decryption(self):
        """APIキーの暗号化・復号化テスト"""
        original_key = "test_api_key_12345678901234567890"
        
        # 暗号化
        encrypted = self.manager.encrypt_api_key(original_key)
        assert encrypted != original_key
        assert len(encrypted) > 0
        
        # 復号化
        decrypted = self.manager.decrypt_api_key(encrypted)
        assert decrypted == original_key
    
    def test_api_key_validation_binance(self):
        """Binance APIキー形式検証テスト"""
        # 有効なBinance APIキー形式（ランダムな文字列）
        valid_key = "Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9Jj0Kk1Ll2Mm3Nn4Oo5Pp6Qq7Rr8Ss9Tt0Uu1V"  # 64文字の英数字
        is_valid, errors = self.manager.validate_api_key(valid_key, "binance")
        assert is_valid is True
        assert len(errors) == 0
        
        # 無効な形式
        invalid_key = "invalid_key"
        is_valid, errors = self.manager.validate_api_key(invalid_key, "binance")
        assert is_valid is False
        assert any("format invalid" in error for error in errors)
    
    def test_api_key_validation_dangerous_patterns(self):
        """危険なパターンの検出テスト"""
        dangerous_keys = [
            "test_api_key_12345678901234567890",
            "demo_key_12345678901234567890",
            "your_api_key_12345678901234567890",
            "change_this_key_12345678901234567890"
        ]
        
        for key in dangerous_keys:
            is_valid, errors = self.manager.validate_api_key(key, "binance")
            assert is_valid is False
            assert any("dangerous pattern" in error for error in errors)
    
    def test_api_key_length_validation(self):
        """APIキー長の検証テスト"""
        # 短すぎる
        short_key = "short"
        is_valid, errors = self.manager.validate_api_key(short_key, "binance")
        assert is_valid is False
        assert any("too short" in error for error in errors)
        
        # 長すぎる
        long_key = "x" * 201
        is_valid, errors = self.manager.validate_api_key(long_key, "binance")
        assert is_valid is False
        assert any("too long" in error for error in errors)
    
    def test_api_key_masking(self):
        """APIキーマスク機能テスト"""
        api_key = "1234567890abcdefghijklmnopqrstuvwxyz"
        masked = self.manager.mask_api_key(api_key, visible_chars=4)
        
        assert masked.startswith("1234")
        assert masked.endswith("wxyz")
        assert "*" in masked
        assert len(masked) == len(api_key)
    
    def test_api_key_hash_generation(self):
        """APIキーハッシュ生成テスト"""
        api_key = "test_key_for_hashing"
        hash1 = self.manager.generate_api_key_hash(api_key)
        hash2 = self.manager.generate_api_key_hash(api_key)
        
        # 同じキーは同じハッシュ
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256は64文字
    
    def test_api_key_integrity_verification(self):
        """APIキー整合性検証テスト"""
        api_key = "test_key_for_integrity"
        correct_hash = self.manager.generate_api_key_hash(api_key)
        wrong_hash = "wrong_hash"
        
        # 正しいハッシュ
        assert self.manager.verify_api_key_integrity(api_key, correct_hash) is True
        
        # 間違ったハッシュ
        assert self.manager.verify_api_key_integrity(api_key, wrong_hash) is False
    
    def test_entropy_check(self):
        """エントロピーチェックテスト"""
        # 低エントロピー（同じ文字の繰り返し）
        low_entropy_key = "aaaaaaaaaaaaaaaa"
        assert self.manager._check_entropy(low_entropy_key) is False
        
        # 高エントロピー（ランダムな文字列）
        high_entropy_key = "aB3xY9mK7nQ2pR5t"
        assert self.manager._check_entropy(high_entropy_key) is True
    
    @patch('src.backend.core.api_key_manager.settings')
    def test_get_exchange_credentials(self, mock_settings):
        """取引所クレデンシャル取得テスト"""
        # モック設定
        mock_settings.BINANCE_API_KEY = "A" * 64
        mock_settings.BINANCE_SECRET = "B" * 64
        mock_settings.is_production = False
        
        api_key, secret = self.manager.get_exchange_credentials("binance")
        assert api_key == "A" * 64
        assert secret == "B" * 64
    
    def test_audit_results_structure(self):
        """監査結果の構造テスト"""
        with patch.object(self.manager, 'get_exchange_credentials') as mock_get_creds:
            mock_get_creds.return_value = ("test_key_123456789012345678901234567890123456789012345678901234567890", "test_secret_123456789012345678901234567890123456789012345678901234567890")
            
            results = self.manager.audit_all_api_keys()
            
            # 結果の構造を確認
            assert "binance" in results
            binance_result = results["binance"]
            
            required_fields = [
                "api_key_present", "secret_present", 
                "api_key_valid", "secret_valid",
                "api_key_errors", "secret_errors",
                "api_key_masked", "secret_masked",
                "last_checked"
            ]
            
            for field in required_fields:
                assert field in binance_result


class TestSecurityIntegration:
    """セキュリティ機能の統合テスト"""
    
    def test_validate_exchange_credentials_success(self):
        """正常なクレデンシャル検証テスト"""
        api_key = "Aa1Bb2Cc3Dd4Ee5Ff6Gg7Hh8Ii9Jj0Kk1Ll2Mm3Nn4Oo5Pp6Qq7Rr8Ss9Tt0Uu1V"  # Binance形式
        secret = "Vv2Ww3Xx4Yy5Zz6Aa7Bb8Cc9Dd0Ee1Ff2Gg3Hh4Ii5Jj6Kk7Ll8Mm9Nn0Oo1Pp2Q"   # Binance形式
        
        is_valid, errors = validate_exchange_credentials("binance", api_key, secret)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_exchange_credentials_failure(self):
        """異常なクレデンシャル検証テスト"""
        api_key = "invalid_key"
        secret = "invalid_secret"
        
        is_valid, errors = validate_exchange_credentials("binance", api_key, secret)
        assert is_valid is False
        assert len(errors) > 0
    
    @patch('src.backend.core.api_key_manager.api_key_manager')
    def test_get_secure_api_credentials_wrapper(self, mock_manager):
        """セキュアAPI認証情報取得のラッパーテスト"""
        mock_manager.get_exchange_credentials.return_value = ("test_key", "test_secret")
        
        api_key, secret = get_secure_api_credentials("binance")
        assert api_key == "test_key"
        assert secret == "test_secret"
        mock_manager.get_exchange_credentials.assert_called_once_with("binance")


if __name__ == "__main__":
    pytest.main(["-v"])