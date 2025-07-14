from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """取引シグナル"""
    timestamp: datetime
    symbol: str
    action: str  # 'enter_long', 'exit_long', 'enter_short', 'exit_short'
    strength: float = 1.0
    price: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class StrategyState:
    """戦略の状態"""
    is_long: bool = False
    is_short: bool = False
    entry_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class BaseStrategy(ABC):
    """戦略の基底クラス"""
    
    def __init__(self, 
                 name: str,
                 symbol: str = "BTCUSDT",
                 timeframe: str = "1h",
                 parameters: Dict[str, Any] = None):
        
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.parameters = parameters or {}
        
        # 戦略の状態
        self.state = StrategyState()
        
        # 履歴データ
        self.data = [] if not HAS_PANDAS else pd.DataFrame()
        self.signals: List[Signal] = []
        
        # パフォーマンス追跡
        self.trades_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info(f"Strategy {name} initialized for {symbol} on {timeframe}")
    
    @abstractmethod
    def calculate_indicators(self, data):
        """テクニカル指標を計算"""
        pass
    
    @abstractmethod
    def generate_signals(self, data) -> List[Signal]:
        """売買シグナルを生成"""
        pass
    
    def update(self, ohlcv: Dict[str, Any]) -> Optional[Signal]:
        """新しいデータで戦略を更新"""
        
        if not HAS_PANDAS:
            logger.warning("Pandas not available, skipping data update")
            return None
        
        # 新しいデータを追加
        new_row = {
            'timestamp': ohlcv.get('timestamp', datetime.now()),
            'open': ohlcv['open'],
            'high': ohlcv['high'],
            'low': ohlcv['low'],
            'close': ohlcv['close'],
            'volume': ohlcv['volume']
        }
        
        # DataFrameに追加
        if len(self.data) == 0:
            self.data = pd.DataFrame([new_row])
        else:
            self.data = pd.concat([self.data, pd.DataFrame([new_row])], ignore_index=True)
        
        # 最新の一定期間のデータのみを保持
        max_length = self.parameters.get('max_history_length', 1000)
        if len(self.data) > max_length:
            self.data = self.data.tail(max_length).reset_index(drop=True)
        
        # 指標を計算
        self.data = self.calculate_indicators(self.data)
        
        # シグナルを生成
        signals = self.generate_signals(self.data)
        
        # 最新のシグナルを返す
        if signals:
            latest_signal = signals[-1]
            self.signals.append(latest_signal)
            return latest_signal
        
        return None
    
    def get_current_position(self) -> Dict[str, Any]:
        """現在のポジション情報を取得"""
        return {
            'is_long': self.state.is_long,
            'is_short': self.state.is_short,
            'entry_price': self.state.entry_price,
            'entry_time': self.state.entry_time,
            'unrealized_pnl': self.state.unrealized_pnl
        }
    
    def update_position(self, action: str, price: float, timestamp: datetime):
        """ポジションを更新"""
        
        if action == 'enter_long':
            self.state.is_long = True
            self.state.is_short = False
            self.state.entry_price = price
            self.state.entry_time = timestamp
            
        elif action == 'exit_long':
            if self.state.is_long:
                pnl = (price - self.state.entry_price) * 1.0  # 簡略化
                self._update_trade_stats(pnl)
                self.state.is_long = False
                self.state.entry_price = None
                self.state.entry_time = None
                
        elif action == 'enter_short':
            self.state.is_short = True
            self.state.is_long = False
            self.state.entry_price = price
            self.state.entry_time = timestamp
            
        elif action == 'exit_short':
            if self.state.is_short:
                pnl = (self.state.entry_price - price) * 1.0  # 簡略化
                self._update_trade_stats(pnl)
                self.state.is_short = False
                self.state.entry_price = None
                self.state.entry_time = None
    
    def _update_trade_stats(self, pnl: float):
        """取引統計を更新"""
        self.trades_count += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得"""
        win_rate = self.winning_trades / self.trades_count if self.trades_count > 0 else 0
        
        return {
            'total_trades': self.trades_count,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_signals': len(self.signals)
        }
    
    def reset(self):
        """戦略をリセット"""
        self.state = StrategyState()
        self.data = [] if not HAS_PANDAS else pd.DataFrame()
        self.signals = []
        self.trades_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info(f"Strategy {self.name} reset")
    
    def validate_parameters(self) -> bool:
        """パラメータの妥当性を検証"""
        # 基本的な検証
        if not self.name:
            logger.error("Strategy name is required")
            return False
        
        if not self.symbol:
            logger.error("Symbol is required")
            return False
        
        return True
    
    def get_required_data_length(self) -> int:
        """必要なデータ長を取得"""
        return self.parameters.get('required_data_length', 100)
    
    def can_generate_signals(self) -> bool:
        """シグナル生成が可能かチェック"""
        if not HAS_PANDAS:
            return False
        return len(self.data) >= self.get_required_data_length()


class TechnicalIndicators:
    """テクニカル指標の計算クラス"""
    
    @staticmethod
    def sma(data: Union[List[float], Any], period: int) -> Union[List[float], Any]:
        """単純移動平均"""
        if not HAS_PANDAS:
            result = []
            for i in range(len(data)):
                if i < period - 1:
                    result.append(0.0)
                else:
                    avg = sum(data[i-period+1:i+1]) / period
                    result.append(avg)
            return result
        
        # pandas版は元のまま
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: Union[List[float], Any], period: int) -> Union[List[float], Any]:
        """指数移動平均"""
        if not HAS_PANDAS:
            if len(data) < period:
                return [0.0] * len(data)
            
            result = []
            multiplier = 2 / (period + 1)
            
            # 最初の値はSMAで初期化
            sma = sum(data[:period]) / period
            result.extend([0.0] * (period - 1))
            result.append(sma)
            
            # EMAを計算
            for i in range(period, len(data)):
                ema_val = (data[i] * multiplier) + (result[i-1] * (1 - multiplier))
                result.append(ema_val)
            
            return result
        
        # pandas版は元のまま
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[float]:
        """RSI"""
        if not HAS_PANDAS:
            if len(data) < period + 1:
                return [0.0] * len(data)
            
            result = [0.0] * period
            gains = []
            losses = []
            
            # 価格変動を計算
            for i in range(1, len(data)):
                change = data[i] - data[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            # RSIを計算
            for i in range(period-1, len(gains)):
                if i == period - 1:
                    avg_gain = sum(gains[:period]) / period
                    avg_loss = sum(losses[:period]) / period
                else:
                    avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                    avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                
                if avg_loss == 0:
                    rsi_val = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi_val = 100 - (100 / (1 + rs))
                
                result.append(rsi_val)
            
            return result
        
        # pandas版は元のまま
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """MACD"""
        if not HAS_PANDAS:
            ema_fast = TechnicalIndicators.ema(data, fast)
            ema_slow = TechnicalIndicators.ema(data, slow)
            
            macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
            signal_line = TechnicalIndicators.ema(macd_line, signal)
            histogram = [m - s for m, s in zip(macd_line, signal_line)]
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        
        # pandas版は元のまま
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, List[float]]:
        """ボリンジャーバンド"""
        if not HAS_PANDAS:
            sma_values = TechnicalIndicators.sma(data, period)
            
            # 標準偏差を計算
            std_values = []
            for i in range(len(data)):
                if i < period - 1:
                    std_values.append(0.0)
                else:
                    window_data = data[i-period+1:i+1]
                    mean = sum(window_data) / period
                    variance = sum((x - mean) ** 2 for x in window_data) / period
                    std_values.append(variance ** 0.5)
            
            upper_band = [sma + (std * std_dev) for sma, std in zip(sma_values, std_values)]
            lower_band = [sma - (std * std_dev) for sma, std in zip(sma_values, std_values)]
            
            return {
                'sma': sma_values,
                'upper': upper_band,
                'lower': lower_band
            }
        
        # pandas版は元のまま
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'sma': sma,
            'upper': upper_band,
            'lower': lower_band
        }


class StrategyValidator:
    """戦略の検証クラス"""
    
    @staticmethod
    def validate_signals(signals: List[Signal]) -> bool:
        """シグナルの妥当性を検証"""
        
        if not signals:
            return True
        
        # 重複チェック
        timestamps = [s.timestamp for s in signals]
        if len(timestamps) != len(set(timestamps)):
            logger.error("Duplicate signal timestamps found")
            return False
        
        # シグナルの順序チェック
        for i in range(1, len(signals)):
            if signals[i].timestamp < signals[i-1].timestamp:
                logger.error("Signal timestamps are not in chronological order")
                return False
        
        # アクションの妥当性チェック
        valid_actions = ['enter_long', 'exit_long', 'enter_short', 'exit_short']
        for signal in signals:
            if signal.action not in valid_actions:
                logger.error(f"Invalid signal action: {signal.action}")
                return False
        
        return True
    
    @staticmethod
    def validate_position_logic(signals: List[Signal]) -> bool:
        """ポジションロジックの妥当性を検証"""
        
        position_state = {'long': False, 'short': False}
        
        for signal in signals:
            if signal.action == 'enter_long':
                if position_state['long']:
                    logger.error("Attempting to enter long position while already long")
                    return False
                if position_state['short']:
                    logger.error("Attempting to enter long position while short")
                    return False
                position_state['long'] = True
                
            elif signal.action == 'exit_long':
                if not position_state['long']:
                    logger.error("Attempting to exit long position while not long")
                    return False
                position_state['long'] = False
                
            elif signal.action == 'enter_short':
                if position_state['short']:
                    logger.error("Attempting to enter short position while already short")
                    return False
                if position_state['long']:
                    logger.error("Attempting to enter short position while long")
                    return False
                position_state['short'] = True
                
            elif signal.action == 'exit_short':
                if not position_state['short']:
                    logger.error("Attempting to exit short position while not short")
                    return False
                position_state['short'] = False
        
        return True
    
    @staticmethod
    def validate_data_requirements(strategy: BaseStrategy, data) -> bool:
        """データ要件の妥当性を検証"""
        
        if not HAS_PANDAS:
            logger.warning("Pandas not available, skipping data validation")
            return True
        
        if len(data) < strategy.get_required_data_length():
            logger.error(f"Insufficient data: required {strategy.get_required_data_length()}, got {len(data)}")
            return False
        
        # 必要な列の存在チェック
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        # データの妥当性チェック
        if data['high'].min() < 0 or data['low'].min() < 0:
            logger.error("Negative price values found")
            return False
        
        if (data['high'] < data['low']).any():
            logger.error("High price is lower than low price")
            return False
        
        if (data['close'] > data['high']).any() or (data['close'] < data['low']).any():
            logger.error("Close price is outside high-low range")
            return False
        
        return True