"""
RSI（Relative Strength Index）戦略

RSIを利用したオシレーター戦略
・RSI 30以下で買いシグナル（売られすぎ）
・RSI 70以上で売りシグナル（買われすぎ）
・ダイバージェンス検出による高精度エントリー
"""

import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..base import BaseStrategy, Signal, TechnicalIndicators

logger = logging.getLogger(__name__)


class RSIStrategy(BaseStrategy):
    """RSI（相対力指数）戦略

    オシレーター系指標として、買われすぎ・売られすぎを判定
    ・RSI < oversold_threshold で買いシグナル
    ・RSI > overbought_threshold で売りシグナル
    ・ダイバージェンス検出による高精度エントリー
    """

    def __init__(
        self,
        name: str = "RSI Strategy",
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        parameters: Optional[Dict[str, Any]] = None,
    ):
        # デフォルトパラメータ
        default_params = {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "volume_threshold": 0.8,  # 平均出来高の80%以上
            "divergence_detection": True,  # ダイバージェンス検出
            "stop_loss_pct": 0.03,  # 3%のストップロス
            "take_profit_pct": 0.06,  # 6%のテイクプロフィット
            "required_data_length": 50,
            "confirmation_bars": 2,  # シグナル確認に必要な足数
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, symbol, timeframe, default_params)

        # 戦略固有の状態
        self.last_rsi_signal = None  # 'buy' or 'sell'
        self.signal_confirmation_count = 0

        logger.info(
            f"RSI Strategy initialized: period={self.parameters['rsi_period']}, "
            f"oversold={self.parameters['oversold_threshold']}, "
            f"overbought={self.parameters['overbought_threshold']}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """RSI及び関連指標を計算"""
        if len(data) < self.parameters["required_data_length"]:
            return data

        try:
            # RSIを計算
            close_prices = data["close"].tolist()
            rsi_values = TechnicalIndicators.rsi(
                close_prices, self.parameters["rsi_period"]
            )
            data["rsi"] = rsi_values

            # 移動平均出来高（ボリューム分析用）
            volume_sma = TechnicalIndicators.sma(data["volume"].tolist(), 20)
            data["volume_sma"] = volume_sma

            # 価格の移動平均（トレンド確認用）
            price_sma = TechnicalIndicators.sma(close_prices, 20)
            data["price_sma"] = price_sma

            # RSIの移動平均（ノイズ軽減）
            if hasattr(data, "rolling") and len(rsi_values) > 0:
                # pandasが利用可能な場合
                data["rsi_sma"] = data["rsi"].rolling(window=3).mean()
            else:
                # pandasが利用不可能な場合
                rsi_sma = TechnicalIndicators.sma(rsi_values, 3)
                data["rsi_sma"] = rsi_sma

            logger.debug(f"RSI calculated for {len(data)} data points")
            return data

        except Exception as e:
            logger.error(f"Error calculating RSI indicators: {e}")
            return data

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """RSIに基づいて売買シグナルを生成"""
        signals = []

        if len(data) < self.parameters["required_data_length"]:
            return signals

        try:
            # 最新データを取得
            current_idx = len(data) - 1
            current_data = data.iloc[current_idx]

            # 必要な指標が存在するかチェック
            if "rsi" not in data.columns or pd.isna(current_data["rsi"]):
                return signals

            current_rsi = current_data["rsi"]
            current_price = current_data["close"]
            current_volume = current_data["volume"]
            avg_volume = current_data.get("volume_sma", current_volume)
            current_time = current_data.get("timestamp", datetime.now())

            # ボリューム確認
            volume_ok = (
                current_volume >= avg_volume * self.parameters["volume_threshold"]
            )

            # RSIベースのシグナル判定
            rsi_oversold = current_rsi <= self.parameters["oversold_threshold"]
            rsi_overbought = current_rsi >= self.parameters["overbought_threshold"]

            # ダイバージェンス検出（設定されている場合）
            divergence_signal = None
            if self.parameters["divergence_detection"] and len(data) >= 20:
                divergence_signal = self._detect_divergence(data, current_idx)

            # 買いシグナル判定
            if rsi_oversold and volume_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_rsi_signal == "buy":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_rsi_signal = "buy"

                # 確認期間を満たした場合にシグナル生成
                if (
                    self.signal_confirmation_count
                    >= self.parameters["confirmation_bars"]
                ):
                    strength = self._calculate_signal_strength(
                        current_rsi, "buy", divergence_signal
                    )

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_long",
                        strength=strength,
                        price=current_price,
                        reason=f"RSI oversold: {current_rsi:.2f} <= {self.parameters['oversold_threshold']}",
                    )
                    signals.append(signal)

                    logger.info(
                        f"RSI Buy signal generated: RSI={current_rsi:.2f}, price={current_price}"
                    )

            # 売りシグナル判定
            elif rsi_overbought and volume_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_rsi_signal == "sell":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_rsi_signal = "sell"

                # 確認期間を満たした場合にシグナル生成
                if (
                    self.signal_confirmation_count
                    >= self.parameters["confirmation_bars"]
                ):
                    strength = self._calculate_signal_strength(
                        current_rsi, "sell", divergence_signal
                    )

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_short",
                        strength=strength,
                        price=current_price,
                        reason=f"RSI overbought: {current_rsi:.2f} >= {self.parameters['overbought_threshold']}",
                    )
                    signals.append(signal)

                    logger.info(
                        f"RSI Sell signal generated: RSI={current_rsi:.2f}, price={current_price}"
                    )

            # エグジットシグナル（既存ポジション向け）
            exit_signals = self._generate_exit_signals(data, current_idx)
            signals.extend(exit_signals)

            return signals

        except Exception as e:
            logger.error(f"Error generating RSI signals: {e}")
            return signals

    def _calculate_signal_strength(
        self, rsi: float, signal_type: str, divergence_signal: Optional[str]
    ) -> float:
        """シグナルの強度を計算"""
        base_strength = 1.0

        if signal_type == "buy":
            # RSIが低いほど強いシグナル（0～1の範囲で正規化）
            if rsi <= self.parameters["oversold_threshold"]:
                # oversold_threshold以下の場合、より低い値ほど高い強度
                rsi_strength = (
                    0.5 + (self.parameters["oversold_threshold"] - rsi) / 60
                )  # 0.5~1.0
            else:
                rsi_strength = 0.3  # 閾値を超えている場合は低い強度
        else:
            # RSIが高いほど強いシグナル（0～1の範囲で正規化）
            if rsi >= self.parameters["overbought_threshold"]:
                # overbought_threshold以上の場合、より高い値ほど高い強度
                rsi_strength = (
                    0.5 + (rsi - self.parameters["overbought_threshold"]) / 60
                )  # 0.5~1.0
            else:
                rsi_strength = 0.3  # 閾値を超えていない場合は低い強度

        # ダイバージェンスがある場合は強度アップ
        if divergence_signal == signal_type:
            rsi_strength *= 1.2

        return min(1.0, base_strength * rsi_strength)

    def _detect_divergence(self, data: pd.DataFrame, current_idx: int) -> Optional[str]:
        """ダイバージェンスを検出"""
        try:
            # 過去20足分のデータを分析
            lookback = min(20, current_idx)
            if lookback < 10:
                return None

            recent_data = data.iloc[current_idx - lookback : current_idx + 1]

            # 価格とRSIの最高値・最安値を取得
            price_highs = recent_data["high"]
            price_lows = recent_data["low"]
            rsi_values = recent_data["rsi"]

            # ベアリッシュダイバージェンス（売りシグナル）
            # 価格は高値更新、RSIは高値を更新せず
            if len(price_highs) >= 2 and len(rsi_values) >= 2:
                price_trend_up = price_highs.iloc[-1] > price_highs.iloc[-10]
                rsi_trend_down = rsi_values.iloc[-1] < rsi_values.iloc[-10]

                if price_trend_up and rsi_trend_down:
                    return "sell"

            # ブリッシュダイバージェンス（買いシグナル）
            # 価格は安値更新、RSIは安値を更新せず
            if len(price_lows) >= 2 and len(rsi_values) >= 2:
                price_trend_down = price_lows.iloc[-1] < price_lows.iloc[-10]
                rsi_trend_up = rsi_values.iloc[-1] > rsi_values.iloc[-10]

                if price_trend_down and rsi_trend_up:
                    return "buy"

            return None

        except Exception as e:
            logger.debug(f"Divergence detection error: {e}")
            return None

    def _generate_exit_signals(
        self, data: pd.DataFrame, current_idx: int
    ) -> List[Signal]:
        """エグジットシグナルを生成"""
        signals = []

        try:
            current_data = data.iloc[current_idx]
            current_rsi = current_data["rsi"]
            current_price = current_data["close"]
            current_time = current_data.get("timestamp", datetime.now())

            # ロングポジションのエグジット
            if self.state.is_long:
                # RSIが中立ゾーンに戻った場合
                if current_rsi >= 50:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_long",
                        strength=0.7,
                        price=current_price,
                        reason=f"RSI neutralized: {current_rsi:.2f} >= 50",
                    )
                    signals.append(signal)

            # ショートポジションのエグジット
            if self.state.is_short:
                # RSIが中立ゾーンに戻った場合
                if current_rsi <= 50:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_short",
                        strength=0.7,
                        price=current_price,
                        reason=f"RSI neutralized: {current_rsi:.2f} <= 50",
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error generating exit signals: {e}")
            return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """戦略情報を取得"""
        return {
            "name": self.name,
            "type": "Oscillator",
            "category": "Mean Reversion",
            "parameters": self.parameters,
            "description": "RSI based strategy for identifying overbought and oversold conditions",
            "indicators": ["RSI", "Volume SMA", "Price SMA"],
            "timeframes": ["15m", "1h", "4h", "1d"],
            "risk_level": "Medium",
        }
