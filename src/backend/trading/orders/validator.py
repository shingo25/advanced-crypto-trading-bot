"""
注文バリデーション機能
市場ルール、残高、シンボル検証などを実行
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple

from src.backend.trading.orders.models import Order, OrderType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


class OrderValidator:
    """
    注文バリデーションクラス
    Chain of Responsibilityパターンでバリデーションを実行
    """
    
    def __init__(self, exchange_adapter=None, account_service=None):
        """
        Args:
            exchange_adapter: 取引所アダプタ
            account_service: アカウントサービス（残高取得用）
        """
        self.exchange_adapter = exchange_adapter
        self.account_service = account_service
        self.exchange_rules: Dict = {}
        
        # デフォルトのバリデーションルール
        self.default_rules = {
            "min_order_value": Decimal("10.0"),    # $10 最小注文金額
            "max_order_value": Decimal("100000.0"), # $100,000 最大注文金額
            "max_price_deviation": 0.1,             # 10% 価格乖離制限
            "min_quantity_precision": 8,            # 最小数量精度
            "min_price_precision": 8,               # 最小価格精度
        }
    
    async def validate(self, order: Order, request_context: Dict = None) -> Tuple[bool, Optional[str]]:
        """
        注文の包括的バリデーション
        
        Args:
            order: 検証する注文
            request_context: リクエストコンテキスト（IPアドレス、ユーザーIDなど）
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # バリデーション実行順序（早期失敗）
            await self._validate_basic_params(order)
            await self._validate_symbol(order)
            await self._validate_order_size(order)
            await self._validate_price(order)
            await self._validate_precision(order)
            await self._validate_market_hours(order)
            
            # 残高チェック（最後に実行）
            if self.account_service:
                await self._validate_balance(order)
            
            logger.info(f"Order validation passed for {order.id}")
            return True, None
            
        except ValidationError as e:
            logger.warning(f"Order validation failed for {order.id}: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected validation error for {order.id}: {e}")
            return False, f"Validation error: {e}"
    
    async def _validate_basic_params(self, order: Order):
        """基本パラメータのバリデーション"""
        if not order.exchange:
            raise ValidationError("Exchange is required")
        
        if not order.symbol:
            raise ValidationError("Symbol is required")
        
        if order.amount <= 0:
            raise ValidationError("Amount must be positive")
        
        # 注文タイプ別のバリデーション
        if order.order_type == OrderType.LIMIT and order.price is None:
            raise ValidationError("Limit orders require a price")
        
        if order.order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if order.stop_price is None:
                raise ValidationError(f"{order.order_type.value} orders require a stop_price")
        
        if order.order_type == OrderType.OCO:
            if not order.oco_take_profit_price or not order.oco_stop_loss_price:
                raise ValidationError("OCO orders require both take_profit_price and stop_loss_price")
    
    async def _validate_symbol(self, order: Order):
        """シンボルの有効性検証"""
        if not self.exchange_adapter:
            logger.warning("Exchange adapter not available for symbol validation")
            return
        
        try:
            # 取引所の利用可能シンボルリストを取得
            available_symbols = await self.exchange_adapter.get_symbols()
            normalized_symbol = self.exchange_adapter.normalize_symbol(order.symbol)
            
            if normalized_symbol not in available_symbols:
                raise ValidationError(f"Symbol {order.symbol} is not available on {order.exchange}")
                
        except Exception as e:
            # ValidationErrorの場合は再度raiseしてバリデーション失敗として扱う
            if "not available" in str(e):
                raise ValidationError(f"Symbol validation failed: {e}")
            else:
                logger.warning(f"Could not validate symbol {order.symbol}: {e}")
                # その他のエラーは警告のみ（取引所接続エラーの可能性）
    
    async def _validate_order_size(self, order: Order):
        """注文サイズのバリデーション"""
        rules = self.exchange_rules.get(order.symbol, self.default_rules)
        
        # 最小注文金額チェック
        estimated_value = order.amount
        if order.price:
            estimated_value = order.amount * order.price
        
        min_value = rules.get("min_order_value", self.default_rules["min_order_value"])
        max_value = rules.get("max_order_value", self.default_rules["max_order_value"])
        
        if estimated_value < min_value:
            raise ValidationError(f"Order value ${estimated_value} is below minimum ${min_value}")
        
        if estimated_value > max_value:
            raise ValidationError(f"Order value ${estimated_value} exceeds maximum ${max_value}")
    
    async def _validate_price(self, order: Order):
        """価格の妥当性検証"""
        if order.price is None and order.order_type != OrderType.MARKET:
            return
        
        if not self.exchange_adapter:
            logger.warning("Exchange adapter not available for price validation")
            return
        
        try:
            # 現在価格を取得
            ticker = await self.exchange_adapter.fetch_ticker(order.symbol)
            current_price = Decimal(str(ticker.last))
            
            if order.price:
                price_deviation = abs(order.price - current_price) / current_price
                max_deviation = self.default_rules["max_price_deviation"]
                
                if price_deviation > max_deviation:
                    raise ValidationError(
                        f"Price ${order.price} deviates {price_deviation:.2%} from market price ${current_price} "
                        f"(max allowed: {max_deviation:.2%})"
                    )
                    
        except Exception as e:
            logger.warning(f"Could not validate price for {order.symbol}: {e}")
            # 価格検証失敗は警告のみ
    
    async def _validate_precision(self, order: Order):
        """数量・価格の精度検証"""
        # 数量精度チェック
        amount_str = str(order.amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1])
            max_precision = self.default_rules["min_quantity_precision"]
            
            if decimal_places > max_precision:
                raise ValidationError(f"Amount precision {decimal_places} exceeds maximum {max_precision}")
        
        # 価格精度チェック
        if order.price:
            price_str = str(order.price)
            if '.' in price_str:
                decimal_places = len(price_str.split('.')[1])
                max_precision = self.default_rules["min_price_precision"]
                
                if decimal_places > max_precision:
                    raise ValidationError(f"Price precision {decimal_places} exceeds maximum {max_precision}")
    
    async def _validate_market_hours(self, order: Order):
        """市場時間の検証"""
        # 24/7の暗号通貨市場では常に取引可能
        # 将来的に取引所のメンテナンス時間などを考慮可能
        current_time = datetime.now(timezone.utc)
        
        # 例：メンテナンス時間チェック（仮想的）
        # maintenance_start = current_time.replace(hour=2, minute=0, second=0)
        # maintenance_end = current_time.replace(hour=4, minute=0, second=0)
        # 
        # if maintenance_start <= current_time <= maintenance_end:
        #     raise ValidationError("Trading is not available during maintenance hours")
        
        logger.debug(f"Market hours validation passed at {current_time}")
    
    async def _validate_balance(self, order: Order):
        """残高の検証"""
        if not self.account_service:
            logger.warning("Account service not available for balance validation")
            return
        
        try:
            # 売り注文の場合：ベース通貨の残高をチェック
            # 買い注文の場合：クォート通貨の残高をチェック
            symbol_parts = order.symbol.split('/')
            if len(symbol_parts) != 2:
                raise ValidationError(f"Invalid symbol format: {order.symbol}")
            
            base_currency, quote_currency = symbol_parts
            
            if order.side.value.lower() == "sell":
                # 売り注文：ベース通貨の残高が必要
                required_balance = order.amount
                currency = base_currency
            else:
                # 買い注文：クォート通貨の残高が必要
                if order.price:
                    required_balance = order.amount * order.price
                else:
                    # 成行注文の場合は概算価格を使用
                    ticker = await self.exchange_adapter.fetch_ticker(order.symbol)
                    estimated_price = Decimal(str(ticker.ask))
                    required_balance = order.amount * estimated_price
                currency = quote_currency
            
            # 残高を取得
            balance = await self.account_service.get_balance()
            available_balance = Decimal(str(balance.get(currency, 0)))
            
            if available_balance < required_balance:
                raise ValidationError(
                    f"Insufficient balance: required {required_balance} {currency}, "
                    f"available {available_balance} {currency}"
                )
                
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Could not validate balance for {order.symbol}: {e}")
            # 残高検証失敗は警告のみ（API接続エラーの可能性）
    
    def load_exchange_rules(self, exchange: str, symbol: str = None) -> Dict:
        """
        取引所固有のルールを読み込み
        
        Args:
            exchange: 取引所名
            symbol: シンボル（オプション）
        
        Returns:
            Dict: ルール設定
        """
        # 将来的には設定ファイルやデータベースから読み込み
        rules = {
            "binance": {
                "min_order_value": Decimal("10.0"),
                "max_order_value": Decimal("50000.0"),
                "max_price_deviation": 0.05,  # 5%
            },
            "hyperliquid": {
                "min_order_value": Decimal("1.0"),
                "max_order_value": Decimal("100000.0"),
                "max_price_deviation": 0.1,   # 10%
            }
        }
        
        exchange_rules = rules.get(exchange.lower(), self.default_rules)
        if symbol:
            self.exchange_rules[symbol] = exchange_rules
        
        return exchange_rules
    
    def update_rules(self, exchange: str, symbol: str, rules: Dict):
        """ルールの動的更新"""
        cache_key = f"{exchange}_{symbol}"
        self.exchange_rules[cache_key] = {**self.default_rules, **rules}
        logger.info(f"Updated rules for {cache_key}")