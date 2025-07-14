import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

from backend.risk.position_sizing import RiskManager
from backend.fee_models.base import FeeModel, TradeType
from backend.fee_models.exchanges import FeeModelFactory

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """注文データ"""
    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    amount: float
    filled_price: Optional[float] = None
    filled_amount: Optional[float] = None
    fee: Optional[float] = None
    trade_id: Optional[str] = None


@dataclass
class Trade:
    """取引データ"""
    timestamp: datetime
    symbol: str
    side: OrderSide
    price: float
    amount: float
    fee: float
    realized_pnl: float
    strategy_name: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Position:
    """ポジションデータ"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: datetime
    
    def update_pnl(self, current_price: float):
        """未実現損益を更新"""
        self.current_price = current_price
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size


@dataclass
class Portfolio:
    """ポートフォリオデータ"""
    equity: float
    cash: float
    positions: Dict[str, Position]
    trades: List[Trade]
    
    def get_total_value(self) -> float:
        """総資産価値を計算"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.cash + total_unrealized


@dataclass
class BacktestResult:
    """バックテスト結果"""
    strategy_name: str
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: pd.DataFrame
    metrics: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)


class BacktestEngine:
    """バックテストエンジン"""
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005,
                 exchange: str = 'binance'):
        
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.exchange = exchange
        
        # 手数料モデル
        self.fee_model = FeeModelFactory.create(exchange)
        
        # ポートフォリオ
        self.portfolio = Portfolio(
            equity=initial_capital,
            cash=initial_capital,
            positions={},
            trades=[]
        )
        
        # 取引記録
        self.orders: List[Order] = []
        self.equity_curve: List[Dict[str, Any]] = []
        
        # リスク管理
        self.risk_manager = None
        
        # 統計情報
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'max_equity': initial_capital,
            'max_drawdown': 0.0,
            'peak_equity': initial_capital
        }
        
        logger.info(f"BacktestEngine initialized with capital: ${initial_capital:,.2f}")
    
    def set_risk_manager(self, risk_config: Dict[str, Any]):
        """リスク管理を設定"""
        self.risk_manager = RiskManager(risk_config)
    
    def process_bar(self, 
                   timestamp: datetime,
                   ohlcv: Dict[str, float],
                   signals: Dict[str, Any],
                   strategy_name: str):
        """バーデータを処理"""
        
        # 現在価格でポジションの未実現損益を更新
        current_price = ohlcv['close']
        symbol = signals.get('symbol', 'BTCUSDT')
        
        # 既存ポジションの更新
        if symbol in self.portfolio.positions:
            self.portfolio.positions[symbol].update_pnl(current_price)
        
        # シグナルの処理
        if signals.get('enter_long'):
            self._process_long_entry(timestamp, symbol, current_price, strategy_name)
        elif signals.get('enter_short'):
            self._process_short_entry(timestamp, symbol, current_price, strategy_name)
        elif signals.get('exit_long'):
            self._process_long_exit(timestamp, symbol, current_price, strategy_name)
        elif signals.get('exit_short'):
            self._process_short_exit(timestamp, symbol, current_price, strategy_name)
        
        # 資産価値の更新
        self.portfolio.equity = self.portfolio.get_total_value()
        
        # 統計情報の更新
        self._update_stats(timestamp)
        
        # 資産曲線の記録
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.portfolio.equity,
            'cash': self.portfolio.cash,
            'unrealized_pnl': sum(pos.unrealized_pnl for pos in self.portfolio.positions.values())
        })
    
    def _process_long_entry(self, 
                           timestamp: datetime,
                           symbol: str,
                           price: float,
                           strategy_name: str):
        """ロングエントリーを処理"""
        
        # 既にポジションがある場合はスキップ
        if symbol in self.portfolio.positions:
            return
        
        # ポジションサイズの計算
        position_size = self._calculate_position_size(symbol, price, strategy_name)
        
        if position_size <= 0:
            return
        
        # 必要な資金を計算
        required_capital = price * position_size
        
        # 現金が不足している場合はスキップ
        if self.portfolio.cash < required_capital:
            logger.warning(f"Insufficient cash for long entry: required ${required_capital:.2f}, available ${self.portfolio.cash:.2f}")
            return
        
        # スリッページを考慮した約定価格
        execution_price = price * (1 + self.slippage)
        
        # 手数料を計算
        fee = self.fee_model.calculate_fee(
            TradeType.TAKER,
            execution_price,
            position_size,
            symbol
        )
        
        # ポジションを作成
        position = Position(
            symbol=symbol,
            side=OrderSide.BUY,
            size=position_size,
            entry_price=execution_price,
            current_price=execution_price,
            unrealized_pnl=0.0,
            entry_time=timestamp
        )
        
        self.portfolio.positions[symbol] = position
        self.portfolio.cash -= (required_capital + fee)
        
        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.BUY,
            price=execution_price,
            amount=position_size,
            fee=fee,
            realized_pnl=0.0,
            strategy_name=strategy_name
        )
        
        self.portfolio.trades.append(trade)
        self.stats['total_trades'] += 1
        
        logger.info(f"Long entry: {symbol} @ ${execution_price:.2f}, size: {position_size:.6f}")
    
    def _process_long_exit(self, 
                          timestamp: datetime,
                          symbol: str,
                          price: float,
                          strategy_name: str):
        """ロングイグジットを処理"""
        
        if symbol not in self.portfolio.positions:
            return
        
        position = self.portfolio.positions[symbol]
        
        if position.side != OrderSide.BUY:
            return
        
        # スリッページを考慮した約定価格
        execution_price = price * (1 - self.slippage)
        
        # 手数料を計算
        fee = self.fee_model.calculate_fee(
            TradeType.TAKER,
            execution_price,
            position.size,
            symbol
        )
        
        # 損益を計算
        realized_pnl = (execution_price - position.entry_price) * position.size - fee
        
        # 現金を更新
        self.portfolio.cash += execution_price * position.size - fee
        
        # ポジションを削除
        del self.portfolio.positions[symbol]
        
        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.SELL,
            price=execution_price,
            amount=position.size,
            fee=fee,
            realized_pnl=realized_pnl,
            strategy_name=strategy_name
        )
        
        self.portfolio.trades.append(trade)
        
        # 統計情報の更新
        if realized_pnl > 0:
            self.stats['winning_trades'] += 1
        else:
            self.stats['losing_trades'] += 1
        
        logger.info(f"Long exit: {symbol} @ ${execution_price:.2f}, PnL: ${realized_pnl:.2f}")
    
    def _process_short_entry(self, 
                            timestamp: datetime,
                            symbol: str,
                            price: float,
                            strategy_name: str):
        """ショートエントリーを処理"""
        
        # 既にポジションがある場合はスキップ
        if symbol in self.portfolio.positions:
            return
        
        # ポジションサイズの計算
        position_size = self._calculate_position_size(symbol, price, strategy_name)
        
        if position_size <= 0:
            return
        
        # 証拠金の計算（簡略化）
        required_margin = price * position_size * 0.1  # 10倍レバレッジ想定
        
        # 証拠金が不足している場合はスキップ
        if self.portfolio.cash < required_margin:
            logger.warning(f"Insufficient margin for short entry: required ${required_margin:.2f}, available ${self.portfolio.cash:.2f}")
            return
        
        # スリッページを考慮した約定価格
        execution_price = price * (1 - self.slippage)
        
        # 手数料を計算
        fee = self.fee_model.calculate_fee(
            TradeType.TAKER,
            execution_price,
            position_size,
            symbol
        )
        
        # ポジションを作成
        position = Position(
            symbol=symbol,
            side=OrderSide.SELL,
            size=position_size,
            entry_price=execution_price,
            current_price=execution_price,
            unrealized_pnl=0.0,
            entry_time=timestamp
        )
        
        self.portfolio.positions[symbol] = position
        self.portfolio.cash -= fee
        
        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.SELL,
            price=execution_price,
            amount=position_size,
            fee=fee,
            realized_pnl=0.0,
            strategy_name=strategy_name
        )
        
        self.portfolio.trades.append(trade)
        self.stats['total_trades'] += 1
        
        logger.info(f"Short entry: {symbol} @ ${execution_price:.2f}, size: {position_size:.6f}")
    
    def _process_short_exit(self, 
                           timestamp: datetime,
                           symbol: str,
                           price: float,
                           strategy_name: str):
        """ショートイグジットを処理"""
        
        if symbol not in self.portfolio.positions:
            return
        
        position = self.portfolio.positions[symbol]
        
        if position.side != OrderSide.SELL:
            return
        
        # スリッページを考慮した約定価格
        execution_price = price * (1 + self.slippage)
        
        # 手数料を計算
        fee = self.fee_model.calculate_fee(
            TradeType.TAKER,
            execution_price,
            position.size,
            symbol
        )
        
        # 損益を計算
        realized_pnl = (position.entry_price - execution_price) * position.size - fee
        
        # 現金を更新
        self.portfolio.cash += realized_pnl
        
        # ポジションを削除
        del self.portfolio.positions[symbol]
        
        # 取引記録
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=OrderSide.BUY,
            price=execution_price,
            amount=position_size,
            fee=fee,
            realized_pnl=realized_pnl,
            strategy_name=strategy_name
        )
        
        self.portfolio.trades.append(trade)
        
        # 統計情報の更新
        if realized_pnl > 0:
            self.stats['winning_trades'] += 1
        else:
            self.stats['losing_trades'] += 1
        
        logger.info(f"Short exit: {symbol} @ ${execution_price:.2f}, PnL: ${realized_pnl:.2f}")
    
    def _calculate_position_size(self, 
                                symbol: str,
                                price: float,
                                strategy_name: str) -> float:
        """ポジションサイズを計算"""
        
        if self.risk_manager:
            # リスク管理を使用
            return self.risk_manager.calculate_position_size(
                strategy_name=strategy_name,
                capital=self.portfolio.equity,
                signal_strength=1.0,
                volatility=0.02,  # 簡略化
                win_rate=0.5,
                avg_win=0.01,
                avg_loss=0.01
            )
        else:
            # 固定サイズ（総資産の5%）
            return (self.portfolio.equity * 0.05) / price
    
    def _update_stats(self, timestamp: datetime):
        """統計情報を更新"""
        
        current_equity = self.portfolio.equity
        
        # 最大資産を更新
        if current_equity > self.stats['max_equity']:
            self.stats['max_equity'] = current_equity
            self.stats['peak_equity'] = current_equity
        
        # ドローダウンを計算
        if self.stats['peak_equity'] > 0:
            drawdown = (self.stats['peak_equity'] - current_equity) / self.stats['peak_equity']
            if drawdown > self.stats['max_drawdown']:
                self.stats['max_drawdown'] = drawdown
    
    def get_results(self, strategy_name: str) -> BacktestResult:
        """バックテスト結果を取得"""
        
        final_capital = self.portfolio.equity
        total_trades = len(self.portfolio.trades)
        winning_trades = self.stats['winning_trades']
        losing_trades = self.stats['losing_trades']
        
        # 基本統計
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # 資産曲線を DataFrame に変換
        equity_df = pd.DataFrame(self.equity_curve)
        
        # パフォーマンス指標を計算
        metrics = self._calculate_performance_metrics(equity_df)
        
        result = BacktestResult(
            strategy_name=strategy_name,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            annualized_return=metrics.get('annualized_return', 0.0),
            max_drawdown=self.stats['max_drawdown'],
            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics.get('sortino_ratio', 0.0),
            calmar_ratio=metrics.get('calmar_ratio', 0.0),
            profit_factor=metrics.get('profit_factor', 0.0),
            trades=self.portfolio.trades,
            equity_curve=equity_df,
            metrics=metrics
        )
        
        return result
    
    def _calculate_performance_metrics(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """パフォーマンス指標を計算"""
        
        if len(equity_df) < 2:
            return {}
        
        # リターン計算
        equity_df['returns'] = equity_df['equity'].pct_change()
        returns = equity_df['returns'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # 年間化係数（1時間足想定）
        periods_per_year = 365 * 24
        
        # 基本統計
        mean_return = returns.mean()
        std_return = returns.std()
        
        # 年間化リターン
        annualized_return = (1 + mean_return) ** periods_per_year - 1
        
        # シャープレシオ
        sharpe_ratio = (mean_return / std_return * np.sqrt(periods_per_year)) if std_return > 0 else 0
        
        # ソルティノレシオ
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
        sortino_ratio = (mean_return / downside_std * np.sqrt(periods_per_year)) if downside_std > 0 else 0
        
        # カルマーレシオ
        calmar_ratio = annualized_return / self.stats['max_drawdown'] if self.stats['max_drawdown'] > 0 else 0
        
        # プロフィットファクター
        winning_trades = [t for t in self.portfolio.trades if t.realized_pnl > 0]
        losing_trades = [t for t in self.portfolio.trades if t.realized_pnl < 0]
        
        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'profit_factor': profit_factor,
            'volatility': std_return * np.sqrt(periods_per_year),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
            'var_95': returns.quantile(0.05),
            'cvar_95': returns[returns <= returns.quantile(0.05)].mean()
        }
    
    def reset(self):
        """エンジンをリセット"""
        self.portfolio = Portfolio(
            equity=self.initial_capital,
            cash=self.initial_capital,
            positions={},
            trades=[]
        )
        
        self.orders = []
        self.equity_curve = []
        
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'max_equity': self.initial_capital,
            'max_drawdown': 0.0,
            'peak_equity': self.initial_capital
        }
        
        logger.info("BacktestEngine reset")
    
    def save_results(self, result: BacktestResult, output_dir: str = "results"):
        """結果を保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 取引履歴を保存
        trades_df = pd.DataFrame([trade.to_dict() for trade in result.trades])
        trades_file = output_path / f"{result.strategy_name}_trades.csv"
        trades_df.to_csv(trades_file, index=False)
        
        # 資産曲線を保存
        equity_file = output_path / f"{result.strategy_name}_equity.csv"
        result.equity_curve.to_csv(equity_file, index=False)
        
        # 結果サマリーを保存
        summary = {
            'strategy_name': result.strategy_name,
            'initial_capital': result.initial_capital,
            'final_capital': result.final_capital,
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'profit_factor': result.profit_factor
        }
        
        summary_file = output_path / f"{result.strategy_name}_summary.json"
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")