"""
MACD（Moving Average Convergence Divergence）戦略

MACD指標を利用したトレンドフォロー戦略
・MACD LineがSignal Lineを上抜けで買いシグナル
・MACD LineがSignal Lineを下抜けで売りシグナル
・ヒストグラムの変化も考慮
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ..base import BaseStrategy, Signal, TechnicalIndicators

logger = logging.getLogger(__name__)


class MACDStrategy(BaseStrategy):
    """MACD（移動平均収束拡散法）戦略

    トレンドフォロー系指標として、MACD線とシグナル線のクロスオーバーを利用
    ・MACD線 > シグナル線 で買いシグナル
    ・MACD線 < シグナル線 で売りシグナル
    ・ヒストグラムの方向性も考慮
    """

    def __init__(
        self,
        name: str = "MACD Strategy",
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        parameters: Optional[Dict[str, Any]] = None,
    ):
        # デフォルトパラメータ
        default_params = {
            "fast_period": 12,  # 短期EMA期間
            "slow_period": 26,  # 長期EMA期間
            "signal_period": 9,  # シグナル線EMA期間
            "volume_threshold": 0.8,  # 平均出来高の80%以上
            "histogram_confirmation": True,  # ヒストグラム確認を使用
            "stop_loss_pct": 0.03,  # 3%のストップロス
            "take_profit_pct": 0.06,  # 6%のテイクプロフィット
            "required_data_length": 100,
            "confirmation_bars": 2,  # シグナル確認に必要な足数
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, symbol, timeframe, default_params)

        # 戦略固有の状態
        self.last_macd_signal = None  # 'buy' or 'sell'
        self.signal_confirmation_count = 0
        self.prev_macd_line = None
        self.prev_signal_line = None

        logger.info(
            f"MACD Strategy initialized: fast={self.parameters['fast_period']}, "
            f"slow={self.parameters['slow_period']}, signal={self.parameters['signal_period']}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """MACD及び関連指標を計算"""
        if len(data) < self.parameters["required_data_length"]:
            return data

        try:
            # MACD指標を計算
            close_prices = data["close"].tolist()
            macd_result = TechnicalIndicators.macd(
                close_prices,
                self.parameters["fast_period"],
                self.parameters["slow_period"],
                self.parameters["signal_period"],
            )

            # MACD線、シグナル線、ヒストグラムを設定
            data["macd_line"] = macd_result["macd"]
            data["signal_line"] = macd_result["signal"]
            data["histogram"] = macd_result["histogram"]

            # 移動平均出来高（ボリューム分析用）
            volume_sma = TechnicalIndicators.sma(data["volume"].tolist(), 20)
            data["volume_sma"] = volume_sma

            # 価格の移動平均（トレンド確認用）
            price_sma = TechnicalIndicators.sma(close_prices, 20)
            data["price_sma"] = price_sma

            # MACDクロスオーバーの検出
            if hasattr(data, "rolling") and len(data) > 1:
                # pandasが利用可能な場合
                data["macd_above_signal"] = data["macd_line"] > data["signal_line"]
                data["macd_cross_above"] = (data["macd_line"] > data["signal_line"]) & (
                    data["macd_line"].shift(1) <= data["signal_line"].shift(1)
                )
                data["macd_cross_below"] = (data["macd_line"] < data["signal_line"]) & (
                    data["macd_line"].shift(1) >= data["signal_line"].shift(1)
                )
            else:
                # pandasが利用不可能な場合、手動で計算
                macd_above_signal = []
                macd_cross_above = []
                macd_cross_below = []

                for i in range(len(data)):
                    if isinstance(data["macd_line"], list):
                        macd_val = data["macd_line"][i]
                        signal_val = data["signal_line"][i]
                    else:
                        # DataFrameの場合
                        macd_val = (
                            data["macd_line"].iloc[i] if hasattr(data["macd_line"], "iloc") else data["macd_line"][i]
                        )
                        signal_val = (
                            data["signal_line"].iloc[i]
                            if hasattr(data["signal_line"], "iloc")
                            else data["signal_line"][i]
                        )

                    above = macd_val > signal_val
                    macd_above_signal.append(above)

                    if i > 0:
                        prev_macd = (
                            data["macd_line"][i - 1]
                            if isinstance(data["macd_line"], list)
                            else (
                                data["macd_line"].iloc[i - 1]
                                if hasattr(data["macd_line"], "iloc")
                                else data["macd_line"][i - 1]
                            )
                        )
                        prev_signal = (
                            data["signal_line"][i - 1]
                            if isinstance(data["signal_line"], list)
                            else (
                                data["signal_line"].iloc[i - 1]
                                if hasattr(data["signal_line"], "iloc")
                                else data["signal_line"][i - 1]
                            )
                        )

                        cross_above = above and (prev_macd <= prev_signal)
                        cross_below = not above and (prev_macd >= prev_signal)
                    else:
                        cross_above = False
                        cross_below = False

                    macd_cross_above.append(cross_above)
                    macd_cross_below.append(cross_below)

                data["macd_above_signal"] = macd_above_signal
                data["macd_cross_above"] = macd_cross_above
                data["macd_cross_below"] = macd_cross_below

            # ヒストグラムの変化方向
            if hasattr(data, "diff"):
                data["histogram_change"] = data["histogram"].diff()
            else:
                histogram_change = [0.0]  # 最初の値
                for i in range(1, len(data)):
                    prev_hist = (
                        data["histogram"][i - 1]
                        if isinstance(data["histogram"], list)
                        else data["histogram"].iloc[i - 1]
                    )
                    curr_hist = (
                        data["histogram"][i] if isinstance(data["histogram"], list) else data["histogram"].iloc[i]
                    )
                    histogram_change.append(curr_hist - prev_hist)
                data["histogram_change"] = histogram_change

            logger.debug(f"MACD calculated for {len(data)} data points")
            return data

        except Exception as e:
            logger.error(f"Error calculating MACD indicators: {e}")
            return data

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """MACDに基づいて売買シグナルを生成"""
        signals = []

        if len(data) < self.parameters["required_data_length"]:
            return signals

        try:
            # 最新データを取得
            current_idx = len(data) - 1
            current_data = data.iloc[current_idx] if hasattr(data, "iloc") else data[-1]

            # 必要な指標が存在するかチェック
            required_cols = ["macd_line", "signal_line", "histogram"]
            if hasattr(data, "columns"):
                for col in required_cols:
                    if col not in data.columns:
                        return signals

            # 値を取得（DataFrameまたはdict形式に対応）
            if hasattr(current_data, "get"):
                current_macd = current_data.get("macd_line", 0)
                current_signal = current_data.get("signal_line", 0)
                current_histogram = current_data.get("histogram", 0)
                current_price = current_data.get("close", 0)
                current_volume = current_data.get("volume", 0)
                avg_volume = current_data.get("volume_sma", current_volume)
                current_time = current_data.get("timestamp", datetime.now())
                macd_cross_above = current_data.get("macd_cross_above", False)
                macd_cross_below = current_data.get("macd_cross_below", False)
            else:
                # list形式での取得
                current_macd = current_data["macd_line"]
                current_signal = current_data["signal_line"]
                current_histogram = current_data["histogram"]
                current_price = current_data["close"]
                current_volume = current_data["volume"]
                avg_volume = current_data.get("volume_sma", current_volume)
                current_time = current_data.get("timestamp", datetime.now())
                macd_cross_above = current_data.get("macd_cross_above", False)
                macd_cross_below = current_data.get("macd_cross_below", False)

            # NaN値をチェック
            if pd.isna(current_macd) or pd.isna(current_signal) or pd.isna(current_histogram):
                return signals

            # ボリューム確認
            volume_ok = current_volume >= avg_volume * self.parameters["volume_threshold"]

            # ヒストグラム確認（設定されている場合）
            histogram_ok = True
            if self.parameters["histogram_confirmation"] and current_idx > 0:
                if hasattr(data, "iloc"):
                    prev_histogram = data.iloc[current_idx - 1]["histogram"]
                else:
                    prev_histogram = data[current_idx - 1]["histogram"]

                # ヒストグラムが改善方向にあるかチェック
                if current_macd > current_signal:  # 上昇トレンド期待
                    histogram_ok = current_histogram >= prev_histogram
                else:  # 下降トレンド期待
                    histogram_ok = current_histogram <= prev_histogram

            # 買いシグナル判定
            if macd_cross_above and volume_ok and histogram_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_macd_signal == "buy":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_macd_signal = "buy"

                # 確認期間を満たした場合にシグナル生成
                if self.signal_confirmation_count >= self.parameters["confirmation_bars"]:
                    strength = self._calculate_signal_strength(current_macd, current_signal, current_histogram, "buy")

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_long",
                        strength=strength,
                        price=current_price,
                        reason=f"MACD bullish crossover: MACD={current_macd:.4f} > Signal={current_signal:.4f}",
                    )
                    signals.append(signal)

                    logger.info(f"MACD Buy signal: MACD={current_macd:.4f}, Signal={current_signal:.4f}")

            # 売りシグナル判定
            elif macd_cross_below and volume_ok and histogram_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_macd_signal == "sell":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_macd_signal = "sell"

                # 確認期間を満たした場合にシグナル生成
                if self.signal_confirmation_count >= self.parameters["confirmation_bars"]:
                    strength = self._calculate_signal_strength(current_macd, current_signal, current_histogram, "sell")

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_short",
                        strength=strength,
                        price=current_price,
                        reason=f"MACD bearish crossover: MACD={current_macd:.4f} < Signal={current_signal:.4f}",
                    )
                    signals.append(signal)

                    logger.info(f"MACD Sell signal: MACD={current_macd:.4f}, Signal={current_signal:.4f}")

            # エグジットシグナル（既存ポジション向け）
            exit_signals = self._generate_exit_signals(data, current_idx)
            signals.extend(exit_signals)

            return signals

        except Exception as e:
            logger.error(f"Error generating MACD signals: {e}")
            return signals

    def _calculate_signal_strength(
        self, macd_line: float, signal_line: float, histogram: float, signal_type: str
    ) -> float:
        """シグナルの強度を計算"""
        base_strength = 1.0

        # MACD線とシグナル線の差が大きいほど強いシグナル
        line_diff = abs(macd_line - signal_line)
        diff_strength = min(1.0, line_diff * 100)  # 正規化

        # ヒストグラムの大きさも考慮
        histogram_strength = min(1.0, abs(histogram) * 50)

        # 総合強度計算
        total_strength = (diff_strength * 0.6 + histogram_strength * 0.4) * base_strength

        return min(1.0, max(0.3, total_strength))

    def _generate_exit_signals(self, data: pd.DataFrame, current_idx: int) -> List[Signal]:
        """エグジットシグナルを生成"""
        signals = []

        try:
            current_data = data.iloc[current_idx] if hasattr(data, "iloc") else data[current_idx]

            if hasattr(current_data, "get"):
                current_macd = current_data.get("macd_line", 0)
                current_signal = current_data.get("signal_line", 0)
                current_price = current_data.get("close", 0)
                current_time = current_data.get("timestamp", datetime.now())
                macd_cross_above = current_data.get("macd_cross_above", False)
                macd_cross_below = current_data.get("macd_cross_below", False)
            else:
                current_macd = current_data["macd_line"]
                current_signal = current_data["signal_line"]
                current_price = current_data["close"]
                current_time = current_data.get("timestamp", datetime.now())
                macd_cross_above = current_data.get("macd_cross_above", False)
                macd_cross_below = current_data.get("macd_cross_below", False)

            # ロングポジションのエグジット
            if self.state.is_long:
                # MACDが下向きクロスした場合
                if macd_cross_below:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_long",
                        strength=0.8,
                        price=current_price,
                        reason=f"MACD bearish crossover: MACD={current_macd:.4f} < Signal={current_signal:.4f}",
                    )
                    signals.append(signal)

            # ショートポジションのエグジット
            if self.state.is_short:
                # MACDが上向きクロスした場合
                if macd_cross_above:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_short",
                        strength=0.8,
                        price=current_price,
                        reason=f"MACD bullish crossover: MACD={current_macd:.4f} > Signal={current_signal:.4f}",
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error generating MACD exit signals: {e}")
            return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """戦略情報を取得"""
        return {
            "name": self.name,
            "type": "Trend Following",
            "category": "Momentum",
            "parameters": self.parameters,
            "description": "MACD based strategy for trend following using crossover signals",
            "indicators": ["MACD Line", "Signal Line", "Histogram", "Volume SMA"],
            "timeframes": ["15m", "1h", "4h", "1d"],
            "risk_level": "Medium",
        }
