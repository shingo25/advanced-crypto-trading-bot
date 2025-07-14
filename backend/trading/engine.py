"""
ライブトレーディングエンジン
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """注文タイプ"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(Enum):
    """注文状態"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class OrderSide(Enum):
    """注文方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """注文"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: float = 0.0
    filled_price: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    strategy_name: Optional[str] = None
    
    def is_filled(self) -> bool:
        """注文が完全に約定したかチェック"""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """注文がアクティブかチェック"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
    
    def update_status(self, status: OrderStatus, filled_amount: float = None, filled_price: float = None):
        """注文状態を更新"""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        
        if filled_amount is not None:
            self.filled_amount = filled_amount
        
        if filled_price is not None:
            self.filled_price = filled_price


@dataclass
class Position:
    """ポジション"""
    symbol: str
    side: OrderSide
    amount: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    strategy_name: Optional[str] = None
    
    def update_price(self, price: float):
        """価格を更新してPnLを計算"""
        self.current_price = price
        self.updated_at = datetime.now(timezone.utc)
        
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (price - self.entry_price) * self.amount
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.amount
    
    def get_market_value(self) -> float:
        """市場価値を取得"""
        return self.current_price * self.amount


class TradingEngine:
    """ライブトレーディングエンジン"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.order_counter = 0
        self.is_running = False
        self.exchange_adapters = {}
        self.strategies = {}
        self.price_data = {}
        
        # イベントハンドラー
        self.on_order_filled: Optional[Callable] = None
        self.on_position_opened: Optional[Callable] = None
        self.on_position_closed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 設定
        self.config = {
            'max_concurrent_orders': 10,
            'order_timeout': 300,  # 5分
            'price_update_interval': 1.0,  # 1秒
            'position_check_interval': 5.0,  # 5秒
            'enable_dry_run': True,  # デモモード
            'risk_limits': {
                'max_position_size': 10000.0,
                'max_daily_loss': 1000.0,
                'max_drawdown': 0.1
            }
        }
        
        # 統計
        self.stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'total_volume': 0.0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'start_time': None,
            'uptime': 0.0
        }
        
        logger.info("TradingEngine initialized")
    
    def add_exchange_adapter(self, name: str, adapter):
        """取引所アダプタを追加"""
        self.exchange_adapters[name] = adapter
        logger.info(f"Exchange adapter added: {name}")
    
    def add_strategy(self, name: str, strategy):
        """戦略を追加"""
        self.strategies[name] = strategy
        logger.info(f"Strategy added: {name}")
    
    def create_order(self, 
                    symbol: str,
                    side: OrderSide,
                    order_type: OrderType,
                    amount: float,
                    price: Optional[float] = None,
                    strategy_name: Optional[str] = None) -> Order:
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
            strategy_name=strategy_name
        )
        
        # バリデーション
        if not self._validate_order(order):
            order.update_status(OrderStatus.REJECTED)
            return order
        
        # 注文を保存
        self.orders[order_id] = order
        
        # 注文を実行
        if not self.config['enable_dry_run']:
            self._execute_order(order)
        else:
            # デモモードでは即座に約定
            self._simulate_order_fill(order)
        
        self.stats['total_orders'] += 1
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
        
        if not self.config['enable_dry_run']:
            # 実際の取引所で注文をキャンセル
            success = self._cancel_order_on_exchange(order)
            if not success:
                return False
        
        order.update_status(OrderStatus.CANCELLED)
        self.stats['cancelled_orders'] += 1
        logger.info(f"Order cancelled: {order_id}")
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """注文を取得"""
        return self.orders.get(order_id)
    
    def get_active_orders(self) -> List[Order]:
        """アクティブな注文を取得"""
        return [order for order in self.orders.values() if order.is_active()]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """ポジションを取得"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """すべてのポジションを取得"""
        return self.positions.copy()
    
    def close_position(self, symbol: str, strategy_name: Optional[str] = None) -> bool:
        """ポジションを閉じる"""
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return False
        
        position = self.positions[symbol]
        
        # 反対方向の注文を作成
        opposite_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
        
        order = self.create_order(
            symbol=symbol,
            side=opposite_side,
            order_type=OrderType.MARKET,
            amount=position.amount,
            strategy_name=strategy_name
        )
        
        if order.is_filled():
            # ポジションが存在するかチェック（_update_positionで削除されている可能性がある）
            if symbol in self.positions:
                # 実現損益を計算
                if position.side == OrderSide.BUY:
                    realized_pnl = (order.filled_price - position.entry_price) * position.amount
                else:
                    realized_pnl = (position.entry_price - order.filled_price) * position.amount
                
                self.stats['total_pnl'] += realized_pnl
                self.stats['daily_pnl'] += realized_pnl
                
                logger.info(f"Position closed: {symbol}, PnL: {realized_pnl:.2f}")
                
                # イベントハンドラーを呼び出し
                if self.on_position_closed:
                    self.on_position_closed(symbol, realized_pnl)
            
            return True
        
        return False
    
    def update_price(self, symbol: str, price: float):
        """価格を更新"""
        self.price_data[symbol] = {
            'price': price,
            'timestamp': datetime.now(timezone.utc)
        }
        
        # ポジションの未実現損益を更新
        if symbol in self.positions:
            self.positions[symbol].update_price(price)
    
    def _validate_order(self, order: Order) -> bool:
        """注文を検証"""
        
        # 数量チェック
        if order.amount <= 0:
            logger.error(f"Invalid order amount: {order.amount}")
            return False
        
        # 価格チェック
        if order.order_type == OrderType.LIMIT and (order.price is None or order.price <= 0):
            logger.error(f"Invalid limit order price: {order.price}")
            return False
        
        # リスク制限チェック
        if order.amount > self.config['risk_limits']['max_position_size']:
            logger.error(f"Order amount exceeds max position size: {order.amount}")
            return False
        
        # 同時注文数チェック
        active_orders = len(self.get_active_orders())
        if active_orders >= self.config['max_concurrent_orders']:
            logger.error(f"Too many active orders: {active_orders}")
            return False
        
        return True
    
    def _execute_order(self, order: Order):
        """注文を実行"""
        try:
            # 取引所アダプタを使用して注文を実行
            # 実際の実装では適切な取引所を選択
            exchange_name = "binance"  # デフォルト
            
            if exchange_name not in self.exchange_adapters:
                logger.error(f"Exchange adapter not found: {exchange_name}")
                order.update_status(OrderStatus.REJECTED)
                return
            
            adapter = self.exchange_adapters[exchange_name]
            
            # 注文を送信
            result = adapter.place_order(
                symbol=order.symbol,
                side=order.side.value,
                type=order.order_type.value,
                amount=order.amount,
                price=order.price
            )
            
            if result.get('success'):
                order.update_status(OrderStatus.FILLED)
                self._handle_order_fill(order)
            else:
                order.update_status(OrderStatus.REJECTED)
                logger.error(f"Order execution failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            order.update_status(OrderStatus.REJECTED)
            
            if self.on_error:
                self.on_error(f"Order execution error: {e}")
    
    def _simulate_order_fill(self, order: Order):
        """注文約定をシミュレート"""
        # デモモードでは現在価格で即座に約定
        if order.symbol in self.price_data:
            fill_price = self.price_data[order.symbol]['price']
        else:
            fill_price = order.price or 50000.0  # デフォルト価格
        
        order.update_status(OrderStatus.FILLED, order.amount, fill_price)
        self._handle_order_fill(order)
    
    def _handle_order_fill(self, order: Order):
        """注文約定の処理"""
        self.stats['filled_orders'] += 1
        self.stats['total_volume'] += order.amount
        
        # ポジションを更新
        self._update_position(order)
        
        # イベントハンドラーを呼び出し
        if self.on_order_filled:
            self.on_order_filled(order)
        
        logger.info(f"Order filled: {order.id} at {order.filled_price}")
    
    def _update_position(self, order: Order):
        """ポジションを更新"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # 新しいポジションを作成
            position = Position(
                symbol=symbol,
                side=order.side,
                amount=order.amount,
                entry_price=order.filled_price,
                current_price=order.filled_price,
                strategy_name=order.strategy_name
            )
            self.positions[symbol] = position
            
            # イベントハンドラーを呼び出し
            if self.on_position_opened:
                self.on_position_opened(position)
            
            logger.info(f"Position opened: {symbol} {order.side.value} {order.amount}")
        
        else:
            # 既存のポジションを更新
            position = self.positions[symbol]
            
            if position.side == order.side:
                # 同じ方向の注文：平均価格で統合
                total_value = (position.amount * position.entry_price) + (order.amount * order.filled_price)
                total_amount = position.amount + order.amount
                
                position.entry_price = total_value / total_amount
                position.amount = total_amount
                position.current_price = order.filled_price
                position.updated_at = datetime.now(timezone.utc)
                
            else:
                # 反対方向の注文：ポジションを削除
                if order.amount >= position.amount:
                    # 完全に決済
                    realized_pnl = position.unrealized_pnl
                    self.stats['total_pnl'] += realized_pnl
                    self.stats['daily_pnl'] += realized_pnl
                    
                    del self.positions[symbol]
                    
                    # イベントハンドラーを呼び出し
                    if self.on_position_closed:
                        self.on_position_closed(symbol, realized_pnl)
                    
                    logger.info(f"Position closed: {symbol}, PnL: {realized_pnl:.2f}")
                
                else:
                    # 部分的に決済
                    position.amount -= order.amount
                    position.updated_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Position partially closed: {symbol}, remaining: {position.amount}")
    
    def _cancel_order_on_exchange(self, order: Order) -> bool:
        """取引所で注文をキャンセル"""
        try:
            exchange_name = "binance"  # デフォルト
            
            if exchange_name not in self.exchange_adapters:
                logger.error(f"Exchange adapter not found: {exchange_name}")
                return False
            
            adapter = self.exchange_adapters[exchange_name]
            result = adapter.cancel_order(order.id, order.symbol)
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            return False
    
    async def start(self):
        """エンジンを開始"""
        if self.is_running:
            logger.warning("TradingEngine is already running")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        logger.info("TradingEngine started")
        
        # バックグラウンドタスクを開始
        await asyncio.gather(
            self._price_update_loop(),
            self._position_check_loop(),
            self._order_timeout_loop()
        )
    
    async def stop(self):
        """エンジンを停止"""
        if not self.is_running:
            logger.warning("TradingEngine is not running")
            return
        
        self.is_running = False
        
        # すべてのアクティブな注文をキャンセル
        active_orders = self.get_active_orders()
        for order in active_orders:
            self.cancel_order(order.id)
        
        logger.info("TradingEngine stopped")
    
    async def _price_update_loop(self):
        """価格更新ループ"""
        while self.is_running:
            try:
                # 価格データを更新
                for symbol in self.positions.keys():
                    if symbol in self.price_data:
                        # 実際の実装では取引所から価格を取得
                        pass
                
                await asyncio.sleep(self.config['price_update_interval'])
                
            except Exception as e:
                logger.error(f"Price update error: {e}")
                if self.on_error:
                    self.on_error(f"Price update error: {e}")
    
    async def _position_check_loop(self):
        """ポジションチェックループ"""
        while self.is_running:
            try:
                # ポジションをチェック
                for position in self.positions.values():
                    # リスク制限チェック
                    if position.unrealized_pnl < -self.config['risk_limits']['max_daily_loss']:
                        logger.warning(f"Position {position.symbol} exceeds daily loss limit")
                        self.close_position(position.symbol)
                
                await asyncio.sleep(self.config['position_check_interval'])
                
            except Exception as e:
                logger.error(f"Position check error: {e}")
                if self.on_error:
                    self.on_error(f"Position check error: {e}")
    
    async def _order_timeout_loop(self):
        """注文タイムアウトループ"""
        while self.is_running:
            try:
                current_time = datetime.now(timezone.utc)
                
                for order in self.get_active_orders():
                    time_diff = (current_time - order.created_at).total_seconds()
                    
                    if time_diff > self.config['order_timeout']:
                        logger.warning(f"Order timeout: {order.id}")
                        self.cancel_order(order.id)
                
                await asyncio.sleep(60)  # 1分間隔でチェック
                
            except Exception as e:
                logger.error(f"Order timeout check error: {e}")
                if self.on_error:
                    self.on_error(f"Order timeout check error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        if self.stats['start_time']:
            self.stats['uptime'] = (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds()
        
        return {
            'total_orders': self.stats['total_orders'],
            'filled_orders': self.stats['filled_orders'],
            'cancelled_orders': self.stats['cancelled_orders'],
            'fill_rate': self.stats['filled_orders'] / max(self.stats['total_orders'], 1),
            'total_volume': self.stats['total_volume'],
            'total_pnl': self.stats['total_pnl'],
            'daily_pnl': self.stats['daily_pnl'],
            'active_orders': len(self.get_active_orders()),
            'open_positions': len(self.positions),
            'uptime': self.stats['uptime'],
            'is_running': self.is_running
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """健全性状態を取得"""
        return {
            'is_running': self.is_running,
            'active_orders': len(self.get_active_orders()),
            'open_positions': len(self.positions),
            'total_pnl': self.stats['total_pnl'],
            'daily_pnl': self.stats['daily_pnl'],
            'uptime': self.stats['uptime'],
            'last_update': datetime.now(timezone.utc).isoformat()
        }
    
    def export_state(self) -> Dict[str, Any]:
        """エンジンの状態をエクスポート"""
        return {
            'orders': {
                order_id: {
                    'id': order.id,
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'order_type': order.order_type.value,
                    'amount': order.amount,
                    'price': order.price,
                    'status': order.status.value,
                    'filled_amount': order.filled_amount,
                    'filled_price': order.filled_price,
                    'created_at': order.created_at.isoformat(),
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                    'strategy_name': order.strategy_name
                }
                for order_id, order in self.orders.items()
            },
            'positions': {
                symbol: {
                    'symbol': position.symbol,
                    'side': position.side.value,
                    'amount': position.amount,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'unrealized_pnl': position.unrealized_pnl,
                    'realized_pnl': position.realized_pnl,
                    'created_at': position.created_at.isoformat(),
                    'updated_at': position.updated_at.isoformat() if position.updated_at else None,
                    'strategy_name': position.strategy_name
                }
                for symbol, position in self.positions.items()
            },
            'stats': self.stats.copy(),
            'config': self.config.copy()
        }