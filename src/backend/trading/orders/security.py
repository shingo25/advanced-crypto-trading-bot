"""
セキュリティ管理機能
APIキー暗号化、IP制限、レート制限、異常検知などを提供
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from typing import Dict, List, Optional, Tuple

from cryptography.fernet import Fernet

from src.backend.trading.orders.models import Order, OrderSide

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """セキュリティエラー"""

    pass


class RateLimitExceeded(SecurityError):
    """レート制限エラー"""

    pass


class AnomalousActivityDetected(SecurityError):
    """異常活動検知エラー"""

    pass


class SecurityManager:
    """
    セキュリティ管理クラス
    暗号化、アクセス制御、異常検知機能を提供
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: セキュリティ設定
        """
        self.config = config

        # 暗号化設定
        encryption_key = config.get("MASTER_ENCRYPTION_KEY")
        if not encryption_key:
            raise SecurityError("MASTER_ENCRYPTION_KEY is required")

        try:
            if isinstance(encryption_key, str):
                # 文字列の場合はbase64デコードを試行

                try:
                    decoded_key = base64.urlsafe_b64decode(encryption_key)
                    self.cipher_suite = Fernet(decoded_key)
                except (base64.binascii.Error, ValueError) as decode_error:
                    # base64デコードに失敗した場合は直接使用
                    logger.debug(f"Base64 decode failed, using string directly: {decode_error}")
                    self.cipher_suite = Fernet(encryption_key.encode())
            else:
                # bytesの場合は直接使用
                self.cipher_suite = Fernet(encryption_key)
        except Exception as e:
            raise SecurityError(f"Invalid encryption key: {e}")

        # IP whitelist設定
        self.ip_whitelist = set(config.get("IP_WHITELIST", []))
        self.enable_ip_filtering = config.get("ENABLE_IP_FILTERING", True)

        # レート制限設定
        self.rate_limits = config.get(
            "RATE_LIMITS",
            {
                "orders_per_minute": 30,
                "orders_per_hour": 200,
                "api_calls_per_minute": 100,
            },
        )

        # レート制限カウンター
        self.rate_limit_counters = defaultdict(
            lambda: {
                "minute": deque(maxlen=60),
                "hour": deque(maxlen=3600),
            }
        )

        # 異常検知設定
        self.anomaly_thresholds = config.get(
            "ANOMALY_THRESHOLDS",
            {
                "max_order_value_ratio": 0.25,  # ポートフォリオの25%
                "max_hourly_trades": 50,  # 1時間50取引
                "max_price_deviation": 0.10,  # 10%価格乖離
                "suspicious_symbol_threshold": 5,  # 新規シンボル5つ/日
            },
        )

        # 異常検知データ
        self.user_activity = defaultdict(
            lambda: {
                "order_history": deque(maxlen=1000),
                "symbol_history": deque(maxlen=100),
                "daily_symbols": set(),
                "last_reset": datetime.now(timezone.utc).date(),
            }
        )

        # 監査ログ
        self.audit_logs = deque(maxlen=10000)

    def encrypt_api_key(self, api_key: str) -> bytes:
        """
        APIキーを暗号化

        Args:
            api_key: 暗号化するAPIキー

        Returns:
            bytes: 暗号化されたAPIキー
        """
        try:
            encrypted = self.cipher_suite.encrypt(api_key.encode("utf-8"))
            self._log_audit_event("api_key_encrypted", {"status": "success"})
            return encrypted
        except Exception as e:
            self._log_audit_event("api_key_encryption_failed", {"error": str(e)})
            raise SecurityError(f"Failed to encrypt API key: {e}")

    def decrypt_api_key(self, encrypted_key: bytes) -> str:
        """
        APIキーを復号化

        Args:
            encrypted_key: 暗号化されたAPIキー

        Returns:
            str: 復号化されたAPIキー
        """
        try:
            decrypted = self.cipher_suite.decrypt(encrypted_key).decode("utf-8")
            self._log_audit_event("api_key_decrypted", {"status": "success"})
            return decrypted
        except Exception as e:
            self._log_audit_event("api_key_decryption_failed", {"error": str(e)})
            raise SecurityError(f"Failed to decrypt API key: {e}")

    def check_ip_address(self, ip_address: str) -> bool:
        """
        IPアドレスのホワイトリストチェック

        Args:
            ip_address: チェックするIPアドレス

        Returns:
            bool: 許可されたIPアドレスかどうか
        """
        if not self.enable_ip_filtering:
            return True

        if not ip_address:
            self._log_audit_event("ip_check_failed", {"error": "No IP address provided"})
            return False

        try:
            # IPv4/IPv6アドレスの正規化
            try:
                normalized_ip = str(IPv4Address(ip_address))
            except AddressValueError:
                try:
                    normalized_ip = str(IPv6Address(ip_address))
                except AddressValueError:
                    self._log_audit_event("ip_check_failed", {"ip": ip_address, "error": "Invalid IP format"})
                    return False

            is_allowed = normalized_ip in self.ip_whitelist or not self.ip_whitelist

            self._log_audit_event(
                "ip_check", {"ip": normalized_ip, "allowed": is_allowed, "whitelist_size": len(self.ip_whitelist)}
            )

            return is_allowed

        except Exception as e:
            self._log_audit_event("ip_check_error", {"ip": ip_address, "error": str(e)})
            return False

    def check_rate_limit(self, user_id: str, operation: str = "order") -> bool:
        """
        レート制限チェック

        Args:
            user_id: ユーザーID
            operation: 操作タイプ

        Returns:
            bool: レート制限内かどうか
        """
        current_time = time.time()
        current_minute = int(current_time // 60)
        current_hour = int(current_time // 3600)

        user_counters = self.rate_limit_counters[user_id]

        # 古いエントリを削除
        self._cleanup_rate_limit_counters(user_counters, current_minute, current_hour)

        # 現在のカウントをチェック
        minute_count = len([t for t in user_counters["minute"] if t >= current_minute])
        hour_count = len([t for t in user_counters["hour"] if t >= current_hour])

        # 制限チェック
        minute_limit = self.rate_limits.get("orders_per_minute", 30)
        hour_limit = self.rate_limits.get("orders_per_hour", 200)

        if minute_count >= minute_limit:
            self._log_audit_event(
                "rate_limit_exceeded",
                {
                    "user_id": user_id,
                    "operation": operation,
                    "period": "minute",
                    "count": minute_count,
                    "limit": minute_limit,
                },
            )
            return False

        if hour_count >= hour_limit:
            self._log_audit_event(
                "rate_limit_exceeded",
                {
                    "user_id": user_id,
                    "operation": operation,
                    "period": "hour",
                    "count": hour_count,
                    "limit": hour_limit,
                },
            )
            return False

        # カウンターを更新
        user_counters["minute"].append(current_minute)
        user_counters["hour"].append(current_hour)

        return True

    def check_for_anomalies(self, order: Order, user_id: str, portfolio_value: Optional[Decimal] = None) -> bool:
        """
        異常取引の検知

        Args:
            order: 注文
            user_id: ユーザーID
            portfolio_value: ポートフォリオ総額

        Returns:
            bool: 異常が検知されたかどうか（True=異常あり）
        """
        user_data = self.user_activity[user_id]
        current_time = datetime.now(timezone.utc)

        # 日次データのリセット
        if user_data["last_reset"] != current_time.date():
            user_data["daily_symbols"] = set()
            user_data["last_reset"] = current_time.date()

        anomalies = []

        # 1. Fat Finger チェック（大額注文）
        if portfolio_value:
            order_value = order.amount * (order.price or Decimal("50000"))  # 概算価格
            value_ratio = order_value / portfolio_value
            max_ratio = self.anomaly_thresholds["max_order_value_ratio"]

            if value_ratio > max_ratio:
                anomalies.append(f"Large order: {value_ratio:.2%} of portfolio (max: {max_ratio:.2%})")

        # 2. 高頻度取引チェック
        hour_ago = current_time.timestamp() - 3600
        recent_orders = [o for o in user_data["order_history"] if o["timestamp"] > hour_ago]
        max_hourly = self.anomaly_thresholds["max_hourly_trades"]

        if len(recent_orders) >= max_hourly:
            anomalies.append(f"High frequency: {len(recent_orders)} orders in last hour (max: {max_hourly})")

        # 3. 新規シンボル取引チェック
        if order.symbol not in user_data["symbol_history"]:
            user_data["daily_symbols"].add(order.symbol)
            max_new_symbols = self.anomaly_thresholds["suspicious_symbol_threshold"]

            if len(user_data["daily_symbols"]) > max_new_symbols:
                anomalies.append(f"Many new symbols: {len(user_data['daily_symbols'])} today (max: {max_new_symbols})")

        # 4. Wash Trading チェック（同じシンボルで反対売買）
        recent_same_symbol = [
            o
            for o in recent_orders
            if o["symbol"] == order.symbol and o["timestamp"] > current_time.timestamp() - 300  # 5分以内
        ]

        if recent_same_symbol:
            recent_sides = [o["side"] for o in recent_same_symbol]
            opposite_side = "sell" if order.side == OrderSide.BUY else "buy"

            if opposite_side in recent_sides:
                anomalies.append("Potential wash trading: opposite orders within 5 minutes")

        # 活動履歴を更新
        user_data["order_history"].append(
            {
                "timestamp": current_time.timestamp(),
                "symbol": order.symbol,
                "side": order.side.value,
                "amount": float(order.amount),
                "price": float(order.price) if order.price else None,
            }
        )

        user_data["symbol_history"].append(order.symbol)

        # 異常が検知された場合
        if anomalies:
            self._log_audit_event(
                "anomaly_detected", {"user_id": user_id, "order_id": order.id, "anomalies": anomalies}
            )
            return True

        return False

    def execute_security_checks(
        self, order: Order, request_context: Dict, portfolio_value: Optional[Decimal] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        包括的セキュリティチェックの実行

        Args:
            order: 注文
            request_context: リクエストコンテキスト
            portfolio_value: ポートフォリオ総額

        Returns:
            Tuple[bool, Optional[str]]: (is_secure, error_message)
        """
        try:
            user_id = request_context.get("user_id", "anonymous")
            ip_address = request_context.get("ip_address")

            # 1. IPアドレスチェック
            if not self.check_ip_address(ip_address):
                return False, f"IP address {ip_address} is not allowed"

            # 2. レート制限チェック
            if not self.check_rate_limit(user_id, "order"):
                return False, "Rate limit exceeded"

            # 3. 異常検知チェック
            if self.check_for_anomalies(order, user_id, portfolio_value):
                return False, "Anomalous trading activity detected"

            self._log_audit_event(
                "security_check_passed", {"user_id": user_id, "order_id": order.id, "ip_address": ip_address}
            )

            return True, None

        except Exception as e:
            self._log_audit_event("security_check_error", {"error": str(e), "order_id": order.id})
            return False, f"Security check failed: {e}"

    def _cleanup_rate_limit_counters(self, counters: Dict, current_minute: int, current_hour: int):
        """レート制限カウンターのクリーンアップ"""
        # 1分以上古いエントリを削除
        counters["minute"] = deque([t for t in counters["minute"] if t >= current_minute - 1], maxlen=60)

        # 1時間以上古いエントリを削除
        counters["hour"] = deque([t for t in counters["hour"] if t >= current_hour - 1], maxlen=3600)

    def _log_audit_event(self, event_type: str, details: Dict):
        """監査ログの記録"""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
        }

        self.audit_logs.append(audit_entry)
        logger.info(f"Security audit: {event_type} - {json.dumps(details)}")

    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """監査ログの取得"""
        return list(self.audit_logs)[-limit:]

    def add_ip_to_whitelist(self, ip_address: str):
        """IPアドレスをホワイトリストに追加"""
        try:
            normalized_ip = str(IPv4Address(ip_address))
        except AddressValueError:
            try:
                normalized_ip = str(IPv6Address(ip_address))
            except AddressValueError:
                raise SecurityError(f"Invalid IP address format: {ip_address}")

        self.ip_whitelist.add(normalized_ip)
        self._log_audit_event("ip_whitelist_updated", {"action": "add", "ip": normalized_ip})

    def remove_ip_from_whitelist(self, ip_address: str):
        """IPアドレスをホワイトリストから削除"""
        self.ip_whitelist.discard(ip_address)
        self._log_audit_event("ip_whitelist_updated", {"action": "remove", "ip": ip_address})

    def update_rate_limits(self, new_limits: Dict):
        """レート制限の更新"""
        old_limits = self.rate_limits.copy()
        self.rate_limits.update(new_limits)

        self._log_audit_event("rate_limits_updated", {"old_limits": old_limits, "new_limits": self.rate_limits})

    def reset_user_activity(self, user_id: str):
        """ユーザー活動データのリセット"""
        if user_id in self.user_activity:
            del self.user_activity[user_id]

        if user_id in self.rate_limit_counters:
            del self.rate_limit_counters[user_id]

        self._log_audit_event("user_activity_reset", {"user_id": user_id})

    def generate_api_signature(self, secret_key: str, method: str, path: str, body: str = "") -> str:
        """
        API署名の生成（追加のセキュリティ機能）

        Args:
            secret_key: シークレットキー
            method: HTTPメソッド
            path: APIパス
            body: リクエストボディ

        Returns:
            str: 生成された署名
        """
        timestamp = str(int(time.time() * 1000))
        message = f"{method}{path}{body}{timestamp}"

        signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

        return signature
