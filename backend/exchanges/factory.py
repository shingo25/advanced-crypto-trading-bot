from typing import Dict, Type
from backend.core.config import settings
from .base import AbstractExchangeAdapter
from .binance import BinanceAdapter
from .bybit import BybitAdapter
import logging

logger = logging.getLogger(__name__)


class ExchangeFactory:
    """取引所アダプタのファクトリークラス"""
    
    _adapters: Dict[str, Type[AbstractExchangeAdapter]] = {
        'binance': BinanceAdapter,
        'bybit': BybitAdapter,
    }
    
    @classmethod
    def create_adapter(cls, exchange_name: str, sandbox: bool = False) -> AbstractExchangeAdapter:
        """指定された取引所のアダプタを作成"""
        exchange_name = exchange_name.lower()
        
        if exchange_name not in cls._adapters:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        adapter_class = cls._adapters[exchange_name]
        
        # 設定から API キーを取得
        if exchange_name == 'binance':
            api_key = settings.BINANCE_API_KEY
            secret = settings.BINANCE_SECRET
        elif exchange_name == 'bybit':
            api_key = settings.BYBIT_API_KEY
            secret = settings.BYBIT_SECRET
        else:
            raise ValueError(f"No credentials configured for {exchange_name}")
        
        if not api_key or not secret:
            raise ValueError(f"API credentials not configured for {exchange_name}")
        
        adapter = adapter_class(api_key=api_key, secret=secret, sandbox=sandbox)
        logger.info(f"Created {exchange_name} adapter (sandbox: {sandbox})")
        
        return adapter
    
    @classmethod
    def get_supported_exchanges(cls) -> list:
        """サポートされている取引所一覧を返す"""
        return list(cls._adapters.keys())
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[AbstractExchangeAdapter]):
        """新しいアダプタを登録"""
        cls._adapters[name.lower()] = adapter_class
        logger.info(f"Registered new exchange adapter: {name}")


# デフォルトアダプタの作成を簡単にするヘルパー関数
def create_default_adapter(sandbox: bool = False) -> AbstractExchangeAdapter:
    """デフォルトの取引所アダプタを作成"""
    # 設定から最初に利用可能な取引所を選択
    if settings.BINANCE_API_KEY and settings.BINANCE_SECRET:
        return ExchangeFactory.create_adapter('binance', sandbox)
    elif settings.BYBIT_API_KEY and settings.BYBIT_SECRET:
        return ExchangeFactory.create_adapter('bybit', sandbox)
    else:
        raise ValueError("No exchange credentials configured")


def create_adapter_from_config(config: dict) -> AbstractExchangeAdapter:
    """設定から取引所アダプタを作成"""
    exchange_name = config.get('exchange', 'binance')
    sandbox = config.get('sandbox', False)
    
    return ExchangeFactory.create_adapter(exchange_name, sandbox)