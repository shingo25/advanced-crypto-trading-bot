"""
取引アダプターの抽象基底クラス
循環import問題を解決するための共通インターフェース
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal


class AbstractTradingAdapter(ABC):
    """
    取引アダプターの抽象基底クラス
    Live Trading と Paper Trading の共通インターフェースを定義
    """
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """残高を取得"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """価格データを取得"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """板情報を取得"""
        pass
    
    @abstractmethod
    async def place_order(self, order) -> Dict[str, Any]:
        """注文を発注"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """注文をキャンセル"""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """注文状況を取得"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """未決済注文を取得"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """取引所に接続"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """取引所から切断"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """接続状態を確認"""
        pass
    
    # 共通プロパティ
    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """取引所名"""
        pass


class AbstractAdapterFactory(ABC):
    """
    アダプターファクトリーの抽象基底クラス
    """
    
    @abstractmethod
    def create_adapter(
        self, 
        exchange_name: str, 
        **kwargs
    ) -> AbstractTradingAdapter:
        """指定された取引所のアダプターを作成"""
        pass
    
    @abstractmethod
    def get_supported_exchanges(self) -> List[str]:
        """サポートされている取引所一覧を返す"""
        pass