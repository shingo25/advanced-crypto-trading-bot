"""
注文とコマンドのファクトリークラス
注文タイプに応じて適切なオブジェクトを生成
"""

import logging
from typing import Dict

from src.backend.core.abstract_adapter import AbstractAdapterFactory
from src.backend.trading.orders.commands import (
    CancelOrderCommand,
    CreateOrderCommand,
    ModifyOrderCommand,
    OrderCommand,
)
from src.backend.trading.orders.models import Order, OrderParams, OrderType
from src.backend.trading.orders.security import SecurityManager
from src.backend.trading.orders.validator import OrderValidator

logger = logging.getLogger(__name__)


class OrderFactory:
    """注文オブジェクトの生成を担当するファクトリー"""

    @staticmethod
    def create_order(params: OrderParams) -> Order:
        """
        OrderParamsから注文オブジェクトを作成

        Args:
            params: 注文パラメータ

        Returns:
            Order: 作成された注文オブジェクト
        """
        try:
            order = Order.from_params(params)

            # 注文タイプ別の追加バリデーション
            OrderFactory._validate_order_type_specific(order)

            logger.info(
                f"Created order: {order.order_type.value} {order.side.value} "
                f"{order.amount} {order.symbol} on {order.exchange}"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise

    @staticmethod
    def _validate_order_type_specific(order: Order):
        """注文タイプ別の特定バリデーション"""
        if order.order_type == OrderType.LIMIT:
            if order.price is None:
                raise ValueError("Limit orders require a price")

        elif order.order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if order.stop_price is None:
                raise ValueError(f"{order.order_type.value} orders require a stop_price")

        elif order.order_type == OrderType.OCO:
            if order.oco_take_profit_price is None or order.oco_stop_loss_price is None:
                raise ValueError("OCO orders require both take_profit_price and stop_loss_price")

            if order.oco_take_profit_price <= order.oco_stop_loss_price:
                raise ValueError("Take profit price must be higher than stop loss price for OCO orders")


class OrderCommandFactory:
    """注文コマンドの生成を担当するファクトリー"""

    def __init__(self, adapter_factory: AbstractAdapterFactory = None, security_config: Dict = None):
        self._adapter_factory = adapter_factory
        self._exchange_adapters: Dict[str, object] = {}
        self._validators: Dict[str, OrderValidator] = {}
        self._security_manager: SecurityManager = None

        # SecurityManagerの初期化
        if security_config:
            self._security_manager = SecurityManager(security_config)

    def _get_exchange_adapter(self, exchange: str, sandbox: bool = False):
        """取引所アダプタを取得（キャッシュ機能付き）"""
        cache_key = f"{exchange}_{sandbox}"

        if cache_key not in self._exchange_adapters:
            try:
                adapter = self._adapter_factory.create_adapter(exchange, sandbox=sandbox)
                self._exchange_adapters[cache_key] = adapter
                logger.info(f"Created exchange adapter for {exchange} (sandbox={sandbox})")
            except Exception as e:
                logger.error(f"Failed to create exchange adapter for {exchange}: {e}")
                raise

        return self._exchange_adapters[cache_key]

    def _get_validator(self, exchange: str, sandbox: bool = False) -> OrderValidator:
        """OrderValidatorを取得（キャッシュ機能付き）"""
        cache_key = f"{exchange}_{sandbox}"

        if cache_key not in self._validators:
            try:
                # 取引所アダプタを取得
                adapter = self._get_exchange_adapter(exchange, sandbox)

                # TODO: account_serviceを実装後に統合
                validator = OrderValidator(
                    exchange_adapter=adapter,
                    account_service=None,  # 後で実装
                )

                # 取引所固有のルールを読み込み
                validator.load_exchange_rules(exchange)

                self._validators[cache_key] = validator
                logger.info(f"Created validator for {exchange} (sandbox={sandbox})")

            except Exception as e:
                logger.error(f"Failed to create validator for {exchange}: {e}")
                raise

        return self._validators[cache_key]

    def create_order_command(
        self, order: Order, command_type: str = "create", sandbox: bool = False, **kwargs
    ) -> OrderCommand:
        """
        注文コマンドを作成

        Args:
            order: 注文オブジェクト
            command_type: コマンドタイプ（create, cancel, modify）
            sandbox: サンドボックスモードかどうか
            **kwargs: コマンド別の追加パラメータ

        Returns:
            OrderCommand: 作成されたコマンドオブジェクト
        """
        try:
            # 取引所アダプタを取得
            exchange_adapter = self._get_exchange_adapter(order.exchange, sandbox)

            # Validatorを取得
            validator = self._get_validator(order.exchange, sandbox)

            # コマンドタイプに応じてコマンドを作成
            if command_type == "create":
                return CreateOrderCommand(order, exchange_adapter, validator, self._security_manager)

            elif command_type == "cancel":
                return CancelOrderCommand(order, exchange_adapter, validator, self._security_manager)

            elif command_type == "modify":
                new_price = kwargs.get("new_price")
                new_amount = kwargs.get("new_amount")
                return ModifyOrderCommand(
                    order, new_price, new_amount, exchange_adapter, validator, self._security_manager
                )

            else:
                raise ValueError(f"Unknown command type: {command_type}")

        except Exception as e:
            logger.error(f"Failed to create order command: {e}")
            raise

    def create_batch_commands(
        self, orders: list[Order], command_type: str = "create", sandbox: bool = False
    ) -> list[OrderCommand]:
        """
        複数の注文に対するコマンドを一括作成

        Args:
            orders: 注文リスト
            command_type: コマンドタイプ
            sandbox: サンドボックスモードかどうか

        Returns:
            list[OrderCommand]: 作成されたコマンドリスト
        """
        commands = []

        for order in orders:
            try:
                command = self.create_order_command(order, command_type, sandbox)
                commands.append(command)
            except Exception as e:
                logger.error(f"Failed to create command for order {order.id}: {e}")
                # エラーが発生した注文はスキップして続行
                continue

        logger.info(f"Created {len(commands)} commands out of {len(orders)} orders")
        return commands


class OrderValidationFactory:
    """注文バリデーション用のファクトリー"""

    @staticmethod
    def create_market_order_params(
        exchange: str, symbol: str, side: str, amount: float, strategy_name: str = None
    ) -> OrderParams:
        """成行注文パラメータを作成"""
        return OrderParams(
            exchange=exchange,
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=side,
            amount=amount,
            strategy_name=strategy_name,
        )

    @staticmethod
    def create_limit_order_params(
        exchange: str, symbol: str, side: str, amount: float, price: float, strategy_name: str = None
    ) -> OrderParams:
        """指値注文パラメータを作成"""
        return OrderParams(
            exchange=exchange,
            symbol=symbol,
            order_type=OrderType.LIMIT,
            side=side,
            amount=amount,
            price=price,
            strategy_name=strategy_name,
        )

    @staticmethod
    def create_stop_loss_params(
        exchange: str, symbol: str, side: str, amount: float, stop_price: float, strategy_name: str = None
    ) -> OrderParams:
        """ストップロス注文パラメータを作成"""
        return OrderParams(
            exchange=exchange,
            symbol=symbol,
            order_type=OrderType.STOP_LOSS,
            side=side,
            amount=amount,
            stop_price=stop_price,
            strategy_name=strategy_name,
        )

    @staticmethod
    def create_oco_order_params(
        exchange: str,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float,
        stop_loss_price: float,
        strategy_name: str = None,
    ) -> OrderParams:
        """OCO注文パラメータを作成"""
        return OrderParams(
            exchange=exchange,
            symbol=symbol,
            order_type=OrderType.OCO,
            side=side,
            amount=amount,
            oco_take_profit_price=take_profit_price,
            oco_stop_loss_price=stop_loss_price,
            strategy_name=strategy_name,
        )
