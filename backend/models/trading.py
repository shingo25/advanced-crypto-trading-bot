"""
取引関連のデータモデル（Supabase SDK版）
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.supabase_db import SupabaseTable, get_supabase_connection

logger = logging.getLogger(__name__)


class StrategiesModel:
    """Strategiesテーブルの操作を管理"""

    def __init__(self):
        self.connection = get_supabase_connection()
        self.table = SupabaseTable("strategies", self.connection)

    def get_user_strategies(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーの戦略一覧を取得"""
        try:
            return self.table.select("*", user_id=user_id)
        except Exception as e:
            logger.error(f"ユーザー戦略取得エラー (ID: {user_id}): {e}")
            return []

    def get_strategy_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """IDで戦略を取得"""
        try:
            strategies = self.table.select("*", id=strategy_id)
            return strategies[0] if strategies else None
        except Exception as e:
            logger.error(f"戦略取得エラー (ID: {strategy_id}): {e}")
            return None

    def create_strategy(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        is_active: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """新しい戦略を作成"""
        try:
            strategy_data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "parameters": parameters or {},
                "is_active": is_active,
                "created_at": datetime.utcnow().isoformat(),
            }
            return self.table.insert(strategy_data)
        except Exception as e:
            logger.error(f"戦略作成エラー: {e}")
            return None

    def update_strategy(self, strategy_id: str, **updates) -> Optional[Dict[str, Any]]:
        """戦略を更新"""
        try:
            strategies = self.table.update(updates, id=strategy_id)
            return strategies[0] if strategies else None
        except Exception as e:
            logger.error(f"戦略更新エラー (ID: {strategy_id}): {e}")
            return None

    def activate_strategy(self, strategy_id: str) -> bool:
        """戦略を有効化"""
        try:
            self.table.update({"is_active": True}, id=strategy_id)
            return True
        except Exception as e:
            logger.error(f"戦略有効化エラー (ID: {strategy_id}): {e}")
            return False

    def deactivate_strategy(self, strategy_id: str) -> bool:
        """戦略を無効化"""
        try:
            self.table.update({"is_active": False}, id=strategy_id)
            return True
        except Exception as e:
            logger.error(f"戦略無効化エラー (ID: {strategy_id}): {e}")
            return False

    def get_active_strategies(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """アクティブな戦略を取得"""
        try:
            filters: Dict[str, Any] = {"is_active": True}
            if user_id:
                filters["user_id"] = user_id
            return self.table.select("*", **filters)
        except Exception as e:
            logger.error(f"アクティブ戦略取得エラー: {e}")
            return []


class TradesModel:
    """Tradesテーブルの操作を管理"""

    def __init__(self):
        self.connection = get_supabase_connection()
        self.table = SupabaseTable("trades", self.connection)

    def get_user_trades(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """ユーザーの取引履歴を取得"""
        try:
            trades = self.table.select("*", user_id=user_id)
            # 時間順でソート（最新が先頭）
            return sorted(trades, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        except Exception as e:
            logger.error(f"ユーザー取引履歴取得エラー (ID: {user_id}): {e}")
            return []

    def get_strategy_trades(self, strategy_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """戦略の取引履歴を取得"""
        try:
            trades = self.table.select("*", strategy_id=strategy_id)
            return sorted(trades, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        except Exception as e:
            logger.error(f"戦略取引履歴取得エラー (ID: {strategy_id}): {e}")
            return []

    def create_trade(
        self,
        user_id: str,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        type_: str,  # 'market', 'limit', etc.
        amount: float,
        price: float,
        exchange_id: str,
        strategy_id: Optional[str] = None,
        order_id: Optional[str] = None,
        fee: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """新しい取引を記録"""
        try:
            trade_data = {
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "type": type_,
                "amount": amount,
                "price": price,
                "exchange_id": exchange_id,
                "strategy_id": strategy_id,
                "order_id": order_id,
                "fee": fee,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return self.table.insert(trade_data)
        except Exception as e:
            logger.error(f"取引作成エラー: {e}")
            return None


class PositionsModel:
    """Positionsテーブルの操作を管理"""

    def __init__(self):
        self.connection = get_supabase_connection()
        self.table = SupabaseTable("positions", self.connection)

    def get_user_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーのポジション一覧を取得"""
        try:
            return self.table.select("*", user_id=user_id)
        except Exception as e:
            logger.error(f"ユーザーポジション取得エラー (ID: {user_id}): {e}")
            return []

    def get_position_by_symbol(self, user_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """シンボルでポジションを取得"""
        try:
            positions = self.table.select("*", user_id=user_id, symbol=symbol)
            return positions[0] if positions else None
        except Exception as e:
            logger.error(f"ポジション取得エラー (Symbol: {symbol}): {e}")
            return None

    def update_or_create_position(
        self, user_id: str, symbol: str, amount: float, average_entry_price: float
    ) -> Optional[Dict[str, Any]]:
        """ポジションを更新または作成"""
        try:
            existing = self.get_position_by_symbol(user_id, symbol)

            position_data = {
                "amount": amount,
                "average_entry_price": average_entry_price,
                "last_updated": datetime.utcnow().isoformat(),
            }

            if existing:
                # 更新
                return self.table.update(position_data, user_id=user_id, symbol=symbol)[0]
            else:
                # 新規作成
                position_data.update({"user_id": user_id, "symbol": symbol})
                return self.table.insert(position_data)

        except Exception as e:
            logger.error(f"ポジション更新/作成エラー: {e}")
            return None


class BacktestResultsModel:
    """BacktestResultsテーブルの操作を管理"""

    def __init__(self):
        self.connection = get_supabase_connection()
        self.table = SupabaseTable("backtest_results", self.connection)

    def get_strategy_backtests(self, strategy_id: str) -> List[Dict[str, Any]]:
        """戦略のバックテスト結果一覧を取得"""
        try:
            return self.table.select("*", strategy_id=strategy_id)
        except Exception as e:
            logger.error(f"戦略バックテスト取得エラー (ID: {strategy_id}): {e}")
            return []

    def create_backtest_result(
        self,
        user_id: str,
        strategy_id: str,
        start_period: str,
        end_period: str,
        results_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """バックテスト結果を保存"""
        try:
            backtest_data = {
                "user_id": user_id,
                "strategy_id": strategy_id,
                "start_period": start_period,
                "end_period": end_period,
                "results_data": results_data,
                "created_at": datetime.utcnow().isoformat(),
            }
            return self.table.insert(backtest_data)
        except Exception as e:
            logger.error(f"バックテスト結果作成エラー: {e}")
            return None


# モデルインスタンスのシングルトン
_strategies_model: Optional[StrategiesModel] = None
_trades_model: Optional[TradesModel] = None
_positions_model: Optional[PositionsModel] = None
_backtest_results_model: Optional[BacktestResultsModel] = None


def get_strategies_model() -> StrategiesModel:
    """Strategiesモデルのシングルトンインスタンスを取得"""
    global _strategies_model
    if _strategies_model is None:
        _strategies_model = StrategiesModel()
    return _strategies_model


def get_trades_model() -> TradesModel:
    """Tradesモデルのシングルトンインスタンスを取得"""
    global _trades_model
    if _trades_model is None:
        _trades_model = TradesModel()
    return _trades_model


def get_positions_model() -> PositionsModel:
    """Positionsモデルのシングルトンインスタンスを取得"""
    global _positions_model
    if _positions_model is None:
        _positions_model = PositionsModel()
    return _positions_model


def get_backtest_results_model() -> BacktestResultsModel:
    """BacktestResultsモデルのシングルトンインスタンスを取得"""
    global _backtest_results_model
    if _backtest_results_model is None:
        _backtest_results_model = BacktestResultsModel()
    return _backtest_results_model
