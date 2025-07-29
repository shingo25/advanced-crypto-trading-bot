"""
データベースサービス
注文・取引データの永続化・取得機能
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import OrderModel, TradeModel, TradingStatistics, DatabaseManager
from ..trading.orders.models import Order, OrderType, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


class OrderService:
    """注文データベースサービス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_order(self, order: Order, user_id: UUID, strategy_id: str = None) -> str:
        """
        注文をデータベースに保存

        Args:
            order: 注文オブジェクト
            user_id: ユーザーID
            strategy_id: 戦略ID

        Returns:
            str: 作成された注文のDB ID
        """
        session = self.db_manager.get_session()
        try:
            # OrderをOrderModelに変換
            order_model = OrderModel(
                user_id=user_id,
                strategy_id=strategy_id,
                strategy_name=order.strategy_name,
                exchange=order.exchange,
                symbol=order.symbol,
                order_type=order.order_type.value,
                side=order.side.value,
                quantity=order.amount,
                price=order.price,
                stop_price=order.stop_price,
                time_in_force=order.time_in_force.value if order.time_in_force else "GTC",
                oco_take_profit_price=order.oco_take_profit_price,
                oco_stop_loss_price=order.oco_stop_loss_price,
                status=order.status.value,
                filled_quantity=order.filled_amount or 0,
                remaining_quantity=order.remaining_amount or order.amount,
                average_fill_price=order.average_fill_price,
                exchange_order_id=order.exchange_order_id,
                client_order_id=order.client_order_id,
                submitted_at=order.submitted_at,
                filled_at=order.filled_at,
                cancelled_at=order.cancelled_at,
                error_message=order.error_message,
                fee_amount=order.fee_amount,
                fee_currency=order.fee_currency,
                paper_trading=getattr(order, "paper_trading", False),
                metadata=getattr(order, "metadata", None),
            )

            session.add(order_model)
            session.commit()

            logger.info(f"Order created in DB: {order_model.id}")
            return str(order_model.id)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create order in DB: {e}")
            raise
        finally:
            session.close()

    def update_order(self, order_id: str, **kwargs) -> bool:
        """
        注文を更新

        Args:
            order_id: 注文ID
            **kwargs: 更新するフィールド

        Returns:
            bool: 更新成功フラグ
        """
        session = self.db_manager.get_session()
        try:
            order_model = session.query(OrderModel).filter(OrderModel.id == order_id).first()
            if not order_model:
                logger.warning(f"Order not found for update: {order_id}")
                return False

            # 更新可能なフィールドのみ適用
            updatable_fields = [
                "status",
                "filled_quantity",
                "remaining_quantity",
                "average_fill_price",
                "exchange_order_id",
                "submitted_at",
                "filled_at",
                "cancelled_at",
                "error_message",
                "error_code",
                "fee_amount",
                "fee_currency",
                "metadata",
            ]

            for key, value in kwargs.items():
                if key in updatable_fields and hasattr(order_model, key):
                    setattr(order_model, key, value)

            session.commit()
            logger.info(f"Order updated in DB: {order_id}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update order {order_id}: {e}")
            return False
        finally:
            session.close()

    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        注文を取得

        Args:
            order_id: 注文ID

        Returns:
            Optional[Dict]: 注文データ
        """
        session = self.db_manager.get_session()
        try:
            order_model = session.query(OrderModel).filter(OrderModel.id == order_id).first()
            if order_model:
                return order_model.to_dict()
            return None

        except SQLAlchemyError as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
        finally:
            session.close()

    def get_orders(
        self,
        user_id: UUID = None,
        strategy_id: str = None,
        exchange: str = None,
        symbol: str = None,
        status: str = None,
        paper_trading: bool = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
    ) -> List[Dict]:
        """
        注文リストを取得

        Args:
            user_id: ユーザーID
            strategy_id: 戦略ID
            exchange: 取引所
            symbol: シンボル
            status: ステータス
            paper_trading: ペーパートレーディングフラグ
            limit: 取得件数制限
            offset: オフセット
            order_by: ソート順

        Returns:
            List[Dict]: 注文リスト
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(OrderModel)

            # フィルター条件
            if user_id:
                query = query.filter(OrderModel.user_id == user_id)
            if strategy_id:
                query = query.filter(OrderModel.strategy_id == strategy_id)
            if exchange:
                query = query.filter(OrderModel.exchange == exchange)
            if symbol:
                query = query.filter(OrderModel.symbol == symbol)
            if status:
                query = query.filter(OrderModel.status == status)
            if paper_trading is not None:
                query = query.filter(OrderModel.paper_trading == paper_trading)

            # ソート
            if order_by == "created_at":
                query = query.order_by(desc(OrderModel.created_at))
            elif order_by == "updated_at":
                query = query.order_by(desc(OrderModel.updated_at))

            # ページネーション
            orders = query.offset(offset).limit(limit).all()

            return [order.to_dict() for order in orders]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get orders: {e}")
            return []
        finally:
            session.close()

    def get_active_orders(self, user_id: UUID = None, exchange: str = None) -> List[Dict]:
        """
        アクティブな注文を取得

        Args:
            user_id: ユーザーID
            exchange: 取引所

        Returns:
            List[Dict]: アクティブ注文リスト
        """
        return self.get_orders(user_id=user_id, exchange=exchange, status="submitted", limit=1000) + self.get_orders(
            user_id=user_id, exchange=exchange, status="partially_filled", limit=1000
        )


