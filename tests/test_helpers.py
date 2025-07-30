"""
テスト用ヘルパー関数
CI環境でのデータベース接続問題を回避するためのユーティリティ
"""

import os
import tempfile
from typing import Dict, Optional
from unittest.mock import MagicMock, patch


def get_test_paper_config(database_url: Optional[str] = None) -> Dict:
    """
    テスト用のPaper Trading設定を返す

    Args:
        database_url: カスタムデータベースURL（省略時はインメモリSQLite）

    Returns:
        Paper Trading設定辞書
    """
    if database_url is None:
        # CI環境またはテスト環境では常にインメモリSQLiteを使用
        if os.environ.get("CI") == "true" or os.environ.get("ENVIRONMENT") in ["test", "ci", "testing"]:
            database_url = "sqlite:///:memory:"
        else:
            # 通常のテスト環境では一時ファイルを使用
            temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            database_url = f"sqlite:///{temp_db.name}"

    return {
        "database_url": database_url,
        "default_setting": "test",
        "fee_rates": {"maker": 0.001, "taker": 0.001},
        "initial_balance": {"USDT": 10000.0},
        "mock_api_keys": True,  # 常にモックAPIキーを使用
    }


def create_mock_database_manager():
    """
    モックのDatabaseManagerを作成
    CI環境でのPostgreSQL接続エラーを回避
    """
    mock_db_manager = MagicMock()

    # 必要なメソッドをモック
    mock_db_manager.create_tables = MagicMock()
    mock_db_manager.drop_tables = MagicMock()
    mock_db_manager.get_session = MagicMock(return_value=MagicMock())
    mock_db_manager.get_engine = MagicMock(return_value=MagicMock())

    return mock_db_manager


def patch_database_manager_for_tests():
    """
    テスト用にDatabaseManagerをパッチ
    デコレータとして使用可能
    """

    def decorator(func):
        @patch("src.backend.database.models.DatabaseManager")
        def wrapper(mock_db_manager_class, *args, **kwargs):
            # DatabaseManagerクラスをモック
            mock_instance = create_mock_database_manager()
            mock_db_manager_class.return_value = mock_instance

            # テスト関数を実行
            return func(*args, **kwargs)

        return wrapper

    return decorator


def create_test_exchange_factory_with_paper_config():
    """
    テスト用のExchangeFactoryを作成（Paper Trading設定済み）
    """
    from src.backend.exchanges.factory import ExchangeFactory

    factory = ExchangeFactory()

    # _create_paper_trading_adapterメソッドをパッチ
    original_method = factory._create_paper_trading_adapter

    def patched_method(real_exchange, user_id, paper_config):
        # 常にテスト用設定を使用
        test_config = get_test_paper_config()
        merged_config = {**test_config, **paper_config}
        return original_method(real_exchange, user_id, merged_config)

    factory._create_paper_trading_adapter = patched_method

    return factory
