"""
データソース管理モジュール
モックデータと実データの切り替えを管理
"""

from .interfaces import DataSourceStrategy
from .live_data_source import LiveDataSource
from .manager import DataSourceManager, data_source_manager
from .mock_data_source import MockDataSource

__all__ = [
    "DataSourceStrategy",
    "DataSourceManager",
    "data_source_manager",
    "MockDataSource",
    "LiveDataSource",
]
