"""
注文管理クラス
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone, timedelta
from .engine import Order, OrderStatus, OrderType, OrderSide

logger = logging.getLogger(__name__)


class OrderManager:
    """注文管理クラス"""

    def __init__(self, config: Dict = None):
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        self.config = config or {}
        self.exchange_adapters = {}

        # イベントハンドラー
        self.on_order_filled: Optional[Callable] = None
        self.on_order_cancelled: Optional[Callable] = None
        self.on_order_rejected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # 統計
        self.stats = {
            "total_orders": 0,
            "filled_orders": 0,
            "cancelled_orders": 0,
            "rejected_orders": 0,
            "total_volume": 0.0,
        }

        logger.info("OrderManager initialized")

    def add_exchange_adapter(self, name: str, adapter):
        """取引所アダプタを追加"""
        self.exchange_adapters[name] = adapter
        logger.info(f"Exchange adapter added to OrderManager: {name}")

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: float,
        price: Optional[float] = None,
        strategy_name: Optional[str] = None,
    ) -> Order:
        """注文を作成"""

        # 注文IDを生成
        order_id = f"order_{self.order_counter:06d}"
        self.order_counter += 1

        # 注文を作成
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            amount=amount,
            price=price,
            strategy_name=strategy_name,
        )

        # バリデーション
        if not self._validate_order(order):
            order.update_status(OrderStatus.REJECTED)
            self._handle_order_rejected(order)
            return order

        # 注文を保存
        self.orders[order_id] = order

        # 注文を実行
        if self.config.get("enable_dry_run", True):
            self._simulate_order_fill(order)
        else:
            self._execute_order(order)

        self.stats["total_orders"] += 1
        logger.info(f"Order created: {order_id} {side.value} {amount} {symbol}")

        return order

    def cancel_order(self, order_id: str) -> bool:
        """注文をキャンセル"""
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return False

        order = self.orders[order_id]

        if not order.is_active():
            logger.warning(f"Order is not active: {order_id}")
            return False

        if not self.config.get("enable_dry_run", True):
            success = self._cancel_order_on_exchange(order)
            if not success:
                return False

        order.update_status(OrderStatus.CANCELLED)
        self.stats["cancelled_orders"] += 1

        if self.on_order_cancelled:
            self.on_order_cancelled(order)

        logger.info(f"Order cancelled: {order_id}")
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """注文を取得"""
        return self.orders.get(order_id)

    def get_active_orders(self) -> List[Order]:
        """アクティブな注文を取得"""
        return [order for order in self.orders.values() if order.is_active()]

    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """シンボル別の注文を取得"""
        return [order for order in self.orders.values() if order.symbol == symbol]

    def get_orders_by_strategy(self, strategy_name: str) -> List[Order]:
        """戦略別の注文を取得"""
        return [
            order
            for order in self.orders.values()
            if order.strategy_name == strategy_name
        ]

    def cancel_orders_by_symbol(self, symbol: str) -> int:
        """シンボル別の注文をキャンセル"""
        orders = self.get_orders_by_symbol(symbol)
        cancelled_count = 0

        for order in orders:
            if order.is_active() and self.cancel_order(order.id):
                cancelled_count += 1

        return cancelled_count

    def cancel_orders_by_strategy(self, strategy_name: str) -> int:
        """戦略別の注文をキャンセル"""
        orders = self.get_orders_by_strategy(strategy_name)
        cancelled_count = 0

        for order in orders:
            if order.is_active() and self.cancel_order(order.id):
                cancelled_count += 1

        return cancelled_count

    def cancel_all_orders(self) -> int:
        """すべての注文をキャンセル"""
        active_orders = self.get_active_orders()
        cancelled_count = 0

        for order in active_orders:
            if self.cancel_order(order.id):
                cancelled_count += 1

        return cancelled_count

    def cleanup_old_orders(self, days: int = 30) -> int:
        """古い注文をクリーンアップ"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cleaned_count = 0

        orders_to_remove = []
        for order_id, order in self.orders.items():
            if order.created_at < cutoff_date and not order.is_active():
                orders_to_remove.append(order_id)

        for order_id in orders_to_remove:
            del self.orders[order_id]
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} old orders")
        return cleaned_count

    def _validate_order(self, order: Order) -> bool:
        """注文を検証"""

        # 数量チェック
        if order.amount <= 0:
            logger.error(f"Invalid order amount: {order.amount}")
            return False

        # 価格チェック
        if order.order_type == OrderType.LIMIT and (
            order.price is None or order.price <= 0
        ):
            logger.error(f"Invalid limit order price: {order.price}")
            return False

        # リスク制限チェック
        max_position_size = self.config.get("risk_limits", {}).get(
            "max_position_size", 10000.0
        )
        if order.amount > max_position_size:
            logger.error(f"Order amount exceeds max position size: {order.amount}")
            return False

        # 同時注文数チェック
        max_concurrent_orders = self.config.get("max_concurrent_orders", 10)
        active_orders = len(self.get_active_orders())
        if active_orders >= max_concurrent_orders:
            logger.error(f"Too many active orders: {active_orders}")
            return False

        return True

    def _execute_order(self, order: Order):
        """注文を実行"""
        try:
            # 取引所アダプタを使用して注文を実行
            exchange_name = "binance"  # デフォルト

            if exchange_name not in self.exchange_adapters:
                logger.error(f"Exchange adapter not found: {exchange_name}")
                order.update_status(OrderStatus.REJECTED)
                self._handle_order_rejected(order)
                return

            adapter = self.exchange_adapters[exchange_name]

            # 注文を送信
            result = adapter.place_order(
                symbol=order.symbol,
                side=order.side.value,
                type=order.order_type.value,
                amount=order.amount,
                price=order.price,
            )

            if result.get("success"):
                order.update_status(
                    OrderStatus.FILLED, order.amount, result.get("price")
                )
                self._handle_order_filled(order)
            else:
                order.update_status(OrderStatus.REJECTED)
                self._handle_order_rejected(order)
                logger.error(f"Order execution failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Order execution error: {e}")
            order.update_status(OrderStatus.REJECTED)
            self._handle_order_rejected(order)

            if self.on_error:
                self.on_error(f"Order execution error: {e}")

    def _simulate_order_fill(self, order: Order):
        """注文約定をシミュレート"""
        # デモモードでは即座に約定
        fill_price = order.price or 50000.0  # デフォルト価格
        order.update_status(OrderStatus.FILLED, order.amount, fill_price)
        self._handle_order_filled(order)

    def _handle_order_filled(self, order: Order):
        """注文約定の処理"""
        self.stats["filled_orders"] += 1
        self.stats["total_volume"] += order.amount

        if self.on_order_filled:
            self.on_order_filled(order)

        logger.info(f"Order filled: {order.id} at {order.filled_price}")

    def _handle_order_rejected(self, order: Order):
        """注文拒否の処理"""
        self.stats["rejected_orders"] += 1

        if self.on_order_rejected:
            self.on_order_rejected(order)

        logger.warning(f"Order rejected: {order.id}")

    def _cancel_order_on_exchange(self, order: Order) -> bool:
        """取引所で注文をキャンセル"""
        try:
            exchange_name = "binance"  # デフォルト

            if exchange_name not in self.exchange_adapters:
                logger.error(f"Exchange adapter not found: {exchange_name}")
                return False

            adapter = self.exchange_adapters[exchange_name]
            result = adapter.cancel_order(order.id, order.symbol)

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_orders": self.stats["total_orders"],
            "filled_orders": self.stats["filled_orders"],
            "cancelled_orders": self.stats["cancelled_orders"],
            "rejected_orders": self.stats["rejected_orders"],
            "fill_rate": self.stats["filled_orders"]
            / max(self.stats["total_orders"], 1),
            "total_volume": self.stats["total_volume"],
            "active_orders": len(self.get_active_orders()),
        }
