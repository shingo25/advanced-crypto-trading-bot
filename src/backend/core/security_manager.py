"""
セキュリティ管理モジュール
APIキーの暗号化、復号化、安全な管理を提供
"""

import base64
import json
import logging
import os
from typing import Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecurityManager:
    """APIキーとシークレットの安全な管理"""

    def __init__(self, master_key: Optional[str] = None):
        """
        セキュリティマネージャーの初期化

        Args:
            master_key: 暗号化のマスターキー（環境変数から取得推奨）
        """
        self.master_key = master_key or os.getenv("CRYPTO_BOT_MASTER_KEY")
        if not self.master_key:
            logger.warning("Master key not provided. Using default key (NOT SECURE FOR PRODUCTION)")
            self.master_key = "default_development_key_do_not_use_in_production"

        self._cipher = self._create_cipher()

    def _create_cipher(self) -> Fernet:
        """暗号化/復号化用のFernetインスタンスを作成"""
        # パスワードからキーを生成
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"crypto_bot_salt_v1",  # 本番環境では環境固有のsaltを使用
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)

    def encrypt_api_key(self, api_key: str) -> str:
        """APIキーを暗号化"""
        try:
            encrypted = self._cipher.encrypt(api_key.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """暗号化されたAPIキーを復号化"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise

    def encrypt_credentials(self, credentials: Dict[str, str]) -> str:
        """認証情報の辞書を暗号化"""
        try:
            json_str = json.dumps(credentials)
            encrypted = self._cipher.encrypt(json_str.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise

    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, str]:
        """暗号化された認証情報を復号化"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credentials.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise

    def validate_api_key_permissions(self, exchange: str, permissions: Dict[str, bool]) -> bool:
        """
        APIキーの権限を検証

        Args:
            exchange: 取引所名
            permissions: 権限の辞書 (例: {"trade": True, "withdraw": False})

        Returns:
            bool: 権限が適切な場合True
        """
        # 必須権限
        required_permissions = {
            "read": True,
            "trade": True,
            "withdraw": False,  # 出金権限は禁止
        }

        # 取引所別の追加チェック
        if exchange in ["binance", "bybit", "bitget"]:
            # 出金権限がないことを確認
            if permissions.get("withdraw", False):
                logger.error(f"API key for {exchange} has withdraw permission - REJECTED")
                return False

        # 必要な権限があることを確認
        for perm, required in required_permissions.items():
            if perm == "withdraw":
                # 出金権限は持っていてはいけない
                if permissions.get(perm, False) != required:
                    return False
            else:
                # その他の権限は必須
                if not permissions.get(perm, False) and required:
                    return False

        return True

    def sanitize_error_message(self, error_msg: str) -> str:
        """エラーメッセージから機密情報を除去"""
        # APIキーやシークレットのパターンを検出して除去
        sensitive_patterns = [
            r"sk_[A-Za-z0-9_]{16,}",  # sk_prefixのAPIキー
            r"[A-Za-z0-9]{32,}",  # 一般的なAPIキーパターン
            r"0x[A-Fa-f0-9]{40,}",  # 秘密鍵パターン（短縮）
            r'secret["\']?\s*[:=]\s*["\']?[^"\'\s]+',  # secretを含む値
            r'key["\']?\s*[:=]\s*["\']?[^"\'\s]+',  # keyを含む値
        ]

        import re

        sanitized = error_msg
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized

    def generate_secure_config(self) -> Dict[str, str]:
        """セキュアな設定テンプレートを生成"""
        return {
            "CRYPTO_BOT_MASTER_KEY": Fernet.generate_key().decode(),
            "USE_MOCK_DATA": "true",  # デフォルトはモックデータ
            "ENABLE_WITHDRAW": "false",  # 出金機能は無効
            "RATE_LIMIT_SAFETY_FACTOR": "0.8",  # レート制限の80%で警告
            "MAX_ORDER_VALUE_USD": "1000",  # 最大注文額制限
            "REQUIRE_2FA_FOR_TRADES": "true",  # 取引時の2段階認証
        }


class IPWhitelistManager:
    """IP制限管理"""

    def __init__(self):
        self.whitelist = set()
        self._load_whitelist()

    def _load_whitelist(self):
        """環境変数からIPホワイトリストを読み込み"""
        ip_list = os.getenv("ALLOWED_IPS", "").split(",")
        self.whitelist = {ip.strip() for ip in ip_list if ip.strip()}

    def is_allowed(self, ip_address: str) -> bool:
        """IPアドレスが許可されているか確認"""
        if not self.whitelist:
            # ホワイトリストが空の場合は全て許可（開発環境）
            return True
        return ip_address in self.whitelist

    def add_ip(self, ip_address: str):
        """IPアドレスをホワイトリストに追加"""
        self.whitelist.add(ip_address)

    def remove_ip(self, ip_address: str):
        """IPアドレスをホワイトリストから削除"""
        self.whitelist.discard(ip_address)


# シングルトンインスタンス
security_manager = SecurityManager()
ip_whitelist = IPWhitelistManager()
