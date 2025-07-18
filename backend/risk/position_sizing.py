from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PositionSizer(ABC):
    """ポジションサイジングの基底クラス"""

    @abstractmethod
    def calculate_size(
        self,
        capital: float,
        signal_strength: float,
        volatility: float,
        win_rate: float = 0.5,
        avg_win: float = 0.01,
        avg_loss: float = 0.01,
    ) -> float:
        """ポジションサイズを計算"""
        pass


class FixedRiskSizer(PositionSizer):
    """固定リスク比率によるポジションサイジング"""

    def __init__(self, risk_pct: float = 0.02):
        self.risk_pct = risk_pct

    def calculate_size(
        self,
        capital: float,
        signal_strength: float,
        volatility: float,
        win_rate: float = 0.5,
        avg_win: float = 0.01,
        avg_loss: float = 0.01,
    ) -> float:
        """固定リスク比率でポジションサイズを計算"""
        risk_amount = capital * self.risk_pct
        # ボラティリティを考慮してサイズを調整
        position_size = risk_amount / (volatility * capital)
        return min(position_size, 0.2)  # 最大20%に制限


class KellyCriterionSizer(PositionSizer):
    """Kelly基準によるポジションサイジング"""

    def __init__(self, max_fraction: float = 0.5):
        self.max_fraction = max_fraction

    def calculate_size(
        self,
        capital: float,
        signal_strength: float,
        volatility: float,
        win_rate: float = 0.5,
        avg_win: float = 0.01,
        avg_loss: float = 0.01,
    ) -> float:
        """Kelly基準でポジションサイズを計算"""
        if avg_loss <= 0:
            return 0.0

        # Kelly fraction = (bp - q) / b
        # b = 勝ちの倍率, p = 勝率, q = 負け率
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # 信号強度を考慮
        kelly_fraction *= signal_strength

        # 上限を適用
        kelly_fraction = min(kelly_fraction, self.max_fraction)

        # 負の値は0に設定
        kelly_fraction = max(kelly_fraction, 0.0)

        logger.debug(f"Kelly fraction: {kelly_fraction:.4f}")
        return kelly_fraction


class VolatilityAdjustedSizer(PositionSizer):
    """ボラティリティ調整によるポジションサイジング"""

    def __init__(self, target_volatility: float = 0.15):
        self.target_volatility = target_volatility

    def calculate_size(
        self,
        capital: float,
        signal_strength: float,
        volatility: float,
        win_rate: float = 0.5,
        avg_win: float = 0.01,
        avg_loss: float = 0.01,
    ) -> float:
        """ボラティリティ調整でポジションサイズを計算"""
        if volatility <= 0:
            return 0.0

        # 目標ボラティリティに基づいてサイズを調整
        size = (self.target_volatility / volatility) * signal_strength

        # 最大20%に制限
        return min(size, 0.2)


class RiskManager:
    """リスク管理クラス"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.position_sizers = {
            "fixed": FixedRiskSizer(config.get("fixed_risk_per_trade", 0.02)),
            "kelly": KellyCriterionSizer(config.get("kelly_fraction_cap", 0.5)),
            "volatility": VolatilityAdjustedSizer(
                config.get("target_volatility", 0.15)
            ),
        }

    def calculate_position_size(
        self,
        strategy_name: str,
        capital: float,
        signal_strength: float,
        volatility: float,
        win_rate: float = 0.5,
        avg_win: float = 0.01,
        avg_loss: float = 0.01,
    ) -> float:
        """戦略に基づいてポジションサイズを計算"""

        # 戦略固有の設定を取得
        strategy_config = self.config.get("strategies", {}).get(strategy_name, {})
        sizing_method = strategy_config.get("position_sizing", "fixed")

        if sizing_method not in self.position_sizers:
            logger.warning(
                f"Unknown position sizing method: {sizing_method}, using fixed"
            )
            sizing_method = "fixed"

        sizer = self.position_sizers[sizing_method]
        position_size = sizer.calculate_size(
            capital=capital,
            signal_strength=signal_strength,
            volatility=volatility,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
        )

        # 最大ポジションサイズ制限
        max_position_size = self.config.get("max_position_size_pct", 0.1)
        position_size = min(position_size, max_position_size)

        logger.info(
            f"Position size calculated: {position_size:.4f} for {strategy_name}"
        )
        return position_size

    def check_drawdown_limit(self, current_equity: float, peak_equity: float) -> bool:
        """ドローダウン制限をチェック"""
        if peak_equity <= 0:
            return True

        drawdown = (peak_equity - current_equity) / peak_equity
        max_drawdown = self.config.get("max_drawdown_per_strategy", 0.15)

        if drawdown > max_drawdown:
            logger.warning(
                f"Drawdown limit exceeded: {drawdown:.4f} > {max_drawdown:.4f}"
            )
            return False

        return True
