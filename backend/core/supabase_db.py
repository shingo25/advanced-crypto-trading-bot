"""
Supabase SDKベースのデータベース接続層
SQLAlchemyの代替として、Supabase SDKを使用したデータベース操作を提供
"""
import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseConnection:
    """Supabase接続を管理するクラス"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Supabaseクライアントを初期化"""
        try:
            url = settings.SUPABASE_URL
            # service_role_keyを使用して管理者権限でアクセス
            key = settings.SUPABASE_SERVICE_ROLE_KEY
            
            if not url or not key:
                raise ValueError("SUPABASE_URLまたはSUPABASE_SERVICE_ROLE_KEYが設定されていません")
            
            self._client = create_client(url, key)
            logger.info("Supabaseクライアント初期化成功")
            
        except Exception as e:
            logger.error(f"Supabaseクライアント初期化失敗: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Supabaseクライアントを取得"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def health_check(self) -> bool:
        """接続の健全性をチェック"""
        try:
            # 簡単なクエリで接続をテスト
            response = self.client.table('profiles').select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"接続ヘルスチェック失敗: {e}")
            return False

class SupabaseTable:
    """Supabaseテーブル操作の基底クラス"""
    
    def __init__(self, table_name: str, connection: SupabaseConnection):
        self.table_name = table_name
        self.connection = connection
        self.table = connection.client.table(table_name)
    
    def select(self, columns: str = "*", **filters) -> List[Dict[str, Any]]:
        """データを選択して取得"""
        try:
            query = self.table.select(columns)
            
            # フィルターを適用
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"{self.table_name}からの選択エラー: {e}")
            raise
    
    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """新しいレコードを挿入"""
        try:
            response = self.table.insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"{self.table_name}への挿入エラー: {e}")
            raise
    
    def update(self, data: Dict[str, Any], **filters) -> List[Dict[str, Any]]:
        """既存のレコードを更新"""
        try:
            query = self.table.update(data)
            
            # フィルターを適用
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"{self.table_name}の更新エラー: {e}")
            raise
    
    def delete(self, **filters) -> List[Dict[str, Any]]:
        """レコードを削除"""
        try:
            query = self.table.delete()
            
            # フィルターを適用
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"{self.table_name}からの削除エラー: {e}")
            raise
    
    def count(self, **filters) -> int:
        """レコード数をカウント"""
        try:
            query = self.table.select("id", count="exact")
            
            # フィルターを適用
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"{self.table_name}のカウントエラー: {e}")
            raise

# グローバルな接続インスタンス
_supabase_connection: Optional[SupabaseConnection] = None

def get_supabase_connection() -> SupabaseConnection:
    """Supabase接続のシングルトンインスタンスを取得"""
    global _supabase_connection
    if _supabase_connection is None:
        _supabase_connection = SupabaseConnection()
    return _supabase_connection

def get_supabase_client() -> Client:
    """Supabaseクライアントを取得（FastAPI依存性注入用）"""
    return get_supabase_connection().client