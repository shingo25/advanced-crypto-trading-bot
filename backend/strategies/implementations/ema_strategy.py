import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..base import BaseStrategy, Signal, TechnicalIndicators

logger = logging.getLogger(__name__)


class EMAStrategy(BaseStrategy):
    """EMA（指数移動平均）戦略
    
    短期EMAと長期EMAのクロスオーバーを利用したトレンドフォロー戦略
    ・ゴールデンクロス（短期EMA > 長期EMA）で買いシグナル
    ・デッドクロス（短期EMA < 長期EMA）で売りシグナル
    """
    
    def __init__(self, 
                 name: str = "EMA Strategy",
                 symbol: str = "BTCUSDT",
                 timeframe: str = "1h",
                 parameters: Dict[str, Any] = None):
        
        # デフォルトパラメータ
        default_params = {
            'ema_fast': 12,
            'ema_slow': 26,
            'volume_threshold': 0.8,  # 平均出来高の80%以上
            'trend_confirmation': True,  # トレンド確認を使用
            'stop_loss_pct': 0.02,  # 2%のストップロス
            'take_profit_pct': 0.06,  # 6%のテイクプロフィット
            'required_data_length': 50
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name, symbol, timeframe, default_params)
        
        # 戦略固有の状態
        self.last_cross_type = None  # 'golden' or 'dead'
        self.cross_confirmation_count = 0
        
        logger.info(f"EMA Strategy initialized: fast={self.parameters['ema_fast']}, slow={self.parameters['ema_slow']}")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標を計算"""
        
        if len(data) < self.parameters['required_data_length']:
            return data
        
        # EMAを計算
        data['ema_fast'] = TechnicalIndicators.ema(data['close'], self.parameters['ema_fast'])
        data['ema_slow'] = TechnicalIndicators.ema(data['close'], self.parameters['ema_slow'])
        
        # 出来高移動平均
        data['volume_sma'] = TechnicalIndicators.sma(data['volume'], 20)
        
        # トレンド強度の計算
        data['trend_strength'] = (data['ema_fast'] - data['ema_slow']) / data['ema_slow']
        
        # クロスオーバーの検出
        data['cross_above'] = (data['ema_fast'] > data['ema_slow']) & (data['ema_fast'].shift(1) <= data['ema_slow'].shift(1))
        data['cross_below'] = (data['ema_fast'] < data['ema_slow']) & (data['ema_fast'].shift(1) >= data['ema_slow'].shift(1))
        
        # トレンドフィルター
        if self.parameters['trend_confirmation']:
            # 長期EMAの傾き
            data['ema_slow_slope'] = data['ema_slow'].diff()
            data['uptrend'] = data['ema_slow_slope'] > 0
            data['downtrend'] = data['ema_slow_slope'] < 0
        else:
            data['uptrend'] = True
            data['downtrend'] = True
        
        # 出来高フィルター
        data['volume_filter'] = data['volume'] > (data['volume_sma'] * self.parameters['volume_threshold'])
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """売買シグナルを生成"""
        
        signals = []
        
        if len(data) < self.parameters['required_data_length']:
            return signals
        
        # 最新の行を取得
        current = data.iloc[-1]
        
        # 現在の時刻
        current_time = current['timestamp']
        current_price = current['close']
        
        # ロングエントリー条件
        if (current['cross_above'] and 
            current['uptrend'] and 
            current['volume_filter'] and
            not self.state.is_long and
            not self.state.is_short):
            
            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action='enter_long',
                strength=abs(current['trend_strength']),
                price=current_price,
                reason="EMA Golden Cross"
            )
            signals.append(signal)
            
            # ストップロスとテイクプロフィットを設定
            self.state.stop_loss = current_price * (1 - self.parameters['stop_loss_pct'])
            self.state.take_profit = current_price * (1 + self.parameters['take_profit_pct'])
            
            logger.info(f"Long entry signal: {current_price:.2f}")
        
        # ロングイグジット条件
        elif (self.state.is_long and 
              (current['cross_below'] or 
               current_price <= self.state.stop_loss or
               current_price >= self.state.take_profit)):
            
            exit_reason = "EMA Dead Cross"
            if current_price <= self.state.stop_loss:
                exit_reason = "Stop Loss"
            elif current_price >= self.state.take_profit:
                exit_reason = "Take Profit"
            
            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action='exit_long',
                strength=1.0,
                price=current_price,
                reason=exit_reason
            )
            signals.append(signal)
            
            logger.info(f"Long exit signal: {current_price:.2f} ({exit_reason})")
        
        # ショートエントリー条件（オプション）
        elif (current['cross_below'] and 
              current['downtrend'] and 
              current['volume_filter'] and
              not self.state.is_long and
              not self.state.is_short and
              self.parameters.get('allow_short', False)):
            
            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action='enter_short',
                strength=abs(current['trend_strength']),
                price=current_price,
                reason="EMA Dead Cross"
            )
            signals.append(signal)
            
            # ストップロスとテイクプロフィットを設定
            self.state.stop_loss = current_price * (1 + self.parameters['stop_loss_pct'])
            self.state.take_profit = current_price * (1 - self.parameters['take_profit_pct'])
            
            logger.info(f"Short entry signal: {current_price:.2f}")
        
        # ショートイグジット条件
        elif (self.state.is_short and 
              (current['cross_above'] or 
               current_price >= self.state.stop_loss or
               current_price <= self.state.take_profit)):
            
            exit_reason = "EMA Golden Cross"
            if current_price >= self.state.stop_loss:
                exit_reason = "Stop Loss"
            elif current_price <= self.state.take_profit:
                exit_reason = "Take Profit"
            
            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action='exit_short',
                strength=1.0,
                price=current_price,
                reason=exit_reason
            )
            signals.append(signal)
            
            logger.info(f"Short exit signal: {current_price:.2f} ({exit_reason})")
        
        return signals
    
    def get_current_analysis(self) -> Dict[str, Any]:
        """現在の分析結果を取得"""
        
        if len(self.data) < self.parameters['required_data_length']:
            return {'status': 'insufficient_data'}
        
        current = self.data.iloc[-1]
        
        analysis = {
            'timestamp': current['timestamp'],
            'price': current['close'],
            'ema_fast': current['ema_fast'],
            'ema_slow': current['ema_slow'],
            'trend_strength': current['trend_strength'],
            'trend_direction': 'bullish' if current['ema_fast'] > current['ema_slow'] else 'bearish',
            'volume_filter': current['volume_filter'],
            'uptrend': current['uptrend'],
            'position': {
                'is_long': self.state.is_long,
                'is_short': self.state.is_short,
                'entry_price': self.state.entry_price,
                'stop_loss': self.state.stop_loss,
                'take_profit': self.state.take_profit
            }
        }
        
        # 直近のクロスオーバーを検出
        if current['cross_above']:
            analysis['recent_cross'] = 'golden'
        elif current['cross_below']:
            analysis['recent_cross'] = 'dead'
        else:
            analysis['recent_cross'] = None
        
        return analysis
    
    def get_required_data_length(self) -> int:
        """必要なデータ長を取得"""
        return max(
            self.parameters['ema_slow'] * 2,
            self.parameters['required_data_length']
        )
    
    def optimize_parameters(self, data: pd.DataFrame, metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """パラメータを最適化"""
        
        from itertools import product
        
        # 最適化範囲
        fast_range = range(5, 25, 2)
        slow_range = range(20, 60, 5)
        
        best_params = None
        best_score = float('-inf')
        
        for fast, slow in product(fast_range, slow_range):
            if fast >= slow:
                continue
            
            # パラメータを設定
            test_params = self.parameters.copy()
            test_params['ema_fast'] = fast
            test_params['ema_slow'] = slow
            
            # バックテストを実行
            try:
                score = self._backtest_with_params(data, test_params, metric)
                
                if score > best_score:
                    best_score = score
                    best_params = test_params
                    
            except Exception as e:
                logger.error(f"Error in parameter optimization: {e}")
                continue
        
        if best_params:
            logger.info(f"Best parameters found: {best_params}, score: {best_score:.4f}")
            return best_params
        else:
            logger.warning("Parameter optimization failed")
            return self.parameters
    
    def _backtest_with_params(self, data: pd.DataFrame, params: Dict[str, Any], metric: str) -> float:
        """パラメータでバックテストを実行して評価値を返す"""
        
        # 簡易バックテスト（実際の実装では BacktestEngine を使用）
        temp_strategy = EMAStrategy(
            name=f"temp_{self.name}",
            symbol=self.symbol,
            timeframe=self.timeframe,
            parameters=params
        )
        
        # データを処理
        temp_data = temp_strategy.calculate_indicators(data.copy())
        
        # シンプルなリターン計算
        returns = []
        position = 0
        entry_price = 0
        
        for i in range(len(temp_data)):
            if i < params['required_data_length']:
                continue
            
            row = temp_data.iloc[i]
            
            # ロングエントリー
            if (row['cross_above'] and 
                row['uptrend'] and 
                row['volume_filter'] and
                position == 0):
                
                position = 1
                entry_price = row['close']
                
            # ロングイグジット
            elif (position == 1 and 
                  (row['cross_below'] or 
                   row['close'] <= entry_price * (1 - params['stop_loss_pct']) or
                   row['close'] >= entry_price * (1 + params['take_profit_pct']))):
                
                exit_return = (row['close'] - entry_price) / entry_price
                returns.append(exit_return)
                position = 0
                entry_price = 0
        
        # 評価指標を計算
        if not returns:
            return 0.0
        
        returns = np.array(returns)
        
        if metric == 'sharpe_ratio':
            return np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
        elif metric == 'total_return':
            return np.sum(returns)
        elif metric == 'win_rate':
            return np.mean(returns > 0)
        else:
            return np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0