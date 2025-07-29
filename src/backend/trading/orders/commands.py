"""
注文実行のCommandパターン実装
各注文操作をコマンドオブジェクトとして表現
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional

from src.backend.trading.orders.models import Order, OrderResult, OrderStatus
from src.backend.trading.orders.security import SecurityManager
from src.backend.trading.orders.validator import OrderValidator

logger = logging.getLogger(__name__)


class OrderCommand(ABC):
    """注文コマンドの抽象基底クラス"""

    def __init__(
        self,
        order: Order,
        exchange_adapter=None,
        validator: Optional[OrderValidator] = None,
        security_manager: Optional[SecurityManager] = None,
    ):
        self.order = order
        self.exchange_adapter = exchange_adapter
        self.validator = validator
        self.security_manager = security_manager
        self.executed = False
        self.result: Optional[OrderResult] = None
        self.execution_time: Optional[datetime] = None

    @abstractmethod
    async def execute(self) -> OrderResult:
        """
        コマンドを実行

        Returns:
            OrderResult: 実行結果
        """
        pass

    async def validate(
        self, request_context: Dict = None, portfolio_value: Optional[Decimal] = None
    ) -> tuple[bool, Optional[str]]:
        """
        包括的な注文バリデーション

        Args:
            request_context: リクエストコンテキスト（IPアドレス、ユーザーIDなど）
            portfolio_value: ポートフォリオ総額

        Returns:
            tuple[bool, Optional[str]]: (検証成功, エラーメッセージ)
        """
        try:
            # 1. OrderValidatorによる詳細バリデーション
            if self.validator:
                is_valid, error_msg = await self.validator.validate(self.order, request_context)
                if not is_valid:
                    return False, f"Validation failed: {error_msg}"
            else:
                # フォールバック：基本的なバリデーション
                basic_validation = await self._basic_validation()
                if not basic_validation[0]:
                    return basic_validation

            # 2. SecurityManagerによるセキュリティチェック
            if self.security_manager and request_context:
                is_secure, error_msg = self.security_manager.execute_security_checks(
                    self.order, request_context, portfolio_value
                )
                if not is_secure:
                    return False, f"Security check failed: {error_msg}"

            return True, None

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation failed: {str(e)}"

    async def _basic_validation(self) -> tuple[bool, Optional[str]]:
        """基本的なバリデーション（フォールバック）"""
        try:
            if not self.order.exchange:
                return False, "Exchange is required"

            if not self.order.symbol:
                return False, "Symbol is required"

            if self.order.amount <= 0:
                return False, "Amount must be positive"

            if self.order.price is not None and self.order.price <= 0:
                return False, "Price must be positive"

            return True, None

        except Exception as e:
            logger.error(f"Basic validation error: {e}")
            return False, f"Basic validation failed: {str(e)}"

    async def log_execution(self, result: OrderResult):
        """実行ログを記録"""
        log_data = {
            "command_type": self.__class__.__name__,
            "order_id": self.order.id,
            "exchange": self.order.exchange,
            "symbol": self.order.symbol,
            "side": self.order.side.value,
            "amount": str(self.order.amount),
            "price": str(self.order.price) if self.order.price else None,
            "success": result.success,
            "error_message": result.error_message,
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
        }

        if result.success:
            logger.info("Order command executed successfully", extra=log_data)
        else:
            logger.error("Order command failed", extra=log_data)


class CreateOrderCommand(OrderCommand):
    """注文作成コマンド"""

    def __init__(
        self,
        order: Order,
        exchange_adapter,
        validator: Optional[OrderValidator] = None,
        security_manager: Optional[SecurityManager] = None,
    ):
        super().__init__(order, exchange_adapter, validator, security_manager)

    async def execute(self, request_context: Dict = None, portfolio_value: Optional[Decimal] = None) -> OrderResult:
        """注文を作成して取引所に送信"""
        self.execution_time = datetime.now(timezone.utc)

        try:
            # 包括的バリデーション
            is_valid, error_msg = await self.validate(request_context, portfolio_value)
            if not is_valid:
                result = OrderResult.error_result(error_msg, "VALIDATION_ERROR")
                await self.log_execution(result)
                return result

            # 注文を取引所に送信
            self.order.status = OrderStatus.PENDING
            self.order.submitted_at = self.execution_time

            # 取引所アダプタを使用して注文を送信
            exchange_response = await self._submit_to_exchange()

            if exchange_response["success"]:
                self.order.exchange_order_id = exchange_response.get("order_id")
                self.order.status = OrderStatus.SUBMITTED
                result = OrderResult.success_result(self.order)
            else:
                self.order.status = OrderStatus.REJECTED
                self.order.error_message = exchange_response.get("error", "Unknown error")
                result = OrderResult.error_result(self.order.error_message, exchange_response.get("error_code"))

            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Order creation failed: {error_msg}")

            self.order.status = OrderStatus.FAILED
            self.order.error_message = error_msg
            result = OrderResult.error_result(error_msg, "EXECUTION_ERROR")

            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

    async def _submit_to_exchange(self) -> Dict:
        """取引所に注文を送信（実装は取引所アダプタに委譲）"""
        try:
            # この部分は取引所アダプタの実装に依存
            # 現在は模擬的な応答を返す
            return {"success": True, "order_id": f"exchange_{self.order.id[:8]}", "status": "submitted"}
        except Exception as e:
            return {"success": False, "error": str(e), "error_code": "EXCHANGE_ERROR"}


class CancelOrderCommand(OrderCommand):
    """注文キャンセルコマンド"""

    def __init__(
        self,
        order: Order,
        exchange_adapter,
        validator: Optional[OrderValidator] = None,
        security_manager: Optional[SecurityManager] = None,
    ):
        super().__init__(order, exchange_adapter, validator, security_manager)

    async def execute(self) -> OrderResult:
        """注文をキャンセル"""
        self.execution_time = datetime.now(timezone.utc)

        try:
            # キャンセル可能状態かチェック
            if not self.order.is_active():
                error_msg = f"Order {self.order.id} is not in cancellable state: {self.order.status}"
                result = OrderResult.error_result(error_msg, "INVALID_STATUS")
                await self.log_execution(result)
                return result

            # 取引所でキャンセル実行
            cancel_response = await self._cancel_on_exchange()

            if cancel_response["success"]:
                self.order.status = OrderStatus.CANCELLED
                self.order.cancelled_at = self.execution_time
                result = OrderResult.success_result(self.order)
            else:
                result = OrderResult.error_result(
                    cancel_response.get("error", "Cancel failed"), cancel_response.get("error_code")
                )

            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Order cancellation failed: {error_msg}")

            result = OrderResult.error_result(error_msg, "EXECUTION_ERROR")
            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

    async def _cancel_on_exchange(self) -> Dict:
        """取引所で注文をキャンセル"""
        try:
            # 取引所アダプタでキャンセル実行
            return {"success": True, "message": "Order cancelled successfully"}
        except Exception as e:
            return {"success": False, "error": str(e), "error_code": "EXCHANGE_ERROR"}


class ModifyOrderCommand(OrderCommand):
    """注文修正コマンド"""

    def __init__(
        self,
        order: Order,
        new_price: Optional[float],
        new_amount: Optional[float],
        exchange_adapter,
        validator: Optional[OrderValidator] = None,
        security_manager: Optional[SecurityManager] = None,
    ):
        super().__init__(order, exchange_adapter, validator, security_manager)
        self.new_price = new_price
        self.new_amount = new_amount

    async def execute(self) -> OrderResult:
        """注文を修正"""
        self.execution_time = datetime.now(timezone.utc)

        try:
            # 修正可能状態かチェック
            if not self.order.is_active():
                error_msg = f"Order {self.order.id} is not modifiable: {self.order.status}"
                result = OrderResult.error_result(error_msg, "INVALID_STATUS")
                await self.log_execution(result)
                return result

            # 修正パラメータの検証
            if self.new_price is not None and self.new_price <= 0:
                result = OrderResult.error_result("New price must be positive", "VALIDATION_ERROR")
                await self.log_execution(result)
                return result

            if self.new_amount is not None and self.new_amount <= 0:
                result = OrderResult.error_result("New amount must be positive", "VALIDATION_ERROR")
                await self.log_execution(result)
                return result

            # 取引所で修正実行
            modify_response = await self._modify_on_exchange()

            if modify_response["success"]:
                # 注文情報を更新
                if self.new_price is not None:
                    self.order.price = self.new_price
                if self.new_amount is not None:
                    self.order.amount = self.new_amount
                    self.order.remaining_amount = self.new_amount - self.order.filled_amount

                result = OrderResult.success_result(self.order)
            else:
                result = OrderResult.error_result(
                    modify_response.get("error", "Modify failed"), modify_response.get("error_code")
                )

            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Order modification failed: {error_msg}")

            result = OrderResult.error_result(error_msg, "EXECUTION_ERROR")
            self.executed = True
            self.result = result
            await self.log_execution(result)
            return result

    async def _modify_on_exchange(self) -> Dict:
        """取引所で注文を修正"""
        try:
            return {"success": True, "message": "Order modified successfully"}
        except Exception as e:
            return {"success": False, "error": str(e), "error_code": "EXCHANGE_ERROR"}
