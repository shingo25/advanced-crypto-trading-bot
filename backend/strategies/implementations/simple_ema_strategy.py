from typing import Dict, Any, List, Optional
import logging

from ..base import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class SimpleEMAStrategy(BaseStrategy):
    """シンプルなEMA戦略（パッケージ依存なし）"""

    def __init__(
        self,
        name: str = "Simple EMA Strategy",
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        parameters: Optional[Dict[str, Any]] = None,
    ):
        # デフォルトパラメータ
        default_params = {
            "ema_fast": 12,
            "ema_slow": 26,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.06,
            "required_data_length": 50,
        }

        if parameters:
            default_params.update(parameters)

        super().__init__(name, symbol, timeframe, default_params)

        # シンプルなデータ保存用
        self.price_data: List[float] = []
        self.ema_fast_values: List[float] = []
        self.ema_slow_values: List[float] = []

        logger.info(
            f"Simple EMA Strategy initialized: fast={self.parameters['ema_fast']}, slow={self.parameters['ema_slow']}"
        )

    def calculate_indicators(self, data):
        """指標を計算（パッケージ依存なし）"""
        if not data:
            return data

        # 価格データを抽出
        if isinstance(data, list):
            prices = [item["close"] for item in data]
        else:
            # pandas DataFrame の場合
            prices = data["close"].tolist()

        # EMAを計算
        self.ema_fast_values = self._calculate_ema(prices, self.parameters["ema_fast"])
        self.ema_slow_values = self._calculate_ema(prices, self.parameters["ema_slow"])

        return data

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """EMAを計算"""
        if len(prices) < period:
            return [0.0] * len(prices)

        ema_values = []
        multiplier = 2 / (period + 1)

        # 最初の値はSMAで初期化
        sma = sum(prices[:period]) / period
        ema_values.extend([0.0] * (period - 1))
        ema_values.append(sma)

        # EMAを計算
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[i - 1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    def generate_signals(self, data) -> List[Signal]:
        """売買シグナルを生成"""
        signals: List[Signal] = []

        if not data or len(data) < self.parameters["required_data_length"]:
            return signals

        # データの最後から値を取得
        if isinstance(data, list):
            current_time = data[-1]["timestamp"]
            current_price = data[-1]["close"]
        else:
            # pandas DataFrame の場合
            current_time = data.iloc[-1]["timestamp"]
            current_price = data.iloc[-1]["close"]

        # EMAの値を取得
        if len(self.ema_fast_values) < 2 or len(self.ema_slow_values) < 2:
            return signals

        current_ema_fast = self.ema_fast_values[-1]
        current_ema_slow = self.ema_slow_values[-1]
        prev_ema_fast = self.ema_fast_values[-2]
        prev_ema_slow = self.ema_slow_values[-2]

        # ゴールデンクロス（買いシグナル）
        if (
            current_ema_fast > current_ema_slow
            and prev_ema_fast <= prev_ema_slow
            and not self.state.is_long
            and not self.state.is_short
        ):
            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action="enter_long",
                strength=1.0,
                price=current_price,
                reason="EMA Golden Cross",
            )
            signals.append(signal)

            # ストップロスとテイクプロフィットを設定
            self.state.stop_loss = current_price * (
                1 - self.parameters["stop_loss_pct"]
            )
            self.state.take_profit = current_price * (
                1 + self.parameters["take_profit_pct"]
            )

            logger.info(f"Long entry signal: {current_price:.2f}")

        # ロングイグジット条件
        elif self.state.is_long and (
            (current_ema_fast < current_ema_slow and prev_ema_fast >= prev_ema_slow)
            or current_price <= self.state.stop_loss
            or current_price >= self.state.take_profit
        ):
            exit_reason = "EMA Dead Cross"
            if current_price <= self.state.stop_loss:
                exit_reason = "Stop Loss"
            elif current_price >= self.state.take_profit:
                exit_reason = "Take Profit"

            signal = Signal(
                timestamp=current_time,
                symbol=self.symbol,
                action="exit_long",
                strength=1.0,
                price=current_price,
                reason=exit_reason,
            )
            signals.append(signal)

            logger.info(f"Long exit signal: {current_price:.2f} ({exit_reason})")

        return signals

    def get_current_analysis(self) -> Dict[str, Any]:
        """現在の分析結果を取得"""

        if len(self.ema_fast_values) < 1 or len(self.ema_slow_values) < 1:
            return {"status": "insufficient_data"}

        current_ema_fast = self.ema_fast_values[-1]
        current_ema_slow = self.ema_slow_values[-1]

        analysis = {
            "ema_fast": current_ema_fast,
            "ema_slow": current_ema_slow,
            "trend_direction": "bullish"
            if current_ema_fast > current_ema_slow
            else "bearish",
            "position": {
                "is_long": self.state.is_long,
                "is_short": self.state.is_short,
                "entry_price": self.state.entry_price,
                "stop_loss": self.state.stop_loss,
                "take_profit": self.state.take_profit,
            },
        }

        return analysis

    def get_required_data_length(self) -> int:
        """必要なデータ長を取得"""
        return max(
            self.parameters["ema_slow"] * 2, self.parameters["required_data_length"]
        )

    def validate_parameters(self) -> bool:
        """パラメータの妥当性を検証"""
        if not super().validate_parameters():
            return False

        # EMAパラメータの検証
        if self.parameters["ema_fast"] >= self.parameters["ema_slow"]:
            logger.error("Fast EMA period must be less than slow EMA period")
            return False

        if self.parameters["ema_fast"] <= 0 or self.parameters["ema_slow"] <= 0:
            logger.error("EMA periods must be positive")
            return False

        if (
            self.parameters["stop_loss_pct"] <= 0
            or self.parameters["take_profit_pct"] <= 0
        ):
            logger.error("Stop loss and take profit percentages must be positive")
            return False

        return True

    def reset(self):
        """戦略をリセット"""
        super().reset()
        self.price_data = []
        self.ema_fast_values = []
        self.ema_slow_values = []
        logger.info(f"Simple EMA Strategy {self.name} reset")
