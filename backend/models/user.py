"""
ユーザー関連のデータモデル（Supabase SDK版）
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.core.supabase_db import SupabaseTable, get_supabase_connection
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ProfilesModel:
    """Profilesテーブルの操作を管理"""

    def __init__(self):
        self._connection = None
        self._table = None

    @property
    def connection(self):
        """遅延初期化でSupabase接続を取得"""
        if self._connection is None:
            self._connection = get_supabase_connection()
        return self._connection

    @property
    def table(self):
        """遅延初期化でSupabaseテーブルを取得"""
        if self._table is None:
            self._table = SupabaseTable("profiles", self.connection)
        return self._table

    def get_profile_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """IDでプロファイルを取得"""
        try:
            profiles = self.table.select("*", id=user_id)
            return profiles[0] if profiles else None
        except Exception as e:
            logger.error(f"プロファイル取得エラー (ID: {user_id}): {e}")
            return None

    def get_profile_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """ユーザー名でプロファイルを取得"""
        try:
            profiles = self.table.select("*", username=username)
            return profiles[0] if profiles else None
        except Exception as e:
            logger.error(f"プロファイル取得エラー (Username: {username}): {e}")
            return None

    def create_profile(self, user_id: str, username: str) -> Optional[Dict[str, Any]]:
        """新しいプロファイルを作成"""
        try:
            profile_data = {
                "id": user_id,
                "username": username,
                "created_at": datetime.utcnow().isoformat(),
            }
            return self.table.insert(profile_data)
        except Exception as e:
            logger.error(f"プロファイル作成エラー: {e}")
            return None

    def update_profile(self, user_id: str, **updates) -> Optional[Dict[str, Any]]:
        """プロファイルを更新"""
        try:
            profiles = self.table.update(updates, id=user_id)
            return profiles[0] if profiles else None
        except Exception as e:
            logger.error(f"プロファイル更新エラー (ID: {user_id}): {e}")
            return None

    def list_profiles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """プロファイル一覧を取得"""
        try:
            return self.table.select("*")[:limit]
        except Exception as e:
            logger.error(f"プロファイル一覧取得エラー: {e}")
            return []


class ExchangesModel:
    """Exchangesテーブルの操作を管理"""

    def __init__(self):
        self._connection = None
        self._table = None

    @property
    def connection(self):
        """遅延初期化でSupabase接続を取得"""
        if self._connection is None:
            self._connection = get_supabase_connection()
        return self._connection

    @property
    def table(self):
        """遅延初期化でSupabaseテーブルを取得"""
        if self._table is None:
            self._table = SupabaseTable("exchanges", self.connection)
        return self._table

    def get_user_exchanges(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーの取引所一覧を取得"""
        try:
            return self.table.select("*", user_id=user_id)
        except Exception as e:
            logger.error(f"ユーザー取引所取得エラー (ID: {user_id}): {e}")
            return []

    def get_exchange_by_id(self, exchange_id: str) -> Optional[Dict[str, Any]]:
        """IDで取引所を取得"""
        try:
            exchanges = self.table.select("*", id=exchange_id)
            return exchanges[0] if exchanges else None
        except Exception as e:
            logger.error(f"取引所取得エラー (ID: {exchange_id}): {e}")
            return None

    def create_exchange(
        self, user_id: str, name: str, api_key: str, api_secret: str
    ) -> Optional[Dict[str, Any]]:
        """新しい取引所を追加"""
        try:
            exchange_data = {
                "user_id": user_id,
                "name": name,
                "api_key": api_key,  # 本来は暗号化すべき
                "api_secret": api_secret,  # 本来は暗号化すべき
                "created_at": datetime.utcnow().isoformat(),
            }
            return self.table.insert(exchange_data)
        except Exception as e:
            logger.error(f"取引所作成エラー: {e}")
            return None

    def update_exchange(self, exchange_id: str, **updates) -> Optional[Dict[str, Any]]:
        """取引所情報を更新"""
        try:
            exchanges = self.table.update(updates, id=exchange_id)
            return exchanges[0] if exchanges else None
        except Exception as e:
            logger.error(f"取引所更新エラー (ID: {exchange_id}): {e}")
            return None

    def delete_exchange(self, exchange_id: str) -> bool:
        """取引所を削除"""
        try:
            self.table.delete(id=exchange_id)
            return True
        except Exception as e:
            logger.error(f"取引所削除エラー (ID: {exchange_id}): {e}")
            return False


# モデルインスタンスのシングルトン
_profiles_model: Optional[ProfilesModel] = None
_exchanges_model: Optional[ExchangesModel] = None


def get_profiles_model() -> ProfilesModel:
    """Profilesモデルのシングルトンインスタンスを取得"""
    global _profiles_model
    if _profiles_model is None:
        _profiles_model = ProfilesModel()
    return _profiles_model


def get_exchanges_model() -> ExchangesModel:
    """Exchangesモデルのシングルトンインスタンスを取得"""
    global _exchanges_model
    if _exchanges_model is None:
        _exchanges_model = ExchangesModel()
    return _exchanges_model


# Pydantic response models
class UserResponse(BaseModel):
    """ユーザー情報のレスポンスモデル"""

    id: str
    username: str
    role: str = "viewer"
    created_at: Optional[str] = None
