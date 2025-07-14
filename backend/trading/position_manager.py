"""
ポジション管理クラス
"""
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone, timedelta
from .engine import Position, Order, OrderSide

logger = logging.getLogger(__name__)


class PositionManager:
    """ポジション管理クラス"""
    
    def __init__(self, config: Dict = None):
        self.positions: Dict[str, Position] = {}
        self.config = config or {}
        self.price_data = {}
        
        # イベントハンドラー
        self.on_position_opened: Optional[Callable] = None
        self.on_position_closed: Optional[Callable] = None
        self.on_position_updated: Optional[Callable] = None
        self.on_risk_limit_exceeded: Optional[Callable] = None
        
        # 統計
        self.stats = {
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'max_drawdown': 0.0,
            'positions_opened': 0,
            'positions_closed': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'last_reset_time': datetime.now(timezone.utc)
        }
        
        logger.info("PositionManager initialized")
    
    def update_position(self, order: Order) -> Optional[Position]:
        """注文に基づいてポジションを更新"""
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
            self.stats['positions_opened'] += 1
            
            if self.on_position_opened:
                self.on_position_opened(position)
            
            logger.info(f"Position opened: {symbol} {order.side.value} {order.amount}")
            return position
        
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
                
                if self.on_position_updated:
                    self.on_position_updated(position)
                
                logger.info(f"Position increased: {symbol}, new amount: {position.amount}")
                return position
            
            else:
                # 反対方向の注文：ポジションを削除または縮小
                if order.amount >= position.amount:
                    # 完全に決済
                    realized_pnl = self._calculate_realized_pnl(position, order.filled_price)
                    self._update_pnl_stats(realized_pnl)
                    
                    del self.positions[symbol]
                    self.stats['positions_closed'] += 1
                    
                    if realized_pnl > 0:
                        self.stats['winning_positions'] += 1
                    else:
                        self.stats['losing_positions'] += 1
                    
                    if self.on_position_closed:
                        self.on_position_closed(symbol, realized_pnl)
                    
                    logger.info(f"Position closed: {symbol}, PnL: {realized_pnl:.2f}")
                    return None
                
                else:
                    # 部分的に決済
                    partial_pnl = self._calculate_partial_pnl(position, order.amount, order.filled_price)
                    self._update_pnl_stats(partial_pnl)
                    
                    position.amount -= order.amount
                    position.updated_at = datetime.now(timezone.utc)
                    
                    if self.on_position_updated:
                        self.on_position_updated(position)
                    
                    logger.info(f"Position partially closed: {symbol}, remaining: {position.amount}, PnL: {partial_pnl:.2f}")
                    return position
    
    def close_position(self, symbol: str) -> Optional[float]:
        """ポジションを強制的に閉じる"""
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # 現在価格で決済
        current_price = self.price_data.get(symbol, {}).get('price', position.current_price)
        realized_pnl = self._calculate_realized_pnl(position, current_price)
        self._update_pnl_stats(realized_pnl)
        
        del self.positions[symbol]
        self.stats['positions_closed'] += 1
        
        if realized_pnl > 0:
            self.stats['winning_positions'] += 1
        else:
            self.stats['losing_positions'] += 1
        
        if self.on_position_closed:
            self.on_position_closed(symbol, realized_pnl)
        
        logger.info(f"Position force closed: {symbol}, PnL: {realized_pnl:.2f}")
        return realized_pnl
    
    def update_price(self, symbol: str, price: float):
        """価格を更新"""
        self.price_data[symbol] = {
            'price': price,
            'timestamp': datetime.now(timezone.utc)
        }
        
        # ポジションの未実現損益を更新
        if symbol in self.positions:
            position = self.positions[symbol]
            old_pnl = position.unrealized_pnl
            position.update_price(price)
            
            # 未実現損益の統計を更新
            self._update_unrealized_pnl_stats()
            
            # リスク制限チェック
            self._check_risk_limits(position)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """ポジションを取得"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """すべてのポジションを取得"""
        return self.positions.copy()
    
    def get_positions_by_strategy(self, strategy_name: str) -> List[Position]:
        """戦略別のポジションを取得"""
        return [pos for pos in self.positions.values() if pos.strategy_name == strategy_name]
    
    def get_total_exposure(self) -> float:
        """総エクスポージャーを取得"""
        total_exposure = 0.0
        for position in self.positions.values():
            total_exposure += position.get_market_value()
        return total_exposure
    
    def get_total_unrealized_pnl(self) -> float:
        """総未実現損益を取得"""
        total_pnl = 0.0
        for position in self.positions.values():
            total_pnl += position.unrealized_pnl
        return total_pnl
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """ポジション要約を取得"""
        summary = {
            'total_positions': len(self.positions),
            'long_positions': 0,
            'short_positions': 0,
            'total_exposure': 0.0,
            'total_unrealized_pnl': 0.0,
            'positions': []
        }
        
        for position in self.positions.values():
            if position.side == OrderSide.BUY:
                summary['long_positions'] += 1
            else:
                summary['short_positions'] += 1
            
            summary['total_exposure'] += position.get_market_value()
            summary['total_unrealized_pnl'] += position.unrealized_pnl
            
            summary['positions'].append({
                'symbol': position.symbol,
                'side': position.side.value,
                'amount': position.amount,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'unrealized_pnl': position.unrealized_pnl,
                'market_value': position.get_market_value(),
                'strategy_name': position.strategy_name
            })
        
        return summary
    
    def reset_daily_stats(self):
        """日次統計をリセット"""
        self.stats['daily_pnl'] = 0.0
        self.stats['last_reset_time'] = datetime.now(timezone.utc)
        logger.info("Daily statistics reset")
    
    def _calculate_realized_pnl(self, position: Position, exit_price: float) -> float:
        """実現損益を計算"""
        if position.side == OrderSide.BUY:
            return (exit_price - position.entry_price) * position.amount
        else:
            return (position.entry_price - exit_price) * position.amount
    
    def _calculate_partial_pnl(self, position: Position, amount: float, exit_price: float) -> float:
        """部分決済の実現損益を計算"""
        if position.side == OrderSide.BUY:
            return (exit_price - position.entry_price) * amount
        else:
            return (position.entry_price - exit_price) * amount
    
    def _update_pnl_stats(self, realized_pnl: float):
        """PnL統計を更新"""
        self.stats['total_pnl'] += realized_pnl
        self.stats['daily_pnl'] += realized_pnl
        self.stats['realized_pnl'] += realized_pnl
        
        # 最大ドローダウンの更新
        if realized_pnl < 0:
            current_drawdown = abs(realized_pnl) / max(self.stats['total_pnl'], 1000.0)
            self.stats['max_drawdown'] = max(self.stats['max_drawdown'], current_drawdown)
    
    def _update_unrealized_pnl_stats(self):
        """未実現損益統計を更新"""
        self.stats['unrealized_pnl'] = self.get_total_unrealized_pnl()
    
    def _check_risk_limits(self, position: Position):
        """リスク制限をチェック"""
        risk_limits = self.config.get('risk_limits', {})
        
        # 日次損失制限
        max_daily_loss = risk_limits.get('max_daily_loss', 1000.0)
        if self.stats['daily_pnl'] < -max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: {self.stats['daily_pnl']}")
            if self.on_risk_limit_exceeded:
                self.on_risk_limit_exceeded('daily_loss', position)
        
        # ポジションサイズ制限
        max_position_size = risk_limits.get('max_position_size', 10000.0)
        if position.get_market_value() > max_position_size:
            logger.warning(f"Position size limit exceeded: {position.symbol}")
            if self.on_risk_limit_exceeded:
                self.on_risk_limit_exceeded('position_size', position)
        
        # 最大ドローダウン制限
        max_drawdown = risk_limits.get('max_drawdown', 0.1)
        if self.stats['max_drawdown'] > max_drawdown:
            logger.warning(f"Max drawdown exceeded: {self.stats['max_drawdown']}")
            if self.on_risk_limit_exceeded:
                self.on_risk_limit_exceeded('max_drawdown', position)
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            'total_positions': len(self.positions),
            'total_pnl': self.stats['total_pnl'],
            'daily_pnl': self.stats['daily_pnl'],
            'realized_pnl': self.stats['realized_pnl'],
            'unrealized_pnl': self.stats['unrealized_pnl'],
            'max_drawdown': self.stats['max_drawdown'],
            'positions_opened': self.stats['positions_opened'],
            'positions_closed': self.stats['positions_closed'],
            'winning_positions': self.stats['winning_positions'],
            'losing_positions': self.stats['losing_positions'],
            'win_rate': self.stats['winning_positions'] / max(self.stats['positions_closed'], 1),
            'total_exposure': self.get_total_exposure(),
            'last_reset_time': self.stats['last_reset_time'].isoformat()
        }