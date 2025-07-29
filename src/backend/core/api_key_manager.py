"""
APIキー管理セキュリティ強化モジュール
APIキーの暗号化、検証、ローテーション機能を提供
"""

import base64
import hashlib
import hmac
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import settings

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    APIキーの安全な管理を行うクラス
    暗号化、検証、ローテーション機能を提供
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Args:
            master_key: 暗号化用のマスターキー（None の場合は JWT_SECRET を使用）
        """
        self.master_key = master_key or settings.JWT_SECRET
        self._fernet = self._create_cipher()

        # APIキーのパターン定義（セキュリティ検証用）
        self.api_key_patterns = {
            "binance": r"^[A-Za-z0-9]{64}$",
            "bybit": r"^[A-Za-z0-9]{20,}$",
            "bitget": r"^bg_[A-Za-z0-9]{32}$",
            "backpack": r"^[A-Za-z0-9\-]{36}$",
        }

        # 危険なキーパターン（テスト用やデフォルト値の検出）
        self.dangerous_patterns = [
            r"test[_\-]?api[_\-]?key",
            r"demo[_\-]?key",
            r"your[_\-]?api[_\-]?key",
            r"change[_\-]?this",
            r"example[_\-]?key",
            r"1234567890",
            r"abcdefgh",
        ]

    def _create_cipher(self) -> Fernet:
        """暗号化用のFernetインスタンスを作成"""
        # マスターキーからキーを派生
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"stable_salt_for_api_keys",  # 本番では動的ソルトを推奨
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)

    def encrypt_api_key(self, api_key: str) -> str:
        """
        APIキーを暗号化

        Args:
            api_key: 暗号化するAPIキー

        Returns:
            str: 暗号化されたAPIキー（base64エンコード）
        """
        if not api_key:
            return ""

        encrypted = self._fernet.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        暗号化されたAPIキーを復号化

        Args:
            encrypted_key: 暗号化されたAPIキー

        Returns:
            str: 復号化されたAPIキー
        """
        if not encrypted_key:
            return ""

        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted = self._fernet.decrypt(encrypted_data)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise ValueError("Invalid encrypted API key")

    def validate_api_key(self, api_key: str, exchange: str) -> Tuple[bool, List[str]]:
        """
        APIキーの形式と安全性を検証

        Args:
            api_key: 検証するAPIキー
            exchange: 取引所名

        Returns:
            Tuple[bool, List[str]]: (有効性, エラーメッセージリスト)
        """
        errors = []

        if not api_key:
            errors.append("API key is empty")
            return False, errors

        # 最小長チェック
        if len(api_key) < 16:
            errors.append("API key is too short (minimum 16 characters)")

        # 最大長チェック
        if len(api_key) > 200:
            errors.append("API key is too long (maximum 200 characters)")

        # 危険なパターンチェック
        for pattern in self.dangerous_patterns:
            if re.search(pattern, api_key, re.IGNORECASE):
                errors.append(f"API key contains dangerous pattern: {pattern}")

        # 取引所固有の形式チェック（実際のAPIキー形式に合わせて緩和）
        if exchange.lower() in self.api_key_patterns:
            pattern = self.api_key_patterns[exchange.lower()]
            # Binanceの場合は64文字で英数字であることを確認
            if exchange.lower() == "binance":
                if len(api_key) != 64 or not re.match(r"^[A-Za-z0-9]+$", api_key):
                    errors.append(f"API key format invalid for {exchange} (expected 64 alphanumeric characters)")
            elif not re.match(pattern, api_key):
                errors.append(f"API key format invalid for {exchange}")

        # エントロピーチェック（ランダム性検証）
        if not self._check_entropy(api_key):
            errors.append("API key has low entropy (may be predictable)")

        return len(errors) == 0, errors

    def _check_entropy(self, key: str, min_entropy: float = 2.5) -> bool:
        """
        APIキーのエントロピーをチェック
        ランダム性の低いキーを検出
        """
        if len(key) < 8:
            return False

        # 同じ文字の連続をチェック
        consecutive_count = 1
        max_consecutive = 1
        for i in range(1, len(key)):
            if key[i] == key[i - 1]:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1

        # 同じ文字が5回以上連続している場合は低エントロピー
        if max_consecutive >= 5:
            return False

        # 文字の種類をチェック
        unique_chars = len(set(key))
        entropy_ratio = unique_chars / len(key)

        return entropy_ratio >= 0.3  # 文字の30%以上が異なる文字である

    def mask_api_key(self, api_key: str, visible_chars: int = 6) -> str:
        """
        APIキーをマスク（ログや表示用）

        Args:
            api_key: マスクするAPIキー
            visible_chars: 表示する文字数

        Returns:
            str: マスクされたAPIキー
        """
        if not api_key:
            return "***EMPTY***"

        if len(api_key) <= visible_chars * 2:
            return "*" * len(api_key)

        start = api_key[:visible_chars]
        end = api_key[-visible_chars:]
        middle = "*" * (len(api_key) - visible_chars * 2)

        return f"{start}{middle}{end}"

    def generate_api_key_hash(self, api_key: str) -> str:
        """
        APIキーのハッシュを生成（重複チェック用）

        Args:
            api_key: ハッシュ化するAPIキー

        Returns:
            str: SHA256ハッシュ
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key_integrity(self, api_key: str, expected_hash: str) -> bool:
        """
        APIキーの整合性を検証

        Args:
            api_key: 検証するAPIキー
            expected_hash: 期待されるハッシュ値

        Returns:
            bool: 整合性チェック結果
        """
        actual_hash = self.generate_api_key_hash(api_key)
        return hmac.compare_digest(actual_hash, expected_hash)

    def get_exchange_credentials(self, exchange: str) -> Tuple[str, str]:
        """
        取引所の認証情報を安全に取得

        Args:
            exchange: 取引所名

        Returns:
            Tuple[str, str]: (api_key, secret)
        """
        exchange = exchange.lower()

        # 環境変数から取得
        api_key = ""
        secret = ""

        if exchange == "binance":
            api_key = settings.BINANCE_API_KEY
            secret = settings.BINANCE_SECRET
        elif exchange == "bybit":
            api_key = settings.BYBIT_API_KEY
            secret = settings.BYBIT_SECRET
        elif exchange == "bitget":
            api_key = settings.BITGET_API_KEY
            secret = settings.BITGET_SECRET
        elif exchange == "backpack":
            api_key = settings.BACKPACK_API_KEY
            secret = settings.BACKPACK_SECRET
        elif exchange == "hyperliquid":
            api_key = settings.HYPERLIQUID_ADDRESS
            secret = settings.HYPERLIQUID_PRIVATE_KEY

        # セキュリティ検証
        if api_key:
            is_valid, errors = self.validate_api_key(api_key, exchange)
            if not is_valid:
                logger.warning(f"Invalid API key for {exchange}: {errors}")
                if settings.is_production:
                    raise ValueError(f"Invalid API key configuration for {exchange}")

        return api_key, secret

    def audit_all_api_keys(self) -> Dict[str, Dict]:
        """
        全てのAPIキーの監査を実行

        Returns:
            Dict: 監査結果
        """
        audit_results = {}

        exchanges = ["binance", "bybit", "bitget", "backpack", "hyperliquid"]

        for exchange in exchanges:
            try:
                api_key, secret = self.get_exchange_credentials(exchange)

                # APIキーの検証
                key_valid, key_errors = (
                    self.validate_api_key(api_key, exchange) if api_key else (False, ["Missing API key"])
                )
                secret_valid, secret_errors = (
                    self.validate_api_key(secret, exchange) if secret else (False, ["Missing secret"])
                )

                audit_results[exchange] = {
                    "api_key_present": bool(api_key),
                    "secret_present": bool(secret),
                    "api_key_valid": key_valid,
                    "secret_valid": secret_valid,
                    "api_key_errors": key_errors,
                    "secret_errors": secret_errors,
                    "api_key_masked": self.mask_api_key(api_key),
                    "secret_masked": self.mask_api_key(secret),
                    "last_checked": datetime.now().isoformat(),
                }

            except Exception as e:
                audit_results[exchange] = {"error": str(e), "last_checked": datetime.now().isoformat()}

        return audit_results


# グローバルインスタンス
api_key_manager = APIKeyManager()


def get_secure_api_credentials(exchange: str) -> Tuple[str, str]:
    """
    安全にAPIクレデンシャルを取得

    Args:
        exchange: 取引所名

    Returns:
        Tuple[str, str]: (api_key, secret)
    """
    return api_key_manager.get_exchange_credentials(exchange)


def validate_exchange_credentials(exchange: str, api_key: str, secret: str) -> Tuple[bool, List[str]]:
    """
    取引所クレデンシャルの検証

    Args:
        exchange: 取引所名
        api_key: APIキー
        secret: シークレットキー

    Returns:
        Tuple[bool, List[str]]: (有効性, エラーリスト)
    """
    all_errors = []

    # APIキーの検証
    key_valid, key_errors = api_key_manager.validate_api_key(api_key, exchange)
    all_errors.extend([f"API Key: {error}" for error in key_errors])

    # シークレットの検証
    secret_valid, secret_errors = api_key_manager.validate_api_key(secret, exchange)
    all_errors.extend([f"Secret: {error}" for error in secret_errors])

    return len(all_errors) == 0, all_errors
