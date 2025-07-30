"""
注文システムのテストスイート
"""

from decimal import Decimal

import pytest

from src.backend.trading.orders import (
    CancelOrderCommand,
    CreateOrderCommand,
    Order,
    OrderFactory,
    OrderParams,
    OrderSide,
    OrderStatus,
    OrderType,
    OrderValidationFactory,
)


class TestOrderModels:
    """注文モデルのテスト"""

    def test_order_creation_from_params(self):
        """OrderParamsからのOrder作成テスト"""
        params = OrderParams(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000"),
        )

        order = Order.from_params(params)

        assert order.exchange == "binance"
        assert order.symbol == "BTC/USDT"
        assert order.order_type == OrderType.LIMIT
        assert order.side == OrderSide.BUY
        assert order.amount == Decimal("0.1")
        assert order.price == Decimal("45000")
        assert order.status == OrderStatus.PENDING
        assert order.remaining_amount == Decimal("0.1")

    def test_order_validation_limit_order_requires_price(self):
        """指値注文の価格必須バリデーション"""
        with pytest.raises(ValueError, match="Limit orders require a price"):
            OrderParams(
                exchange="binance",
                symbol="BTC/USDT",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                amount=Decimal("0.1"),
                # price=None  # 価格なし
            )

    def test_order_validation_stop_loss_requires_stop_price(self):
        """ストップロス注文のストップ価格必須バリデーション"""
        with pytest.raises(ValueError, match="stop_loss orders require a stop_price"):
            OrderParams(
                exchange="binance",
                symbol="BTC/USDT",
                order_type=OrderType.STOP_LOSS,
                side=OrderSide.SELL,
                amount=Decimal("0.1"),
                # stop_price=None  # ストップ価格なし
            )

    def test_order_update_fill(self):
        """約定情報更新のテスト"""
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("1.0"),
            price=Decimal("45000"),
        )

        # 部分約定
        order.update_fill(Decimal("0.3"), Decimal("45000"))
        assert order.filled_amount == Decimal("0.3")
        assert order.remaining_amount == Decimal("0.7")
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.average_fill_price == Decimal("45000")

        # 完全約定
        order.update_fill(Decimal("0.7"), Decimal("45100"))
        assert order.filled_amount == Decimal("1.0")
        assert order.remaining_amount == Decimal("0.0")
        assert order.status == OrderStatus.FILLED
        # 平均約定価格の計算確認
        expected_avg = (Decimal("45000") * Decimal("0.3") + Decimal("45100") * Decimal("0.7")) / Decimal("1.0")
        assert order.average_fill_price == expected_avg

    def test_order_status_checks(self):
        """注文状態チェックのテスト"""
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("1.0"),
            price=Decimal("45000"),
        )

        # 初期状態（PENDING）
        assert not order.is_complete()
        assert not order.is_active()

        # SUBMITTED状態
        order.status = OrderStatus.SUBMITTED
        assert not order.is_complete()
        assert order.is_active()

        # FILLED状態
        order.status = OrderStatus.FILLED
        assert order.is_complete()
        assert not order.is_active()


class TestOrderFactory:
    """注文ファクトリのテスト"""

    def test_create_order_success(self):
        """正常な注文作成テスト"""
        params = OrderParams(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000"),
        )

        order = OrderFactory.create_order(params)

        assert isinstance(order, Order)
        assert order.exchange == "binance"
        assert order.symbol == "BTC/USDT"

    def test_create_order_validation_failure(self):
        """注文作成時のバリデーション失敗テスト"""
        from pydantic import ValidationError

        # OrderParamsの作成時点でValidationErrorが発生
        with pytest.raises(ValidationError):
            OrderParams(
                exchange="binance",
                symbol="BTC/USDT",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                amount=Decimal("0.1"),
                # price なし
            )


