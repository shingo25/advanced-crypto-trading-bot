"""
PyTest設定ファイル
テスト実行時のSupabase接続モック化を実装
"""

import os
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test_key"
os.environ["JWT_SECRET"] = "test_secret_key_for_jwt"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


class MockSupabaseClient:
    """モックSupabaseクライアント"""

    def __init__(self):
        self._tables = {}

    def table(self, table_name: str):
        """モックテーブルを返す"""
        if table_name not in self._tables:
            self._tables[table_name] = MockSupabaseTable(table_name)
        return self._tables[table_name]


class MockSupabaseTable:
    """モックSupabaseテーブル"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._query = MockSupabaseQuery()

    def select(self, columns: str = "*"):
        """SELECT操作のモック"""
        self._query._columns = columns
        return self._query

    def insert(self, data: Dict[str, Any]):
        """INSERT操作のモック"""
        return MockSupabaseResponse([{"id": 1, **data}])

    def update(self, data: Dict[str, Any]):
        """UPDATE操作のモック"""
        self._query._update_data = data
        return self._query

    def delete(self):
        """DELETE操作のモック"""
        return self._query


class MockSupabaseQuery:
    """モックSupabaseクエリ"""

    def __init__(self):
        self._columns = "*"
        self._filters = {}
        self._update_data = {}
        self._limit_value = None

    def eq(self, column: str, value: Any):
        """等価条件のモック"""
        self._filters[column] = value
        return self

    def limit(self, count: int):
        """LIMIT操作のモック"""
        self._limit_value = count
        return self

    def execute(self):
        """クエリ実行のモック"""
        # テーブル名に応じたモックデータを返す
        if "profiles" in str(self._filters) or self._columns == "id":
            # ヘルスチェック用のモックレスポンス
            return MockSupabaseResponse([{"id": 1}])
        elif self._update_data:
            # UPDATE操作のモックレスポンス
            return MockSupabaseResponse([{"id": 1, **self._update_data}])
        else:
            # その他のモックレスポンス
            return MockSupabaseResponse([])


class MockSupabaseResponse:
    """モックSupabaseレスポンス"""

    def __init__(self, data: List[Dict[str, Any]], count: Optional[int] = None):
        self.data = data
        self.count = count if count is not None else len(data)


class MockSupabaseConnection:
    """モックSupabaseConnection"""

    def __init__(self):
        self._client = MockSupabaseClient()

    @property
    def client(self):
        """モッククライアントを返す"""
        return self._client

    def health_check(self) -> bool:
        """ヘルスチェックのモック（常に成功）"""
        return True


@pytest.fixture(autouse=True)
def mock_supabase_connection(monkeypatch):
    """
    Supabase接続を自動的にモック化するフィクスチャ
    全てのテストで自動的に適用される
    """
    # SupabaseConnectionクラスをモック化
    mock_connection = MockSupabaseConnection()

    # get_supabase_connection関数をモック化
    def mock_get_supabase_connection():
        return mock_connection

    # get_supabase_client関数をモック化
    def mock_get_supabase_client():
        return mock_connection.client

    # monkeypatchで関数を置き換え
    monkeypatch.setattr("backend.core.supabase_db.get_supabase_connection", mock_get_supabase_connection)
    monkeypatch.setattr("backend.core.supabase_db.get_supabase_client", mock_get_supabase_client)

    # SupabaseConnectionクラス自体もモック化
    monkeypatch.setattr("backend.core.supabase_db.SupabaseConnection", MockSupabaseConnection)

    return mock_connection


@pytest.fixture
def mock_supabase_client(mock_supabase_connection):
    """モックSupabaseクライアントを返すフィクスチャ"""
    return mock_supabase_connection.client


@pytest.fixture
def sample_user_data():
    """テスト用のサンプルユーザーデータ"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_trading_data():
    """テスト用のサンプル取引データ"""
    return {
        "id": "trade-123",
        "user_id": "test-user-123",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.001,
        "price": 45000.0,
        "status": "filled",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_strategy_data():
    """テスト用のサンプル戦略データ"""
    return {
        "id": "strategy-123",
        "name": "EMA Cross Strategy",
        "description": "Simple EMA crossover strategy",
        "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis for all tests"""
    mock_redis_client = MagicMock()
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.return_value = None
    mock_redis_client.set.return_value = True
    mock_redis_client.publish.return_value = 1
    mock_redis_client.pubsub.return_value = MagicMock()
    mock_redis_client.subscribe = MagicMock()
    mock_redis_client.unsubscribe = MagicMock()

    def mock_redis_constructor(*args, **kwargs):
        return mock_redis_client

    monkeypatch.setattr("redis.Redis", mock_redis_constructor)
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: mock_redis_client)

    # Mock Redis in alert system
    try:
        import backend.notifications.alert_manager

        monkeypatch.setattr(backend.notifications.alert_manager, "redis_client", mock_redis_client)
    except ImportError:
        pass

    return mock_redis_client


@pytest.fixture
def test_user():
    """Test user data for authentication"""
    return {"id": "test-user-123", "email": "test@example.com", "username": "testuser"}


@pytest.fixture
def auth_headers(test_user):
    """Authorization headers with valid JWT token"""
    from backend.api.auth import create_access_token

    token = create_access_token(data={"sub": test_user["id"]}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_auth_dependency(monkeypatch, test_user):
    """Mock authentication dependency for all tests"""

    async def mock_get_current_user(*args, **kwargs):
        return test_user

    # Mock in multiple places to ensure coverage
    try:
        from backend.api import auth

        monkeypatch.setattr(auth, "get_current_user", mock_get_current_user)
    except ImportError:
        pass

    try:
        from backend.core import security

        monkeypatch.setattr(security, "get_current_user", mock_get_current_user)
    except ImportError:
        pass

    return mock_get_current_user
