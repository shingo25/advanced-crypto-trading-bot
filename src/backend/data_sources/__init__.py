"""
データソース管理モジュール
モックデータと実データの切り替えを管理
"""

from .interfaces import DataSourceStrategy
from .manager import DataSourceManager, data_source_manager
from .mock_data_source import MockDataSource
from .live_data_source import LiveDataSource

__all__ = [
    "DataSourceStrategy",
    "DataSourceManager",
    "data_source_manager",
    "MockDataSource",
    "LiveDataSource",
]