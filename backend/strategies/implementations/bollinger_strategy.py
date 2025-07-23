"""
Bollinger Bands戦略

ボリンジャーバンドを利用した平均回帰戦略
・価格が下部バンドを下回った後、バンド内に戻る時に買いシグナル
・価格が上部バンドを上回った後、バンド内に戻る時に売りシグナル
・バンド幅（ボラティリティ）とポジションも考慮
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ..base import BaseStrategy, Signal, TechnicalIndicators

logger = logging.getLogger(__name__)


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands戦略

    平均回帰系指標として、統計的な価格チャネルを利用
    ・価格がバンド外に出た後の反転を狙う
    ・バンド幅（ボラティリティ）も考慮
    ・%B（価格のバンド内位置）によるシグナル判定
    """

    def __init__(
        self,
        name: str = "Bollinger Bands Strategy",
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        parameters: Optional[Dict[str, Any]] = None,
    ):
        # デフォルトパラメータ
        default_params = {
            "bb_period": 20,  # ボリンジャーバンド期間
            "bb_std_dev": 2.0,  # 標準偏差倍数
            "volume_threshold": 0.8,  # 平均出来高の80%以上
            "bb_position_threshold": 0.8,  # %Bの閾値（0.8以上で上部バンド付近）
            "squeeze_threshold": 0.1,  # バンド幅が狭い時の閾値
            "stop_loss_pct": 0.02,  # 2%のストップロス
            "take_profit_pct": 0.04,  # 4%のテイクプロフィット
            "required_data_length": 60,
            "confirmation_bars": 2,  # シグナル確認に必要な足数
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, symbol, timeframe, default_params)

        # 戦略固有の状態
        self.last_bb_signal = None  # 'buy' or 'sell'
        self.signal_confirmation_count = 0
        self.last_squeeze_state = False  # 前回のスクイーズ状態

        logger.info(
            f"Bollinger Bands Strategy initialized: period={self.parameters['bb_period']}, "
            f"std_dev={self.parameters['bb_std_dev']}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Bollinger Bands及び関連指標を計算"""
        if len(data) < self.parameters["required_data_length"]:
            return data

        try:
            # Bollinger Bandsを計算
            close_prices = data["close"].tolist()
            bb_result = TechnicalIndicators.bollinger_bands(
                close_prices,
                self.parameters["bb_period"],
                self.parameters["bb_std_dev"],
            )

            # Bollinger Bands線を設定
            data["bb_upper"] = bb_result["upper"]
            data["bb_middle"] = bb_result["sma"]  # 中央線（SMA）
            data["bb_lower"] = bb_result["lower"]

            # %B（価格のバンド内位置）を計算
            # %B = (Close - Lower Band) / (Upper Band - Lower Band)
            bb_position = []
            for i in range(len(data)):
                upper = bb_result["upper"][i] if isinstance(bb_result["upper"], list) else bb_result["upper"].iloc[i]
                lower = bb_result["lower"][i] if isinstance(bb_result["lower"], list) else bb_result["lower"].iloc[i]
                close = close_prices[i]

                if upper != lower:  # ゼロ除算を避ける
                    position = (close - lower) / (upper - lower)
                else:
                    position = 0.5  # デフォルト値

                bb_position.append(position)

            data["bb_position"] = bb_position

            # バンド幅（正規化）を計算
            # Band Width = (Upper Band - Lower Band) / Middle Band
            bb_width = []
            for i in range(len(data)):
                upper = bb_result["upper"][i] if isinstance(bb_result["upper"], list) else bb_result["upper"].iloc[i]
                lower = bb_result["lower"][i] if isinstance(bb_result["lower"], list) else bb_result["lower"].iloc[i]
                middle = bb_result["sma"][i] if isinstance(bb_result["sma"], list) else bb_result["sma"].iloc[i]

                if middle != 0:  # ゼロ除算を避ける
                    width = (upper - lower) / middle
                else:
                    width = 0.0

                bb_width.append(width)

            data["bb_width"] = bb_width

            # スクイーズ検出（バンド幅が小さい状態）
            if len(bb_width) > 20:
                # 過去20期間の平均バンド幅と比較
                current_width = bb_width[-1]
                avg_width = sum(bb_width[-20:]) / 20
                data["bb_squeeze"] = [current_width < avg_width * self.parameters["squeeze_threshold"]] * len(data)
            else:
                data["bb_squeeze"] = [False] * len(data)

            # 移動平均出来高（ボリューム分析用）
            volume_sma = TechnicalIndicators.sma(data["volume"].tolist(), 20)
            data["volume_sma"] = volume_sma

            # 価格とバンドの関係
            price_above_upper = []
            price_below_lower = []
            price_inside_bands = []

            for i in range(len(data)):
                close = close_prices[i]
                upper = bb_result["upper"][i] if isinstance(bb_result["upper"], list) else bb_result["upper"].iloc[i]
                lower = bb_result["lower"][i] if isinstance(bb_result["lower"], list) else bb_result["lower"].iloc[i]

                price_above_upper.append(close > upper)
                price_below_lower.append(close < lower)
                price_inside_bands.append(lower <= close <= upper)

            data["price_above_upper"] = price_above_upper
            data["price_below_lower"] = price_below_lower
            data["price_inside_bands"] = price_inside_bands

            logger.debug(f"Bollinger Bands calculated for {len(data)} data points")
            return data

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands indicators: {e}")
            return data

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Bollinger Bandsに基づいて売買シグナルを生成"""
        signals = []

        if len(data) < self.parameters["required_data_length"]:
            return signals

        try:
            # 最新データを取得
            current_idx = len(data) - 1
            if hasattr(data, "iloc"):
                current_data = data.iloc[current_idx]
                prev_data = data.iloc[current_idx - 1] if current_idx > 0 else None
            else:
                current_data = data[current_idx]
                prev_data = data[current_idx - 1] if current_idx > 0 else None

            # 必要な指標が存在するかチェック
            required_cols = ["bb_upper", "bb_lower", "bb_middle", "bb_position"]
            if hasattr(data, "columns"):
                for col in required_cols:
                    if col not in data.columns:
                        return signals

            # 値を取得
            if hasattr(current_data, "get"):
                current_price = current_data.get("close", 0)
                current_bb_position = current_data.get("bb_position", 0.5)
                current_bb_width = current_data.get("bb_width", 0)
                current_volume = current_data.get("volume", 0)
                avg_volume = current_data.get("volume_sma", current_volume)
                current_time = current_data.get("timestamp", datetime.now())
                price_inside_bands = current_data.get("price_inside_bands", True)
                bb_squeeze = current_data.get("bb_squeeze", False)
                upper_band = current_data.get("bb_upper", current_price)
                lower_band = current_data.get("bb_lower", current_price)

                # 前回データ
                if prev_data is not None:
                    prev_price_above_upper = prev_data.get("price_above_upper", False)
                    prev_price_below_lower = prev_data.get("price_below_lower", False)
                else:
                    prev_price_above_upper = False
                    prev_price_below_lower = False
            else:
                # dict形式での取得
                current_price = current_data["close"]
                current_bb_position = current_data["bb_position"]
                current_bb_width = current_data["bb_width"]
                current_volume = current_data["volume"]
                avg_volume = current_data.get("volume_sma", current_volume)
                current_time = current_data.get("timestamp", datetime.now())
                price_inside_bands = current_data["price_inside_bands"]
                bb_squeeze = current_data.get("bb_squeeze", False)
                upper_band = current_data["bb_upper"]
                lower_band = current_data["bb_lower"]

                # 前回データ
                if prev_data is not None:
                    prev_price_above_upper = prev_data["price_above_upper"]
                    prev_price_below_lower = prev_data["price_below_lower"]
                else:
                    prev_price_above_upper = False
                    prev_price_below_lower = False

            # NaN値をチェック
            if pd.isna(current_bb_position) or pd.isna(current_bb_width) or pd.isna(upper_band) or pd.isna(lower_band):
                return signals

            # ボリューム確認
            volume_ok = current_volume >= avg_volume * self.parameters["volume_threshold"]

            # 買いシグナル判定
            # 条件：価格が下部バンドを下回った後、バンド内に戻る
            buy_condition = (
                prev_price_below_lower  # 前回は下部バンド外
                and price_inside_bands  # 現在はバンド内
                and current_bb_position < (1 - self.parameters["bb_position_threshold"])  # 下部寄り
            )

            if buy_condition and volume_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_bb_signal == "buy":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_bb_signal = "buy"

                # 確認期間を満たした場合にシグナル生成
                if self.signal_confirmation_count >= self.parameters["confirmation_bars"]:
                    strength = self._calculate_signal_strength(current_bb_position, current_bb_width, "buy", bb_squeeze)

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_long",
                        strength=strength,
                        price=current_price,
                        reason=f"BB bounce from lower band: %B={current_bb_position:.3f}, width={current_bb_width:.3f}",
                    )
                    signals.append(signal)

                    logger.info(f"BB Buy signal: %B={current_bb_position:.3f}, price={current_price}")

            # 売りシグナル判定
            # 条件：価格が上部バンドを上回った後、バンド内に戻る
            sell_condition = (
                prev_price_above_upper  # 前回は上部バンド外
                and price_inside_bands  # 現在はバンド内
                and current_bb_position > self.parameters["bb_position_threshold"]  # 上部寄り
            )

            if sell_condition and volume_ok:
                # 前回のシグナルと同じ場合は確認カウント
                if self.last_bb_signal == "sell":
                    self.signal_confirmation_count += 1
                else:
                    self.signal_confirmation_count = 1
                    self.last_bb_signal = "sell"

                # 確認期間を満たした場合にシグナル生成
                if self.signal_confirmation_count >= self.parameters["confirmation_bars"]:
                    strength = self._calculate_signal_strength(
                        current_bb_position, current_bb_width, "sell", bb_squeeze
                    )

                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="enter_short",
                        strength=strength,
                        price=current_price,
                        reason=f"BB bounce from upper band: %B={current_bb_position:.3f}, width={current_bb_width:.3f}",
                    )
                    signals.append(signal)

                    logger.info(f"BB Sell signal: %B={current_bb_position:.3f}, price={current_price}")

            # エグジットシグナル（既存ポジション向け）
            exit_signals = self._generate_exit_signals(data, current_idx)
            signals.extend(exit_signals)

            return signals

        except Exception as e:
            logger.error(f"Error generating Bollinger Bands signals: {e}")
            return signals

    def _calculate_signal_strength(self, bb_position: float, bb_width: float, signal_type: str, squeeze: bool) -> float:
        """シグナルの強度を計算"""
        base_strength = 1.0

        if signal_type == "buy":
            # %Bが低いほど（下部バンド寄り）強いシグナル
            position_strength = max(0.3, 1.0 - bb_position)
        else:
            # %Bが高いほど（上部バンド寄り）強いシグナル
            position_strength = max(0.3, bb_position)

        # バンド幅が狭い時（スクイーズ）は強いシグナル
        width_strength = 1.0
        if squeeze:
            width_strength = 1.3  # スクイーズ時はボーナス
        elif bb_width > 0.1:  # 通常のバンド幅
            width_strength = 1.0
        else:  # 狭いバンド幅
            width_strength = 1.1

        # 総合強度計算
        total_strength = position_strength * width_strength * base_strength

        return min(1.0, max(0.3, total_strength))

    def _generate_exit_signals(self, data: pd.DataFrame, current_idx: int) -> List[Signal]:
        """エグジットシグナルを生成"""
        signals = []

        try:
            if hasattr(data, "iloc"):
                current_data = data.iloc[current_idx]
            else:
                current_data = data[current_idx]

            if hasattr(current_data, "get"):
                current_bb_position = current_data.get("bb_position", 0.5)
                current_price = current_data.get("close", 0)
                current_time = current_data.get("timestamp", datetime.now())
            else:
                current_bb_position = current_data["bb_position"]
                current_price = current_data["close"]
                current_time = current_data.get("timestamp", datetime.now())

            # ロングポジションのエグジット
            if self.state.is_long:
                # %Bが中央より上（0.5以上）に戻った場合
                if current_bb_position >= 0.5:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_long",
                        strength=0.7,
                        price=current_price,
                        reason=f"BB position normalized: %B={current_bb_position:.3f} >= 0.5",
                    )
                    signals.append(signal)

            # ショートポジションのエグジット
            if self.state.is_short:
                # %Bが中央より下（0.5以下）に戻った場合
                if current_bb_position <= 0.5:
                    signal = Signal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="exit_short",
                        strength=0.7,
                        price=current_price,
                        reason=f"BB position normalized: %B={current_bb_position:.3f} <= 0.5",
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error generating BB exit signals: {e}")
            return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """戦略情報を取得"""
        return {
            "name": self.name,
            "type": "Mean Reversion",
            "category": "Statistical",
            "parameters": self.parameters,
            "description": "Bollinger Bands based strategy for mean reversion trading",
            "indicators": ["Bollinger Bands", "%B", "Band Width", "Volume SMA"],
            "timeframes": ["15m", "1h", "4h", "1d"],
            "risk_level": "Medium",
        }
