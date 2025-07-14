from .base import FeeModel, TradeType
from typing import Dict


class BinanceFeeModel(FeeModel):
    """Binance手数料モデル"""
    
    def __init__(self):
        # Binanceの手数料構造（VIP0レベル）
        self.maker_fee = 0.001  # 0.1%
        self.taker_fee = 0.001  # 0.1%
        self.slippage_bps = 0.5  # 0.05%
    
    def calculate_fee(self, 
                     trade_type: TradeType,
                     price: float,
                     amount: float,
                     symbol: str = "BTCUSDT") -> float:
        """Binance手数料を計算"""
        notional = price * amount
        
        # スポット取引の場合
        if trade_type == TradeType.MAKER:
            return notional * self.maker_fee
        else:
            return notional * self.taker_fee
    
    def calculate_slippage(self,
                          price: float,
                          amount: float,
                          side: str,
                          symbol: str = "BTCUSDT") -> float:
        """Binanceスリッページを計算"""
        slippage_amount = price * (self.slippage_bps / 10000)
        
        if side.lower() == "buy":
            return slippage_amount
        else:
            return -slippage_amount


class BybitFeeModel(FeeModel):
    """Bybit手数料モデル"""
    
    def __init__(self):
        # Bybitの手数料構造
        self.maker_fee = 0.0001  # 0.01%
        self.taker_fee = 0.0006  # 0.06%
        self.slippage_bps = 0.3  # 0.03%
    
    def calculate_fee(self, 
                     trade_type: TradeType,
                     price: float,
                     amount: float,
                     symbol: str = "BTCUSDT") -> float:
        """Bybit手数料を計算"""
        notional = price * amount
        
        if trade_type == TradeType.MAKER:
            return notional * self.maker_fee
        else:
            return notional * self.taker_fee
    
    def calculate_slippage(self,
                          price: float,
                          amount: float,
                          side: str,
                          symbol: str = "BTCUSDT") -> float:
        """Bybitスリッページを計算"""
        slippage_amount = price * (self.slippage_bps / 10000)
        
        if side.lower() == "buy":
            return slippage_amount
        else:
            return -slippage_amount


class FeeModelFactory:
    """手数料モデルファクトリー"""
    
    _models = {
        'binance': BinanceFeeModel,
        'bybit': BybitFeeModel,
    }
    
    @classmethod
    def create(cls, exchange: str) -> FeeModel:
        """指定された取引所の手数料モデルを作成"""
        exchange_lower = exchange.lower()
        
        if exchange_lower not in cls._models:
            raise ValueError(f"Unsupported exchange: {exchange}")
        
        return cls._models[exchange_lower]()
    
    @classmethod
    def get_supported_exchanges(cls) -> list:
        """サポートされている取引所一覧を返す"""
        return list(cls._models.keys())