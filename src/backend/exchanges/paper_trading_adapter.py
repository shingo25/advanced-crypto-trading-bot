"""
Paper Trading Adapter
リアルタイム価格データを使用した模擬取引システム
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.backend.core.abstract_adapter import AbstractTradingAdapter

from ..database.models import DatabaseManager
from ..database.paper_wallet_service import PaperWalletService
from ..trading.orders.models import Order, OrderSide, OrderStatus, OrderType
from .base import AbstractExchangeAdapter
from .binance import BinanceAdapter

logger = logging.getLogger(__name__)


class PaperTradingAdapter(AbstractTradingAdapter):
    """
    Paper Trading Adapter
    リアルタイム価格を使用した模擬取引システム
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 設定辞書
                - real_exchange: 実際の取引所名 (binance, bybit, etc.)
                - user_id: ユーザーID
                - database_url: データベースURL
                - initial_balances: 初期残高設定
                - fee_rates: 手数料率設定
        """
        self.config = config
        self._exchange_name = "paper_trading"
        self.user_id = config.get("user_id", "default_user")

        # データベースサービス初期化
        database_url = config.get("database_url", "sqlite:///paper_trading.db")
        self.db_manager = DatabaseManager(database_url)
        self.wallet_service = PaperWalletService(self.db_manager)

        # ユーザーウォレット初期化
        default_setting = config.get("default_setting", "beginner")
        if not self.wallet_service.initialize_user_wallet(UUID(self.user_id), default_setting):
            logger.warning(f"Failed to initialize wallet for user {self.user_id}")

        # 実際の取引所Adapterを内部に保持（価格データ取得用）
        real_exchange = config.get("real_exchange", "binance")
        self.real_adapter = self._create_real_adapter(real_exchange, config)

        # 手数料率設定
        self.fee_rates = config.get(
            "fee_rates",
            {
                "maker": 0.001,  # 0.1%
                "taker": 0.001,  # 0.1%
            },
        )

        # 約定シミュレーション設定
        self.execution_delay = config.get("execution_delay", 0.1)  # 0.1秒遅延
        self.slippage_rate = config.get("slippage_rate", 0.0001)  # 0.01%スリッページ

        # 注文管理
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []

        logger.info(f"PaperTradingAdapter initialized for user {self.user_id}")

    def _create_real_adapter(self, exchange_name: str, config: Dict[str, Any]) -> AbstractExchangeAdapter:
        """実際の取引所Adapterを作成（価格データ取得用）"""
        # セキュリティ上、Paper Tradingでは実際のAPIキーは不要
        mock_config = {
            "api_key": "paper_trading_mock",
            "secret": "paper_trading_mock",
            "sandbox": True,  # サンドボックスモードで安全に
        }

        if exchange_name == "binance":
            return BinanceAdapter(
                api_key=mock_config["api_key"], secret=mock_config["secret"], sandbox=mock_config["sandbox"]
            )
        # 他の取引所も必要に応じて追加
        else:
            # デフォルトはBinance
            return BinanceAdapter(
                api_key=mock_config["api_key"], secret=mock_config["secret"], sandbox=mock_config["sandbox"]
            )

    async def get_balance(self) -> Dict[str, float]:
        """仮想残高を取得"""
        balances = self.wallet_service.get_user_balances(UUID(self.user_id))
        return {
            asset: {"free": info["available"], "used": info["locked"], "total": info["total"]}
            for asset, info in balances.items()
        }

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """実際の取引所から価格データを取得"""
        try:
            return await self.real_adapter.get_ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            # フォールバック価格
            return {
                "symbol": symbol,
                "price": 50000.0,  # BTC/USDTのフォールバック価格
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """実際の取引所から板情報を取得"""
        try:
            return await self.real_adapter.get_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            # フォールバック板情報
            ticker = await self.get_ticker(symbol)
            price = float(ticker["price"])
            return {
                "bids": [[price * 0.999, 1.0], [price * 0.998, 2.0]],
                "asks": [[price * 1.001, 1.0], [price * 1.002, 2.0]],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """模擬注文を実行"""
        try:
            logger.info(f"Placing paper order: {order.symbol} {order.side.value} {order.amount} @ {order.price}")

            # 注文IDを生成
            order.exchange_order_id = str(uuid4())
            order.submitted_at = datetime.now(timezone.utc)
            order.paper_trading = True

            # 残高チェック
            if not await self._check_balance_for_order(order):
                order.status = OrderStatus.REJECTED
                order.error_message = "Insufficient balance"
                return self._format_order_response(order)

            # 残高をロック
            await self._lock_balance_for_order(order)

            # アクティブ注文に追加
            self.active_orders[order.exchange_order_id] = order

            # 成行注文の場合は即座に約定
            if order.order_type == OrderType.MARKET:
                await self._execute_market_order(order)
            else:
                # 指値注文の場合は待機状態
                order.status = OrderStatus.SUBMITTED
                # バックグラウンドで約定チェックを開始
                asyncio.create_task(self._monitor_limit_order(order))

            self.order_history.append(order)

            return self._format_order_response(order)

        except Exception as e:
            logger.error(f"Error placing paper order: {e}")
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            return self._format_order_response(order)

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """注文をキャンセル"""
        if order_id not in self.active_orders:
            return {"error": "Order not found"}

        order = self.active_orders[order_id]

        # 残高のロックを解除
        await self._unlock_balance_for_order(order)

        # 注文をキャンセル状態に
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)

        # アクティブ注文から削除
        del self.active_orders[order_id]

        logger.info(f"Paper order cancelled: {order_id}")
        return self._format_order_response(order)

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """注文状況を取得"""
        # アクティブ注文から検索
        if order_id in self.active_orders:
            return self._format_order_response(self.active_orders[order_id])

        # 履歴から検索
        for order in self.order_history:
            if order.exchange_order_id == order_id:
                return self._format_order_response(order)

        return {"error": "Order not found"}

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """未決済注文を取得"""
        orders = list(self.active_orders.values())

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        return [self._format_order_response(o) for o in orders]

    async def _check_balance_for_order(self, order: Order) -> bool:
        """注文に必要な残高があるかチェック"""
        symbol_parts = order.symbol.split("/")
        if len(symbol_parts) != 2:
            return False

        base_asset, quote_asset = symbol_parts

        if order.side == OrderSide.BUY:
            # 買い注文: quote通貨が必要
            required_amount = float(order.amount * (order.price or Decimal("50000")))
            balance_info = self.wallet_service.get_asset_balance(UUID(self.user_id), quote_asset)
            return balance_info["available"] >= required_amount
        else:
            # 売り注文: base通貨が必要
            required_amount = float(order.amount)
            balance_info = self.wallet_service.get_asset_balance(UUID(self.user_id), base_asset)
            return balance_info["available"] >= required_amount

    async def _lock_balance_for_order(self, order: Order):
        """注文に必要な残高をロック"""
        symbol_parts = order.symbol.split("/")
        base_asset, quote_asset = symbol_parts

        if order.side == OrderSide.BUY:
            # 買い注文: quote通貨をロック
            required_amount = Decimal(str(float(order.amount * (order.price or Decimal("50000")))))
            self.wallet_service.lock_balance(UUID(self.user_id), quote_asset, required_amount, order.exchange_order_id)
        else:
            # 売り注文: base通貨をロック
            required_amount = Decimal(str(float(order.amount)))
            self.wallet_service.lock_balance(UUID(self.user_id), base_asset, required_amount, order.exchange_order_id)

    async def _unlock_balance_for_order(self, order: Order):
        """注文でロックした残高を解除"""
        symbol_parts = order.symbol.split("/")
        base_asset, quote_asset = symbol_parts

        if order.side == OrderSide.BUY:
            required_amount = Decimal(str(float(order.amount * (order.price or Decimal("50000")))))
            self.wallet_service.unlock_balance(
                UUID(self.user_id), quote_asset, required_amount, order.exchange_order_id
            )
        else:
            required_amount = Decimal(str(float(order.amount)))
            self.wallet_service.unlock_balance(UUID(self.user_id), base_asset, required_amount, order.exchange_order_id)

    async def _execute_market_order(self, order: Order):
        """成行注文を即座に約定"""
        try:
            # 実行遅延をシミュレート
            await asyncio.sleep(self.execution_delay)

            # 現在の最良気配値を取得
            order_book = await self.get_order_book(order.symbol)

            if order.side == OrderSide.BUY:
                # 買い注文: Ask価格で約定
                execution_price = float(order_book["asks"][0][0])
            else:
                # 売り注文: Bid価格で約定
                execution_price = float(order_book["bids"][0][0])

            # スリッページを適用
            if order.side == OrderSide.BUY:
                execution_price *= 1 + self.slippage_rate
            else:
                execution_price *= 1 - self.slippage_rate

            # 約定処理
            await self._fill_order(order, execution_price, float(order.amount))

        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            order.status = OrderStatus.FAILED
            order.error_message = str(e)

    async def _monitor_limit_order(self, order: Order):
        """指値注文の約定を監視"""
        try:
            while order.exchange_order_id in self.active_orders:
                # 現在価格をチェック
                ticker = await self.get_ticker(order.symbol)
                current_price = float(ticker["price"])
                order_price = float(order.price)

                # 約定条件チェック
                should_fill = False
                if order.side == OrderSide.BUY and current_price <= order_price:
                    should_fill = True
                elif order.side == OrderSide.SELL and current_price >= order_price:
                    should_fill = True

                if should_fill:
                    await self._fill_order(order, order_price, float(order.amount))
                    break

                # 1秒待機
                await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"Error monitoring limit order: {e}")

    async def _fill_order(self, order: Order, fill_price: float, fill_quantity: float):
        """注文を約定"""
        try:
            symbol_parts = order.symbol.split("/")
            base_asset, quote_asset = symbol_parts

            # 手数料計算
            fee_rate = self.fee_rates.get("taker", 0.001)

            if order.side == OrderSide.BUY:
                # 買い注文
                cost = fill_quantity * fill_price
                fee = fill_quantity * fee_rate  # Base通貨で手数料

                # データベース上で取引実行
                success = self.wallet_service.execute_trade(
                    user_id=UUID(self.user_id),
                    buy_asset=base_asset,
                    sell_asset=quote_asset,
                    buy_amount=Decimal(str(fill_quantity)),
                    sell_amount=Decimal(str(cost)),
                    fee_asset=base_asset,
                    fee_amount=Decimal(str(fee)),
                    related_order_id=order.exchange_order_id,
                    description=f"Paper trading order fill: {order.symbol} {order.side.value}",
                )

                # ロック解除
                self.wallet_service.unlock_balance(
                    UUID(self.user_id), quote_asset, Decimal(str(cost)), order.exchange_order_id
                )

            else:
                # 売り注文
                proceeds = fill_quantity * fill_price
                fee = proceeds * fee_rate  # Quote通貨で手数料

                # データベース上で取引実行
                success = self.wallet_service.execute_trade(
                    user_id=UUID(self.user_id),
                    buy_asset=quote_asset,
                    sell_asset=base_asset,
                    buy_amount=Decimal(str(proceeds)),
                    sell_amount=Decimal(str(fill_quantity)),
                    fee_asset=quote_asset,
                    fee_amount=Decimal(str(fee)),
                    related_order_id=order.exchange_order_id,
                    description=f"Paper trading order fill: {order.symbol} {order.side.value}",
                )

                # ロック解除
                self.wallet_service.unlock_balance(
                    UUID(self.user_id), base_asset, Decimal(str(fill_quantity)), order.exchange_order_id
                )

            if not success:
                raise Exception("Failed to execute trade in database")

            # 注文ステータス更新
            order.status = OrderStatus.FILLED
            order.filled_amount = Decimal(str(fill_quantity))
            order.average_fill_price = Decimal(str(fill_price))
            order.fee_amount = Decimal(str(fee if order.side == OrderSide.BUY else fee))
            order.fee_currency = base_asset if order.side == OrderSide.BUY else quote_asset
            order.filled_at = datetime.now(timezone.utc)

            # アクティブ注文から削除
            if order.exchange_order_id in self.active_orders:
                del self.active_orders[order.exchange_order_id]

            logger.info(f"Paper order filled: {order.symbol} {order.side.value} {fill_quantity} @ {fill_price}")

        except Exception as e:
            logger.error(f"Error filling order: {e}")
            order.status = OrderStatus.FAILED
            order.error_message = str(e)

    def _format_order_response(self, order: Order) -> Dict[str, Any]:
        """注文レスポンスを整形"""
        return {
            "id": order.exchange_order_id,
            "symbol": order.symbol,
            "type": order.order_type.value,
            "side": order.side.value,
            "amount": float(order.amount),
            "price": float(order.price) if order.price else None,
            "status": order.status.value,
            "filled": float(order.filled_amount) if order.filled_amount else 0.0,
            "remaining": float(order.remaining_amount) if order.remaining_amount else float(order.amount),
            "average": float(order.average_fill_price) if order.average_fill_price else None,
            "fee": {"amount": float(order.fee_amount) if order.fee_amount else 0.0, "currency": order.fee_currency},
            "timestamp": order.submitted_at.isoformat() if order.submitted_at else None,
            "datetime": order.submitted_at.isoformat() if order.submitted_at else None,
            "info": {"paper_trading": True, "user_id": self.user_id},
        }

    # AbstractExchangeAdapterの抽象メソッド実装
    async def connect(self) -> bool:
        """接続（Paper Tradingでは常に成功）"""
        logger.info("Paper Trading adapter connected")
        return True

    async def disconnect(self):
        """切断"""
        # アクティブ注文をすべてキャンセル
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
        logger.info("Paper Trading adapter disconnected")

    def is_connected(self) -> bool:
        """接続状態（Paper Tradingでは常にTrue）"""
        return True

    @property
    def exchange_name(self) -> str:
        """取引所名（Paper Trading固定）"""
        return self._exchange_name

    # 追加のヘルパーメソッド
    def get_wallet_summary(self) -> Dict[str, Any]:
        """ウォレット情報サマリーを取得"""
        portfolio = self.wallet_service.get_portfolio_summary(UUID(self.user_id))
        return {
            "user_id": self.user_id,
            "balances": portfolio.get("balances", {}),
            "statistics": portfolio.get("statistics", {}),
            "active_orders": len(self.active_orders),
            "total_orders": len(self.order_history),
            "timestamp": portfolio.get("timestamp"),
        }

    def reset_wallet(self, default_setting: str = "beginner"):
        """ウォレットをリセット（テスト用）"""
        # すべての注文をキャンセル
        for order_id in list(self.active_orders.keys()):
            asyncio.create_task(self.cancel_order(order_id))

        # ウォレットを再初期化
        self.wallet_service.reset_user_wallet(UUID(self.user_id), default_setting)
        self.order_history.clear()

        logger.info(f"Paper wallet reset for user {self.user_id}")

    def get_transaction_history(self, asset: str = None, limit: int = 100) -> List[Dict]:
        """取引履歴を取得"""
        return self.wallet_service.get_transaction_history(UUID(self.user_id), asset=asset, limit=limit)
