import logging
from typing import Dict, Type, Optional
from uuid import UUID

from src.backend.core.config import settings

from .base import AbstractExchangeAdapter
from .binance import BinanceAdapter
from .bybit import BybitAdapter
from .bitget import BitgetAdapter
from .hyperliquid import HyperliquidAdapter
from .backpack import BackpackAdapter
from .paper_trading_adapter import PaperTradingAdapter

logger = logging.getLogger(__name__)


class ExchangeFactory:
    """取引所アダプタのファクトリークラス（Paper Trading対応）"""

    _adapters: Dict[str, Type[AbstractExchangeAdapter]] = {
        "binance": BinanceAdapter,
        "bybit": BybitAdapter,
        "bitget": BitgetAdapter,
        "hyperliquid": HyperliquidAdapter,
        "backpack": BackpackAdapter,
    }
    
    # Paper Trading特別扱い（セキュリティのため）
    _paper_trading_adapter = PaperTradingAdapter

    @classmethod
    def create_adapter(
        cls, 
        exchange_name: str, 
        sandbox: bool = False,
        trading_mode: str = "live",
        user_id: Optional[str] = None,
        paper_config: Optional[Dict] = None
    ) -> AbstractExchangeAdapter:
        """
        指定された取引所のアダプタを作成
        
        Args:
            exchange_name: 取引所名
            sandbox: サンドボックスモード
            trading_mode: 取引モード ("live" or "paper")
            user_id: Paper Trading用ユーザーID
            paper_config: Paper Trading設定
        """
        exchange_name = exchange_name.lower()
        trading_mode = trading_mode.lower()
        
        # セキュリティ: Paper Tradingモードの厳格な検証
        if trading_mode == "paper":
            if not user_id:
                raise ValueError("Paper trading requires user_id")
            return cls._create_paper_trading_adapter(exchange_name, user_id, paper_config or {})
        
        # Live Trading モード（既存ロジック）
        if trading_mode != "live":
            raise ValueError(f"Invalid trading mode: {trading_mode}. Must be 'live' or 'paper'")
            
        return cls._create_live_adapter(exchange_name, sandbox)

    @classmethod
    def _create_live_adapter(cls, exchange_name: str, sandbox: bool) -> AbstractExchangeAdapter:
        """Live Trading用アダプタを作成（既存ロジック）"""
        if exchange_name not in cls._adapters:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        adapter_class = cls._adapters[exchange_name]

        # 設定から API キーを取得
        if exchange_name == "binance":
            api_key = settings.BINANCE_API_KEY
            secret = settings.BINANCE_SECRET
        elif exchange_name == "bybit":
            api_key = settings.BYBIT_API_KEY
            secret = settings.BYBIT_SECRET
        elif exchange_name == "bitget":
            api_key = settings.BITGET_API_KEY
            secret = settings.BITGET_SECRET
        elif exchange_name == "hyperliquid":
            api_key = settings.HYPERLIQUID_ADDRESS  # HyperliquidではaddressをAPIキーとして使用
            secret = settings.HYPERLIQUID_PRIVATE_KEY
        elif exchange_name == "backpack":
            api_key = settings.BACKPACK_API_KEY
            secret = settings.BACKPACK_SECRET
        else:
            raise ValueError(f"No credentials configured for {exchange_name}")

        if not api_key or not secret:
            raise ValueError(f"API credentials not configured for {exchange_name}")

        adapter = adapter_class(api_key=api_key, secret=secret, sandbox=sandbox)
        logger.info(f"Created {exchange_name} live adapter (sandbox: {sandbox})")

        return adapter
    
    @classmethod
    def _create_paper_trading_adapter(
        cls, 
        real_exchange: str, 
        user_id: str, 
        paper_config: Dict
    ) -> PaperTradingAdapter:
        """
        Paper Trading用アダプタを作成（セキュリティ重視）
        
        Args:
            real_exchange: 実際の取引所名（価格データ取得用）
            user_id: ユーザーID
            paper_config: Paper Trading設定
        """
        # セキュリティ: 実際のAPIキーは使用しない
        if real_exchange not in cls._adapters:
            logger.warning(f"Unsupported real exchange for paper trading: {real_exchange}, using binance as default")
            real_exchange = "binance"
        
        # Paper Trading専用設定
        safe_config = {
            "real_exchange": real_exchange,
            "user_id": user_id,
            "database_url": paper_config.get("database_url", "postgresql://localhost/trading_bot_paper"),
            "default_setting": paper_config.get("default_setting", "beginner"),
            "fee_rates": paper_config.get("fee_rates", {"maker": 0.001, "taker": 0.001}),
            "execution_delay": paper_config.get("execution_delay", 0.1),
            "slippage_rate": paper_config.get("slippage_rate", 0.0001),
            # セキュリティ: 実際のAPIキーは絶対に使用しない
            "mock_api_keys": True,
        }
        
        adapter = cls._paper_trading_adapter(safe_config)
        logger.info(f"Created paper trading adapter for user {user_id} (real_exchange: {real_exchange})")
        
        return adapter

    @classmethod
    def get_supported_exchanges(cls, include_paper_trading: bool = False) -> list:
        """
        サポートされている取引所一覧を返す
        
        Args:
            include_paper_trading: Paper Tradingを含むかどうか
        """
        exchanges = list(cls._adapters.keys())
        if include_paper_trading:
            exchanges.append("paper_trading")
        return exchanges

    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[AbstractExchangeAdapter]):
        """新しいアダプタを登録"""
        cls._adapters[name.lower()] = adapter_class
        logger.info(f"Registered new exchange adapter: {name}")


# デフォルトアダプタの作成を簡単にするヘルパー関数
def create_default_adapter(sandbox: bool = False, trading_mode: str = "live") -> AbstractExchangeAdapter:
    """デフォルトの取引所アダプタを作成"""
    # Paper Tradingの場合はuser_idが必要
    if trading_mode == "paper":
        raise ValueError("Paper trading requires explicit user_id and config")
    
    # 設定から最初に利用可能な取引所を選択
    if settings.BINANCE_API_KEY and settings.BINANCE_SECRET:
        return ExchangeFactory.create_adapter("binance", sandbox, trading_mode)
    elif settings.BYBIT_API_KEY and settings.BYBIT_SECRET:
        return ExchangeFactory.create_adapter("bybit", sandbox, trading_mode)
    else:
        raise ValueError("No exchange credentials configured")


def create_adapter_from_config(config: dict) -> AbstractExchangeAdapter:
    """設定から取引所アダプタを作成（セキュリティ強化版）"""
    exchange_name = config.get("exchange", "binance")
    sandbox = config.get("sandbox", False)
    trading_mode = config.get("trading_mode", "live")
    
    # Paper Tradingの場合の追加パラメータ
    user_id = config.get("user_id")
    paper_config = config.get("paper_config", {})

    return ExchangeFactory.create_adapter(
        exchange_name=exchange_name,
        sandbox=sandbox,
        trading_mode=trading_mode,
        user_id=user_id,
        paper_config=paper_config
    )


def create_paper_trading_adapter(
    user_id: str,
    real_exchange: str = "binance",
    paper_config: Optional[Dict] = None
) -> PaperTradingAdapter:
    """
    Paper Trading用アダプタを作成するヘルパー関数
    
    Args:
        user_id: ユーザーID
        real_exchange: 実際の取引所名（価格データ用）
        paper_config: Paper Trading設定
    """
    return ExchangeFactory.create_adapter(
        exchange_name=real_exchange,
        trading_mode="paper",
        user_id=user_id,
        paper_config=paper_config or {}
    )