class TestOrderValidationFactory:
    """注文バリデーションファクトリのテスト"""

    def test_create_market_order_params(self):
        """成行注文パラメータ作成テスト"""
        params = OrderValidationFactory.create_market_order_params(
            exchange="binance", symbol="BTC/USDT", side="buy", amount=0.1, strategy_name="test_strategy"
        )

        assert params.exchange == "binance"
        assert params.symbol == "BTC/USDT"
        assert params.order_type == OrderType.MARKET
        assert params.side == OrderSide.BUY
        assert params.amount == Decimal("0.1")
        assert params.strategy_name == "test_strategy"

    def test_create_limit_order_params(self):
        """指値注文パラメータ作成テスト"""
        params = OrderValidationFactory.create_limit_order_params(
            exchange="binance", symbol="BTC/USDT", side="buy", amount=0.1, price=45000.0
        )

        assert params.order_type == OrderType.LIMIT
        assert params.price == 45000.0

    def test_create_oco_order_params(self):
        """OCO注文パラメータ作成テスト"""
        params = OrderValidationFactory.create_oco_order_params(
            exchange="binance",
            symbol="BTC/USDT",
            side="sell",
            amount=0.1,
            take_profit_price=50000.0,
            stop_loss_price=40000.0,
        )

        assert params.order_type == OrderType.OCO
        assert params.oco_take_profit_price == 50000.0
        assert params.oco_stop_loss_price == 40000.0


class TestOrderCommands:
    """注文コマンドのテスト"""

    @pytest.mark.asyncio
    async def test_create_order_command_validation(self):
        """注文作成コマンドのバリデーションテスト"""
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000"),
        )

        command = CreateOrderCommand(order, None)  # exchange_adapter=None for test

        # バリデーション成功ケース
        is_valid, error_msg = await command.validate()
        assert is_valid
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_create_order_command_validation_failure(self):
        """注文作成コマンドのバリデーション失敗テスト"""
        order = Order(
            exchange="",  # 空の取引所名
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000"),
        )

        command = CreateOrderCommand(order, None)

        is_valid, error_msg = await command.validate()
        assert not is_valid
        assert "Exchange is required" in error_msg

    @pytest.mark.asyncio
    async def test_cancel_order_command_invalid_status(self):
        """キャンセルコマンドの無効状態テスト"""
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("0.1"),
            price=Decimal("45000"),
            status=OrderStatus.FILLED,  # 完了済み
        )

        command = CancelOrderCommand(order, None)
        result = await command.execute()

        assert not result.success
        assert "not in cancellable state" in result.error_message


class TestSecurityFeatures:
    """セキュリティ機能のテスト"""

    @pytest.mark.asyncio
    async def test_large_order_security_check(self):
        """大額注文のセキュリティチェックテスト"""
        # SecurityManagerの設定（有効なFernetキーを生成）
        from cryptography.fernet import Fernet

        from src.backend.trading.orders.security import SecurityManager

        encryption_key = Fernet.generate_key()

        security_config = {
            "MASTER_ENCRYPTION_KEY": encryption_key,  # 有効なFernetキー
            "ANOMALY_THRESHOLDS": {
                "max_order_value_ratio": 0.25,  # ポートフォリオの25%
                "max_hourly_trades": 50,  # 1時間50取引
                "max_price_deviation": 0.10,  # 10%価格乖離
                "suspicious_symbol_threshold": 5,  # 新規シンボル5つ/日
            },
        }
        security_manager = SecurityManager(security_config)

        # 異常に大きな注文額
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("10"),  # 10 BTC
            price=Decimal("50000"),  # $50,000 = $500,000の注文
        )

        command = CreateOrderCommand(order, None, security_manager=security_manager)
        # ポートフォリオ価値$1,000,000を設定（50%の注文なのでセキュリティチェックに引っかかる）
        is_valid, error_msg = await command.validate(
            request_context={"user_id": "test_user", "ip_address": "127.0.0.1"}, portfolio_value=Decimal("1000000")
        )

        assert not is_valid
        assert "Anomalous trading activity detected" in error_msg

    @pytest.mark.asyncio
    async def test_negative_amount_validation(self):
        """負の数量のバリデーションテスト"""
        order = Order(
            exchange="binance",
            symbol="BTC/USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=Decimal("-0.1"),  # 負の数量
            price=Decimal("45000"),
        )

        command = CreateOrderCommand(order, None)
        is_valid, error_msg = await command.validate()

        assert not is_valid
        assert "must be positive" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