class TradeService:
    """取引データベースサービス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_trade(
        self,
        order_id: str,
        user_id: UUID,
        strategy_id: str,
        exchange: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fee_amount: Decimal = None,
        fee_currency: str = None,
        exchange_trade_id: str = None,
        exchange_order_id: str = None,
        is_maker: bool = None,
        paper_trading: bool = False,
        slippage: Decimal = None,
        metadata: Dict = None,
    ) -> str:
        """
        取引をデータベースに保存

        Args:
            order_id: 関連注文ID
            user_id: ユーザーID
            strategy_id: 戦略ID
            exchange: 取引所
            symbol: シンボル
            side: 売買方向
            quantity: 数量
            price: 価格
            fee_amount: 手数料
            fee_currency: 手数料通貨
            exchange_trade_id: 取引所取引ID
            exchange_order_id: 取引所注文ID
            is_maker: メイカー取引フラグ
            paper_trading: ペーパートレーディングフラグ
            slippage: スリッページ
            metadata: メタデータ

        Returns:
            str: 作成された取引のDB ID
        """
        session = self.db_manager.get_session()
        try:
            trade_model = TradeModel(
                order_id=order_id,
                user_id=user_id,
                strategy_id=strategy_id,
                exchange=exchange,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fee_amount=fee_amount,
                fee_currency=fee_currency,
                exchange_trade_id=exchange_trade_id,
                exchange_order_id=exchange_order_id,
                is_maker=is_maker,
                paper_trading=paper_trading,
                slippage=slippage,
                metadata=metadata,
                executed_at=datetime.now(timezone.utc),
            )

            session.add(trade_model)
            session.commit()

            logger.info(f"Trade created in DB: {trade_model.id}")
            return str(trade_model.id)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create trade in DB: {e}")
            raise
        finally:
            session.close()

    def get_trades(
        self,
        user_id: UUID = None,
        strategy_id: str = None,
        exchange: str = None,
        symbol: str = None,
        order_id: str = None,
        paper_trading: bool = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """
        取引リストを取得

        Args:
            user_id: ユーザーID
            strategy_id: 戦略ID
            exchange: 取引所
            symbol: シンボル
            order_id: 注文ID
            paper_trading: ペーパートレーディングフラグ
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得件数制限
            offset: オフセット

        Returns:
            List[Dict]: 取引リスト
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(TradeModel)

            # フィルター条件
            if user_id:
                query = query.filter(TradeModel.user_id == user_id)
            if strategy_id:
                query = query.filter(TradeModel.strategy_id == strategy_id)
            if exchange:
                query = query.filter(TradeModel.exchange == exchange)
            if symbol:
                query = query.filter(TradeModel.symbol == symbol)
            if order_id:
                query = query.filter(TradeModel.order_id == order_id)
            if paper_trading is not None:
                query = query.filter(TradeModel.paper_trading == paper_trading)
            if start_date:
                query = query.filter(TradeModel.executed_at >= start_date)
            if end_date:
                query = query.filter(TradeModel.executed_at <= end_date)

            # ソート・ページネーション
            trades = query.order_by(desc(TradeModel.executed_at)).offset(offset).limit(limit).all()

            return [trade.to_dict() for trade in trades]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get trades: {e}")
            return []
        finally:
            session.close()

    def get_position_summary(self, user_id: UUID, paper_trading: bool = False) -> List[Dict]:
        """
        ポジション集計を取得

        Args:
            user_id: ユーザーID
            paper_trading: ペーパートレーディングフラグ

        Returns:
            List[Dict]: ポジション集計リスト
        """
        session = self.db_manager.get_session()
        try:
            # SQLによる集計クエリ
            query = (
                session.query(
                    TradeModel.exchange,
                    TradeModel.symbol,
                    func.sum(
                        func.case((TradeModel.side == "buy", TradeModel.quantity), else_=-TradeModel.quantity)
                    ).label("net_quantity"),
                    func.avg(func.case((TradeModel.side == "buy", TradeModel.price), else_=None)).label(
                        "avg_buy_price"
                    ),
                    func.avg(func.case((TradeModel.side == "sell", TradeModel.price), else_=None)).label(
                        "avg_sell_price"
                    ),
                    func.sum(
                        func.case(
                            (TradeModel.side == "buy", TradeModel.quantity * TradeModel.price),
                            else_=-TradeModel.quantity * TradeModel.price,
                        )
                    ).label("net_value"),
                    func.count().label("trade_count"),
                    func.min(TradeModel.executed_at).label("first_trade"),
                    func.max(TradeModel.executed_at).label("last_trade"),
                )
                .filter(and_(TradeModel.user_id == user_id, TradeModel.paper_trading == paper_trading))
                .group_by(TradeModel.exchange, TradeModel.symbol)
                .having(
                    func.sum(func.case((TradeModel.side == "buy", TradeModel.quantity), else_=-TradeModel.quantity))
                    != 0
                )
            )

            results = []
            for row in query.all():
                results.append(
                    {
                        "exchange": row.exchange,
                        "symbol": row.symbol,
                        "net_quantity": float(row.net_quantity) if row.net_quantity else 0,
                        "avg_buy_price": float(row.avg_buy_price) if row.avg_buy_price else None,
                        "avg_sell_price": float(row.avg_sell_price) if row.avg_sell_price else None,
                        "net_value": float(row.net_value) if row.net_value else 0,
                        "trade_count": int(row.trade_count),
                        "first_trade": row.first_trade.isoformat() if row.first_trade else None,
                        "last_trade": row.last_trade.isoformat() if row.last_trade else None,
                    }
                )

            return results

        except SQLAlchemyError as e:
            logger.error(f"Failed to get position summary: {e}")
            return []
        finally:
            session.close()


