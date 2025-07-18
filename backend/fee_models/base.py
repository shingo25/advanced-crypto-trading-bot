from abc import ABC, abstractmethod
from typing import Dict
from enum import Enum


class TradeType(Enum):
    MAKER = "maker"
    TAKER = "taker"


class FeeModel(ABC):
    """手数料モデルの基底クラス"""

    @abstractmethod
    def calculate_fee(
        self,
        trade_type: TradeType,
        price: float,
        amount: float,
        symbol: str = "BTCUSDT",
    ) -> float:
        """手数料を計算"""
        pass

    @abstractmethod
    def calculate_slippage(
        self, price: float, amount: float, side: str, symbol: str = "BTCUSDT"
    ) -> float:
        """スリッページを計算"""
        pass


class SimpleFeeModel(FeeModel):
    """シンプルな手数料モデル"""

    def __init__(
        self,
        maker_fee: float = 0.0001,
        taker_fee: float = 0.0004,
        slippage_bps: float = 0.5,
    ):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_bps = slippage_bps / 10000  # bps to decimal

    def calculate_fee(
        self,
        trade_type: TradeType,
        price: float,
        amount: float,
        symbol: str = "BTCUSDT",
    ) -> float:
        """手数料を計算"""
        notional = price * amount

        if trade_type == TradeType.MAKER:
            return notional * self.maker_fee
        else:
            return notional * self.taker_fee

    def calculate_slippage(
        self, price: float, amount: float, side: str, symbol: str = "BTCUSDT"
    ) -> float:
        """スリッページを計算"""
        slippage_amount = price * self.slippage_bps

        if side.lower() == "buy":
            return slippage_amount
        else:
            return -slippage_amount


class VolumeBasedFeeModel(FeeModel):
    """出来高ベースの手数料モデル"""

    def __init__(
        self, fee_tiers: Dict[float, Dict[str, float]], base_slippage: float = 0.5
    ):
        """
        fee_tiers: {volume_threshold: {"maker": fee, "taker": fee}}
        """
        self.fee_tiers = fee_tiers
        self.base_slippage = base_slippage / 10000

    def calculate_fee(
        self,
        trade_type: TradeType,
        price: float,
        amount: float,
        symbol: str = "BTCUSDT",
    ) -> float:
        """出来高に基づいて手数料を計算"""
        notional = price * amount

        # 出来高に基づいて手数料ティアを決定
        # 実際の実装では、過去30日間の出来高を参照する
        volume_30d = self._get_30day_volume()  # TODO: 実装

        fee_rate = self._get_fee_rate(volume_30d, trade_type)
        return notional * fee_rate

    def calculate_slippage(
        self, price: float, amount: float, side: str, symbol: str = "BTCUSDT"
    ) -> float:
        """出来高に基づいてスリッページを計算"""
        # 大きな注文ほどスリッページが大きくなる
        size_factor = min(amount / 10.0, 2.0)  # 最大2倍
        slippage = self.base_slippage * size_factor

        slippage_amount = price * slippage

        if side.lower() == "buy":
            return slippage_amount
        else:
            return -slippage_amount

    def _get_30day_volume(self) -> float:
        """過去30日間の出来高を取得（TODO: 実装）"""
        return 0.0  # ダミー値

    def _get_fee_rate(self, volume: float, trade_type: TradeType) -> float:
        """出来高に基づいて手数料レートを取得"""
        # 出来高の大きい順にソート
        sorted_tiers = sorted(self.fee_tiers.items(), key=lambda x: x[0], reverse=True)

        for threshold, fees in sorted_tiers:
            if volume >= threshold:
                return fees[trade_type.value]

        # デフォルトの手数料
        return sorted_tiers[-1][1][trade_type.value]
