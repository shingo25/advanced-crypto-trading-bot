"""価格データモデル - Supabase price_data テーブル用"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, Numeric, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


@dataclass
class PriceDataSchema:
    """価格データのスキーマ（データクラス）"""

    exchange: str
    symbol: str
    timeframe: str
    timestamp: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    created_at: Optional[datetime] = None
    id: Optional[int] = None


class PriceData(Base):
    """価格データテーブルのSQLAlchemyモデル"""

    __tablename__ = "price_data"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exchange = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<PriceData(exchange='{self.exchange}', symbol='{self.symbol}', "
            f"timeframe='{self.timeframe}', timestamp='{self.timestamp}', "
            f"close='{self.close_price}')>"
        )

    @classmethod
    def from_ohlcv(cls, exchange: str, symbol: str, timeframe: str, ohlcv_data) -> "PriceData":
        """OHLCV データオブジェクトからPriceDataインスタンスを作成"""
        return cls(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=ohlcv_data.timestamp,
            open_price=Decimal(str(ohlcv_data.open)),
            high_price=Decimal(str(ohlcv_data.high)),
            low_price=Decimal(str(ohlcv_data.low)),
            close_price=Decimal(str(ohlcv_data.close)),
            volume=Decimal(str(ohlcv_data.volume)),
        )

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "open_price": float(self.open_price),
            "high_price": float(self.high_price),
            "low_price": float(self.low_price),
            "close_price": float(self.close_price),
            "volume": float(self.volume),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