class AnalyticsService:
    """分析・統計サービス"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_trading_performance(
        self,
        user_id: UUID,
        strategy_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        paper_trading: bool = False,
    ) -> Dict:
        """
        取引パフォーマンスを取得

        Args:
            user_id: ユーザーID
            strategy_id: 戦略ID
            start_date: 開始日時
            end_date: 終了日時
            paper_trading: ペーパートレーディングフラグ

        Returns:
            Dict: パフォーマンス指標
        """
        session = self.db_manager.get_session()
        try:
            # フィルター条件
            filters = [TradeModel.user_id == user_id, TradeModel.paper_trading == paper_trading]

            if strategy_id:
                filters.append(TradeModel.strategy_id == strategy_id)
            if start_date:
                filters.append(TradeModel.executed_at >= start_date)
            if end_date:
                filters.append(TradeModel.executed_at <= end_date)

            # 基本統計
            stats_query = session.query(
                func.count().label("total_trades"),
                func.sum(TradeModel.quantity * TradeModel.price).label("total_volume"),
                func.sum(TradeModel.fee_amount).label("total_fees"),
                func.avg(TradeModel.price).label("avg_price"),
                func.min(TradeModel.price).label("min_price"),
                func.max(TradeModel.price).label("max_price"),
                func.count(func.case((TradeModel.side == "buy", 1))).label("buy_count"),
                func.count(func.case((TradeModel.side == "sell", 1))).label("sell_count"),
            ).filter(and_(*filters))

            stats = stats_query.first()

            # 日次損益（簡略化版）
            daily_pnl_query = (
                session.query(
                    func.date(TradeModel.executed_at).label("trade_date"),
                    func.sum(
                        func.case(
                            (
                                TradeModel.side == "sell",
                                (TradeModel.quantity * TradeModel.price) - TradeModel.fee_amount,
                            ),
                            else_=-(TradeModel.quantity * TradeModel.price) - TradeModel.fee_amount,
                        )
                    ).label("daily_pnl"),
                )
                .filter(and_(*filters))
                .group_by(func.date(TradeModel.executed_at))
                .order_by(func.date(TradeModel.executed_at))
            )

            daily_results = []
            for row in daily_pnl_query.all():
                daily_results.append(
                    {
                        "date": row.trade_date.isoformat() if row.trade_date else None,
                        "pnl": float(row.daily_pnl) if row.daily_pnl else 0,
                    }
                )

            # 結果をまとめる
            performance = {
                "total_trades": int(stats.total_trades) if stats.total_trades else 0,
                "total_volume": float(stats.total_volume) if stats.total_volume else 0,
                "total_fees": float(stats.total_fees) if stats.total_fees else 0,
                "avg_price": float(stats.avg_price) if stats.avg_price else 0,
                "min_price": float(stats.min_price) if stats.min_price else 0,
                "max_price": float(stats.max_price) if stats.max_price else 0,
                "buy_count": int(stats.buy_count) if stats.buy_count else 0,
                "sell_count": int(stats.sell_count) if stats.sell_count else 0,
                "daily_pnl": daily_results,
                "total_pnl": sum(day["pnl"] for day in daily_results),
            }

            return performance

        except SQLAlchemyError as e:
            logger.error(f"Failed to get trading performance: {e}")
            return {}
        finally:
            session.close()

    def get_risk_metrics(
        self, user_id: UUID, start_date: datetime = None, end_date: datetime = None, paper_trading: bool = False
    ) -> Dict:
        """
        リスクメトリクスを取得

        Args:
            user_id: ユーザーID
            start_date: 開始日時
            end_date: 終了日時
            paper_trading: ペーパートレーディングフラグ

        Returns:
            Dict: リスクメトリクス
        """
        session = self.db_manager.get_session()
        try:
            # 集中度リスク計算
            concentration_query = (
                session.query(
                    TradeModel.symbol, func.sum(TradeModel.quantity * TradeModel.price).label("symbol_volume")
                )
                .filter(
                    and_(
                        TradeModel.user_id == user_id,
                        TradeModel.paper_trading == paper_trading,
                        TradeModel.executed_at >= start_date if start_date else True,
                        TradeModel.executed_at <= end_date if end_date else True,
                    )
                )
                .group_by(TradeModel.symbol)
            )

            symbol_volumes = []
            total_volume = 0
            for row in concentration_query.all():
                volume = float(row.symbol_volume) if row.symbol_volume else 0
                symbol_volumes.append({"symbol": row.symbol, "volume": volume})
                total_volume += volume

            # 集中度計算
            concentrations = []
            max_concentration = 0
            for item in symbol_volumes:
                concentration = item["volume"] / total_volume if total_volume > 0 else 0
                concentrations.append({"symbol": item["symbol"], "concentration": concentration})
                max_concentration = max(max_concentration, concentration)

            return {
                "total_volume": total_volume,
                "symbol_concentrations": concentrations,
                "max_concentration": max_concentration,
                "diversification_ratio": 1.0 / len(concentrations) if concentrations else 0,
            }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get risk metrics: {e}")
            return {}
        finally:
            session.close()


# サービスファクトリ
class DatabaseServiceFactory:
    """データベースサービスファクトリ"""

    def __init__(self, database_url: str):
        self.db_manager = DatabaseManager(database_url)
        self.order_service = OrderService(self.db_manager)
        self.trade_service = TradeService(self.db_manager)
        self.analytics_service = AnalyticsService(self.db_manager)

    def initialize_database(self):
        """データベースを初期化"""
        self.db_manager.create_tables()
        logger.info("Database initialized successfully")

    def get_order_service(self) -> OrderService:
        """注文サービスを取得"""
        return self.order_service

    def get_trade_service(self) -> TradeService:
        """取引サービスを取得"""
        return self.trade_service

    def get_analytics_service(self) -> AnalyticsService:
        """分析サービスを取得"""
        return self.analytics_service
